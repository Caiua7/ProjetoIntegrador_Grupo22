import assert from 'node:assert/strict'
import test from 'node:test'
import { arredondarCentavos } from './centavos.ts'

test('arredonda para centavos metade para longe do zero', () => {
  assert.equal(arredondarCentavos('521800.000'), '521800.00')
  assert.equal(arredondarCentavos('116700.0049'), '116700.00')
  assert.equal(arredondarCentavos('116700.005'), '116700.01')
  assert.equal(arredondarCentavos('-34400.125'), '-34400.13')
  assert.equal(arredondarCentavos('0.004'), '0.00')
  assert.equal(arredondarCentavos('-0.004'), '0.00')
  assert.equal(arredondarCentavos('7'), '7.00')
})

test('mantém valores ausentes e textos fora do formato', () => {
  assert.equal(arredondarCentavos(null), null)
  assert.equal(arredondarCentavos(undefined), null)
  assert.equal(arredondarCentavos('abc'), 'abc')
})

test('não perde precisão em operações grandes', () => {
  assert.equal(arredondarCentavos('123456789012345.678'), '123456789012345.68')
})
