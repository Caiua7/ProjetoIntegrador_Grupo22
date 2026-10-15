import { BrandMark } from '../../components/layout/Brand'
import { Spinner } from '../../components/Spinner'
import './auth.css'

export function LoadingScreen() {
  return <main className="auth-loading" role="status" aria-live="polite">
    <BrandMark tamanho={48} />
    <span><Spinner /> Carregando sua sessão…</span>
  </main>
}
