import { apiFetch } from '../../services/apiClient'
import type { CalculateRequest, CalculateResponse } from '../../types/calculate.generated'

/** Executa o motor real da API. Premissas ainda não homologadas pelo PO seguem sinalizadas na resposta. */
export function calcularCenario(entrada: CalculateRequest): Promise<CalculateResponse> {
  return apiFetch<CalculateResponse>('/calculate', {
    method: 'POST', body: JSON.stringify(entrada),
  })
}
