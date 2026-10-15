import { apiFetch } from '../../services/apiClient'
import { parametrosInsumos, type ConsultaInsumos } from './insumosQuery'

export type TipoInsumo = 'materias-primas' | 'embalagens'
export type UnidadeMedida = 'kg' | 'g' | 'l' | 'ml' | 'un'

export type Insumo = {
  id: string
  codigo: string
  descricao: string
  unidade_medida: UnidadeMedida
  ncm_codigo: string
  ativo: boolean
  created_at: string
  updated_at: string
}

export type InsumoEntrada = Pick<Insumo, 'codigo' | 'descricao' | 'unidade_medida' | 'ncm_codigo'>
export type InsumoPatch = Partial<InsumoEntrada> & { ativo?: boolean }
export type Ncm = { codigo: string, descricao: string }
export type PaginaInsumos = {
  registros: Insumo[]
  total: number
  pagina: number
  tamanho_pagina: number
  total_paginas: number
}

export function listarInsumos(tipo: TipoInsumo, consulta: ConsultaInsumos): Promise<PaginaInsumos> {
  return apiFetch<PaginaInsumos>(parametrosInsumos(tipo, consulta))
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
