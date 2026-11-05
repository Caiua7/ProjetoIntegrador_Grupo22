import { apiFetch } from '../../services/apiClient'
import { caminhoComparacaoCenarios, caminhoDetalheCenario, caminhoDuplicacaoCenario, caminhoListaCenarios } from './cenariosPaths'

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

export type CenarioDetalhe = CenarioResumo & {
  entrada: Record<string, unknown>
  resultado: Record<string, unknown>
}

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
