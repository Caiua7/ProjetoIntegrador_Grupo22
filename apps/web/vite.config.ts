import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import { assertPublicSupabaseKey } from './scripts/publicSupabaseKey.mjs'

const appRoot = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, appRoot, '')
  assertPublicSupabaseKey(env.VITE_NEOPRICE_SUPABASE_ANON_KEY ?? '')

  return {
    plugins: [react()],
    // Only inject the explicitly public values below. Other VITE_ variables
    // (including accidental secrets) are not exposed through import.meta.env.
    envPrefix: 'NEOPRICE_PUBLIC_ONLY_',
    define: {
      'import.meta.env.VITE_NEOPRICE_SUPABASE_URL': JSON.stringify(env.VITE_NEOPRICE_SUPABASE_URL ?? ''),
      'import.meta.env.VITE_NEOPRICE_SUPABASE_ANON_KEY': JSON.stringify(env.VITE_NEOPRICE_SUPABASE_ANON_KEY ?? ''),
      'import.meta.env.VITE_NEOPRICE_API_URL': JSON.stringify(env.VITE_NEOPRICE_API_URL ?? ''),
    },
  }
})
