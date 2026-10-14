import type { PricingListItem, PricingStatus } from './pricingList.mock.ts'

export type PricingStatusFilter = PricingStatus | 'all'

export function filterPricingList<T extends Pick<PricingListItem, 'customer' | 'status'>>(
  items: readonly T[],
  status: PricingStatusFilter,
  customer: string,
): T[] {
  return items.filter((item) =>
    (status === 'all' || item.status === status) &&
    (customer === 'all' || item.customer === customer),
  )
}
