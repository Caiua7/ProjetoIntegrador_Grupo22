/**
 * Regras puras da fila de aprovação do gerente (US36, #67). Margens
 * trafegam em fração, como na API (0.284 = 28,4%); a distância da política
 * é em pontos percentuais.
 */

export type SituacaoMargem = 'abaixo_da_politica' | 'dentro_da_politica'
export type OrdemFila = 'mais_antigas' | 'mais_recentes'

export type FiltrosFila = {
  clienteId?: string
  situacao?: SituacaoMargem
  ordem?: OrdemFila
}

export type ItemFila = {
  precificacao_id: string
  codigo: string
  cliente_id: string
  cliente_nome: string
  produto_descricao: string
  modalidade_comercial: string
  uf_destino: string | null
  homologacao_pendente: boolean
  submetido_em: string
  submetido_por_nome: string | null
  cenario_versao: number | null
  versao_anterior: number | null
  volume: string | null
  preco_bruto: string | null
  margem_contribuicao_valor: string | null
  margem_contribuicao_percentual: string | null
  abaixo_da_politica: boolean | null
  distancia_da_politica: string | null
}

export type FilaAprovacao = {
  politica: { margem_minima: string, vigencia_inicio: string } | null
  clientes: { id: string, nome: string }[]
  total_em_aprovacao: number
  itens: ItemFila[]
}

export function caminhoFila(filtros: FiltrosFila): string {
  const parametros = new URLSearchParams()
  if (filtros.clienteId) parametros.set('cliente_id', filtros.clienteId)
  if (filtros.situacao) parametros.set('situacao', filtros.situacao)
  if (filtros.ordem && filtros.ordem !== 'mais_antigas') parametros.set('ordem', filtros.ordem)
  const query = parametros.toString()
  return query ? `/aprovacoes/fila?${query}` : '/aprovacoes/fila'
}

const umaCasa = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** '0.284' → '28,4%'; nulo vira travessão. */
export function percentualDaFracao(fracao: string | null): string {
  if (fracao == null || fracao === '' || !Number.isFinite(Number(fracao))) return '—'
  return `${umaCasa.format(Number(fracao) * 100)}%`
}

/** '-0.048' → '−4,8 p.p.'; '0.044' → '+4,4 p.p.'. */
export function pontosPercentuais(fracao: string | null): string {
  if (fracao == null || fracao === '' || !Number.isFinite(Number(fracao))) return '—'
  const pontos = Number(fracao) * 100
  if (Math.abs(pontos) < 0.05) return '0,0 p.p.'
  return `${pontos > 0 ? '+' : '−'}${umaCasa.format(Math.abs(pontos))} p.p.`
}

/** Só dá para comparar quando a vigente tem uma versão anterior. */
export function podeComparar(item: Pick<ItemFila, 'cenario_versao' | 'versao_anterior'>): boolean {
  return item.cenario_versao != null && item.versao_anterior != null
}

/** Dias inteiros esperando decisão, a partir da submissão. */
export function diasEsperando(submetidoEm: string, agora: Date = new Date()): number {
  const diferenca = agora.getTime() - new Date(submetidoEm).getTime()
  return Math.max(0, Math.floor(diferenca / 86_400_000))
}
