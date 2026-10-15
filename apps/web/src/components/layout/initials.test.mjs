import assert from 'node:assert/strict'
import { test } from 'node:test'
import { initials } from './initials.ts'

test('usa a inicial do primeiro e do último nome', () => {
  assert.equal(initials('Felipe Corso Pretoni'), 'FP')
})

test('nome único vira as duas primeiras letras', () => {
  assert.equal(initials('admin'), 'AD')
})

test('ignora espaços extras', () => {
  assert.equal(initials('  Ana   Souza '), 'AS')
})
