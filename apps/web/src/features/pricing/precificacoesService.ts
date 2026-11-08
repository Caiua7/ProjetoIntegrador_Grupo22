import { apiFetch } from '../../services/apiClient'

export type OpcaoPrecificacao = { id: string, codigo: string, descricao: string }
export type OpcoesPrecificacao = { clientes: OpcaoPrecificacao[], produtos: OpcaoPrecificacao[] }
export type RegimeTributario = 'lucro_real' | 'lucro_presumido' | 'simples_nacional'
export type Precificacao = {
  id: string
  codigo: string
  cliente_id: string
  produto_id: string
  modalidade_comercial: string
  uf_destino: string | null
  frete: string | null
  regime_tributario: RegimeTributario | null
  status: 'em_preenchimento' | 'em_aprovacao' | 'aprovado' | 'reprovado'
  homologacao_pendente: boolean
  created_at: string
  updated_at: string
  cliente?: { razao_social: string } | null
  produto?: { descricao: string, ncm_codigo?: string } | null
}
export type PrecificacaoEntrada = Pick<Precificacao, 'cliente_id' | 'produto_id' | 'modalidade_comercial'> & { uf_destino: string, frete: string, regime_tributario: string }
export type VerificacaoSubmissao = {
  pode_submeter: boolean
  modo_politica: 'demonstracao' | 'homologada'
  homologacao_pendente: boolean
  campos_obrigatorios: string[]
  motivos_bloqueio: string[]
  status?: string
}
export type HistoricoStatus = { id: string, status_anterior: string, status_novo: string, modo: 'demonstracao' | 'homologada', responsavel_id: string, ocorrido_em: string }

export const obterOpcoesPrecificacao = () => apiFetch<OpcoesPrecificacao>('/precificacoes/opcoes')
export const listarPrecificacoes = () => apiFetch<Precificacao[]>('/precificacoes')
export const criarPrecificacao = (entrada: PrecificacaoEntrada) => apiFetch<Precificacao>('/precificacoes', {
  method: 'POST', body: JSON.stringify(entrada),
})
export const verificarSubmissao = (id: string) => apiFetch<VerificacaoSubmissao>(`/precificacoes/${id}/submissao`)
export const submeterPrecificacao = (id: string) => apiFetch<VerificacaoSubmissao>(`/precificacoes/${id}/submissao`, { method: 'POST' })
export const listarHistoricoStatus = (id: string) => apiFetch<HistoricoStatus[]>(`/precificacoes/${id}/historico-status`)
