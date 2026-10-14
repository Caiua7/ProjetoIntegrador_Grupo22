import { useState } from 'react'
import './App.css'
import PricingCreate from './features/pricing/PricingCreate'
import PricingList from './features/pricing/PricingList'

type Screen = 'dashboard' | 'pricing-list' | 'new-pricing'

const navigation = [
  { title: 'Precificação', items: [
    { id: 'dashboard', label: 'Painel', icon: '◫' },
    { id: 'pricing-list', label: 'Precificações', icon: '▤' },
    { id: 'new-pricing', label: 'Nova precificação', icon: '+' },
    { id: 'scenario', label: 'Cenário aberto', icon: '◉' },
    { id: 'inverse', label: 'Modo inverso', icon: '⇄' },
    { id: 'compare', label: 'Comparar cenários', icon: '▥' },
    { id: 'approvals', label: 'Aprovações', icon: '✓' },
    { id: 'proposal', label: 'Proposta comercial', icon: '▧' },
  ] },
  { title: 'Análises', items: [
    { id: 'break-even', label: 'Break-even', icon: '⌁' },
    { id: 'sensitivity', label: 'Sensibilidade', icon: '◌' },
    { id: 'bi', label: 'Exportar para BI', icon: '↗' },
  ] },
  { title: 'Cadastros', items: [
    { id: 'records', label: 'Cadastros base', icon: '▦' },
    { id: 'quotes', label: 'Cotações', icon: '↻' },
    { id: 'import-quotes', label: 'Importar cotações', icon: '⇧' },
    { id: 'taxes', label: 'Tributos', icon: '%' },
  ] },
  { title: 'Sistema', items: [
    { id: 'users', label: 'Usuários e perfis', icon: '♙' },
    { id: 'metadata', label: 'Metadados', icon: '⚙' },
    { id: 'audit', label: 'Auditoria', icon: '◷' },
    { id: 'settings', label: 'Ajustes', icon: '⚙' },
  ] },
]

function App() {
  const [screen, setScreen] = useState<Screen>('dashboard')
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark',
  )

  const pageTitle: Record<Screen, string> = {
    dashboard: 'Painel',
    'pricing-list': 'Precificações',
    'new-pricing': 'Nova precificação',
  }
  const pageSubtitle: Record<Screen, string> = {
    dashboard: 'Terça, 15 de setembro de 2026',
    'pricing-list': 'Cenários demonstrativos da carteira',
    'new-pricing': 'Cabeçalho comercial e fiscal do estudo',
  }

  return (
    <div className="neoprice" data-theme={theme}>
      <aside className="sidebar">
        <a className="brand" href="#painel" onClick={(event) => { event.preventDefault(); setScreen('dashboard') }}>
          <span className="brand-icon" aria-hidden="true">N</span>
          <span><strong>NeoPrice</strong><small>Grupo 22 · PI VI</small></span>
        </a>

        <nav className="navigation" aria-label="Navegação principal">
          {navigation.map((group) => (
            <section className="nav-group" key={group.title}>
              <h2>{group.title}</h2>
              {group.items.map((item) => {
                const available = item.id === 'dashboard' || item.id === 'pricing-list' || item.id === 'new-pricing'
                const active = item.id === screen
                return <button
                  className={`nav-item${active ? ' active' : ''}`}
                  key={item.id}
                  type="button"
                  disabled={!available}
                  aria-current={active ? 'page' : undefined}
                  title={available ? item.label : 'Fora do fluxo implementado nesta etapa'}
                  onClick={() => available && setScreen(item.id as Screen)}
                ><span className="nav-icon" aria-hidden="true">{item.icon}</span><span>{item.label}</span></button>
              })}
            </section>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="avatar">RC</span>
          <span className="user-label"><strong>Rafael Costa</strong><small>Analista de Pricing · demonstração</small></span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><h1>{pageTitle[screen]}</h1><p>{pageSubtitle[screen]}</p></div>
          <div className="profile-actions">
            <button className="icon-button" type="button" aria-label={`Ativar tema ${theme === 'dark' ? 'claro' : 'escuro'}`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? '☼' : '☾'}
            </button>
            <button className="icon-button notification-button" type="button" aria-label="Notificações" title="Notificações indisponíveis nesta etapa">♧</button>
            <span className="avatar" aria-label="Rafael Costa">RC</span>
          </div>
        </header>

        {screen === 'dashboard' && <Dashboard onNewPricing={() => setScreen('new-pricing')} />}
        {screen === 'pricing-list' && <PricingList onNewPricing={() => setScreen('new-pricing')} />}
        {screen === 'new-pricing' && <PricingCreate onCancel={() => setScreen('pricing-list')} />}
      </main>
    </div>
  )
}

function Dashboard({ onNewPricing }: { onNewPricing: () => void }) {
  return <section className="content">
    <div className="welcome">
      <div><span className="eyebrow">VISÃO GERAL</span><h2>Visão geral da precificação</h2>
        <p>Acompanhe os cenários, a rentabilidade e as aprovações da sua carteira.</p></div>
      <button className="button primary" onClick={onNewPricing}><span aria-hidden="true">+</span> Nova precificação</button>
    </div>
    <div className="demo-notice"><span className="notice-dot" />Painel demonstrativo · os indicadores abaixo são dados ilustrativos do protótipo.</div>
    <div className="metrics">
      <article className="metric featured"><span>MaCo média — setembro</span><strong>26,8%</strong><small>Política mínima: 24% · 3 cenários abaixo</small></article>
      <article className="metric"><span>Cenários no mês</span><strong>34</strong><small>6 a mais que agosto</small></article>
      <article className="metric"><span>Aguardando aprovação</span><strong>7</strong><small>Mais antigo parado há 3 dias</small></article>
      <article className="metric"><span>ROB aprovada — trimestre</span><strong>R$ 2,43 mi</strong><small>MaCo absoluta de R$ 490 mil</small></article>
    </div>
    <article className="panel">
      <div><span className="eyebrow">PRÓXIMA ETAPA</span><h3>Comece um estudo de preço</h3><p>Informe os dados comerciais e fiscais para abrir uma nova precificação.</p></div>
      <button className="button secondary" onClick={onNewPricing}>Criar precificação <span aria-hidden="true">→</span></button>
    </article>
  </section>
}

export default App
