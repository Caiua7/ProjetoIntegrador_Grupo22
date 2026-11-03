import { apiFetch } from '../../services/apiClient'

export type Produto = { id: string, codigo: string, descricao: string, categoria: string, peso_liquido_g: number | null }
export type TipoItem = 'materia_prima' | 'embalagem'
export type Unidade = 'kg' | 'g' | 'l' | 'ml' | 'un'
export type FormulacaoItem = {
  id?: string
  tipo_insumo: TipoItem
  materia_prima_id: string | null
  embalagem_id: string | null
  quantidade: string
  unidade_medida: Unidade
  perda_percentual: string | null
  ordem?: number
}
export type Formulacao = { id: string, produto_id: string, created_at: string, updated_at: string, itens: FormulacaoItem[] }

export const listarProdutos = () => apiFetch<Produto[]>('/formulacoes/produtos')
export const obterFormulacao = (produtoId: string) => apiFetch<Formulacao>(`/formulacoes/${produtoId}`)
export const salvarFormulacao = (produtoId: string, itens: FormulacaoItem[]) =>
  apiFetch<Formulacao>(`/formulacoes/${produtoId}`, { method: 'PUT', body: JSON.stringify({ itens }) })
