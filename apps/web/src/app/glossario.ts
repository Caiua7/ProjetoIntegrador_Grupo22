/**
 * Siglas e termos do NeoPrice. Cada entrada aparece no tooltip do <Sigla>:
 * o nome por extenso e uma frase dizendo o que significa na precificação.
 */
export type Termo = { nome: string, explicacao: string, calculo?: string }

export const GLOSSARIO = {
  MaCo: {
    nome: 'Margem de Contribuição',
    explicacao: 'Quanto sobra da receita líquida depois dos custos variáveis. É o principal indicador de rentabilidade do cenário.',
    calculo: 'MaCo = ROL − (MP + embalagem + encargo + perda + comissão). Em %: MaCo ÷ preço bruto.',
  },
  ROB: {
    nome: 'Receita Operacional Bruta',
    explicacao: 'Faturamento total do cenário (preço bruto × volume), antes de descontar impostos.',
    calculo: 'ROB = preço sem IPI × volume.',
  },
  ROL: {
    nome: 'Receita Operacional Líquida',
    explicacao: 'Receita bruta menos os impostos sobre a venda.',
    calculo: 'ROL = preço sem IPI − ICMS − (preço sem IPI − ICMS) × (PIS + COFINS).',
  },
  MB: {
    nome: 'Margem Bruta',
    explicacao: 'Receita líquida menos o custo do produto vendido, em percentual.',
  },
  PB: {
    nome: 'Preço Bruto',
    explicacao: 'Preço unitário de venda com os impostos incluídos.',
    calculo: 'PB = preço com IPI + ICMS-ST (quando houver).',
  },
  NCM: {
    nome: 'Nomenclatura Comum do Mercosul',
    explicacao: 'Código de 8 dígitos que classifica o produto e define os impostos que incidem sobre ele.',
  },
  MP: {
    nome: 'Matéria-prima',
    explicacao: 'Insumo que entra na formulação do produto.',
  },
  UF: {
    nome: 'Unidade Federativa',
    explicacao: 'Estado de destino da venda; muda o ICMS aplicado.',
  },
  ICMS: {
    nome: 'Imposto sobre Circulação de Mercadorias e Serviços',
    explicacao: 'Imposto estadual cobrado na venda do produto.',
  },
  'ICMS-ST': {
    nome: 'ICMS por Substituição Tributária',
    explicacao: 'ICMS da cadeia inteira recolhido antecipadamente pelo fabricante.',
    calculo: 'ICMS-ST = preço com IPI × (1 + MVA) × (ICMS interno + FCP) − ICMS próprio.',
  },
  MVA: {
    nome: 'Margem de Valor Agregado',
    explicacao: 'Percentual usado para estimar o preço final ao consumidor no cálculo do ICMS-ST.',
  },
  FCP: {
    nome: 'Fundo de Combate à Pobreza',
    explicacao: 'Adicional de ICMS cobrado por alguns estados.',
  },
  IPI: {
    nome: 'Imposto sobre Produtos Industrializados',
    explicacao: 'Imposto federal sobre o produto industrializado.',
  },
  PIS: {
    nome: 'Programa de Integração Social',
    explicacao: 'Contribuição federal sobre a receita.',
  },
  COFINS: {
    nome: 'Contribuição para o Financiamento da Seguridade Social',
    explicacao: 'Contribuição federal sobre a receita.',
  },
  MDO: {
    nome: 'Mão de Obra',
    explicacao: 'Custo de mão de obra direta na produção.',
  },
  BI: {
    nome: 'Business Intelligence',
    explicacao: 'Ferramentas de análise de dados, como Power BI, que recebem os dados exportados.',
  },
  GGF: {
    nome: 'Gastos Gerais de Fabricação',
    explicacao: 'Custos indiretos da fábrica, como energia e manutenção, rateados por hora de produção.',
    calculo: 'GGF por unidade = taxa de GGF ÷ produtividade.',
  },
  MOD: {
    nome: 'Mão de Obra Direta',
    explicacao: 'Custo das pessoas que trabalham na linha de produção, por hora.',
    calculo: 'MOD por unidade = (taxa de MOD ÷ produtividade) × funcionários na linha.',
  },
  PBsIPI: {
    nome: 'Preço Bruto sem IPI',
    explicacao: 'Preço de venda com ICMS, PIS e COFINS embutidos, antes de somar o IPI.',
    calculo: '(custo total + margem × custo total + encargo) ÷ (1 − PIS − COFINS − ICMS − comissão − frete) − material do cliente − isenção de MOD.',
  },
  PBcIPI: {
    nome: 'Preço Bruto com IPI',
    explicacao: 'Preço sem IPI acrescido do IPI, que é calculado por fora.',
    calculo: 'PBcIPI = preço sem IPI × (1 + IPI).',
  },
  PBsIPIsEncargo: {
    nome: 'Preço Bruto sem IPI e sem Encargo',
    explicacao: 'Preço antes do encargo financeiro do prazo de pagamento.',
    calculo: 'custo total ÷ denominador − material do cliente − isenção de MOD.',
  },
  ST: {
    nome: 'Substituição Tributária',
    explicacao: 'Regime em que o fabricante recolhe antecipadamente o ICMS de toda a cadeia.',
  },
  DIFAL: {
    nome: 'Diferencial de Alíquota do ICMS',
    explicacao: 'Diferença entre a alíquota interna do estado de destino e a interestadual.',
  },
  PTAX: {
    nome: 'Taxa de câmbio de referência do Banco Central',
    explicacao: 'Média do dólar calculada pelo Banco Central, usada como referência para o câmbio.',
  },
  USD: {
    nome: 'Dólar americano',
    explicacao: 'Moeda de insumos importados; convertida em reais pelo câmbio vigente.',
  },
  BRL: {
    nome: 'Real brasileiro',
    explicacao: 'Moeda em que o preço final é calculado.',
  },
  EUR: {
    nome: 'Euro',
    explicacao: 'Moeda de insumos importados; convertida em reais pelo câmbio vigente.',
  },
  FOB: {
    nome: 'Free On Board',
    explicacao: 'Frete por conta do comprador: o preço vale com a mercadoria entregue na origem.',
  },
  CIF: {
    nome: 'Cost, Insurance and Freight',
    explicacao: 'Frete e seguro por conta do vendedor até o destino.',
  },
  CNPJ: {
    nome: 'Cadastro Nacional da Pessoa Jurídica',
    explicacao: 'Número de identificação da empresa na Receita Federal.',
  },
  CEP: {
    nome: 'Código de Endereçamento Postal',
    explicacao: 'Código do endereço; identifica o município e o estado do cliente.',
  },
  CSV: {
    nome: 'Comma-Separated Values',
    explicacao: 'Arquivo de texto em formato de tabela, aberto no Excel ou no Power BI.',
  },
  XLSX: {
    nome: 'Planilha do Excel',
    explicacao: 'Formato de planilha do Microsoft Excel.',
  },
  JSON: {
    nome: 'JavaScript Object Notation',
    explicacao: 'Formato de texto para troca de dados entre sistemas.',
  },
  PDF: {
    nome: 'Portable Document Format',
    explicacao: 'Formato de documento para enviar ou imprimir.',
  },
  API: {
    nome: 'Application Programming Interface',
    explicacao: 'Serviço que recebe os pedidos da tela e faz os cálculos e as gravações.',
  },
  MCP: {
    nome: 'Model Context Protocol',
    explicacao: 'Protocolo que conecta o Claude ao NeoPrice, com as mesmas permissões do seu cargo.',
  },
  IA: {
    nome: 'Inteligência Artificial',
    explicacao: 'Assistente que consulta e opera o sistema em linguagem natural.',
  },
  KPI: {
    nome: 'Key Performance Indicator',
    explicacao: 'Indicador usado para acompanhar o desempenho.',
  },
  CBS: {
    nome: 'Contribuição sobre Bens e Serviços',
    explicacao: 'Tributo federal da reforma tributária que substitui PIS e COFINS.',
  },
  IBS: {
    nome: 'Imposto sobre Bens e Serviços',
    explicacao: 'Tributo da reforma tributária que substitui ICMS e ISS.',
  },
  ISS: {
    nome: 'Imposto Sobre Serviços',
    explicacao: 'Imposto municipal sobre a prestação de serviços.',
  },
  PRC: {
    nome: 'Precificação',
    explicacao: 'Código de um estudo de preço (ex.: PRC-2026-0145).',
  },
  PA: {
    nome: 'Produto Acabado',
    explicacao: 'Código de um produto pronto para venda (ex.: PA-0003).',
  },
  EMB: {
    nome: 'Embalagem',
    explicacao: 'Código de uma embalagem (ex.: EMB-0001): pote, tampa, rótulo.',
  },
  'Break-even': {
    nome: 'Ponto de equilíbrio',
    explicacao: 'Volume mínimo em que a receita cobre todos os custos.',
  },
  Política: {
    nome: 'Política de margem',
    explicacao: 'MaCo mínima aceita pela empresa (hoje 24%). Abaixo disso o cenário precisa de aprovação do gerente.',
  },
} satisfies Record<string, Termo>

export type SiglaConhecida = keyof typeof GLOSSARIO

/** Nomes das contas do cálculo, reconhecidos na tela (sem diferenciar maiúsculas). */
export const CONTAS: Record<string, Termo> = {
  'custo total': { nome: 'Custo total', explicacao: 'Tudo o que o produto custa por unidade.', calculo: 'MP + embalagem + perda + MOD + GGF.' },
  'matéria-prima': { nome: 'Custo de matéria-prima', explicacao: 'Soma dos insumos da formulação.', calculo: 'Σ preço negociado × câmbio × (1 + margem de segurança) × quantidade.' },
  'embalagem': { nome: 'Custo de embalagem', explicacao: 'Embalagens da formulação.', calculo: 'Σ preço × quantidade × % de descarte.' },
  'perda': { nome: 'Custo de perda', explicacao: 'Material perdido na produção.', calculo: '(MP + embalagem − material do cliente) × % de perda.' },
  'mão de obra': { nome: 'Mão de obra direta (MOD)', explicacao: 'Custo das pessoas na linha, por unidade.', calculo: '(taxa de MOD ÷ produtividade) × funcionários na linha.' },
  'encargo financeiro': { nome: 'Encargo financeiro', explicacao: 'Custo de receber a prazo.', calculo: '(1 + taxa mensal)^(prazo médio ÷ 30) − 1.' },
  'encargo': { nome: 'Encargo financeiro', explicacao: 'Custo de receber a prazo.', calculo: '(1 + taxa mensal)^(prazo médio ÷ 30) − 1.' },
  'denominador': { nome: 'Denominador do preço', explicacao: 'O que sobra do preço depois de impostos, comissão, frete e margem. O preço é o custo dividido por ele.', calculo: '1 − [comissão + frete + margem × (1 − impostos) + impostos].' },
  'preço bruto': { nome: 'Preço bruto (PB)', explicacao: 'Preço final ao cliente, com todos os impostos.', calculo: 'PB = preço com IPI + ICMS-ST (quando houver).' },
  'preço sem ipi': { nome: 'Preço sem IPI (PBsIPI)', explicacao: 'Preço com ICMS, PIS e COFINS embutidos, antes do IPI.', calculo: '(custo total + margem × custo total + encargo) ÷ (1 − PIS − COFINS − ICMS − comissão − frete) − material do cliente − isenção de MOD.' },
  'preço com ipi': { nome: 'Preço com IPI (PBcIPI)', explicacao: 'Preço sem IPI acrescido do IPI.', calculo: 'preço sem IPI × (1 + IPI).' },
  'receita operacional bruta': { nome: 'Receita operacional bruta (ROB)', explicacao: 'Faturamento do cenário.', calculo: 'preço sem IPI × volume.' },
  'receita líquida': { nome: 'Receita operacional líquida (ROL)', explicacao: 'Receita depois dos impostos sobre a venda.', calculo: 'preço sem IPI − ICMS − (preço sem IPI − ICMS) × (PIS + COFINS).' },
  'receita operacional líquida': { nome: 'Receita operacional líquida (ROL)', explicacao: 'Receita depois dos impostos sobre a venda.', calculo: 'preço sem IPI − ICMS − (preço sem IPI − ICMS) × (PIS + COFINS).' },
  'deduções': { nome: 'Deduções', explicacao: 'Impostos sobre a receita. PIS e COFINS sem o ICMS na base (STF, Tema 69).', calculo: 'ICMS + (preço sem IPI − ICMS) × (PIS + COFINS).' },
  'margem de contribuição': { nome: 'Margem de contribuição (MaCo)', explicacao: 'Quanto sobra depois dos custos variáveis.', calculo: 'ROL − (MP + embalagem + encargo + perda + comissão). Em %: MaCo ÷ preço bruto.' },
  'margem bruta': { nome: 'Margem bruta', explicacao: 'Receita líquida menos o custo do produto.', calculo: 'ROL − custo total.' },
  'margem desejada': { nome: 'Margem desejada', explicacao: 'Margem que entra no denominador para formar o preço.', calculo: 'Aplicada sobre o custo total (base da margem).' },
  'comissão': { nome: 'Comissão', explicacao: 'Comissão do vendedor.', calculo: 'comissão % × preço bruto.' },
  'impostos destacados': { nome: 'Impostos destacados', explicacao: 'Quanto de cada imposto existe no preço.', calculo: 'ICMS = preço sem IPI × ICMS; PIS/COFINS sobre (preço sem IPI − ICMS); IPI = preço sem IPI × IPI; ICMS-ST = PB − preço com IPI.' },
}
