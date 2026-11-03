import { apiFetch } from '../../services/apiClient'

export type OpcaoPrecificacao = { id: string, codigo: string, descricao: string }
export type OpcoesPrecificacao = { clientes: OpcaoPrecificacao[], produtos: OpcaoPrecificacao[] }
export type Precificacao = {
  id: string
  codigo: string
  cliente_id: string
  produto_id: string
  modalidade_comercial: string
  uf_destino: string
  frete: string
  regime_tributario: string
  status: 'em_preenchimento' | 'em_aprovacao' | 'aprovado' | 'reprovado'
  created_at: string
  updated_at: string
  cliente?: { razao_social: string } | null
  produto?: { descricao: string } | null
}
export type PrecificacaoEntrada = Pick<Precificacao, 'cliente_id' | 'produto_id' | 'modalidade_comercial' | 'uf_destino' | 'frete' | 'regime_tributario'>

export const obterOpcoesPrecificacao = () => apiFetch<OpcoesPrecificacao>('/precificacoes/opcoes')
export const listarPrecificacoes = () => apiFetch<Precificacao[]>('/precificacoes')
export const criarPrecificacao = (entrada: PrecificacaoEntrada) => apiFetch<Precificacao>('/precificacoes', {
  method: 'POST', body: JSON.stringify(entrada),
})
