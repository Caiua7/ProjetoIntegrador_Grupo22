import { apiFetch } from '../../services/apiClient'

export type RegimeTributario = 'lucro_real' | 'lucro_presumido' | 'simples_nacional'

export type AliquotaFiscal = {
  id: string
  uf_destino: string
  ncm_codigo: string | null
  regime_tributario: RegimeTributario
  vigencia_inicio: string
  pis_percentual: string
  cofins_percentual: string
  icms_percentual: string
  ipi_percentual: string
  icms_interno_percentual: string
  fcp_percentual: string
  mva_percentual: string
  created_at: string
  updated_at: string
}

export type AliquotaEntrada = Omit<AliquotaFiscal, 'id' | 'created_at' | 'updated_at'>
export type AliquotaPatch = Partial<AliquotaEntrada>

export type FiltroAliquota = {
  uf_destino?: string
  ncm_codigo?: string
  regime_tributario?: RegimeTributario
  vigencia_ate?: string
}

function queryString(filtro: FiltroAliquota): string {
  const parametros = new URLSearchParams()
  for (const [chave, valor] of Object.entries(filtro)) {
    if (valor) parametros.set(chave, valor)
  }
  const query = parametros.toString()
  return query ? `?${query}` : ''
}

export function listarAliquotas(filtro: FiltroAliquota): Promise<AliquotaFiscal[]> {
  return apiFetch<AliquotaFiscal[]>(`/parametros-fiscais/aliquotas${queryString(filtro)}`)
}

export function resolverAliquota(filtro: Required<Pick<FiltroAliquota, 'uf_destino' | 'ncm_codigo' | 'regime_tributario'>> & { data_referencia: string }): Promise<AliquotaFiscal> {
  return apiFetch<AliquotaFiscal>(`/parametros-fiscais/aliquotas/resolver${queryString(filtro)}`)
}

export function criarAliquota(entrada: AliquotaEntrada): Promise<AliquotaFiscal> {
  return apiFetch<AliquotaFiscal>('/parametros-fiscais/aliquotas', { method: 'POST', body: JSON.stringify(entrada) })
}

export function atualizarAliquota(id: string, entrada: AliquotaPatch): Promise<AliquotaFiscal> {
  return apiFetch<AliquotaFiscal>(`/parametros-fiscais/aliquotas/${id}`, { method: 'PATCH', body: JSON.stringify(entrada) })
}
