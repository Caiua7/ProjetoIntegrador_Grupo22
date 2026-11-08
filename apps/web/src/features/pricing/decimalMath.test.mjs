import assert from 'node:assert/strict'
import test from 'node:test'
import { multiplicarDecimais } from './decimalMath.ts'

test('multiplica valores decimais sem converter por ponto flutuante', () => {
  assert.equal(multiplicarDecimais('0.125', '42000'), '5250')
  assert.equal(multiplicarDecimais('0.0003', '0.25'), '0.000075')
  assert.equal(multiplicarDecimais('1.20', '2.5'), '3')
})

test('recusa valores fora do formato decimal API', () => {
  assert.throws(() => multiplicarDecimais('1,2', '3'))
  assert.throws(() => multiplicarDecimais('-1', '3'))
})
