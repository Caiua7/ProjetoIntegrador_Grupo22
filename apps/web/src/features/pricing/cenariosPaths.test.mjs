import assert from 'node:assert/strict'
import test from 'node:test'
import {
  caminhoComparacaoCenarios,
  caminhoDetalheCenario,
  caminhoDuplicacaoCenario,
  caminhoListaCenarios,
  caminhoSalvarCenario,
} from './cenariosPaths.ts'

test('separa a listagem com custo da listagem restrita a preço', () => {
  assert.equal(caminhoListaCenarios('precificacao 1', true), '/precificacoes/precificacao%201/cenarios')
  assert.equal(caminhoListaCenarios('precificacao 1', false), '/precificacoes/precificacao%201/cenarios/precos')
})

test('usa os caminhos documentados para consulta, comparação e duplicação', () => {
  assert.equal(caminhoDetalheCenario('abc', 2), '/precificacoes/abc/cenarios/2')
  assert.equal(caminhoComparacaoCenarios('abc', 1, 3), '/precificacoes/abc/cenarios/comparacao?de=1&para=3')
  assert.equal(caminhoDuplicacaoCenario('abc', 2), '/precificacoes/abc/cenarios/2/duplicar')
})

test('salva uma nova versão no endpoint de cenários da precificação', () => {
  assert.equal(caminhoSalvarCenario('id com espaço'), '/precificacoes/id%20com%20espa%C3%A7o/cenarios')
})
