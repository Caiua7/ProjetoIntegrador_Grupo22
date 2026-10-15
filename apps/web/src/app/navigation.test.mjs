import assert from 'node:assert/strict'
import { test } from 'node:test'
import { canOpen, navigationFor } from './navigation.ts'

const perfil = (...permissoes) => (codigo) => permissoes.includes(codigo)

test('esconde itens e grupos sem permissão', () => {
  const grupos = navigationFor(perfil('precificacao.ler'))
  const ids = grupos.flatMap((grupo) => grupo.items.map((item) => item.id))
  assert.ok(ids.includes('pricing-list'))
  assert.ok(!ids.includes('new-pricing'))
  assert.ok(!grupos.some((grupo) => grupo.title === 'Cadastros'))
})

test('painel e ajustes valem para qualquer usuário ativo', () => {
  const ids = navigationFor(perfil()).flatMap((grupo) => grupo.items.map((item) => item.id))
  assert.deepEqual(ids, ['dashboard', 'settings'])
})

test('guarda de rota barra tela sem permissão', () => {
  assert.equal(canOpen('new-pricing', perfil('precificacao.ler')), false)
  assert.equal(canOpen('new-pricing', perfil('precificacao.editar')), true)
  assert.equal(canOpen('dashboard', perfil()), true)
})
