import { novoIdCorrelacao, registrarFalhaApi } from '../app/observabilidade'
import { supabaseClient } from './supabaseClient'

const apiUrl = (import.meta.env.VITE_NEOPRICE_API_URL?.trim() || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export type SessaoUsuario = {
  id: string
  nome: string
  email: string
  perfil_codigo: string
  perfil_nome: string
  permissoes: string[]
}

async function accessToken(): Promise<string | null> {
  if (!supabaseClient) return null
  const { data } = await supabaseClient.auth.getSession()
  return data.session?.access_token ?? null
}

async function send(path: string, init: RequestInit, token: string | null, requestId: string): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('X-Request-ID', requestId)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  return fetch(`${apiUrl}${path}`, { ...init, headers })
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') return body.detail
  if (body && typeof body === 'object' && 'detail' in body && body.detail && typeof body.detail === 'object') {
    const detalhe = body.detail
    if ('mensagem' in detalhe && typeof detalhe.mensagem === 'string') {
      const codigo = 'codigo' in detalhe && typeof detalhe.codigo === 'string' ? `${detalhe.codigo}: ` : ''
      return `${codigo}${detalhe.mensagem}`
    }
  }
  return fallback
}

/**
 * Cache curto de leituras: trocar de aba não refaz as mesmas chamadas.
 * Requisições iguais em andamento são compartilhadas. Qualquer escrita
 * (POST/PUT/PATCH/DELETE) ou sessão expirada limpa tudo, então a releitura
 * depois de salvar sempre vem da API.
 */
const CACHE_MS = 30_000
const cacheLeitura = new Map<string, { expira: number; promessa: Promise<unknown> }>()

export function limparCacheApi(): void {
  cacheLeitura.clear()
}

export function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const metodo = (init.method ?? 'GET').toUpperCase()
  if (metodo !== 'GET') {
    cacheLeitura.clear()
    return chamarApi<T>(path, init).finally(limparCacheApi)
  }
  const agora = Date.now()
  const guardado = cacheLeitura.get(path)
  if (guardado && guardado.expira > agora) return guardado.promessa as Promise<T>
  const promessa = chamarApi<T>(path, init)
  cacheLeitura.set(path, { expira: agora + CACHE_MS, promessa })
  promessa.catch(() => { if (cacheLeitura.get(path)?.promessa === promessa) cacheLeitura.delete(path) })
  return promessa
}

/**
 * Chama a API do NeoPrice com o token da sessão. Se a API responder 401,
 * renova a sessão uma vez e repete; se ainda assim falhar, encerra a sessão
 * e o app volta para o login.
 */
async function chamarApi<T>(path: string, init: RequestInit): Promise<T> {
  const requestId = novoIdCorrelacao()
  let response: Response
  try {
    response = await send(path, init, await accessToken(), requestId)
    if (response.status === 401 && supabaseClient) {
      const { data } = await supabaseClient.auth.refreshSession()
      if (data.session) response = await send(path, init, data.session.access_token, requestId)
      if (response.status === 401) { limparCacheApi(); await supabaseClient.auth.signOut() }
    }
  } catch {
    throw new ApiError(0, 'Não foi possível falar com a API do NeoPrice. Confira se ela está no ar.')
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) registrarFalhaApi(response.status, path, requestId)
  if (!response.ok) throw new ApiError(response.status, detailMessage(body, `Erro ${response.status} na API.`))
  return body as T
}

export function fetchSessaoUsuario(): Promise<SessaoUsuario> {
  // Sessão nova (login ou troca de usuário): nada do cache anterior vale.
  limparCacheApi()
  return apiFetch<SessaoUsuario>('/auth/me')
}
