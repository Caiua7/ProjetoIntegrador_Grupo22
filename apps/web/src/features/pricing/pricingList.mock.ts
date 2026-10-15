export type PricingStatus = 'draft' | 'approval' | 'approved' | 'rejected'

export type PricingListItem = {
  code: string
  customer: string
  uf: string
  product: string
  ncm: string
  modality: string
  version: number
  volume: number
  contributionMarginPercent: number
  grossOperatingRevenue: number
  status: PricingStatus
  updatedAt: string
}

// Demonstration records transcribed from the official prototype's PRECIFICACOES data.
// They are presentation fixtures and do not represent persisted scenarios or API results.
export const pricingListDemo: PricingListItem[] = [
  { code: 'PRC-2026-0148', customer: 'Nutrafit Distribuidora', uf: 'SP', product: 'WPC 80 — pote 600 g', ncm: '2106.90.30', modality: 'Full Service Nacional', version: 3, volume: 42000, contributionMarginPercent: 28.4, grossOperatingRevenue: 2433480, status: 'approval', updatedAt: 'há 2 h' },
  { code: 'PRC-2026-0147', customer: 'Corpore Suplementos', uf: 'MG', product: 'Creatina mono 300 g', ncm: '2106.90.30', modality: 'Full Service Nacional', version: 2, volume: 18000, contributionMarginPercent: 19.2, grossOperatingRevenue: 716400, status: 'approval', updatedAt: 'há 5 h' },
  { code: 'PRC-2026-0146', customer: 'Atlas Nutrition LLC', uf: 'EX', product: 'Whey isolado 900 g', ncm: '2106.90.30', modality: 'Full Service Exportação', version: 1, volume: 26000, contributionMarginPercent: 34.1, grossOperatingRevenue: 2925000, status: 'approved', updatedAt: 'ontem' },
  { code: 'PRC-2026-0145', customer: 'Vita Prime Indústria', uf: 'PR', product: 'Pré-treino 300 g — marca própria', ncm: '2106.90.30', modality: 'Industrialização por Encomenda', version: 4, volume: 12000, contributionMarginPercent: 14.8, grossOperatingRevenue: 494400, status: 'rejected', updatedAt: 'ontem' },
  { code: 'PRC-2026-0144', customer: 'Nutrafit Distribuidora', uf: 'SP', product: 'BCAA 2:1:1 — 250 g', ncm: '2106.90.30', modality: 'Full Service Nacional', version: 1, volume: 9000, contributionMarginPercent: 26.7, grossOperatingRevenue: 434700, status: 'draft', updatedAt: 'há 3 dias' },
  { code: 'PRC-2026-0143', customer: 'Corpore Suplementos', uf: 'MG', product: 'Hipercalórico 3 kg', ncm: '2106.90.30', modality: 'Full Service Nacional', version: 2, volume: 15000, contributionMarginPercent: 22.9, grossOperatingRevenue: 1476000, status: 'approved', updatedAt: 'há 4 dias' },
  { code: 'PRC-2026-0142', customer: 'Forma Natural', uf: 'RJ', product: 'Colágeno verisol 300 g', ncm: '2106.90.30', modality: 'Full Service Nacional', version: 1, volume: 8500, contributionMarginPercent: 31.5, grossOperatingRevenue: 541450, status: 'approved', updatedAt: 'há 6 dias' },
]

export const pricingStatusLabels: Record<PricingStatus, string> = {
  draft: 'Em preenchimento',
  approval: 'Em aprovação',
  approved: 'Aprovado',
  rejected: 'Reprovado',
}

export const pricingStatusCounts: { id: PricingStatus | 'all'; label: string; count: number }[] = [
  { id: 'all', label: 'Todas', count: pricingListDemo.length },
  ...(['draft', 'approval', 'approved', 'rejected'] as const).map((status) => ({
    id: status,
    label: ({ draft: 'Em preenchimento', approval: 'Em aprovação', approved: 'Aprovadas', rejected: 'Reprovadas' } as const)[status],
    count: pricingListDemo.filter((item) => item.status === status).length,
  })),
]

export const pricingDemoCustomers = [...new Set(pricingListDemo.map((item) => item.customer))]
