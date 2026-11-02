import * as Sentry from '@sentry/react'

/**
 * Sentry do front (issue #65). Só liga quando há VITE_SENTRY_DSN, ou seja, em
 * staging/produção; em local e nos testes não faz nada.
 */
export function iniciarObservabilidade(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN?.trim()
  if (!dsn) return
  Sentry.init({
    dsn,
    environment: import.meta.env.VITE_AMBIENTE?.trim() || import.meta.env.MODE,
    release: import.meta.env.VITE_VERSAO?.trim() || undefined,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.2,
  })
}

/** Id de correlação de uma chamada à API: vai no cabeçalho e aparece no log da API e no Sentry. */
export function novoIdCorrelacao(): string {
  return crypto.randomUUID().replaceAll('-', '')
}

export function registrarFalhaApi(status: number, path: string, requestId: string): void {
  if (status < 500) return
  Sentry.captureMessage(`API respondeu ${status} em ${path}`, {
    level: 'error',
    tags: { request_id: requestId, status: String(status) },
  })
}
