const base = (precificacaoId: string) => `/precificacoes/${encodeURIComponent(precificacaoId)}/cenarios`

export const caminhoListaCenarios = (precificacaoId: string, podeVerCusto: boolean) =>
  `${base(precificacaoId)}${podeVerCusto ? '' : '/precos'}`

export const caminhoSalvarCenario = (precificacaoId: string) => base(precificacaoId)

export const caminhoDetalheCenario = (precificacaoId: string, versao: number) =>
  `${base(precificacaoId)}/${versao}`

export const caminhoComparacaoCenarios = (precificacaoId: string, de: number, para: number) =>
  `${base(precificacaoId)}/comparacao?de=${de}&para=${para}`

export const caminhoDuplicacaoCenario = (precificacaoId: string, versao: number) =>
  `${caminhoDetalheCenario(precificacaoId, versao)}/duplicar`
