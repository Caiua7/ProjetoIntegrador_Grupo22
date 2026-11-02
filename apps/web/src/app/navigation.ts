import type { IconName } from '../components/icons/Icon'

/** Telas já implementadas; o resto do menu aparece desabilitado. */
export type Screen = 'dashboard' | 'pricing-list' | 'new-pricing' | 'records' | 'taxes'

export type NavItem = {
  id: string
  label: string
  icon: IconName
  /** Permissão nomeada exigida; null = todo usuário ativo. */
  permission: string | null
  /** Uma frase sobre o que a tela faz, mostrada no hover do menu. */
  description: string
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
    { id: 'dashboard', label: 'Painel', icon: 'painel', permission: null, description: 'Resumo da carteira: margem, pendências e últimas movimentações' },
    { id: 'pricing-list', label: 'Precificações', icon: 'precificacoes', permission: 'precificacao.ler', description: 'Todos os estudos de preço, com status e margem' },
    { id: 'new-pricing', label: 'Nova precificação', icon: 'nova', permission: 'precificacao.editar', description: 'Abrir um estudo de preço para um cliente e produto' },
    { id: 'scenario', label: 'Cenário aberto', icon: 'cenario', permission: 'precificacao.ler', description: 'Detalhe de um cenário: custos, impostos e margens' },
    { id: 'inverse', label: 'Modo inverso', icon: 'inverso', permission: 'precificacao.editar', description: 'Informe a margem desejada e descubra o preço' },
    { id: 'compare', label: 'Comparar cenários', icon: 'comparar', permission: 'precificacao.ler', description: 'Compare versões e cenários lado a lado' },
    { id: 'approvals', label: 'Aprovações', icon: 'aprovacoes', permission: 'precificacao.aprovar', description: 'Cenários esperando a sua decisão' },
    { id: 'proposal', label: 'Proposta comercial', icon: 'proposta', permission: 'precificacao.ler', description: 'Gere a proposta para enviar ao cliente' },
  ] },
  { title: 'Análises', items: [
    { id: 'break-even', label: 'Break-even', icon: 'equilibrio', permission: 'precificacao.ler', description: 'Volume mínimo para cobrir todos os custos' },
    { id: 'sensitivity', label: 'Sensibilidade', icon: 'sensibilidade', permission: 'precificacao.ler', description: 'Como câmbio e custos mexem na margem' },
    { id: 'bi', label: 'Exportar para BI', icon: 'exportar', permission: 'precificacao.ler', description: 'Exporte os dados para ferramentas de análise' },
  ] },
  { title: 'Cadastros', items: [
    { id: 'records', label: 'Matérias-primas e embalagens', icon: 'cadastros', permission: 'cadastro.ler', description: 'Matérias-primas e embalagens usadas nos produtos' },
    { id: 'quotes', label: 'Cotações', icon: 'cotacoes', permission: 'custo.ler', description: 'Preços negociados com fornecedores, por faixa de volume' },
    { id: 'import-quotes', label: 'Importar cotações', icon: 'importar', permission: 'custo.editar', description: 'Carregue cotações a partir de planilha' },
    { id: 'taxes', label: 'Tributos', icon: 'tributos', permission: 'parametro_fiscal.ler', description: 'Alíquotas de impostos por estado, NCM e regime' },
  ] },
  { title: 'Sistema', items: [
    { id: 'users', label: 'Usuários e perfis', icon: 'usuarios', permission: 'acesso.administrar', description: 'Quem acessa o sistema e com qual perfil' },
    { id: 'metadata', label: 'Metadados', icon: 'metadados', permission: 'acesso.administrar', description: 'Parâmetros gerais do sistema' },
    { id: 'audit', label: 'Auditoria', icon: 'auditoria', permission: 'acesso.administrar', description: 'Histórico de quem alterou o quê' },
    { id: 'settings', label: 'Ajustes', icon: 'ajustes', permission: null, description: 'Preferências da sua conta' },
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
