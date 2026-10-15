import assert from 'node:assert/strict'
import test from 'node:test'
import { parametrosInsumos } from './insumosQuery.ts'

test('monta a consulta paginada padrão sem filtros', () => {
  assert.equal(parametrosInsumos('materias-primas', {
    busca: '   ', ativo: 'todos', unidade_medida: 'todas', pagina: 1, tamanho_pagina: 20,
  }), '/cadastros/materias-primas?pagina=1&tamanho_pagina=20')
})

test('preserva busca normalizada e filtros ao trocar de página', () => {
  const caminho = parametrosInsumos('embalagens', {
    busca: '  caixa azul  ', ativo: 'inativos', unidade_medida: 'un', pagina: 3, tamanho_pagina: 50,
  })
  const parametros = new URLSearchParams(caminho.split('?')[1])
  assert.equal(caminho.split('?')[0], '/cadastros/embalagens')
  assert.equal(parametros.get('busca'), 'caixa azul')
  assert.equal(parametros.get('ativo'), 'false')
  assert.equal(parametros.get('unidade_medida'), 'un')
  assert.equal(parametros.get('pagina'), '3')
  assert.equal(parametros.get('tamanho_pagina'), '50')
})

test('codifica os caracteres da busca na query string', () => {
  const caminho = parametrosInsumos('materias-primas', {
    busca: 'a&b/c', ativo: 'ativos', unidade_medida: 'kg', pagina: 1, tamanho_pagina: 20,
  })
  assert.equal(new URLSearchParams(caminho.split('?')[1]).get('busca'), 'a&b/c')
})
