import assert from 'node:assert/strict'
import test from 'node:test'
import { deslocarDecimal, formatarDecimalBr, multiplicarDecimal, somarDecimal } from './decimal.ts'

test('desloca a vírgula sem passar por float', () => {
  assert.equal(deslocarDecimal('0.012', 2), '1.2')
  assert.equal(deslocarDecimal('0.012000', 2), '1.2')
  assert.equal(deslocarDecimal('1,2', -2), '0.012')
  assert.equal(deslocarDecimal('0.1', -2), '0.001')
  assert.equal(deslocarDecimal('17', -2), '0.17')
  assert.equal(deslocarDecimal('0', 2), '0')
  assert.equal(deslocarDecimal('45', 0), '45')
  assert.equal(deslocarDecimal('abc', 2), '')
  assert.equal(deslocarDecimal('', 2), '')
})

test('multiplica com arredondamento meio para cima', () => {
  assert.equal(multiplicarDecimal('5.1234', '1.02', 6), '5.225868')
  assert.equal(multiplicarDecimal('5.123456', '1.015', 6), '5.200308')
  assert.equal(multiplicarDecimal('0.1', '0.2', 4), '0.02')
  assert.equal(multiplicarDecimal('2', '3', 2), '6')
  assert.equal(multiplicarDecimal('x', '3', 2), '')
})

test('soma exata', () => {
  assert.equal(somarDecimal('1', '0.015'), '1.015')
  assert.equal(somarDecimal('0.1', '0.2'), '0.3')
  assert.equal(somarDecimal('1', '-1.5'), '-0.5')
})

test('formata em pt-BR', () => {
  assert.equal(formatarDecimalBr('5.123400'), '5,1234')
  assert.equal(formatarDecimalBr('45.000000'), '45')
  assert.equal(formatarDecimalBr('5.1', 4), '5,1000')
})
