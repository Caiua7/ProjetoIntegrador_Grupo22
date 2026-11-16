import { useEffect, useState } from 'react'
import { AuthLayout } from './AuthLayout'
import { Icon } from '../../components/icons/Icon'
import { supabaseClient } from '../../services/supabaseClient'

type Detalhes = {
  cliente: string
  email: string
  escopos: string[]
}

/** Tela de consentimento do servidor OAuth do Supabase (conector MCP, #130). */
export function OAuthConsentPage() {
  const authorizationId = new URLSearchParams(window.location.search).get('authorization_id')
  const [detalhes, setDetalhes] = useState<Detalhes | null>(null)
  const [erro, setErro] = useState<string | null>(authorizationId ? null : 'Pedido de autorização inválido.')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (!authorizationId || !supabaseClient) return
    void supabaseClient.auth.oauth.getAuthorizationDetails(authorizationId).then(({ data, error }) => {
      if (error || !data) return setErro('Não foi possível carregar o pedido de autorização.')
      if ('redirect_url' in data && data.redirect_url) return window.location.assign(data.redirect_url)
      if (!('client' in data)) return setErro('Pedido de autorização inválido.')
      setDetalhes({
        cliente: data.client?.name || 'Aplicativo externo',
        email: data.user?.email ?? '',
        escopos: (data.scope ?? '').split(' ').filter(Boolean),
      })
    })
  }, [authorizationId])

  async function decidir(aprovar: boolean) {
    if (!authorizationId || !supabaseClient) return
    setEnviando(true)
    const oauth = supabaseClient.auth.oauth
    const { data, error } = aprovar
      ? await oauth.approveAuthorization(authorizationId, { skipBrowserRedirect: true })
      : await oauth.denyAuthorization(authorizationId, { skipBrowserRedirect: true })
    if (error || !data?.redirect_url) {
      setEnviando(false)
      return setErro('Não foi possível registrar sua decisão. Tente de novo.')
    }
    window.location.assign(data.redirect_url)
  }

  return <AuthLayout labelledBy="consent-title">
    <header className="auth-header">
      <span className="auth-header-icon"><Icon name="cadeado" size={22} /></span>
      <h1 id="consent-title">Autorizar acesso</h1>
      <p>
        {detalhes
          ? <><strong>{detalhes.cliente}</strong> quer acessar o NeoPrice com a sua conta{detalhes.email && <> ({detalhes.email})</>}. Ele verá e fará só o que o seu perfil permite.</>
          : 'Carregando o pedido de autorização…'}
      </p>
    </header>
    {detalhes && detalhes.escopos.length > 0 && (
      <p className="auth-message">Escopos: {detalhes.escopos.join(', ')}</p>
    )}
    {erro && <div className="auth-message auth-message-error" role="alert"><Icon name="alerta" size={16} />{erro}</div>}
    {detalhes && <>
      <button className="auth-submit" type="button" disabled={enviando} aria-busy={enviando} onClick={() => void decidir(true)}>Autorizar</button>
      <button className="auth-link" type="button" disabled={enviando} onClick={() => void decidir(false)}>Negar</button>
    </>}
  </AuthLayout>
}
