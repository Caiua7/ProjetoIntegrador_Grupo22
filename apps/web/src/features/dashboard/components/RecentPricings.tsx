import { Icon } from '../../../components/icons/Icon'
import { Sigla } from '../../../components/Sigla'
import type { ListPreset } from '../../pricing/listPreset'
import { pricingListDemo } from '../../pricing/pricingList.mock'
import { StatusPill } from '../../pricing/StatusPill'
import { POLITICA_MACO, moedaCompacta, percentual } from '../dashboard.data'

/** As últimas precificações movimentadas; a linha inteira abre a lista naquela etapa. */
export function RecentPricings({ onAbrir }: { onAbrir: (preset: ListPreset) => void }) {
  return <section className="dash-card dash-recentes" aria-labelledby="recentes-titulo">
    <header className="dash-card-cabecalho">
      <div>
        <h3 id="recentes-titulo">Movimentadas recentemente</h3>
        <p>As últimas precificações criadas ou alteradas.</p>
      </div>
      <button className="link-acao" type="button" onClick={() => onAbrir({})}>Ver todas <Icon name="seta" size={14} /></button>
    </header>
    <div className="table-scroll">
      <table className="dash-tabela">
        <thead><tr>
          <th scope="col">Precificação</th>
          <th scope="col">Cliente</th>
          <th scope="col" className="numeric"><Sigla termo="MaCo" /></th>
          <th scope="col" className="numeric"><Sigla termo="ROB" /></th>
          <th scope="col">Status</th>
          <th scope="col" className="numeric">Atualizada</th>
        </tr></thead>
        <tbody>{pricingListDemo.slice(0, 5).map((item, i) => <tr key={item.code} className="linha-clicavel" style={{ animationDelay: `${.2 + i * .05}s` }}
          tabIndex={0} aria-label={`Abrir ${item.code} na lista de precificações`}
          onClick={() => onAbrir({ status: item.status })}
          onKeyDown={(e) => { if (e.key === 'Enter') onAbrir({ status: item.status }) }}>
          <th scope="row"><span className="codigo">{item.code}</span><small>{item.product}</small></th>
          <td>{item.customer}<small>{item.modality}</small></td>
          <td className={`numeric valor${item.contributionMarginPercent < POLITICA_MACO ? ' abaixo' : ''}`}>{percentual(item.contributionMarginPercent)}</td>
          <td className="numeric valor">{moedaCompacta(item.grossOperatingRevenue)}</td>
          <td><StatusPill status={item.status} /></td>
          <td className="numeric quando">{item.updatedAt}</td>
        </tr>)}</tbody>
      </table>
    </div>
  </section>
}
