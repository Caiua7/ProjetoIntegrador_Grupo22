import { apiFetch } from '../../services/apiClient'
import { caminhoComparacaoCenarios, caminhoDetalheCenario, caminhoDuplicacaoCenario, caminhoListaCenarios, caminhoSalvarCenario } from './cenariosPaths'
import type { CalculateRequest } from '../../types/calculate.generated'

export type CenarioResumo = {
  id?: string
  precificacao_id?: string
  versao: number
  vigente: boolean
  cenario_origem_id?: string | null
  observacao?: string | null
  volume: string | null
  data_calculo: string
  versao_motor?: string
  preco_bruto: string
  preco_bruto_sem_ipi: string
  custo_total?: string
  margem_contribuicao_valor?: string
  margem_contribuicao_percentual?: string
  created_at: string
}

/** Valores em reais do cenário inteiro para o volume negociado (#64). */
export type RentabilidadeCenario = {
  volume: string
  receita_operacional_bruta: string
  deducoes: string
  receita_operacional_liquida: string
  margem_contribuicao: string
  margem_bruta: string
}

export type CenarioDetalhe = CenarioResumo & {
  entrada: Record<string, unknown>
  resultado: Record<string, unknown>
  rentabilidade: RentabilidadeCenario | null
}

export type CenarioSalvoSemCustos = Pick<CenarioResumo,
  'id' | 'precificacao_id' | 'versao' | 'vigente' | 'volume' | 'data_calculo' | 'versao_motor' | 'preco_bruto' | 'preco_bruto_sem_ipi' | 'created_at'
>

export type NovaVersaoCenario = { entrada: CalculateRequest, volume?: string | null, observacao?: string | null }

export type IndicadorCenario = {
  codigo: string
  rotulo: string
  unidade: 'un' | 'brl' | 'percentual'
  valor_de: string | null
  valor_para: string | null
  variacao: string | null
  variacao_percentual: string | null
  sentido: 'subiu' | 'desceu' | 'igual' | 'sem_base'
}

export type ComparacaoCenarios = {
  versao_de: number
  versao_para: number
  indicadores: IndicadorCenario[]
}

export const listarCenarios = (precificacaoId: string, podeVerCusto: boolean) =>
  apiFetch<CenarioResumo[]>(caminhoListaCenarios(precificacaoId, podeVerCusto))

export const consultarCenario = (precificacaoId: string, versao: number) =>
  apiFetch<CenarioDetalhe>(caminhoDetalheCenario(precificacaoId, versao))

export const compararCenarios = (precificacaoId: string, de: number, para: number) =>
  apiFetch<ComparacaoCenarios>(caminhoComparacaoCenarios(precificacaoId, de, para))

export const duplicarCenario = (precificacaoId: string, versao: number) =>
  apiFetch<CenarioDetalhe>(caminhoDuplicacaoCenario(precificacaoId, versao), {
    method: 'POST',
    body: JSON.stringify({}),
  })

export const salvarCenario = (precificacaoId: string, corpo: NovaVersaoCenario) =>
  apiFetch<CenarioDetalhe | CenarioSalvoSemCustos>(caminhoSalvarCenario(precificacaoId), {
    method: 'POST', body: JSON.stringify(corpo),
  })
