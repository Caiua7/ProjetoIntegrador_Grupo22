import { Icon } from '../../../components/icons/Icon'
import type { ListPreset } from '../../pricing/listPreset'
import { pricingStatusLabels, type PricingStatus } from '../../pricing/pricingList.mock'
import { statusDescricao } from '../../pricing/status'
import { porStatus } from '../dashboard.data'

const ORDEM: PricingStatus[] = ['draft', 'approval', 'approved', 'rejected']

/** Em que etapa do fluxo estão os cenários: preenchimento → aprovação → aprovado/reprovado. */
export function StatusOverview({ onAbrir }: { onAbrir: (preset: ListPreset) => void }) {
  const contagem = porStatus()
  const total = ORDEM.reduce((soma, s) => soma + contagem[s], 0)

  return <section className="dash-card dash-status" aria-labelledby="status-titulo">
    <header className="dash-card-cabecalho">
      <div>
        <h3 id="status-titulo">Cenários por etapa</h3>
        <p>Onde está cada um dos {total} cenários da carteira.</p>
      </div>
    </header>
    <div className="status-barra" role="img" aria-label={ORDEM.map((s) => `${pricingStatusLabels[s]}: ${contagem[s]}`).join(', ')}>
      {ORDEM.filter((s) => contagem[s] > 0).map((s, i) => <span key={s} className={`status-segmento ${s}`}
        style={{ flexGrow: contagem[s], animationDelay: `${.2 + i * .08}s` }} />)}
    </div>
    <ul className="status-lista">
      {ORDEM.map((s) => <li key={s}>
        <button type="button" className="status-item" onClick={() => onAbrir({ status: s })}>
          <i className={`status-ponto ${s}`} aria-hidden="true" />
          <span className="status-texto"><strong>{pricingStatusLabels[s]}</strong><small>{statusDescricao[s]}</small></span>
          <span className="status-numero">{contagem[s]}</span>
          <Icon name="seta" size={14} className="pendencia-seta" />
        </button>
      </li>)}
    </ul>
  </section>
}
