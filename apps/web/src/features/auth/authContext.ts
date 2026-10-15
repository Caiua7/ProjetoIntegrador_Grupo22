import { createContext } from 'react'
import type { Session } from '@supabase/supabase-js'

export type AuthContextValue = {
  session: Session | null
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
