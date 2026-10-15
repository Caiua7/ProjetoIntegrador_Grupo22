import { createContext } from 'react'
import type { Session } from '@supabase/supabase-js'
import type { SessaoUsuario } from '../../services/apiClient'

export type AuthContextValue = {
  session: Session | null
  usuario: SessaoUsuario | null
  accessError: string | null
  hasPermission: (codigo: string) => boolean
  loading: boolean
  recoveryMode: boolean
  isConfigured: boolean
  configurationMessage: string | null
  startupError: string | null
  statusMessage: string | null
  signIn: (email: string, password: string) => Promise<string | null>
  requestPasswordReset: (email: string) => Promise<string | null>
  updatePassword: (password: string) => Promise<string | null>
  signOut: () => Promise<string | null>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
