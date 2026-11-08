import { apiFetch } from '../../services/apiClient'

export type CotacaoResolvida = {
  id: string
  materia_prima_id: string
  fornecedor_id: string
  moeda: string
  preco: string
  volume_minimo: string
  validade_inicio: string
  validade_fim: string | null
  prazo_entrega_dias: number
}

export function resolverCotacao(materiaPrimaId: string, quantidade: string): Promise<CotacaoResolvida> {
  const query = new URLSearchParams({ materia_prima_id: materiaPrimaId, quantidade })
  return apiFetch<CotacaoResolvida>(`/cotacoes/resolver?${query}`)
}
