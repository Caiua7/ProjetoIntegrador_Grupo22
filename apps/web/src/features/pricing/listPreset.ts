import type { PricingStatusFilter } from './pricingList.filter.ts'

/** Filtro com que a lista abre quando o painel manda a pessoa para lá. */
export type ListPreset = { status?: PricingStatusFilter, abaixoDaPolitica?: boolean }
