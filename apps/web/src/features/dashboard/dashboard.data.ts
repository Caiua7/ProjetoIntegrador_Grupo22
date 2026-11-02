/**
 * Números do painel. Até a API de precificação existir, saem das mesmas
 * precificações de demonstração da lista (pricingList.mock), para os dois
 * baterem; a série mensal é ilustrativa.
 */
import { pricingListDemo, type PricingListItem, type PricingStatus } from '../pricing/pricingList.mock'
import type { ListPreset } from '../pricing/listPreset'

export const POLITICA_MACO = 24

export type Formato = 'percentual' | 'inteiro' | 'moeda'

export type Indicador = {
  numero: number
  formato: Formato
  variacao: { texto: string, tendencia: 'alta' | 'baixa' | 'neutra', boa: boolean }
  ajuda: string
  serie: number[]
  /** Para onde o cartão leva: a lista de precificações já filtrada. */
  destino: ListPreset
  acao: string
}

export type MesMargem = { mes: string, maco: number, cenarios: number }

export const MARGEM_POR_MES: MesMargem[] = [
  { mes: 'mai', maco: 25.1, cenarios: 21 },
  { mes: 'jun', maco: 23.4, cenarios: 24 },
  { mes: 'jul', maco: 24.8, cenarios: 26 },
  { mes: 'ago', maco: 25.9, cenarios: 28 },
  { mes: 'set', maco: 26.8, cenarios: 34 },
  { mes: 'out', maco: 26.2, cenarios: 19 },
]

const media = (valores: number[]) => valores.reduce((soma, v) => soma + v, 0) / (valores.length || 1)

export const percentual = (valor: number) =>
  `${valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`

export const moedaCompacta = (valor: number) =>
  valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', notation: 'compact', maximumFractionDigits: 2 })

export function formatar(valor: number, formato: Formato) {
  if (formato === 'percentual') return percentual(valor)
  if (formato === 'moeda') return moedaCompacta(valor)
  return Math.round(valor).toLocaleString('pt-BR')
}

export function porStatus(itens: PricingListItem[] = pricingListDemo): Record<PricingStatus, number> {
  const contagem: Record<PricingStatus, number> = { draft: 0, approval: 0, approved: 0, rejected: 0 }
  for (const item of itens) contagem[item.status] += 1
  return contagem
}

export function abaixoDaPolitica(itens: PricingListItem[] = pricingListDemo) {
  return itens.filter((item) => item.status !== 'rejected' && item.contributionMarginPercent < POLITICA_MACO)
}

export function indicadores(itens: PricingListItem[] = pricingListDemo) {
  const aprovadas = itens.filter((item) => item.status === 'approved')
  const status = porStatus(itens)
  const atual = MARGEM_POR_MES.at(-1)!
  const anterior = MARGEM_POR_MES.at(-2)!
  const macoAtual = media(itens.filter((item) => item.status !== 'rejected').map((item) => item.contributionMarginPercent))
  const robAprovada = aprovadas.reduce((soma, item) => soma + item.grossOperatingRevenue, 0)
  const diferenca = macoAtual - anterior.maco
  const abaixo = abaixoDaPolitica(itens).length

  return {
    maco: {
      numero: macoAtual,
      formato: 'percentual',
      variacao: {
        texto: `${diferenca >= 0 ? '+' : ''}${diferenca.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p. vs. ${anterior.mes}`,
        tendencia: diferenca > 0 ? 'alta' : diferenca < 0 ? 'baixa' : 'neutra',
        boa: diferenca >= 0,
      },
      ajuda: `${abaixo} ${abaixo === 1 ? 'cenário' : 'cenários'} abaixo da política`,
      serie: MARGEM_POR_MES.map((m) => m.maco),
      destino: { abaixoDaPolitica: true },
      acao: 'Ver os que estão abaixo',
    },
    cenarios: {
      numero: atual.cenarios,
      formato: 'inteiro',
      variacao: { texto: `${anterior.cenarios} em ${anterior.mes}`, tendencia: 'neutra', boa: true },
      ajuda: 'Criados ou recalculados no mês',
      serie: MARGEM_POR_MES.map((m) => m.cenarios),
      destino: {},
      acao: 'Ver todas',
    },
    aprovacao: {
      numero: status.approval,
      formato: 'inteiro',
      variacao: { texto: 'mais antigo há 5 h', tendencia: 'neutra', boa: true },
      ajuda: 'Esperando o gerente comercial',
      serie: [3, 4, 2, 5, 3, status.approval],
      destino: { status: 'approval' },
      acao: 'Ver fila de aprovação',
    },
    rob: {
      numero: robAprovada,
      formato: 'moeda',
      variacao: { texto: `${aprovadas.length} cenários aprovados`, tendencia: 'neutra', boa: true },
      ajuda: 'Receita bruta dos cenários aprovados',
      serie: [3.1, 3.6, 4.2, 4.0, 4.6, robAprovada / 1e6],
      destino: { status: 'approved' },
      acao: 'Ver aprovadas',
    },
  } satisfies Record<string, Indicador>
}
