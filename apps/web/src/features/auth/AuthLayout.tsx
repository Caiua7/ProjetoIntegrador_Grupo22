import type { ReactNode } from 'react'
import { Icon, type IconName } from '../../components/icons/Icon'
import { Brand } from '../../components/layout/Brand'
import { ShowcaseBackdrop } from './ShowcaseBackdrop'
import './auth.css'

const highlights: { icon: IconName, title: string, text: string }[] = [
  { icon: 'comparar', title: 'Motor de cálculo auditável', text: 'Custo, impostos e margem com as mesmas regras em todo cenário.' },
  { icon: 'usuarios', title: 'Acesso por carteira', text: 'Cada pessoa enxerga só os clientes e as precificações que atende.' },
  { icon: 'auditoria', title: 'Aprovação com histórico', text: 'Toda alteração e decisão fica registrada para consulta.' },
]

/** Moldura das telas de acesso: vitrine do produto à esquerda, formulário à direita. */
export function AuthLayout({ children, labelledBy }: { children: ReactNode, labelledBy: string }) {
  return <main className="auth-page">
    <aside className="auth-showcase" aria-hidden="true">
      <ShowcaseBackdrop />
      <Brand tema="escuro" altura={28} />
      <div className="auth-showcase-body">
        <span className="eyebrow">PLATAFORMA DE PRICING</span>
        <h2>Preço certo,<br />margem protegida.</h2>
        <p>Do custo da formulação à proposta aprovada, em um só lugar.</p>
        <ul className="auth-highlights">
          {highlights.map((item, index) => <li key={item.title} style={{ animationDelay: `${.15 + index * .1}s` }}>
            <span className="auth-highlight-icon"><Icon name={item.icon} size={18} className="ia-tocar" /></span>
            <div><strong>{item.title}</strong><small>{item.text}</small></div>
          </li>)}
        </ul>
      </div>
      <small className="auth-showcase-foot">Grupo 22 · Projeto Integrador VI</small>
    </aside>

    <section className="auth-panel">
      <div className="auth-card" role="region" aria-labelledby={labelledBy}>
        <div className="auth-card-brand"><Brand altura={28} /></div>
        {children}
      </div>
    </section>
  </main>
}
