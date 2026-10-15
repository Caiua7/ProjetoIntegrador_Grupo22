export type AuthErrorLike = {
  code?: string | null
  name?: string | null
  status?: number | null
  message?: string | null
}

export function getAuthErrorMessage(error: AuthErrorLike): string {
  const code = error.code?.toLowerCase() ?? ''
  const message = error.message?.toLowerCase() ?? ''

  if (code === 'email_not_confirmed') {
    return 'Confirme seu e-mail antes de entrar. Verifique também a pasta de spam.'
  }
  if (code === 'invalid_credentials' || code === 'invalid_grant' || message.includes('invalid login credentials')) {
    return 'E-mail ou senha inválidos.'
  }
  if (code.includes('rate_limit') || code === 'over_request_rate_limit' || error.status === 429) {
    return 'Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.'
  }
  if (code === 'weak_password') {
    return 'A senha não atende aos requisitos configurados no Supabase.'
  }
  if (code === 'email_address_invalid' || code === 'validation_failed') {
    return 'Confira o formato do e-mail e tente novamente.'
  }
  if (error.name === 'AuthRetryableFetchError' || error.status === 0 || error.status === 502 || error.status === 503) {
    return 'Não foi possível conectar ao serviço de autenticação. Verifique a conexão e tente novamente.'
  }

  return 'Não foi possível concluir a solicitação de autenticação. Tente novamente.'
}
