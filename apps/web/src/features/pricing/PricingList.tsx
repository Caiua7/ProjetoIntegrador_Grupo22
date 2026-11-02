import { useMemo, useState } from 'react'
import { Select } from '../../components/form/Select'
import {
  pricingDemoCustomers,
  pricingListDemo,
  pricingStatusCounts,
} from './pricingList.mock'
import { filterPricingList, type PricingStatusFilter } from './pricingList.filter.ts'
import { Icon } from '../../components/icons/Icon'
import { Sigla } from '../../components/Sigla'
import { StatusPill } from './StatusPill'
import type { ListPreset } from './listPreset'

const POLITICA = 24

type Props = { onNewPricing: () => void, preset?: ListPreset }

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
const volume = new Intl.NumberFormat('pt-BR')

function PricingList({ onNewPricing, preset }: Props) {
  const [status, setStatus] = useState<PricingStatusFilter>(preset?.status ?? 'all')
  const [customer, setCustomer] = useState('all')
  const [abaixo, setAbaixo] = useState(preset?.abaixoDaPolitica ?? false)

  const rows = useMemo(() => filterPricingList(pricingListDemo, status, customer)
    .filter((item) => !abaixo || item.contributionMarginPercent < POLITICA), [status, customer, abaixo])

  return <section className="content list-content">
    <div className="list-intro">
      <div><span className="eyebrow">PRECIFICAÇÃO</span><h2>Precificações</h2><p>Cada linha é um estudo de preço para um cliente e produto. Filtre por etapa ou cliente e passe o mouse nas siglas para ver o que significam.</p></div>
      <button className="button primary" type="button" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button>
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
        <button className={`filter-chip aviso${abaixo ? ' selected' : ''}`} type="button" aria-pressed={abaixo}
          title="Mostra só os cenários com margem abaixo da política mínima de 24%" onClick={() => setAbaixo(!abaixo)}>
          Abaixo da política<span>{pricingListDemo.filter((item) => item.contributionMarginPercent < POLITICA).length}</span>
        </button>
      </div>
      <label className="customer-filter"><span className="sr-only">Filtrar por cliente</span>
        <Select value={customer} onChange={setCustomer} ariaLabel="Filtrar por cliente"
          options={[{ value: 'all', label: 'Todos os clientes' }, ...pricingDemoCustomers.map((name) => ({ value: name, label: name }))]} />
      </label>
    </div>

    <section className="form-card pricing-list-card">
      <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true"><Icon name="precificacoes" size={16} /></span><h3>Precificações</h3></div><span className="list-scope">Carteira Sudeste · demonstração</span></div>
      {rows.length > 0 ? <>
        <p className="list-result-count" aria-live="polite">{rows.length} {rows.length === 1 ? 'cenário demonstrativo' : 'cenários demonstrativos'}</p>
        <div className="table-scroll" role="region" aria-label="Resultados da listagem de precificações" tabIndex={0}>
        <table className="pricing-table">
          <caption className="sr-only">Precificações demonstrativas com cliente, modalidade, produto, volume, MaCo, ROB, status e data de atualização</caption>
          <thead><tr>
            <th scope="col">Código</th><th scope="col">Cliente e modalidade</th><th scope="col">Produto</th>
            <th scope="col" className="numeric">Volume</th><th scope="col" className="numeric"><Sigla termo="MaCo" /></th>
            <th scope="col" className="numeric"><Sigla termo="ROB" /></th><th scope="col">Status</th><th scope="col" className="numeric">Atualizada</th>
          </tr></thead>
          <tbody>{rows.map((item) => <tr key={item.code}>
            <th scope="row" className="code-cell"><span>{item.code}</span><span className="version-tag">v{item.version}</span></th>
            <td className="customer-cell">{item.customer}<span>{item.uf} · {item.modality}</span></td>
            <td className="product-cell">{item.product}<span><Sigla termo="NCM" /> {item.ncm}</span></td>
            <td className="numeric mono-cell">{volume.format(item.volume)}</td>
            <td className={`numeric mono-cell margin-cell${item.contributionMarginPercent < 24 ? ' below-policy' : ''}`}>{item.contributionMarginPercent.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%</td>
            <td className="numeric mono-cell">{currency.format(item.grossOperatingRevenue)}</td>
            <td><StatusPill status={item.status} /></td>
            <td className="numeric updated-cell">{item.updatedAt}</td>
          </tr>)}</tbody>
        </table>
        </div>
      </> : <div className="empty-list" role="status">
        <span className="empty-icon" aria-hidden="true"><Icon name="precificacoes" size={20} /></span>
        <h3>Nenhuma precificação encontrada</h3>
        <p>Não há registros para a combinação de status e cliente selecionada.</p>
        <button className="button secondary" type="button" onClick={() => { setStatus('all'); setCustomer('all'); setAbaixo(false) }}>Limpar filtros</button>
      </div>}
      <p className="list-footnote"><Sigla termo="MaCo" /> em âmbar: margem abaixo da <Sigla termo="Política">política mínima de 24%</Sigla>; o cenário precisa de aprovação do gerente. Valores ilustrativos do protótipo.</p>
    </section>
  </section>
}

export default PricingList
