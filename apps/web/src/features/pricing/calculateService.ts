import { apiFetch } from '../../services/apiClient'
import type { CalculateRequest, CalculateResponseAutorizada } from '../../types/calculate.generated'

/** Executa o motor real da API. Premissas ainda não homologadas pelo PO seguem sinalizadas na resposta. */
export function calcularCenario(entrada: CalculateRequest): Promise<CalculateResponseAutorizada> {
  return apiFetch<CalculateResponseAutorizada>('/calculate', {
    method: 'POST', body: JSON.stringify(entrada),
  })
}

/** Rota separada de demonstração; o servidor aplica e identifica as assunções mock. */
export function calcularCenarioDemo(dados: Record<string, unknown>): Promise<CalculateResponseAutorizada> {
  return apiFetch<CalculateResponseAutorizada>('/calculate/demo', {
    method: 'POST', body: JSON.stringify({ dados }),
  })
}
