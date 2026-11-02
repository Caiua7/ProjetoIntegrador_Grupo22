import { Icon } from '../../components/icons/Icon'
import { Sigla } from '../../components/Sigla'
import type { ListPreset } from '../pricing/listPreset'
import { AttentionPanel } from './components/AttentionPanel'
import { KpiCard } from './components/KpiCard'
import { MarginChart } from './components/MarginChart'
import { PolicyMeter } from './components/PolicyMeter'
import { RecentPricings } from './components/RecentPricings'
import { StatusOverview } from './components/StatusOverview'
import { indicadores } from './dashboard.data'
import './dashboard.css'

type Props = {
  nome: string
  canCreate: boolean
  onNewPricing: () => void
  onOpenList: (preset?: ListPreset) => void
}

function saudacao(agora = new Date()) {
  const hora = agora.getHours()
  return hora < 12 ? 'Bom dia' : hora < 18 ? 'Boa tarde' : 'Boa noite'
}

function hoje() {
  const texto = new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

export function Dashboard({ nome, canCreate, onNewPricing, onOpenList }: Props) {
  const kpi = indicadores()
  const primeiroNome = nome.split(/\s+/)[0]

  return <section className="content dash">
    <header className="dash-intro">
      <div>
        <span className="dash-data">{hoje()}</span>
        <h2>{saudacao()}, {primeiroNome}</h2>
        <p>Rentabilidade da carteira, o que espera decisão e o que mudou por último. Clique em qualquer número para ver os cenários por trás dele.</p>
      </div>
      {canCreate && <button className="button primary" type="button" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button>}
    </header>

    <div className="dash-kpis">
      <KpiCard titulo={<><Sigla termo="MaCo" /> média do mês</>} indicador={kpi.maco} onAbrir={onOpenList}
        destaque={<PolicyMeter maco={kpi.maco.numero} />} />
      <KpiCard titulo="Cenários no mês" indicador={kpi.cenarios} onAbrir={onOpenList} />
      <KpiCard titulo="Aguardando aprovação" indicador={kpi.aprovacao} onAbrir={onOpenList} />
      <KpiCard titulo={<><Sigla termo="ROB" /> aprovada</>} indicador={kpi.rob} onAbrir={onOpenList} />
    </div>

    <div className="dash-grade">
      <MarginChart />
      <AttentionPanel onAbrir={onOpenList} />
      <StatusOverview onAbrir={onOpenList} />
      <RecentPricings onAbrir={onOpenList} />
    </div>

    <p className="dash-rodape"><span className="notice-dot" />Dados de demonstração: os indicadores passam a ser reais quando o cálculo de precificação estiver integrado.</p>
  </section>
}
