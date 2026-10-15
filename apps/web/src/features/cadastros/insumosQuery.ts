import type { TipoInsumo, UnidadeMedida } from './insumosService'

export type FiltroAtivo = 'todos' | 'ativos' | 'inativos'
export type FiltroUnidade = 'todas' | UnidadeMedida

export type ConsultaInsumos = {
  busca: string
  ativo: FiltroAtivo
  unidade_medida: FiltroUnidade
  pagina: number
  tamanho_pagina: number
}

export function parametrosInsumos(tipo: TipoInsumo, consulta: ConsultaInsumos): string {
  const parametros = new URLSearchParams({
    pagina: String(consulta.pagina),
    tamanho_pagina: String(consulta.tamanho_pagina),
  })
  const busca = consulta.busca.trim()
  if (busca) parametros.set('busca', busca)
  if (consulta.ativo !== 'todos') parametros.set('ativo', String(consulta.ativo === 'ativos'))
  if (consulta.unidade_medida !== 'todas') parametros.set('unidade_medida', consulta.unidade_medida)
  return `/cadastros/${tipo}?${parametros.toString()}`
}
