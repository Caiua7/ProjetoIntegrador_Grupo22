import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import { Icon } from '../../components/icons/Icon'
import { listarPrecificacoes, listarHistoricoStatus, submeterPrecificacao, verificarSubmissao, type Precificacao, type VerificacaoSubmissao } from './precificacoesService'
import type { ListPreset } from './listPreset'
import ScenarioHistoryPanel from './ScenarioHistoryPanel'
import { listarDecisoesAprovacao, registrarDecisao, type DecisaoAprovacao } from './aprovacoesService'
import { Modal } from '../../components/modal/Modal'
import { CAMPO, FRETE, MODALIDADE, REGIME, rotulo, rotuloCampo } from './rotulos'
import { combinarHistoricoWorkflow, type WorkflowEvent, type WorkflowStatus } from './workflowHistory'

type Props = { onNewPricing: () => void, preset?: ListPreset, canViewCost: boolean, canEdit: boolean, canApprove: boolean,
  canReadCatalog: boolean, canReadCambio: boolean, canReadParametros: boolean, canReadImpostos: boolean }
const statusLabel: Record<Precificacao['status'], string> = {
  em_preenchimento: 'Em preenchimento', em_aprovacao: 'Em aprovação', aprovado: 'Aprovado', reprovado: 'Reprovado',
}
const statusClasse: Record<Precificacao['status'], string> = {
  em_preenchimento: 'status-neutral', em_aprovacao: 'status-review', aprovado: 'status-approved', reprovado: 'status-rejected',
}
const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

function PricingList({ onNewPricing, preset, canViewCost, canEdit, canApprove, canReadCatalog, canReadCambio, canReadParametros, canReadImpostos }: Props) {
  const [items, setItems] = useState<Precificacao[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const statusPreset: Record<string, 'all' | Precificacao['status']> = {
    all: 'all', draft: 'em_preenchimento', approval: 'em_aprovacao', approved: 'aprovado', rejected: 'reprovado',
    em_preenchimento: 'em_preenchimento', em_aprovacao: 'em_aprovacao', aprovado: 'aprovado', reprovado: 'reprovado',
  }
  const [status, setStatus] = useState<'all' | Precificacao['status']>(statusPreset[preset?.status ?? 'all'] ?? 'all')
  const [cenarioPrecificacao, setCenarioPrecificacao] = useState<Precificacao | null>(null)
  const [decisaoPrecificacao, setDecisaoPrecificacao] = useState<Precificacao | null>(null)
  const [decisao, setDecisao] = useState<DecisaoAprovacao>('aprovado')
  const [comentario, setComentario] = useState('')
  const [salvandoDecisao, setSalvandoDecisao] = useState(false)
  const [erroDecisao, setErroDecisao] = useState<string | null>(null)
  const [submissaoPrecificacao, setSubmissaoPrecificacao] = useState<Precificacao | null>(null)
  const [verificacaoSubmissao, setVerificacaoSubmissao] = useState<VerificacaoSubmissao | null>(null)
  const [historicoStatus, setHistoricoStatus] = useState<WorkflowEvent[]>([])
  const [carregandoSubmissao, setCarregandoSubmissao] = useState(false)
  const [erroSubmissao, setErroSubmissao] = useState<string | null>(null)
  const [confirmandoSubmissao, setConfirmandoSubmissao] = useState(false)
  const [mensagemSubmissao, setMensagemSubmissao] = useState<string | null>(null)
  const [historicoPrecificacao, setHistoricoPrecificacao] = useState<Precificacao | null>(null)
  const [eventosHistorico, setEventosHistorico] = useState<WorkflowEvent[]>([])
  const [carregandoHistorico, setCarregandoHistorico] = useState(false)
  const [erroHistorico, setErroHistorico] = useState<string | null>(null)

  async function carregarHistorico(id: string) {
    const [submissoes, decisoes] = await Promise.all([
      listarHistoricoStatus(id),
      listarDecisoesAprovacao(id),
    ])
    return combinarHistoricoWorkflow(submissoes.map((item) => ({ ...item,
      status_anterior: item.status_anterior as WorkflowStatus,
      status_novo: item.status_novo as WorkflowStatus,
    })), decisoes)
  }

  async function abrirHistorico(item: Precificacao) {
    setHistoricoPrecificacao(item); setEventosHistorico([]); setErroHistorico(null); setCarregandoHistorico(true)
    try { setEventosHistorico(await carregarHistorico(item.id)) }
    catch (falha) { setErroHistorico(falha instanceof ApiError ? falha.message : 'Não foi possível carregar o histórico de status.') }
    finally { setCarregandoHistorico(false) }
  }

  async function abrirSubmissao(item: Precificacao) {
    setSubmissaoPrecificacao(item); setVerificacaoSubmissao(null); setErroSubmissao(null); setMensagemSubmissao(null); setConfirmandoSubmissao(false); setCarregandoSubmissao(true)
    try {
      const [verificacao, historico] = await Promise.all([verificarSubmissao(item.id), carregarHistorico(item.id)])
      setVerificacaoSubmissao(verificacao); setHistoricoStatus(historico)
    } catch (falha) { setErroSubmissao(falha instanceof ApiError ? falha.message : 'Não foi possível verificar os requisitos de submissão.') }
    finally { setCarregandoSubmissao(false) }
  }

  async function submeter() {
    if (!submissaoPrecificacao) return
    setCarregandoSubmissao(true); setErroSubmissao(null)
    try {
      await submeterPrecificacao(submissaoPrecificacao.id)
      setSubmissaoPrecificacao(null); setVerificacaoSubmissao(null); setConfirmandoSubmissao(false)
      setMensagemSubmissao(`${submissaoPrecificacao.codigo} foi submetida para aprovação.`)
      try { setItems(await listarPrecificacoes()) }
      catch (falha) { setError(falha instanceof ApiError ? `Submetida, mas não foi possível atualizar a lista: ${falha.message}` : 'Submetida, mas não foi possível atualizar a lista.') }
    } catch (falha) { setErroSubmissao(falha instanceof ApiError ? falha.message : 'Não foi possível submeter a precificação.') }
    finally { setCarregandoSubmissao(false) }
  }

  async function salvarDecisao() {
    if (!decisaoPrecificacao || (decisao === 'reprovado' && !comentario.trim())) return
    setSalvandoDecisao(true); setErroDecisao(null)
    try {
      await registrarDecisao(decisaoPrecificacao.id, decisao, comentario)
      setDecisaoPrecificacao(null); setComentario('')
      try { setItems(await listarPrecificacoes()) }
      catch (falha) { setError(falha instanceof ApiError ? falha.message : 'Decisão registrada, mas não foi possível atualizar a lista.') }
    } catch (falha) { setErroDecisao(falha instanceof ApiError ? falha.message : 'Não foi possível registrar a decisão.') }
    finally { setSalvandoDecisao(false) }
  }
  useEffect(() => {
    let ativo = true
    listarPrecificacoes().then((lista) => { if (ativo) setItems(lista) })
      .catch((falha: unknown) => { if (ativo) setError(falha instanceof ApiError ? falha.message : 'Não foi possível carregar as precificações.') })
      .finally(() => { if (ativo) setLoading(false) })
    return () => { ativo = false }
  }, [])
  const rows = useMemo(() => items.filter((item) => status === 'all' || item.status === status), [items, status])

  const linhaTempo = (eventos: WorkflowEvent[]) => eventos.length
    ? <ol className="workflow-timeline">{eventos.map((item) => <li key={item.id}>
        <strong>{statusLabel[item.status_anterior]} → {statusLabel[item.status_novo]}</strong>
        <span>{item.origem === 'submissao' ? (item.modo === 'demonstracao' ? 'Submissão demonstrativa' : 'Submissão para aprovação') : `Decisão de ${item.responsavel_nome ?? 'aprovador'}`}{item.comentario ? ` · “${item.comentario}”` : ''}</span>
        <time dateTime={item.ocorrido_em}>{dataHora.format(new Date(item.ocorrido_em))}</time>
      </li>)}</ol>
    : <p className="field-hint">Nenhuma mudança de status registrada ainda.</p>

  const contagem = (valor: 'all' | Precificacao['status']) => loading ? '–' : valor === 'all' ? items.length : items.filter((item) => item.status === valor).length

  return <section className="content list-content">
    <div className="list-intro"><div><span className="eyebrow">PRECIFICAÇÃO</span><h2>Precificações</h2><p>Estudos de preço da sua carteira, com status e cenários.</p></div>{canEdit && <button className="button primary" type="button" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button>}</div>
    {error && <p className="catalog-error" role="alert">{error}</p>}
    {mensagemSubmissao && <p className="catalog-success" role="status">{mensagemSubmissao}</p>}
    <div className="pricing-filters" aria-label="Filtros de precificações"><div className="status-filters" role="group" aria-label="Filtrar por status">
      {(['all', 'em_preenchimento', 'em_aprovacao', 'aprovado', 'reprovado'] as const).map((value) => <button key={value} className={`filter-chip${status === value ? ' selected' : ''}`} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>{value === 'all' ? 'Todas' : statusLabel[value]}<span>{contagem(value)}</span></button>)}
    </div></div>
    <section className="form-card pricing-list-card"><div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true"><Icon name="precificacoes" size={16} /></span><h3>Precificações</h3></div><span className="list-scope">{loading ? '' : `${rows.length} ${rows.length === 1 ? 'registro' : 'registros'}`}</span></div>
      {loading ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando precificações…</div> : rows.length ? <div className="table-scroll" role="region" aria-label="Precificações" tabIndex={0}>
        <table className="pricing-table pricing-main-table"><thead><tr><th>Código</th><th>Cliente e produto</th><th>Modalidade</th><th>Destino</th><th>Regime</th><th>Status</th><th>Atualizada</th><th><span className="sr-only">Ações</span></th></tr></thead>
        <tbody>{rows.map((item) => <tr key={item.id}>
          <th scope="row" className="code-cell">{item.codigo}</th>
          <td className="customer-cell">{item.cliente?.razao_social ?? '—'}<span>{item.produto?.descricao ?? '—'}</span></td>
          <td>{rotulo(MODALIDADE, item.modalidade_comercial)}</td>
          <td className="nowrap">{item.uf_destino ?? '—'}{item.frete && <span className="cell-sub-inline"> · {rotulo(FRETE, item.frete)}</span>}</td>
          <td className="nowrap">{rotulo(REGIME, item.regime_tributario)}</td>
          <td><span className={`status-pill ${statusClasse[item.status]}`}><i />{statusLabel[item.status]}</span>{item.homologacao_pendente && <small className="status-demo">Homologação pendente</small>}</td>
          <td className="updated-cell">{dataHora.format(new Date(item.updated_at))}</td>
          <td className="cell-acoes"><div className="row-actions">
            <button className="button secondary compacto" type="button" onClick={() => setCenarioPrecificacao(item)} aria-label={`Cenários de ${item.codigo}`}>Cenários</button>
            <button className="button secondary compacto" type="button" onClick={() => { void abrirHistorico(item) }} aria-label={`Histórico de ${item.codigo}`}>Histórico</button>
            {canEdit && ['em_preenchimento', 'reprovado'].includes(item.status) && <button className="button primary compacto" type="button" onClick={() => { void abrirSubmissao(item) }}>Submeter</button>}
            {canApprove && item.status === 'em_aprovacao' && <button className="button primary compacto" type="button" onClick={() => { setDecisaoPrecificacao(item); setDecisao(item.homologacao_pendente ? 'reprovado' : 'aprovado'); setComentario(''); setErroDecisao(null) }}>Decidir</button>}
          </div></td>
        </tr>)}</tbody></table></div>
        : <div className="empty-list" role="status"><h3>{items.length ? 'Nenhuma precificação neste status' : 'Nenhuma precificação encontrada'}</h3><p>{items.length ? 'Escolha outro status para consultar os registros.' : 'Crie uma precificação para começar.'}</p>{canEdit && <button className="button secondary" type="button" onClick={onNewPricing}>Nova precificação</button>}</div>}
    </section>

    {submissaoPrecificacao && <Modal titulo={`Submeter ${submissaoPrecificacao.codigo} para aprovação`} subtitulo={`${submissaoPrecificacao.cliente?.razao_social ?? ''} · ${submissaoPrecificacao.produto?.descricao ?? ''}`}
      ocupado={carregandoSubmissao && confirmandoSubmissao} onFechar={() => setSubmissaoPrecificacao(null)}
      rodape={<>
        <button className="button secondary" type="button" disabled={carregandoSubmissao && confirmandoSubmissao} onClick={() => (confirmandoSubmissao ? setConfirmandoSubmissao(false) : setSubmissaoPrecificacao(null))}>{confirmandoSubmissao ? 'Voltar' : 'Fechar'}</button>
        {verificacaoSubmissao?.pode_submeter && (confirmandoSubmissao
          ? <button className="button primary" type="button" disabled={carregandoSubmissao} onClick={() => { void submeter() }}>{carregandoSubmissao ? 'Submetendo…' : 'Confirmar submissão'}</button>
          : <button className="button primary" type="button" disabled={carregandoSubmissao} onClick={() => setConfirmandoSubmissao(true)}>Submeter</button>)}
      </>}>
      {carregandoSubmissao && !verificacaoSubmissao && <p className="np-carregando-linha" role="status"><span className="np-carregando" aria-hidden="true" />Conferindo os requisitos…</p>}
      {erroSubmissao && <p className="catalog-error" role="alert">{erroSubmissao}</p>}
      {verificacaoSubmissao && <>
        {verificacaoSubmissao.modo_politica === 'demonstracao' && <div className="demo-notice"><span className="notice-dot" />A política de aprovação ainda é demonstrativa. Se submeter, a precificação fica marcada com homologação pendente e não poderá ser aprovada.</div>}
        {verificacaoSubmissao.motivos_bloqueio.length > 0
          ? <div className="np-pendencias" role="status"><strong>Antes de submeter, resolva:</strong><ul>{verificacaoSubmissao.motivos_bloqueio.map((motivo) => <li key={motivo}>{CAMPO[motivo] ? `Preencha ${rotuloCampo(motivo)} no cabeçalho.` : motivo}</li>)}</ul></div>
          : <p className="catalog-success" role="status">Tudo certo: os campos obrigatórios estão preenchidos e há um cenário calculado salvo.</p>}
        {confirmandoSubmissao && <p className="np-confirma-texto">A precificação passa para <strong>Em aprovação</strong> e não poderá ser editada até a decisão.</p>}
      </>}
      <h4 className="np-secao">Histórico de status</h4>
      {linhaTempo(historicoStatus)}
    </Modal>}

    {historicoPrecificacao && <Modal titulo={`Histórico de ${historicoPrecificacao.codigo}`} subtitulo={`${historicoPrecificacao.cliente?.razao_social ?? ''} · ${historicoPrecificacao.produto?.descricao ?? ''}`} onFechar={() => setHistoricoPrecificacao(null)}>
      {carregandoHistorico && <p className="np-carregando-linha" role="status"><span className="np-carregando" aria-hidden="true" />Carregando submissões e decisões…</p>}
      {erroHistorico && <p className="catalog-error" role="alert">{erroHistorico}</p>}
      {!carregandoHistorico && !erroHistorico && linhaTempo(eventosHistorico)}
    </Modal>}

    {cenarioPrecificacao && <ScenarioHistoryPanel key={cenarioPrecificacao.id} precificacaoId={cenarioPrecificacao.id} codigo={cenarioPrecificacao.codigo} precificacao={cenarioPrecificacao}
      canViewCost={canViewCost} canEdit={canEdit} canReadCatalog={canReadCatalog} canReadCambio={canReadCambio} canReadParametros={canReadParametros} canReadImpostos={canReadImpostos}
      onClose={() => setCenarioPrecificacao(null)} />}

    {decisaoPrecificacao && <Modal titulo={`Decisão de ${decisaoPrecificacao.codigo}`} subtitulo={`${decisaoPrecificacao.cliente?.razao_social ?? ''} · ${decisaoPrecificacao.produto?.descricao ?? ''}`}
      ocupado={salvandoDecisao} onFechar={() => setDecisaoPrecificacao(null)}
      rodape={<>
        <button className="button secondary" type="button" disabled={salvandoDecisao} onClick={() => setDecisaoPrecificacao(null)}>Cancelar</button>
        <button className={`button ${decisao === 'reprovado' ? 'perigo' : 'primary'}`} type="button" disabled={salvandoDecisao || (decisao === 'reprovado' && !comentario.trim())} onClick={() => { void salvarDecisao() }}>{salvandoDecisao ? 'Registrando…' : decisao === 'reprovado' ? 'Reprovar' : 'Aprovar'}</button>
      </>}>
      {decisaoPrecificacao.homologacao_pendente && <div className="demo-notice"><span className="notice-dot" />Esta precificação foi submetida com a política demonstrativa e aguarda homologação, por isso só pode ser reprovada.</div>}
      <div className="decisao-opcoes" role="radiogroup" aria-label="Decisão">
        <button type="button" role="radio" aria-checked={decisao === 'aprovado'} disabled={decisaoPrecificacao.homologacao_pendente} className={`decisao-opcao aprovar${decisao === 'aprovado' ? ' selecionada' : ''}`} onClick={() => setDecisao('aprovado')}><Icon name="check" size={18} />Aprovar</button>
        <button type="button" role="radio" aria-checked={decisao === 'reprovado'} className={`decisao-opcao reprovar${decisao === 'reprovado' ? ' selecionada' : ''}`} onClick={() => setDecisao('reprovado')}><Icon name="fechar" size={18} />Reprovar</button>
      </div>
      <label className="field"><span>Comentário {decisao === 'reprovado' ? <b aria-hidden="true">*</b> : <small>(opcional)</small>}</span><textarea className="decisao-comentario" maxLength={2000} placeholder={decisao === 'reprovado' ? 'Explique o motivo para o analista corrigir.' : 'Observação para o histórico.'} value={comentario} onChange={(event) => setComentario(event.target.value)} /></label>
      {erroDecisao && <p className="catalog-error" role="alert">{erroDecisao}</p>}
    </Modal>}
  </section>
}

export default PricingList
