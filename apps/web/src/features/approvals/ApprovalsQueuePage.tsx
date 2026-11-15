import { Fragment, useEffect, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import { Icon } from '../../components/icons/Icon'
import { Modal } from '../../components/modal/Modal'
import { Select } from '../../components/form/Select'
import { compararCenarios, type ComparacaoCenarios } from '../pricing/cenariosService'
import { registrarDecisao, type DecisaoAprovacao } from '../pricing/aprovacoesService'
import { MODALIDADE, rotulo } from '../pricing/rotulos'
import { diasEsperando, percentualDaFracao, podeComparar, pontosPercentuais, type FilaAprovacao, type ItemFila, type OrdemFila, type SituacaoMargem } from './filaAprovacao'
import { consultarFila } from './filaAprovacaoService'
import './approvals.css'

const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const dataCurta = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' })
const formatoMoeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const formatoNumero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const moeda = (valor: string | null) => valor == null || !Number.isFinite(Number(valor)) ? '—' : formatoMoeda.format(Number(valor))
const numero = (valor: string | null) => valor == null || !Number.isFinite(Number(valor)) ? '—' : formatoNumero.format(Number(valor))
const SENTIDO: Record<string, string> = { subiu: 'Subiu', desceu: 'Desceu', igual: 'Sem variação', sem_base: 'Sem base' }

const FILTROS_MARGEM: { valor: SituacaoMargem | 'todas', rotulo: string }[] = [
  { valor: 'todas', rotulo: 'Todas' },
  { valor: 'abaixo_da_politica', rotulo: 'Abaixo da política' },
  { valor: 'dentro_da_politica', rotulo: 'Dentro da política' },
]

function ComparacaoComAnterior({ item }: { item: ItemFila }) {
  const [comparacao, setComparacao] = useState<ComparacaoCenarios | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    compararCenarios(item.precificacao_id, item.versao_anterior!, item.cenario_versao!)
      .then((valor) => { if (ativo) setComparacao(valor) })
      .catch((falha: unknown) => { if (ativo) setErro(falha instanceof ApiError ? falha.message : 'Não foi possível comparar as versões.') })
    return () => { ativo = false }
  }, [item.precificacao_id, item.versao_anterior, item.cenario_versao])

  if (erro) return <p className="catalog-error" role="alert">{erro}</p>
  if (!comparacao) return <p className="np-carregando-linha" role="status"><span className="np-carregando" aria-hidden="true" />Comparando v{item.versao_anterior} com v{item.cenario_versao}…</p>

  const valor = (unidade: string, texto: string | null, variacao = false) =>
    unidade === 'percentual' ? (variacao ? pontosPercentuais(texto) : percentualDaFracao(texto)) : unidade === 'brl' ? moeda(texto) : numero(texto)

  return <div className="table-scroll"><table className="pricing-table fila-comparacao-tabela">
    <caption className="sr-only">Versão proposta comparada com a anterior</caption>
    <thead><tr><th scope="col">Indicador</th><th className="numeric" scope="col">v{comparacao.versao_de} (anterior)</th><th className="numeric" scope="col">v{comparacao.versao_para} (proposta)</th><th className="numeric" scope="col">Variação</th><th className="numeric" scope="col">Variação %</th><th scope="col">Sentido</th></tr></thead>
    <tbody>{comparacao.indicadores.map((indicador) => <tr key={indicador.codigo} className={`fila-sentido-${indicador.sentido}`}>
      <th scope="row">{indicador.rotulo}</th>
      <td className="numeric mono-cell">{valor(indicador.unidade, indicador.valor_de)}</td>
      <td className="numeric mono-cell">{valor(indicador.unidade, indicador.valor_para)}</td>
      <td className="numeric mono-cell">{valor(indicador.unidade, indicador.variacao, true)}</td>
      <td className="numeric mono-cell">{percentualDaFracao(indicador.variacao_percentual)}</td>
      <td>{SENTIDO[indicador.sentido]}</td>
    </tr>)}</tbody>
  </table></div>
}

export function ApprovalsQueuePage() {
  const [clienteId, setClienteId] = useState('')
  const [situacao, setSituacao] = useState<SituacaoMargem | 'todas'>('todas')
  const [ordem, setOrdem] = useState<OrdemFila>('mais_antigas')
  const [fila, setFila] = useState<FilaAprovacao | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)
  const [recarregar, setRecarregar] = useState(0)
  const [aberta, setAberta] = useState<string | null>(null)
  const [decidindo, setDecidindo] = useState<ItemFila | null>(null)
  const [decisao, setDecisao] = useState<DecisaoAprovacao>('aprovado')
  const [comentario, setComentario] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erroDecisao, setErroDecisao] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    consultarFila({ clienteId: clienteId || undefined, situacao: situacao === 'todas' ? undefined : situacao, ordem })
      .then((valor) => { if (ativo) { setFila(valor); setErro(null) } })
      .catch((falha: unknown) => { if (ativo) setErro(falha instanceof ApiError ? falha.message : 'Não foi possível carregar a fila de aprovação.') })
      .finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
  }, [clienteId, situacao, ordem, recarregar])

  function filtrar(atualizar: () => void) {
    setCarregando(true); setMensagem(null); setAberta(null)
    atualizar()
  }

  function abrirDecisao(item: ItemFila) {
    setDecidindo(item); setDecisao(item.homologacao_pendente ? 'reprovado' : 'aprovado'); setComentario(''); setErroDecisao(null)
  }

  async function confirmarDecisao() {
    if (!decidindo || (decisao === 'reprovado' && !comentario.trim())) return
    setSalvando(true); setErroDecisao(null)
    try {
      await registrarDecisao(decidindo.precificacao_id, decisao, comentario)
      setMensagem(`${decidindo.codigo} foi ${decisao === 'aprovado' ? 'aprovada' : 'reprovada'} e saiu da fila.`)
      setDecidindo(null); setAberta(null); setCarregando(true); setRecarregar((n) => n + 1)
    } catch (falha) {
      setErroDecisao(falha instanceof ApiError ? falha.message : 'Não foi possível registrar a decisão.')
    } finally { setSalvando(false) }
  }

  const politica = fila?.politica
  const itens = fila?.itens ?? []
  const opcoesCliente = [{ value: '', label: 'Todos os clientes' }, ...(fila?.clientes ?? []).map((c) => ({ value: c.id, label: c.nome }))]

  return <section className="content list-content approvals-content">
    <div className="list-intro"><div><span className="eyebrow">APROVAÇÕES</span><h2>Fila de aprovação</h2><p>Precificações da sua carteira esperando decisão, das submetidas há mais tempo para as mais recentes.</p></div>
      <div className={`fila-politica${politica ? '' : ' sem-politica'}`} role="note">
        {politica ? <><strong>Política: MaCo mínima {percentualDaFracao(politica.margem_minima)}</strong><small>vigente desde {dataCurta.format(new Date(`${politica.vigencia_inicio}T00:00:00`))}</small></>
          : <><strong>Sem margem mínima cadastrada</strong><small>Cadastre em Câmbio e parâmetros para separar o que está fora da política.</small></>}
      </div>
    </div>
    {erro && <p className="catalog-error" role="alert">{erro}</p>}
    {mensagem && <p className="catalog-success" role="status">{mensagem}</p>}

    <div className="pricing-filters fila-filtros" aria-label="Filtros da fila">
      <div className="status-filters" role="group" aria-label="Filtrar por margem">
        {FILTROS_MARGEM.map((filtro) => <button key={filtro.valor} type="button" className={`filter-chip${situacao === filtro.valor ? ' selected' : ''}`} aria-pressed={situacao === filtro.valor}
          disabled={filtro.valor !== 'todas' && !politica && !carregando} title={filtro.valor !== 'todas' && !politica ? 'Sem margem mínima cadastrada' : undefined}
          onClick={() => filtrar(() => setSituacao(filtro.valor))}>{filtro.rotulo}</button>)}
      </div>
      <label className="field fila-filtro-cliente"><span>Cliente</span><Select compacto value={clienteId} options={opcoesCliente} onChange={(valor) => filtrar(() => setClienteId(valor))} /></label>
      <label className="field fila-filtro-ordem"><span>Ordem</span><Select compacto value={ordem} options={[{ value: 'mais_antigas', label: 'Submetidas há mais tempo' }, { value: 'mais_recentes', label: 'Submetidas mais recentemente' }]} onChange={(valor) => filtrar(() => setOrdem(valor as OrdemFila))} /></label>
    </div>

    <section className="form-card pricing-list-card">
      <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true"><Icon name="aprovacoes" size={16} /></span><h3>Esperando decisão</h3></div>
        <span className="list-scope">{carregando || !fila ? '' : `${itens.length} de ${fila.total_em_aprovacao} em aprovação`}</span></div>
      {carregando && !fila ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando a fila…</div>
        : itens.length === 0 ? <div className="empty-list" role="status"><h3>{fila?.total_em_aprovacao ? 'Nada com estes filtros' : 'Nenhuma precificação esperando decisão'}</h3><p>{fila?.total_em_aprovacao ? 'Troque o filtro de margem ou de cliente.' : 'Quando um analista submeter uma precificação da sua carteira, ela aparece aqui.'}</p></div>
          : <div className="table-scroll" role="region" aria-label="Fila de aprovação" tabIndex={0}>
            <table className="pricing-table fila-tabela"><thead><tr><th scope="col">Código</th><th scope="col">Cliente e produto</th><th scope="col">Submetida</th><th scope="col">Versão</th><th className="numeric" scope="col">Preço bruto</th><th className="numeric" scope="col">MaCo</th><th className="numeric" scope="col">vs. política</th><th scope="col"><span className="sr-only">Ações</span></th></tr></thead>
              <tbody>{itens.map((item) => {
                const expandida = aberta === item.precificacao_id
                const dias = diasEsperando(item.submetido_em)
                return <Fragment key={item.precificacao_id}>
                  <tr className={item.abaixo_da_politica ? 'fila-linha-abaixo' : undefined}>
                    <th scope="row" className="code-cell">{item.codigo}{item.homologacao_pendente && <small className="status-demo">Homologação pendente</small>}</th>
                    <td className="customer-cell">{item.cliente_nome}<span>{item.produto_descricao} · {rotulo(MODALIDADE, item.modalidade_comercial)}</span></td>
                    <td className="updated-cell">{dataHora.format(new Date(item.submetido_em))}<span className="cell-sub">{dias === 0 ? 'hoje' : `há ${dias} ${dias === 1 ? 'dia' : 'dias'}`}{item.submetido_por_nome ? ` · ${item.submetido_por_nome}` : ''}</span></td>
                    <td className="nowrap">{item.cenario_versao ? `v${item.cenario_versao}` : 'Sem cenário'}{item.versao_anterior && <span className="cell-sub-inline"> · anterior v{item.versao_anterior}</span>}</td>
                    <td className="numeric mono-cell">{moeda(item.preco_bruto)}</td>
                    <td className="numeric mono-cell">{percentualDaFracao(item.margem_contribuicao_percentual)}</td>
                    <td className="numeric">{item.distancia_da_politica == null ? <span className="cell-sub">—</span>
                      : <span className={`fila-distancia ${item.abaixo_da_politica ? 'abaixo' : 'dentro'}`}>{pontosPercentuais(item.distancia_da_politica)}</span>}</td>
                    <td className="cell-acoes"><div className="row-actions">
                      <button className="button secondary compacto" type="button" disabled={!podeComparar(item)} aria-expanded={expandida} aria-controls={`comparacao-${item.precificacao_id}`}
                        title={podeComparar(item) ? undefined : 'Esta é a primeira versão do cenário'}
                        onClick={() => setAberta(expandida ? null : item.precificacao_id)}>{expandida ? 'Fechar comparação' : 'Comparar'}</button>
                      <button className="button primary compacto" type="button" onClick={() => abrirDecisao(item)}>Decidir</button>
                    </div></td>
                  </tr>
                  {expandida && <tr className="fila-comparacao" id={`comparacao-${item.precificacao_id}`}><td colSpan={8}>
                    <h4>Proposta v{item.cenario_versao} comparada com a versão anterior v{item.versao_anterior}</h4>
                    <ComparacaoComAnterior item={item} />
                  </td></tr>}
                </Fragment>
              })}</tbody>
            </table></div>}
    </section>

    {decidindo && <Modal titulo={`Decisão de ${decidindo.codigo}`} subtitulo={`${decidindo.cliente_nome} · ${decidindo.produto_descricao}`}
      ocupado={salvando} onFechar={() => setDecidindo(null)}
      rodape={<>
        <button className="button secondary" type="button" disabled={salvando} onClick={() => setDecidindo(null)}>Cancelar</button>
        <button className={`button ${decisao === 'reprovado' ? 'perigo' : 'primary'}`} type="button" disabled={salvando || (decisao === 'reprovado' && !comentario.trim())} onClick={() => { void confirmarDecisao() }}>{salvando ? 'Registrando…' : decisao === 'reprovado' ? 'Reprovar' : 'Aprovar'}</button>
      </>}>
      {decidindo.abaixo_da_politica && <div className="demo-notice"><span className="notice-dot" />A margem da versão proposta ({percentualDaFracao(decidindo.margem_contribuicao_percentual)}) está {pontosPercentuais(decidindo.distancia_da_politica)} da política.</div>}
      {decidindo.homologacao_pendente && <div className="demo-notice"><span className="notice-dot" />Esta precificação foi submetida com a política demonstrativa e aguarda homologação, por isso só pode ser reprovada.</div>}
      <div className="decisao-opcoes" role="radiogroup" aria-label="Decisão">
        <button type="button" role="radio" aria-checked={decisao === 'aprovado'} disabled={decidindo.homologacao_pendente} className={`decisao-opcao aprovar${decisao === 'aprovado' ? ' selecionada' : ''}`} onClick={() => setDecisao('aprovado')}><Icon name="check" size={18} />Aprovar</button>
        <button type="button" role="radio" aria-checked={decisao === 'reprovado'} className={`decisao-opcao reprovar${decisao === 'reprovado' ? ' selecionada' : ''}`} onClick={() => setDecisao('reprovado')}><Icon name="fechar" size={18} />Reprovar</button>
      </div>
      <label className="field"><span>Comentário {decisao === 'reprovado' ? <b aria-hidden="true">*</b> : <small>(opcional)</small>}</span><textarea className="decisao-comentario" maxLength={2000} placeholder={decisao === 'reprovado' ? 'Explique o motivo para o analista corrigir.' : 'Observação para o histórico.'} value={comentario} onChange={(evento) => setComentario(evento.target.value)} /></label>
      {erroDecisao && <p className="catalog-error" role="alert">{erroDecisao}</p>}
    </Modal>}
  </section>
}
