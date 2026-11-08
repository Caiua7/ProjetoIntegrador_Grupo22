import type { PricingStatusFilter } from './pricingList.filter.ts'
import type { Precificacao } from './precificacoesService'

/** Filtro com que a lista abre quando o painel manda a pessoa para lá. */
export type ListPreset = { status?: PricingStatusFilter | Precificacao['status'], abaixoDaPolitica?: boolean }
