import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import { Icon } from '../../components/icons/Icon'
import { listarPrecificacoes, type Precificacao } from './precificacoesService'
import type { ListPreset } from './listPreset'
import ScenarioHistoryPanel from './ScenarioHistoryPanel'
import { registrarDecisao, type DecisaoAprovacao } from './aprovacoesService'

type Props = { onNewPricing: () => void, preset?: ListPreset, canViewCost: boolean, canEdit: boolean, canApprove: boolean }
const statusLabel: Record<Precificacao['status'], string> = {
  em_preenchimento: 'Em preenchimento', em_aprovacao: 'Em aprovação', aprovado: 'Aprovado', reprovado: 'Reprovado',
}
const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

function PricingList({ onNewPricing, canViewCost, canEdit, canApprove }: Props) {
  const [items, setItems] = useState<Precificacao[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<'all' | Precificacao['status']>('all')
  const [cenarioPrecificacao, setCenarioPrecificacao] = useState<Precificacao | null>(null)
  const [decisaoPrecificacao, setDecisaoPrecificacao] = useState<Precificacao | null>(null)
  const [decisao, setDecisao] = useState<DecisaoAprovacao>('aprovado')
  const [comentario, setComentario] = useState('')
  const [salvandoDecisao, setSalvandoDecisao] = useState(false)
  const [erroDecisao, setErroDecisao] = useState<string | null>(null)

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
      {loading ? <div className="empty-list" role="status">Carregando precificações…</div> : rows.length ? <div className="table-scroll" role="region" aria-label="Precificações persistidas" tabIndex={0}><table className="pricing-table"><thead><tr><th>Código</th><th>Cliente</th><th>Produto</th><th>Modalidade</th><th>Destino</th><th>Frete</th><th>Regime</th><th>Status</th><th>Atualizada</th><th>Cenários</th>{canApprove && <th>Decisão</th>}</tr></thead><tbody>{rows.map((item) => <tr key={item.id}><th scope="row" className="code-cell">{item.codigo}</th><td>{item.cliente?.razao_social ?? item.cliente_id}</td><td>{item.produto?.descricao ?? item.produto_id}</td><td>{item.modalidade_comercial}</td><td>{item.uf_destino ?? '—'}</td><td>{item.frete?.toUpperCase() ?? '—'}</td><td>{item.regime_tributario?.replaceAll('_', ' ') ?? '—'}</td><td>{statusLabel[item.status]}</td><td>{dataHora.format(new Date(item.updated_at))}</td><td><button className="button secondary" type="button" onClick={() => setCenarioPrecificacao(item)} aria-label={`Ver cenários da precificação ${item.codigo}`}>Ver cenários</button></td>{canApprove && <td>{item.status === 'em_aprovacao' && <button className="button secondary" type="button" onClick={() => { setDecisaoPrecificacao(item); setDecisao('aprovado'); setComentario(''); setErroDecisao(null) }}>Decidir</button>}</td>}</tr>)}</tbody></table></div> : <div className="empty-list" role="status"><h3>{items.length ? 'Nenhuma precificação neste status' : 'Nenhuma precificação encontrada'}</h3><p>{items.length ? 'Escolha outro status para consultar os registros.' : 'Crie uma precificação para começar.'}</p><button className="button secondary" type="button" onClick={onNewPricing}>Nova precificação</button></div>}
    </section>
    {cenarioPrecificacao && <ScenarioHistoryPanel key={cenarioPrecificacao.id} precificacaoId={cenarioPrecificacao.id} codigo={cenarioPrecificacao.codigo}
      canViewCost={canViewCost} canEdit={canEdit} onClose={() => setCenarioPrecificacao(null)} />}
    {decisaoPrecificacao && <section className="form-card scenario-detail" aria-label={`Registrar decisão de ${decisaoPrecificacao.codigo}`}>
      <div className="list-card-heading"><h3>Decisão de {decisaoPrecificacao.codigo}</h3><button className="button secondary" type="button" onClick={() => setDecisaoPrecificacao(null)}>Fechar</button></div>
      <label className="field">Decisão<select value={decisao} onChange={(event) => setDecisao(event.target.value as DecisaoAprovacao)}><option value="aprovado">Aprovar</option><option value="reprovado">Reprovar</option></select></label>
      <label className="field">Comentário{decisao === 'reprovado' && ' (obrigatório)'}<textarea maxLength={2000} value={comentario} onChange={(event) => setComentario(event.target.value)} /></label>
      {erroDecisao && <p className="catalog-error" role="alert">{erroDecisao}</p>}
      <button className="button primary" type="button" disabled={salvandoDecisao || (decisao === 'reprovado' && !comentario.trim())} onClick={() => { void salvarDecisao() }}>{salvandoDecisao ? 'Registrando…' : 'Registrar decisão'}</button>
    </section>}
  </section>
}

export default PricingList
