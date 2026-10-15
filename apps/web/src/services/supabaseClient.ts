import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const projectUrl = import.meta.env.VITE_NEOPRICE_SUPABASE_URL?.trim() ?? ''
const publicKey = import.meta.env.VITE_NEOPRICE_SUPABASE_ANON_KEY?.trim() ?? ''

function getConfigurationMessage(): string | null {
  if (!projectUrl || !publicKey) {
    return 'Autenticação não configurada. Defina VITE_NEOPRICE_SUPABASE_URL e VITE_NEOPRICE_SUPABASE_ANON_KEY em apps/web/.env.local usando os valores públicos do projeto.'
  }

  try {
    const url = new URL(projectUrl)
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error()
  } catch {
    return 'A URL pública do Supabase está inválida. Confira a configuração local do frontend.'
  }

  return null
}

let configurationMessage = getConfigurationMessage()

let client: SupabaseClient | null = null
if (!configurationMessage) {
  try {
    client = createClient(projectUrl, publicKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  } catch {
    // Never include configuration values in logs or user-facing messages.
    configurationMessage = 'Não foi possível iniciar o cliente Supabase. Confira a configuração pública do frontend.'
  }
}

export const supabaseConfigurationMessage = configurationMessage
export const supabaseClient = client
export const isSupabaseConfigured = client !== null
