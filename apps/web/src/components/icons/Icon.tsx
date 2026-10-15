/**
 * Ícones próprios do NeoPrice: grade de 24px, traço único de 1,75px, pontas e
 * junções arredondadas, sem preenchimento (currentColor).
 *
 * Os desenhos ficam em navegacao.tsx e acoes.tsx, com partes nomeadas (`a-*`)
 * que contam o que o ícone representa no hover ou foco do controle e no item
 * de menu ativo. As animações ficam em icons.css; parado, é só o desenho.
 */
import { acoes } from './acoes'
import { navegacao } from './navegacao'
import './icons.css'

const ICONS = { ...navegacao, ...acoes }

export type IconName = keyof typeof ICONS

export function Icon({ name, size = 18, className = '' }: { name: IconName, size?: number, className?: string }) {
  return <svg className={`ic ia ia-${name} ${className}`.trim()} width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {ICONS[name]}
  </svg>
}
