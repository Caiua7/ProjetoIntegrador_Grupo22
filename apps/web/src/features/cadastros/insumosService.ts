import { apiFetch } from '../../services/apiClient'

export type TipoInsumo = 'materias-primas' | 'embalagens'

export type Insumo = {
  id: string
  codigo: string
  descricao: string
  unidade_medida: 'kg' | 'g' | 'l' | 'ml' | 'un'
  ncm_codigo: string
  ativo: boolean
  created_at: string
  updated_at: string
}

export type InsumoEntrada = Pick<Insumo, 'codigo' | 'descricao' | 'unidade_medida' | 'ncm_codigo'>
export type InsumoPatch = Partial<InsumoEntrada> & { ativo?: boolean }
export type Ncm = { codigo: string, descricao: string }

export function listarInsumos(tipo: TipoInsumo): Promise<Insumo[]> {
  return apiFetch<Insumo[]>(`/cadastros/${tipo}`)
}

export function obterInsumo(tipo: TipoInsumo, id: string): Promise<Insumo> {
  return apiFetch<Insumo>(`/cadastros/${tipo}/${id}`)
}

export function criarInsumo(tipo: TipoInsumo, entrada: InsumoEntrada): Promise<Insumo> {
  return apiFetch<Insumo>(`/cadastros/${tipo}`, { method: 'POST', body: JSON.stringify(entrada) })
}

export function atualizarInsumo(tipo: TipoInsumo, id: string, entrada: InsumoPatch): Promise<Insumo> {
  return apiFetch<Insumo>(`/cadastros/${tipo}/${id}`, { method: 'PATCH', body: JSON.stringify(entrada) })
}

export function inativarInsumo(tipo: TipoInsumo, id: string): Promise<Insumo> {
  return apiFetch<Insumo>(`/cadastros/${tipo}/${id}`, { method: 'DELETE' })
}

export function buscarNcm(termo: string): Promise<Ncm[]> {
  return apiFetch<Ncm[]>(`/cadastros/ncm?termo=${encodeURIComponent(termo)}`)
}
