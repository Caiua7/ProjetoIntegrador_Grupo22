/**
 * Regras puras da tela de câmbio e parâmetros globais (US13/US14, #49).
 * Mesmas convenções da API: percentuais trafegam em fração (0.012 = 1,2%),
 * o prazo em dias inteiros, e o vigente numa data é o registro de data mais
 * recente que não seja posterior a ela.
 */
import { deslocarDecimal, multiplicarDecimal, somarDecimal } from '../../app/decimal.ts'
import type { CodigoParametro } from './parametrosService.ts'

export type UnidadeParametro = 'percentual' | 'dias'

export const PARAMETROS: readonly { codigo: CodigoParametro, rotulo: string, unidade: UnidadeParametro, descricao: string }[] = [
  { codigo: 'perda_percentual', rotulo: 'Perda padrão', unidade: 'percentual', descricao: 'Perda de processo aplicada sobre MP e embalagem quando o item não informa a sua' },
  { codigo: 'taxa_financeira_mensal_percentual', rotulo: 'Taxa financeira mensal', unidade: 'percentual', descricao: 'Custo do dinheiro usado no encargo financeiro do prazo' },
  { codigo: 'prazo_medio_padrao_dias', rotulo: 'Prazo médio padrão', unidade: 'dias', descricao: 'Prazo de pagamento sugerido quando o cenário não informa outro' },
  { codigo: 'desvio_maximo_cotacao_percentual', rotulo: 'Desvio máximo de cotação', unidade: 'percentual', descricao: 'Alerta quando a cotação foge da média histórica além deste limite' },
]

export function definicaoParametro(codigo: CodigoParametro) {
  return PARAMETROS.find((item) => item.codigo === codigo)!
}

/** Data local de hoje em ISO (AAAA-MM-DD), sem fuso UTC. */
export function hojeIso(agora: Date = new Date()): string {
  return `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, '0')}-${String(agora.getDate()).padStart(2, '0')}`
}

/** O banco só deixa a aplicação mexer em vigência de hoje em diante. */
export function editavel(dataIso: string, hoje: string): boolean {
  return dataIso >= hoje
}

/** O vigente por chave: data mais recente que não passe de `dataRef`. */
export function vigentesPorChave<T>(registros: readonly T[], chave: (r: T) => string, data: (r: T) => string, dataRef: string): Map<string, T> {
  const vigentes = new Map<string, T>()
  for (const registro of registros) {
    const d = data(registro)
    if (d > dataRef) continue
    const atual = vigentes.get(chave(registro))
    if (!atual || d > data(atual)) vigentes.set(chave(registro), registro)
  }
  return new Map([...vigentes.entries()].sort(([a], [b]) => a.localeCompare(b)))
}

/** taxa × (1 + margem), a taxa que entra no custo, com 6 casas como a API. */
export function taxaComMargem(taxa: string, margemFracao: string): string {
  return multiplicarDecimal(taxa, somarDecimal('1', margemFracao), 6)
}

export function fracaoParaPercentual(fracao: string): string {
  return deslocarDecimal(fracao, 2) || '0'
}

export function percentualParaFracao(percentual: string): string {
  return deslocarDecimal(percentual, -2)
}

/** Valor digitado na tela → valor da API; null se inválido para o código. */
export function valorParametroParaApi(codigo: CodigoParametro, digitado: string): string | null {
  const limpo = digitado.trim().replace(',', '.')
  if (definicaoParametro(codigo).unidade === 'dias') return /^\d{1,6}$/.test(limpo) ? limpo.replace(/^0+(?=\d)/, '') : null
  if (!/^\d{1,3}(?:\.\d{1,4})?$/.test(limpo)) return null
  const fracao = percentualParaFracao(limpo)
  return fracao && percentualAte100(limpo) ? fracao : null
}

/** Valor da API → valor para o campo da tela (percentual ou dias). */
export function valorParametroParaTela(codigo: CodigoParametro, valor: string): string {
  return definicaoParametro(codigo).unidade === 'dias' ? deslocarDecimal(valor, 0) : fracaoParaPercentual(valor)
}

/** Margem digitada em % → fração (0 a 100%, até 4 casas); null se inválida. */
export function margemParaApi(digitada: string): string | null {
  const limpo = digitada.trim().replace(',', '.') || '0'
  if (!/^\d{1,3}(?:\.\d{1,4})?$/.test(limpo) || !percentualAte100(limpo)) return null
  return percentualParaFracao(limpo)
}

/** Taxa digitada → valor da API (positivo, até 8 inteiros e 6 casas); null se inválida. */
export function taxaParaApi(digitada: string): string | null {
  const limpo = digitada.trim().replace(',', '.')
  if (!/^\d{1,8}(?:\.\d{1,6})?$/.test(limpo) || !/[1-9]/.test(limpo)) return null
  return limpo.replace(/^0+(?=\d)/, '')
}

export function moedaValida(moeda: string): boolean {
  return /^[A-Z]{3}$/.test(moeda) && moeda !== 'BRL'
}

function percentualAte100(limpo: string): boolean {
  const [inteiro, fracao = ''] = limpo.split('.')
  const n = BigInt(inteiro)
  return n < 100n || (n === 100n && /^0*$/.test(fracao))
}
