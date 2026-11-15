import assert from 'node:assert/strict'
import test from 'node:test'
import { caminhoFila, diasEsperando, percentualDaFracao, podeComparar, pontosPercentuais } from './filaAprovacao.ts'

test('sem filtro, a fila abre na ordem padrão (mais antigas primeiro)', () => {
  assert.equal(caminhoFila({}), '/aprovacoes/fila')
  assert.equal(caminhoFila({ ordem: 'mais_antigas' }), '/aprovacoes/fila')
})

test('filtros de cliente, margem e ordem vão para a query', () => {
  const caminho = caminhoFila({ clienteId: 'abc', situacao: 'abaixo_da_politica', ordem: 'mais_recentes' })
  const parametros = new URLSearchParams(caminho.split('?')[1])
  assert.equal(parametros.get('cliente_id'), 'abc')
  assert.equal(parametros.get('situacao'), 'abaixo_da_politica')
  assert.equal(parametros.get('ordem'), 'mais_recentes')
})

test('margem em fração vira percentual com uma casa', () => {
  assert.equal(percentualDaFracao('0.284'), '28,4%')
  assert.equal(percentualDaFracao('0.24'), '24,0%')
  assert.equal(percentualDaFracao(null), '—')
})

test('distância da política em pontos percentuais com sinal', () => {
  assert.equal(pontosPercentuais('-0.048'), '−4,8 p.p.')
  assert.equal(pontosPercentuais('0.044'), '+4,4 p.p.')
  assert.equal(pontosPercentuais('0'), '0,0 p.p.')
  assert.equal(pontosPercentuais(null), '—')
})

test('comparação só existe com versão anterior', () => {
  assert.equal(podeComparar({ cenario_versao: 3, versao_anterior: 2 }), true)
  assert.equal(podeComparar({ cenario_versao: 1, versao_anterior: null }), false)
  assert.equal(podeComparar({ cenario_versao: null, versao_anterior: null }), false)
})

test('dias esperando decisão contam a partir da submissão', () => {
  const agora = new Date('2026-11-15T12:00:00Z')
  assert.equal(diasEsperando('2026-11-12T10:00:00Z', agora), 3)
  assert.equal(diasEsperando('2026-11-15T11:00:00Z', agora), 0)
})
