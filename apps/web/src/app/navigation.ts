import type { IconName } from '../components/icons/Icon'

/** Telas já implementadas; o resto do menu aparece desabilitado. */
export type Screen = 'dashboard' | 'pricing-list' | 'new-pricing' | 'records' | 'taxes'

export type NavItem = {
  id: string
  label: string
  icon: IconName
  /** Permissão nomeada exigida; null = todo usuário ativo. */
  permission: string | null
}

export type NavGroup = { title: string, items: NavItem[] }

export const IMPLEMENTED_SCREENS: readonly Screen[] = ['dashboard', 'pricing-list', 'new-pricing', 'records', 'taxes']

export const SCREEN_HEADER: Record<Screen, { title: string, subtitle: string }> = {
  dashboard: { title: 'Painel', subtitle: 'Visão geral da sua carteira' },
  'pricing-list': { title: 'Precificações', subtitle: 'Cenários demonstrativos da carteira' },
  'new-pricing': { title: 'Nova precificação', subtitle: 'Cabeçalho comercial e fiscal do estudo' },
  records: { title: 'Matérias-primas e embalagens', subtitle: 'Cadastros de insumos' },
  taxes: { title: 'Alíquotas fiscais', subtitle: 'Parâmetros fiscais por vigência' },
}

export const NAVIGATION: NavGroup[] = [
  { title: 'Precificação', items: [
    { id: 'dashboard', label: 'Painel', icon: 'painel', permission: null },
    { id: 'pricing-list', label: 'Precificações', icon: 'precificacoes', permission: 'precificacao.ler' },
    { id: 'new-pricing', label: 'Nova precificação', icon: 'nova', permission: 'precificacao.editar' },
    { id: 'scenario', label: 'Cenário aberto', icon: 'cenario', permission: 'precificacao.ler' },
    { id: 'inverse', label: 'Modo inverso', icon: 'inverso', permission: 'precificacao.editar' },
    { id: 'compare', label: 'Comparar cenários', icon: 'comparar', permission: 'precificacao.ler' },
    { id: 'approvals', label: 'Aprovações', icon: 'aprovacoes', permission: 'precificacao.aprovar' },
    { id: 'proposal', label: 'Proposta comercial', icon: 'proposta', permission: 'precificacao.ler' },
  ] },
  { title: 'Análises', items: [
    { id: 'break-even', label: 'Break-even', icon: 'equilibrio', permission: 'precificacao.ler' },
    { id: 'sensitivity', label: 'Sensibilidade', icon: 'sensibilidade', permission: 'precificacao.ler' },
    { id: 'bi', label: 'Exportar para BI', icon: 'exportar', permission: 'precificacao.ler' },
  ] },
  { title: 'Cadastros', items: [
    { id: 'records', label: 'Matérias-primas e embalagens', icon: 'cadastros', permission: 'cadastro.ler' },
    { id: 'quotes', label: 'Cotações', icon: 'cotacoes', permission: 'custo.ler' },
    { id: 'import-quotes', label: 'Importar cotações', icon: 'importar', permission: 'custo.editar' },
    { id: 'taxes', label: 'Tributos', icon: 'tributos', permission: 'parametro_fiscal.ler' },
  ] },
  { title: 'Sistema', items: [
    { id: 'users', label: 'Usuários e perfis', icon: 'usuarios', permission: 'acesso.administrar' },
    { id: 'metadata', label: 'Metadados', icon: 'metadados', permission: 'acesso.administrar' },
    { id: 'audit', label: 'Auditoria', icon: 'auditoria', permission: 'acesso.administrar' },
    { id: 'settings', label: 'Ajustes', icon: 'ajustes', permission: null },
  ] },
]

export function isImplemented(id: string): id is Screen {
  return (IMPLEMENTED_SCREENS as readonly string[]).includes(id)
}

/** Grupos com só os itens que o perfil alcança; grupo vazio some. */
export function navigationFor(hasPermission: (codigo: string) => boolean): NavGroup[] {
  return NAVIGATION
    .map((group) => ({ ...group, items: group.items.filter((item) => item.permission === null || hasPermission(item.permission)) }))
    .filter((group) => group.items.length > 0)
}

export function canOpen(screen: Screen, hasPermission: (codigo: string) => boolean): boolean {
  return navigationFor(hasPermission).some((group) => group.items.some((item) => item.id === screen))
}
