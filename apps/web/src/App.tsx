import { useState } from 'react'
import './App.css'
import { canOpen, navigationFor, SCREEN_HEADER, type Screen } from './app/navigation'
import { Sidebar } from './components/layout/Sidebar'
import { Topbar, type Theme } from './components/layout/Topbar'
import { AccessDenied } from './features/auth/AccessDenied'
import { AuthProvider } from './features/auth/AuthProvider'
import { LoadingScreen } from './features/auth/LoadingScreen'
import LoginPage from './features/auth/LoginPage'
import PasswordRecoveryPage from './features/auth/PasswordRecoveryPage'
import { useAuth } from './features/auth/useAuth'
import { Dashboard } from './features/dashboard/Dashboard'
import { InsumosPage } from './features/cadastros/InsumosPage'
import PricingCreate from './features/pricing/PricingCreate'
import PricingList from './features/pricing/PricingList'
import type { ListPreset } from './features/pricing/listPreset'
import { TaxRatesPage } from './features/taxes/TaxRatesPage'

function App() {
  return <AuthProvider><AuthGate /></AuthProvider>
}

/** Decide entre carregamento, login, recuperação, acesso negado e o app. */
function AuthGate() {
  const { session, usuario, accessError, loading, recoveryMode, isConfigured, signOut } = useAuth()

  if (loading) return <LoadingScreen />
  if (recoveryMode) return <PasswordRecoveryPage />
  if (!isConfigured || !session) return <LoginPage />
  if (!usuario) return <AccessDenied message={accessError} onSignOut={() => { void signOut() }} />
  return <AppShell />
}

function AppShell() {
  const { usuario, hasPermission, signOut, statusMessage } = useAuth()
  const [screen, setScreen] = useState<Screen>('dashboard')
  // Filtro com que a lista abre; a chave remonta a lista a cada atalho do painel
  const [listPreset, setListPreset] = useState<{ key: number, preset: ListPreset }>({ key: 0, preset: {} })
  const openList = (preset: ListPreset = {}) => {
    setListPreset((atual) => ({ key: atual.key + 1, preset }))
    setScreen('pricing-list')
  }
  const [theme, setTheme] = useState<Theme>(() =>
    window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark',
  )

  // Guarda de rota: tela sem permissão cai no painel.
  const current: Screen = canOpen(screen, hasPermission) ? screen : 'dashboard'
  const header = SCREEN_HEADER[current]
  const section = navigationFor(hasPermission).find((group) => group.items.some((item) => item.id === current))?.title

  return <div className="neoprice" data-theme={theme}>
    <Sidebar groups={navigationFor(hasPermission)} current={current} usuario={usuario!} theme={theme}
      onNavigate={(destino) => (destino === 'pricing-list' ? openList() : setScreen(destino))} onSignOut={() => { void signOut() }} />

    <main className="main">
      <Topbar section={section} title={header.title} theme={theme} userName={usuario!.nome}
        onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')} />

      {statusMessage && <div className="auth-status-banner" role="status">{statusMessage}</div>}
      {current === 'dashboard' && <Dashboard nome={usuario!.nome} canCreate={canOpen('new-pricing', hasPermission)}
        onNewPricing={() => setScreen('new-pricing')} onOpenList={openList} />}
      {current === 'pricing-list' && <PricingList key={listPreset.key} preset={listPreset.preset} onNewPricing={() => setScreen('new-pricing')} />}
      {current === 'new-pricing' && <PricingCreate onCancel={() => setScreen('pricing-list')} />}
      {current === 'records' && <InsumosPage canEdit={hasPermission('cadastro.editar')} />}
      {current === 'taxes' && <TaxRatesPage canEdit={hasPermission('parametro_fiscal.editar')} />}
    </main>
  </div>
}

export default App
