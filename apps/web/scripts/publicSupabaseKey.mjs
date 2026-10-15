export function isPrivilegedSupabaseKey(value) {
  if (/^sb_secret_/i.test(value.trim())) return true

  const payload = value.split('.')[1]
  if (!payload) return false

  try {
    const decoded = Buffer.from(payload, 'base64url').toString('utf8')
    return JSON.parse(decoded).role === 'service_role'
  } catch {
    return false
  }
}

export function assertPublicSupabaseKey(value) {
  if (value && isPrivilegedSupabaseKey(value)) {
    throw new Error('VITE_NEOPRICE_SUPABASE_ANON_KEY must be a public anon/publishable key; privileged keys are not allowed.')
  }
}
