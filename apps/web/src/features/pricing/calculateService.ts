import { apiFetch } from '../../services/apiClient'
import type { CalculateRequest, CalculateResponse } from '../../types/calculate.generated'

/** A API atual retorna metadata.is_mock=true; o chamador deve sinalizar isso ao usuário. */
export function calcularCenario(entrada: CalculateRequest): Promise<CalculateResponse> {
  return apiFetch<CalculateResponse>('/calculate', {
    method: 'POST', body: JSON.stringify(entrada),
  })
}
