import { apiFetch } from '../../services/apiClient'
import { caminhoFila, type FilaAprovacao, type FiltrosFila } from './filaAprovacao'

export const consultarFila = (filtros: FiltrosFila) => apiFetch<FilaAprovacao>(caminhoFila(filtros))
