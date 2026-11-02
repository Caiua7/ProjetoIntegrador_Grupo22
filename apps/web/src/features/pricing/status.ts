import type { PricingStatus } from './pricingList.mock'

/** O que cada status significa no fluxo, para dicas e legendas. */
export const statusDescricao: Record<PricingStatus, string> = {
  draft: 'O analista ainda está montando o cenário.',
  approval: 'Enviado ao gerente comercial, esperando decisão.',
  approved: 'Liberado para virar proposta comercial.',
  rejected: 'Devolvido pelo gerente; precisa de nova versão.',
}
