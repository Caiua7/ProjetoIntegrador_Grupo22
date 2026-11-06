import assert from 'node:assert/strict'
import test from 'node:test'
import { custoEstimado, faixaDe, faixas, fornecedores, precisaFornecedor, quantidadeParaApi, rotuloFornecedor } from './cotacoesRules.ts'

const cot = (campos) => ({
  id: 'x', materia_prima_id: 'mp', fornecedor_id: 'f-aaaaaaaa-1', fornecedor_codigo: null, fornecedor_nome: null,
  moeda: 'BRL', preco: '10', volume_minimo: '0', validade_inicio: '2026-11-01', validade_fim: null, prazo_entrega_dias: 7, ...campos,
})

test('faixas distintas em ordem numérica, a última aberta', () => {
  const lista = faixas([cot({ volume_minimo: '1000.000' }), cot({ volume_minimo: '0' }), cot({ volume_minimo: '101' }), cot({ volume_minimo: '1000' }), cot({ volume_minimo: '20.5' })])
  assert.deepEqual(lista.map((f) => [f.minimo, f.ateExclusive]), [['0', '20.5'], ['20.5', '101'], ['101', '1000.000'], ['1000.000', null]])
  assert.equal(faixaDe('1000', lista)?.ateExclusive, null)
  assert.equal(faixaDe('101.000', lista)?.ateExclusive, '1000.000')
})

test('quantidade aceita vírgula, milhar e até 3 casas', () => {
  assert.equal(quantidadeParaApi('250'), '250')
  assert.equal(quantidadeParaApi('1.250,5'), '1250.5')
  assert.equal(quantidadeParaApi('0,125'), '0.125')
  assert.equal(quantidadeParaApi('2.5'), '2.5')
  assert.equal(quantidadeParaApi('0'), null)
  assert.equal(quantidadeParaApi('1,2345'), null)
  assert.equal(quantidadeParaApi('-3'), null)
  assert.equal(quantidadeParaApi(''), null)
})

test('custo estimado exato com 2 casas', () => {
  assert.equal(custoEstimado('8.250000', '250'), '2062.5')
  assert.equal(custoEstimado('3.333333', '3'), '10')
  assert.equal(custoEstimado('0.105', '1'), '0.11')
})

test('rótulo do fornecedor cai para o código e depois para o id', () => {
  assert.equal(rotuloFornecedor(cot({ fornecedor_codigo: 'F001', fornecedor_nome: 'Alfa' })), 'F001 · Alfa')
  assert.equal(rotuloFornecedor(cot({ fornecedor_codigo: 'F001' })), 'F001')
  assert.equal(rotuloFornecedor(cot({})), 'Fornecedor f-aaaaaa')
})

test('fornecedores distintos e ordenados', () => {
  const lista = fornecedores([cot({ fornecedor_id: 'b', fornecedor_nome: 'Beta' }), cot({ fornecedor_id: 'a', fornecedor_nome: 'Alfa' }), cot({ fornecedor_id: 'b', fornecedor_nome: 'Beta' })])
  assert.deepEqual(lista, [{ id: 'a', rotulo: 'Alfa' }, { id: 'b', rotulo: 'Beta' }])
})

test('409 pede fornecedor', () => {
  assert.equal(precisaFornecedor(409), true)
  assert.equal(precisaFornecedor(404), false)
})
