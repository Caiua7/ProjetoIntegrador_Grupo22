import { pricingStatusLabels, type PricingStatus } from './pricingList.mock'
import { statusDescricao } from './status'

const statusClass: Record<PricingStatus, string> = {
  draft: 'status-neutral',
  approval: 'status-review',
  approved: 'status-approved',
  rejected: 'status-rejected',
}

export function StatusPill({ status }: { status: PricingStatus }) {
  return <span className={`status-pill ${statusClass[status]}`} title={statusDescricao[status]}>
    <i aria-hidden="true" />{pricingStatusLabels[status]}
  </span>
}
