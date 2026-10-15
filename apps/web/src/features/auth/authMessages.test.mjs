import assert from 'node:assert/strict'
import test from 'node:test'
import { getAuthErrorMessage } from './authMessages.ts'

test('invalid credentials get a simple message without distinguishing account existence', () => {
  assert.equal(getAuthErrorMessage({ code: 'invalid_credentials' }), 'E-mail ou senha inválidos.')
})

test('unconfirmed email gets an actionable message', () => {
  assert.match(getAuthErrorMessage({ code: 'email_not_confirmed' }), /Confirme seu e-mail/)
})

test('rate limits and connection failures are explained', () => {
  assert.match(getAuthErrorMessage({ status: 429 }), /Muitas tentativas/)
  assert.match(getAuthErrorMessage({ name: 'AuthRetryableFetchError' }), /conectar ao serviço/)
})

test('unrecognized server messages are not exposed to the user', () => {
  const secretMessage = 'Bearer very-secret-token'
  assert.equal(getAuthErrorMessage({ message: secretMessage }), 'Não foi possível concluir a solicitação de autenticação. Tente novamente.')
  assert.doesNotMatch(getAuthErrorMessage({ message: secretMessage }), /very-secret-token/)
})
