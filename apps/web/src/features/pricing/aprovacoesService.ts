import { apiFetch } from '../../services/apiClient'

export type DecisaoAprovacao = 'aprovado' | 'reprovado'
export type DecisaoRegistrada = {
  id: string
  precificacao_id: string
  cenario_id: string | null
  cenario_versao: number | null
  decisao: DecisaoAprovacao
  comentario: string | null
  responsavel_id: string
  responsavel_nome: string | null
  decidido_em: string
}

export const registrarDecisao = (precificacaoId: string, decisao: DecisaoAprovacao, comentario?: string) =>
  apiFetch<DecisaoRegistrada>(`/precificacoes/${encodeURIComponent(precificacaoId)}/decisoes`, {
    method: 'POST', body: JSON.stringify({ decisao, comentario: comentario || null }),
  })

export const listarDecisoesAprovacao = (precificacaoId: string) =>
  apiFetch<DecisaoRegistrada[]>(`/precificacoes/${encodeURIComponent(precificacaoId)}/decisoes`)
