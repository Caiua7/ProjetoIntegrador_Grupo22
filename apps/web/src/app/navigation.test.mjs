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

test('cadastros de insumos exigem leitura para abrir e edição para manter registros', () => {
  assert.equal(canOpen('records', perfil()), false)
  assert.equal(canOpen('records', perfil('cadastro.ler')), true)
  const ids = navigationFor(perfil('cadastro.ler')).flatMap((grupo) => grupo.items.map((item) => item.id))
  assert.ok(ids.includes('records'))
})

test('fórmulas exige leitura de preços e do catálogo para resolver produto e insumos', () => {
  assert.equal(canOpen('formulation', perfil('precificacao.ler')), false)
  assert.equal(canOpen('formulation', perfil('cadastro.ler')), false)
  assert.equal(canOpen('formulation', perfil('precificacao.ler', 'cadastro.ler')), true)
})

test('cotações abre com custo.ler', () => {
  assert.equal(canOpen('quotes', perfil('cadastro.ler')), false)
  assert.equal(canOpen('quotes', perfil('custo.ler')), true)
})

test('câmbio e parâmetros abre com cambio.ler e fica em Cadastros', () => {
  assert.equal(canOpen('exchange', perfil()), false)
  assert.equal(canOpen('exchange', perfil('cambio.ler')), true)
  const cadastros = navigationFor(perfil('cambio.ler')).find((grupo) => grupo.title === 'Cadastros')
  assert.deepEqual(cadastros?.items.map((item) => item.id), ['exchange'])
})
