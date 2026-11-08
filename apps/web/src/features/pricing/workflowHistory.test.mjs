import assert from 'node:assert/strict'
import { test } from 'node:test'
import { combinarHistoricoWorkflow } from './workflowHistory.ts'

test('combina submissões e decisões em ordem cronológica', () => {
  const eventos = combinarHistoricoWorkflow(
    [{
      id: 's1', status_anterior: 'em_preenchimento', status_novo: 'em_aprovacao',
      modo: 'demonstracao', responsavel_id: 'u1', ocorrido_em: '2026-11-08T10:00:00Z',
    }],
    [{
      id: 'd1', decisao: 'reprovado', responsavel_id: 'u2', responsavel_nome: 'Ana',
      decidido_em: '2026-11-08T11:00:00Z',
    }],
  )

  assert.deepEqual(eventos.map(({ status_anterior, status_novo, origem }) => ({ status_anterior, status_novo, origem })), [
    { status_anterior: 'em_preenchimento', status_novo: 'em_aprovacao', origem: 'submissao' },
    { status_anterior: 'em_aprovacao', status_novo: 'reprovado', origem: 'decisao' },
  ])
  assert.equal(eventos[0].modo, 'demonstracao')
  assert.equal(eventos[1].responsavel_nome, 'Ana')
})

test('preserva a trilha de submissão quando ainda não existem decisões', () => {
  const eventos = combinarHistoricoWorkflow([{
    id: 's1', status_anterior: 'reprovado', status_novo: 'em_aprovacao',
    modo: 'homologada', responsavel_id: 'u1', ocorrido_em: '2026-11-08T10:00:00Z',
  }], [])

  assert.equal(eventos.length, 1)
  assert.equal(eventos[0].status_anterior, 'reprovado')
})
