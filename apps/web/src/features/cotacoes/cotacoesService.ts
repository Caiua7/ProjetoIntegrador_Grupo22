import { apiFetch } from '../../services/apiClient'

export type Cotacao = {
  id: string
  materia_prima_id: string
  fornecedor_id: string
  /** Nulos quando o perfil não lê o cadastro de fornecedores. */
  fornecedor_codigo: string | null
  fornecedor_nome: string | null
  moeda: string
  /** NUMERIC como string (Decimal da API). */
  preco: string
  volume_minimo: string
  validade_inicio: string
  validade_fim: string | null
  prazo_entrega_dias: number
}

function query(params: Record<string, string | undefined>): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(params)) if (valor) busca.set(chave, valor)
  return busca.toString()
}

export function listarCotacoesVigentes(materiaPrimaId: string, dataReferencia: string): Promise<Cotacao[]> {
  return apiFetch<Cotacao[]>(`/cotacoes/vigentes?${query({ materia_prima_id: materiaPrimaId, data_referencia: dataReferencia })}`)
}

export function resolverCotacao(params: { materiaPrimaId: string, quantidade: string, dataReferencia: string, fornecedorId?: string }): Promise<Cotacao> {
  return apiFetch<Cotacao>(`/cotacoes/resolver?${query({
    materia_prima_id: params.materiaPrimaId,
    quantidade: params.quantidade,
    data_referencia: params.dataReferencia,
    fornecedor_id: params.fornecedorId,
  })}`)
}
