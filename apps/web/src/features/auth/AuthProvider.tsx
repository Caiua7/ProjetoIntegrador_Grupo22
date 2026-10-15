import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { getAuthErrorMessage, type AuthErrorLike } from './authMessages'
import { isSupabaseConfigured, supabaseClient, supabaseConfigurationMessage } from '../../services/supabaseClient'
import { AuthContext, type AuthContextValue } from './authContext'

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

  useEffect(() => {
    if (!supabaseClient) return

    let active = true
    const { data: { subscription } } = supabaseClient.auth.onAuthStateChange((event, nextSession) => {
      if (!active) return
      setSession(nextSession)
      if (event === 'PASSWORD_RECOVERY') setRecoveryMode(true)
      if (event === 'SIGNED_OUT') {
        setRecoveryMode(false)
        setStatusMessage(null)
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

  const value = useMemo<AuthContextValue>(() => ({
    session,
    loading,
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
  }), [session, loading, recoveryMode, startupError, statusMessage])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
