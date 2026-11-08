import { useEffect, useState } from 'react'
import { Icon } from '../../components/icons/Icon'
import { ApiError } from '../../services/apiClient'
import { listarPrecificacoes, type Precificacao } from '../pricing/precificacoesService'
import type { ListPreset } from '../pricing/listPreset'
import './dashboard.css'

type Props = {
  nome: string
  canCreate: boolean
  onNewPricing: () => void
  onOpenList: (preset?: ListPreset) => void
}

const statusLabel: Record<Precificacao['status'], string> = {
  em_preenchimento: 'Em preenchimento',
  em_aprovacao: 'Em aprovação',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
}
const statusOrder: Precificacao['status'][] = ['em_preenchimento', 'em_aprovacao', 'aprovado', 'reprovado']
const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

function saudacao(agora = new Date()) {
  const hora = agora.getHours()
  return hora < 12 ? 'Bom dia' : hora < 18 ? 'Boa tarde' : 'Boa noite'
}

function hoje() {
  const texto = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

export function Dashboard({ nome, canCreate, onNewPricing, onOpenList }: Props) {
  const [items, setItems] = useState<Precificacao[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const primeiroNome = nome.split(/\s+/)[0]

  useEffect(() => {
    let vigente = true
    listarPrecificacoes().then((lista) => { if (vigente) setItems(lista) })
      .catch((falha: unknown) => {
        if (vigente) setErro(falha instanceof ApiError ? falha.message : 'Não foi possível carregar os dados da carteira.')
      }).finally(() => { if (vigente) setCarregando(false) })
    return () => { vigente = false }
  }, [])

  const contagem = Object.fromEntries(statusOrder.map((status) => [status, items.filter((item) => item.status === status).length])) as Record<Precificacao['status'], number>

  return <section className="content dash">
    <header className="dash-intro">
      <div>
        <span className="dash-data">{hoje()}</span>
        <h2>{saudacao()}, {primeiroNome}</h2>
        <p>Resumo das precificações persistidas na sua carteira.</p>
      </div>
      {canCreate && <button className="button primary" type="button" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button>}
    </header>

    {erro && <p className="catalog-error" role="alert">{erro}</p>}
    {carregando ? <p role="status">Carregando precificações…</p> : <>
      <div className="dash-real-kpis" aria-label="Contagem real de precificações">
        {statusOrder.map((status) => <button className="dash-real-card" key={status} type="button" onClick={() => onOpenList({ status })}>
          <span>{statusLabel[status]}</span><strong>{contagem[status]}</strong>
        </button>)}
      </div>
      <section className="form-card dash-real-list">
        <div className="list-card-heading"><div><h3>Precificações atualizadas recentemente</h3><p>Dados retornados pela API.</p></div>
          <button className="link-acao" type="button" onClick={() => onOpenList({})}>Ver todas <Icon name="seta" size={14} /></button>
        </div>
        {items.length === 0 ? <div className="empty-list"><h3>Nenhuma precificação encontrada</h3><p>Quando houver registros na sua carteira, eles aparecerão aqui.</p></div> :
          <div className="table-scroll"><table className="pricing-table"><thead><tr><th>Código</th><th>Cliente</th><th>Produto</th><th>Status</th><th>Atualizada</th></tr></thead><tbody>
            {items.slice(0, 8).map((item) => <tr key={item.id}>
              <th scope="row" className="code-cell">{item.codigo}</th><td>{item.cliente?.razao_social ?? item.cliente_id}</td>
              <td>{item.produto?.descricao ?? item.produto_id}</td><td>{statusLabel[item.status]}</td>
              <td>{dataHora.format(new Date(item.updated_at))}</td>
            </tr>)}
          </tbody></table></div>}
      </section>
    </>}
  </section>
}
