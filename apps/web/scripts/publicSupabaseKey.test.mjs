import assert from 'node:assert/strict'
import test from 'node:test'
import { assertPublicSupabaseKey, isPrivilegedSupabaseKey } from './publicSupabaseKey.mjs'

test('identifies Supabase secret keys without including their value in errors', () => {
  assert.equal(isPrivilegedSupabaseKey('sb_secret_example-only'), true)
  assert.throws(() => assertPublicSupabaseKey('sb_secret_example-only'), /public anon\/publishable key/)
})

test('identifies service_role JWTs', () => {
  const payload = Buffer.from(JSON.stringify({ role: 'service_role' })).toString('base64url')
  assert.equal(isPrivilegedSupabaseKey(`header.${payload}.signature`), true)
})

test('accepts public-key formats and malformed non-JWT values without echoing them', () => {
  assert.equal(isPrivilegedSupabaseKey('sb_publishable_example-only'), false)
  assert.equal(isPrivilegedSupabaseKey('not-a-jwt'), false)
  assert.doesNotThrow(() => assertPublicSupabaseKey('sb_publishable_example-only'))
})
