import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { getAuthErrorMessage, type AuthErrorLike } from './authMessages'
import { isSupabaseConfigured, supabaseClient, supabaseConfigurationMessage } from '../../services/supabaseClient'
import { AuthContext, type AuthContextValue } from './authContext'
import { fetchSessaoUsuario, type SessaoUsuario } from '../../services/apiClient'

function toAuthError(error: unknown): AuthErrorLike {
  if (error && typeof error === 'object') return error as AuthErrorLike
  return {}
}

function errorMessage(error: unknown): string {
  return getAuthErrorMessage(toAuthError(error))
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(isSupabaseConfigured)
  const [recoveryMode, setRecoveryMode] = useState(false)
  const [startupError, setStartupError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  // Resultado de /auth/me guardado junto com o id a que se refere: se o
  // usuário logado mudou, o resultado antigo deixa de valer sozinho.
  const [perfil, setPerfil] = useState<{ userId: string, usuario: SessaoUsuario | null, error: string | null } | null>(null)
  const signingOut = useRef(false)
  const userId = session?.user.id ?? null
  const perfilAtual = perfil && perfil.userId === userId ? perfil : null
  const usuario = perfilAtual?.usuario ?? null
  const accessError = perfilAtual?.error ?? null
  const loadingUsuario = userId !== null && perfilAtual === null

  useEffect(() => {
    if (!supabaseClient) return

    let active = true
    const { data: { subscription } } = supabaseClient.auth.onAuthStateChange((event, nextSession) => {
      if (!active) return
      setSession(nextSession)
      if (event === 'PASSWORD_RECOVERY') setRecoveryMode(true)
      if (event === 'SIGNED_OUT') {
        setRecoveryMode(false)
        // Saída que o usuário não pediu = a sessão expirou e não renovou.
        setStatusMessage(signingOut.current ? null : 'Sua sessão expirou. Entre novamente.')
        signingOut.current = false
      }
      setLoading(false)
    })

    void supabaseClient.auth.getSession().then(({ data, error }) => {
      if (!active) return
      setSession(data.session)
      setStartupError(error ? errorMessage(error) : null)
      setLoading(false)
    }).catch((error: unknown) => {
      if (!active) return
      setStartupError(errorMessage(error))
      setLoading(false)
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  // Perfil e permissões vêm da API; recarrega só quando muda o usuário logado,
  // não a cada renovação de token.
  useEffect(() => {
    if (!userId) return
    let active = true
    fetchSessaoUsuario()
      .then((dados) => { if (active) setPerfil({ userId, usuario: dados, error: null }) })
      .catch((error: unknown) => {
        if (!active) return
        const message = error instanceof Error ? error.message : 'Não foi possível carregar seu perfil.'
        setPerfil({ userId, usuario: null, error: message })
      })
    return () => { active = false }
  }, [userId])

  const value = useMemo<AuthContextValue>(() => ({
    session,
    usuario,
    accessError,
    hasPermission: (codigo) => usuario?.permissoes.includes(codigo) ?? false,
    loading: loading || loadingUsuario,
    recoveryMode,
    isConfigured: isSupabaseConfigured,
    configurationMessage: supabaseConfigurationMessage,
    startupError,
    statusMessage,
    async signIn(email, password) {
      if (!supabaseClient) return supabaseConfigurationMessage ?? 'Autenticação indisponível.'
      setStatusMessage(null)
      try {
        const { error } = await supabaseClient.auth.signInWithPassword({ email, password })
        return error ? getAuthErrorMessage(error) : null
      } catch (error) {
        return errorMessage(error)
      }
    },
    async requestPasswordReset(email) {
      if (!supabaseClient) return supabaseConfigurationMessage ?? 'Autenticação indisponível.'
      try {
        const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
          redirectTo: window.location.origin,
        })
        return error ? getAuthErrorMessage(error) : null
      } catch (error) {
        return errorMessage(error)
      }
    },
    async updatePassword(password) {
      if (!supabaseClient) return supabaseConfigurationMessage ?? 'Autenticação indisponível.'
      try {
        const { error } = await supabaseClient.auth.updateUser({ password })
        if (error) return getAuthErrorMessage(error)
        setStatusMessage('Senha atualizada. Sua sessão continua ativa.')
        setRecoveryMode(false)
        return null
      } catch (error) {
        return errorMessage(error)
      }
    },
    async signOut() {
      if (!supabaseClient) return supabaseConfigurationMessage ?? 'Autenticação indisponível.'
      signingOut.current = true
      try {
        const { error } = await supabaseClient.auth.signOut()
        const message = error ? getAuthErrorMessage(error) : null
        setStatusMessage(message)
        return message
      } catch (error) {
        const message = errorMessage(error)
        setStatusMessage(message)
        return message
      }
    },
  }), [session, usuario, accessError, loading, loadingUsuario, recoveryMode, startupError, statusMessage])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
