import assert from 'node:assert/strict'
import test from 'node:test'
import { filterPricingList } from './pricingList.filter.ts'
import { pricingListDemo, pricingStatusCounts } from './pricingList.mock.ts'

test('counts in the status filters match the demonstration list', () => {
  assert.deepEqual(pricingStatusCounts.map(({ id, count }) => [id, count]), [
    ['all', 7],
    ['draft', 1],
    ['approval', 2],
    ['approved', 3],
    ['rejected', 1],
  ])
})

test('status filter returns only records in that status', () => {
  const items = filterPricingList(pricingListDemo, 'approval', 'all')
  assert.deepEqual(items.map(({ code }) => code), ['PRC-2026-0148', 'PRC-2026-0147'])
})

test('customer filter combines with status filter', () => {
  const items = filterPricingList(pricingListDemo, 'approved', 'Corpore Suplementos')
  assert.deepEqual(items.map(({ code }) => code), ['PRC-2026-0143'])
})

test('all statuses and customers return the complete list', () => {
  assert.equal(filterPricingList(pricingListDemo, 'all', 'all').length, 7)
})

test('a filter combination without matches returns an empty list', () => {
  assert.deepEqual(filterPricingList(pricingListDemo, 'draft', 'Corpore Suplementos'), [])
})
