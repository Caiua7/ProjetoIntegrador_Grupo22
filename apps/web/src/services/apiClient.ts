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

async function send(path: string, init: RequestInit, token: string | null): Promise<Response> {
  const headers = new Headers(init.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  return fetch(`${apiUrl}${path}`, { ...init, headers })
}

function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') return body.detail
  return fallback
}

/**
 * Chama a API do NeoPrice com o token da sessão. Se a API responder 401,
 * renova a sessão uma vez e repete; se ainda assim falhar, encerra a sessão
 * e o app volta para o login.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await send(path, init, await accessToken())
    if (response.status === 401 && supabaseClient) {
      const { data } = await supabaseClient.auth.refreshSession()
      if (data.session) response = await send(path, init, data.session.access_token)
      if (response.status === 401) await supabaseClient.auth.signOut()
    }
  } catch {
    throw new ApiError(0, 'Não foi possível falar com a API do NeoPrice. Confira se ela está no ar.')
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, detailMessage(body, `Erro ${response.status} na API.`))
  return body as T
}

export function fetchSessaoUsuario(): Promise<SessaoUsuario> {
  return apiFetch<SessaoUsuario>('/auth/me')
}
