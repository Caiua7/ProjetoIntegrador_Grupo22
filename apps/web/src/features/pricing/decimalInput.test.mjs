import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizarDecimal, perdaValida, quantidadeValida } from './decimalInput.ts'

test('valida quantidade positiva com no maximo seis casas e precisao do banco', () => {
  assert.equal(quantidadeValida('12345678.123456'), true)
  assert.equal(quantidadeValida('0,000001'), true)
  assert.equal(quantidadeValida('0'), false)
  assert.equal(quantidadeValida('1.0000001'), false)
  assert.equal(quantidadeValida('123456789'), false)
  assert.equal(quantidadeValida('-1'), false)
})

test('valida perda de zero a cem com quatro casas', () => {
  assert.equal(perdaValida('100'), true)
  assert.equal(perdaValida('99,9999'), true)
  assert.equal(perdaValida('100.0001'), false)
  assert.equal(perdaValida('0.00001'), false)
  assert.equal(perdaValida('-0.1'), false)
})

test('normaliza virgula decimal sem converter por ponto flutuante', () => {
  assert.equal(normalizarDecimal('12345678,123456'), '12345678.123456')
})
