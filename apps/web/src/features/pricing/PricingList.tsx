import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import { Icon } from '../../components/icons/Icon'
import { listarPrecificacoes, listarHistoricoStatus, submeterPrecificacao, verificarSubmissao, type HistoricoStatus, type Precificacao, type VerificacaoSubmissao } from './precificacoesService'
import type { ListPreset } from './listPreset'
import ScenarioHistoryPanel from './ScenarioHistoryPanel'
import { registrarDecisao, type DecisaoAprovacao } from './aprovacoesService'

type Props = { onNewPricing: () => void, preset?: ListPreset, canViewCost: boolean, canEdit: boolean, canApprove: boolean,
  canReadCatalog: boolean, canReadCambio: boolean, canReadParametros: boolean, canReadImpostos: boolean }
const statusLabel: Record<Precificacao['status'], string> = {
  em_preenchimento: 'Em preenchimento', em_aprovacao: 'Em aprovação', aprovado: 'Aprovado', reprovado: 'Reprovado',
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
  const [historicoStatus, setHistoricoStatus] = useState<HistoricoStatus[]>([])
  const [carregandoSubmissao, setCarregandoSubmissao] = useState(false)
  const [erroSubmissao, setErroSubmissao] = useState<string | null>(null)

  async function abrirSubmissao(item: Precificacao) {
    setSubmissaoPrecificacao(item); setVerificacaoSubmissao(null); setErroSubmissao(null); setCarregandoSubmissao(true)
    try {
      const [verificacao, historico] = await Promise.all([verificarSubmissao(item.id), listarHistoricoStatus(item.id)])
      setVerificacaoSubmissao(verificacao); setHistoricoStatus(historico)
    } catch (falha) { setErroSubmissao(falha instanceof ApiError ? falha.message : 'Não foi possível verificar os requisitos de submissão.') }
    finally { setCarregandoSubmissao(false) }
  }

  async function submeter() {
    if (!submissaoPrecificacao) return
    setCarregandoSubmissao(true); setErroSubmissao(null)
    try {
      await submeterPrecificacao(submissaoPrecificacao.id)
      setSubmissaoPrecificacao(null); setVerificacaoSubmissao(null)
      setItems(await listarPrecificacoes())
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

  return <section className="content list-content">
    <div className="list-intro"><div><span className="eyebrow">PRECIFICAÇÃO</span><h2>Precificações</h2><p>Registros persistidos com acesso limitado pelas permissões e carteira do usuário.</p></div><button className="button primary" type="button" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button></div>
    {error && <p className="catalog-error" role="alert">{error}</p>}
    <div className="pricing-filters" aria-label="Filtros de precificações"><div className="status-filters" role="group" aria-label="Filtrar por status">
      {(['all', 'em_preenchimento', 'em_aprovacao', 'aprovado', 'reprovado'] as const).map((value) => <button key={value} className={`filter-chip${status === value ? ' selected' : ''}`} type="button" aria-pressed={status === value} onClick={() => setStatus(value)}>{value === 'all' ? 'Todas' : statusLabel[value]}<span>{value === 'all' ? items.length : items.filter((item) => item.status === value).length}</span></button>)}
    </div></div>
    <section className="form-card pricing-list-card"><div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true"><Icon name="precificacoes" size={16} /></span><h3>Precificações</h3></div><span className="list-scope">Dados da API</span></div>
      {loading ? <div className="empty-list" role="status">Carregando precificações…</div> : rows.length ? <div className="table-scroll" role="region" aria-label="Precificações persistidas" tabIndex={0}><table className="pricing-table"><thead><tr><th>Código</th><th>Cliente</th><th>Produto</th><th>Modalidade</th><th>Destino</th><th>Frete</th><th>Regime</th><th>Status</th><th>Atualizada</th><th>Cenários</th>{(canApprove || canEdit) && <th>Ações</th>}</tr></thead><tbody>{rows.map((item) => <tr key={item.id}><th scope="row" className="code-cell">{item.codigo}</th><td>{item.cliente?.razao_social ?? item.cliente_id}</td><td>{item.produto?.descricao ?? item.produto_id}</td><td>{item.modalidade_comercial}</td><td>{item.uf_destino ?? '—'}</td><td>{item.frete?.toUpperCase() ?? '—'}</td><td>{item.regime_tributario?.replaceAll('_', ' ') ?? '—'}</td><td>{statusLabel[item.status]}{item.homologacao_pendente && <small className="status-demo"> · demonstração; homologação pendente</small>}</td><td>{dataHora.format(new Date(item.updated_at))}</td><td><button className="button secondary" type="button" onClick={() => setCenarioPrecificacao(item)} aria-label={`Ver cenários da precificação ${item.codigo}`}>Ver cenários</button></td>{(canApprove || canEdit) && <td>{canEdit && ['em_preenchimento', 'reprovado'].includes(item.status) && <button className="button secondary" type="button" onClick={() => { void abrirSubmissao(item) }}>Verificar e submeter</button>}{canApprove && item.status === 'em_aprovacao' && <button className="button secondary" type="button" onClick={() => { setDecisaoPrecificacao(item); setDecisao(item.homologacao_pendente ? 'reprovado' : 'aprovado'); setComentario(''); setErroDecisao(null) }}>Decidir</button>}</td>}</tr>)}</tbody></table></div> : <div className="empty-list" role="status"><h3>{items.length ? 'Nenhuma precificação neste status' : 'Nenhuma precificação encontrada'}</h3><p>{items.length ? 'Escolha outro status para consultar os registros.' : 'Crie uma precificação para começar.'}</p><button className="button secondary" type="button" onClick={onNewPricing}>Nova precificação</button></div>}
    </section>
    {submissaoPrecificacao && <section className="form-card scenario-detail" aria-label={`Submissão de ${submissaoPrecificacao.codigo}`}>
      <div className="list-card-heading"><h3>Submeter {submissaoPrecificacao.codigo} para aprovação</h3><button className="button secondary" type="button" onClick={() => setSubmissaoPrecificacao(null)}>Fechar</button></div>
      {carregandoSubmissao && <p role="status">Verificando os requisitos…</p>}
      {erroSubmissao && <p className="catalog-error" role="alert">{erroSubmissao}</p>}
      {verificacaoSubmissao && <>
        {verificacaoSubmissao.modo_politica === 'demonstracao' && <p className="catalog-error" role="status"><strong>Política demonstrativa, não homologada pelo PO.</strong> Se submeter, a precificação ficará identificada com homologação pendente e não poderá ser aprovada como real.</p>}
        {verificacaoSubmissao.motivos_bloqueio.length > 0 ? <div className="catalog-error" role="status"><strong>Corrija estes itens antes de submeter:</strong><ul>{verificacaoSubmissao.motivos_bloqueio.map((motivo) => <li key={motivo}>{motivo}</li>)}</ul></div> : <p className="catalog-success" role="status">Critérios configurados atendidos. O backend confirmou um cenário real vigente.</p>}
        <p className="field-hint">Campos obrigatórios configurados: {verificacaoSubmissao.campos_obrigatorios.join(', ')}.</p>
        {verificacaoSubmissao.pode_submeter && <button className="button primary" type="button" disabled={carregandoSubmissao} onClick={() => { void submeter() }}>Submeter para aprovação</button>}
      </>}
      <h4>Histórico de status</h4>
      {historicoStatus.length ? <ol>{historicoStatus.map((item) => <li key={item.id}>{statusLabel[item.status_anterior as Precificacao['status']]} → {statusLabel[item.status_novo as Precificacao['status']]} · {item.modo === 'demonstracao' ? 'política demo' : 'política homologada'} · {dataHora.format(new Date(item.ocorrido_em))}</li>)}</ol> : <p className="field-hint">Ainda não há transições registradas.</p>}
    </section>}
    {cenarioPrecificacao && <ScenarioHistoryPanel key={cenarioPrecificacao.id} precificacaoId={cenarioPrecificacao.id} codigo={cenarioPrecificacao.codigo} precificacao={cenarioPrecificacao}
      canViewCost={canViewCost} canEdit={canEdit} canReadCatalog={canReadCatalog} canReadCambio={canReadCambio} canReadParametros={canReadParametros} canReadImpostos={canReadImpostos}
      onClose={() => setCenarioPrecificacao(null)} />}
    {decisaoPrecificacao && <section className="form-card scenario-detail" aria-label={`Registrar decisão de ${decisaoPrecificacao.codigo}`}>
      <div className="list-card-heading"><h3>Decisão de {decisaoPrecificacao.codigo}</h3><button className="button secondary" type="button" onClick={() => setDecisaoPrecificacao(null)}>Fechar</button></div>
      {decisaoPrecificacao.homologacao_pendente && <p className="catalog-error" role="status">Demonstração: esta precificação aguarda homologação e só pode ser reprovada. O backend também bloqueia qualquer tentativa de aprová-la.</p>}
      <label className="field">Decisão<select value={decisao} onChange={(event) => setDecisao(event.target.value as DecisaoAprovacao)}><option value="aprovado" disabled={decisaoPrecificacao.homologacao_pendente}>Aprovar</option><option value="reprovado">Reprovar</option></select></label>
      <label className="field">Comentário{decisao === 'reprovado' && ' (obrigatório)'}<textarea maxLength={2000} value={comentario} onChange={(event) => setComentario(event.target.value)} /></label>
      {erroDecisao && <p className="catalog-error" role="alert">{erroDecisao}</p>}
      <button className="button primary" type="button" disabled={salvandoDecisao || (decisao === 'reprovado' && !comentario.trim())} onClick={() => { void salvarDecisao() }}>{salvandoDecisao ? 'Registrando…' : 'Registrar decisão'}</button>
    </section>}
  </section>
}

export default PricingList
