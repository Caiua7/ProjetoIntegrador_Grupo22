import { apiFetch } from '../../services/apiClient'

export type FonteCambio = 'manual' | 'ptax'

export type Cambio = {
  id: string
  moeda: string
  data_referencia: string
  /** Reais por unidade da moeda (NUMERIC 14,6 como string). */
  taxa: string
  /** Fração: 0.02 = 2%. */
  margem_seguranca_percentual: string
  fonte: FonteCambio
  created_at: string
  updated_at: string
}

export type CambioVigente = Cambio & { taxa_com_margem: string }

export type CambioEntrada = Pick<Cambio, 'moeda' | 'data_referencia' | 'taxa' | 'margem_seguranca_percentual' | 'fonte'>
export type CambioPatch = Partial<Pick<Cambio, 'taxa' | 'margem_seguranca_percentual' | 'fonte'>>

export type CodigoParametro =
  | 'perda_percentual'
  | 'taxa_financeira_mensal_percentual'
  | 'prazo_medio_padrao_dias'
  | 'desvio_maximo_cotacao_percentual'

export type ParametroGlobal = {
  id: string
  codigo: CodigoParametro
  valor: string
  vigencia_inicio: string
  created_at: string
  updated_at: string
}

export type ParametroEntrada = Pick<ParametroGlobal, 'codigo' | 'valor' | 'vigencia_inicio'>

export type ParametrosVigentes = {
  data_referencia: string
  parametros: Partial<Record<CodigoParametro, ParametroGlobal>>
  faltando: CodigoParametro[]
}

function query(params: Record<string, string | undefined>): string {
  const busca = new URLSearchParams()
  for (const [chave, valor] of Object.entries(params)) if (valor) busca.set(chave, valor)
  const texto = busca.toString()
  return texto ? `?${texto}` : ''
}

export function listarCambios(filtro: { moeda?: string, data_ate?: string } = {}): Promise<Cambio[]> {
  return apiFetch<Cambio[]>(`/cambios${query(filtro)}`)
}

export function consultarCambioVigente(moeda: string): Promise<CambioVigente> {
  return apiFetch<CambioVigente>(`/cambios/vigente${query({ moeda })}`)
}

export function criarCambio(entrada: CambioEntrada): Promise<Cambio> {
  return apiFetch<Cambio>('/cambios', { method: 'POST', body: JSON.stringify(entrada) })
}

export function corrigirCambio(id: string, entrada: CambioPatch): Promise<Cambio> {
  return apiFetch<Cambio>(`/cambios/${id}`, { method: 'PATCH', body: JSON.stringify(entrada) })
}

export function listarParametros(codigo?: CodigoParametro): Promise<ParametroGlobal[]> {
  return apiFetch<ParametroGlobal[]>(`/parametros-globais${query({ codigo })}`)
}

export function consultarParametrosVigentes(dataReferencia?: string): Promise<ParametrosVigentes> {
  return apiFetch<ParametrosVigentes>(`/parametros-globais/vigentes${query({ data_referencia: dataReferencia })}`)
}

export function criarVigenciaParametro(entrada: ParametroEntrada): Promise<ParametroGlobal> {
  return apiFetch<ParametroGlobal>('/parametros-globais', { method: 'POST', body: JSON.stringify(entrada) })
}

export function corrigirVigenciaParametro(id: string, valor: string): Promise<ParametroGlobal> {
  return apiFetch<ParametroGlobal>(`/parametros-globais/${id}`, { method: 'PATCH', body: JSON.stringify({ valor }) })
}
