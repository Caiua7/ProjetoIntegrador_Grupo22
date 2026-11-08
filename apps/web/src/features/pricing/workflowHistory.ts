export type WorkflowStatus = 'em_preenchimento' | 'em_aprovacao' | 'aprovado' | 'reprovado'

export type SubmissionEventSource = {
  id: string
  status_anterior: WorkflowStatus
  status_novo: WorkflowStatus
  modo: 'demonstracao' | 'homologada'
  responsavel_id: string
  ocorrido_em: string
}

export type DecisionEventSource = {
  id: string
  decisao: 'aprovado' | 'reprovado'
  responsavel_id: string
  responsavel_nome: string | null
  decidido_em: string
}

export type WorkflowEvent = {
  id: string
  status_anterior: WorkflowStatus
  status_novo: WorkflowStatus
  ocorrido_em: string
  responsavel_id: string
  responsavel_nome: string | null
  origem: 'submissao' | 'decisao'
  modo?: 'demonstracao' | 'homologada'
}

export function combinarHistoricoWorkflow(
  submissoes: SubmissionEventSource[],
  decisoes: DecisionEventSource[],
): WorkflowEvent[] {
  const eventos: WorkflowEvent[] = [
    ...submissoes.map((item) => ({
      id: `submissao-${item.id}`,
      status_anterior: item.status_anterior,
      status_novo: item.status_novo,
      ocorrido_em: item.ocorrido_em,
      responsavel_id: item.responsavel_id,
      responsavel_nome: null,
      origem: 'submissao' as const,
      modo: item.modo,
    })),
    ...decisoes.map((item) => ({
      id: `decisao-${item.id}`,
      status_anterior: 'em_aprovacao' as const,
      status_novo: item.decisao,
      ocorrido_em: item.decidido_em,
      responsavel_id: item.responsavel_id,
      responsavel_nome: item.responsavel_nome,
      origem: 'decisao' as const,
    })),
  ]

  return eventos.sort((a, b) => Date.parse(a.ocorrido_em) - Date.parse(b.ocorrido_em))
}
