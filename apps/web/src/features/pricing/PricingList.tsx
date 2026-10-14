import { useMemo, useState } from 'react'
import {
  pricingDemoCustomers,
  pricingListDemo,
  pricingStatusCounts,
  pricingStatusLabels,
  type PricingStatus,
} from './pricingList.mock'
import { filterPricingList, type PricingStatusFilter } from './pricingList.filter.ts'

type Props = { onNewPricing: () => void }

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const volume = new Intl.NumberFormat('pt-BR')

const statusClass: Record<PricingStatus, string> = {
  draft: 'status-neutral',
  approval: 'status-review',
  approved: 'status-approved',
  rejected: 'status-rejected',
}

function PricingList({ onNewPricing }: Props) {
  const [status, setStatus] = useState<PricingStatusFilter>('all')
  const [customer, setCustomer] = useState('all')

  const rows = useMemo(() => filterPricingList(pricingListDemo, status, customer), [status, customer])

  return <section className="content list-content">
    <div className="list-intro">
      <div><span className="eyebrow">PRECIFICAÇÃO</span><h2>Precificações</h2><p>Consulte os cenários e acompanhe seus status.</p></div>
      <button className="button primary" type="button" onClick={onNewPricing}><span aria-hidden="true">+</span> Nova</button>
    </div>

    <div className="demo-notice"><span className="notice-dot" />Lista demonstrativa · os registros e indicadores vieram do protótipo e não são dados persistidos.</div>

    <div className="pricing-filters" aria-label="Filtros de precificações">
      <div className="status-filters" role="group" aria-label="Filtrar por status">
        {pricingStatusCounts.map((filter) => <button
          className={`filter-chip${status === filter.id ? ' selected' : ''}`}
          type="button"
          key={filter.id}
          aria-pressed={status === filter.id}
          onClick={() => setStatus(filter.id)}
        >{filter.label}<span>{filter.count}</span></button>)}
      </div>
      <label className="customer-filter"><span className="sr-only">Filtrar por cliente</span>
        <select value={customer} onChange={(event) => setCustomer(event.target.value)}>
          <option value="all">Todos os clientes</option>
          {pricingDemoCustomers.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </label>
    </div>

    <section className="form-card pricing-list-card">
      <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">▤</span><h3>Precificações</h3></div><span className="list-scope">Carteira Sudeste · demonstração</span></div>
      {rows.length > 0 ? <>
        <p className="list-result-count" aria-live="polite">{rows.length} {rows.length === 1 ? 'cenário demonstrativo' : 'cenários demonstrativos'}</p>
        <div className="table-scroll" role="region" aria-label="Resultados da listagem de precificações" tabIndex={0}>
        <table className="pricing-table">
          <caption className="sr-only">Precificações demonstrativas com cliente, modalidade, produto, volume, MaCo, ROB, status e data de atualização</caption>
          <thead><tr>
            <th scope="col">Código</th><th scope="col">Cliente e modalidade</th><th scope="col">Produto</th>
            <th scope="col" className="numeric">Volume</th><th scope="col" className="numeric">MaCo</th>
            <th scope="col" className="numeric">ROB</th><th scope="col">Status</th><th scope="col" className="numeric">Atualizada</th>
          </tr></thead>
          <tbody>{rows.map((item) => <tr key={item.code}>
            <th scope="row" className="code-cell"><span>{item.code}</span><span className="version-tag">v{item.version}</span></th>
            <td className="customer-cell">{item.customer}<span>{item.uf} · {item.modality}</span></td>
            <td className="product-cell">{item.product}<span>NCM {item.ncm}</span></td>
            <td className="numeric mono-cell">{volume.format(item.volume)}</td>
            <td className={`numeric mono-cell margin-cell${item.contributionMarginPercent < 24 ? ' below-policy' : ''}`}>{item.contributionMarginPercent.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%</td>
            <td className="numeric mono-cell">{currency.format(item.grossOperatingRevenue)}</td>
            <td><span className={`status-pill ${statusClass[item.status]}`}><i />{pricingStatusLabels[item.status]}</span></td>
            <td className="numeric updated-cell">{item.updatedAt}</td>
          </tr>)}</tbody>
        </table>
        </div>
      </> : <div className="empty-list" role="status">
        <span className="empty-icon" aria-hidden="true">⌕</span>
        <h3>Nenhuma precificação encontrada</h3>
        <p>Não há registros para a combinação de status e cliente selecionada.</p>
        <button className="button secondary" type="button" onClick={() => { setStatus('all'); setCustomer('all') }}>Limpar filtros</button>
      </div>}
      <p className="list-footnote">MaCo em âmbar indica margem abaixo da política de 24%. Valores ilustrativos copiados do protótipo.</p>
    </section>
  </section>
}

export default PricingList
