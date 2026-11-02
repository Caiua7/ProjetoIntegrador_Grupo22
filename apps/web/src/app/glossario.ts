/**
 * Siglas e termos do NeoPrice. Cada entrada aparece no tooltip do <Sigla>:
 * o nome por extenso e uma frase dizendo o que significa na precificação.
 */
export type Termo = { nome: string, explicacao: string }

export const GLOSSARIO = {
  MaCo: {
    nome: 'Margem de Contribuição',
    explicacao: 'Quanto sobra da receita líquida depois dos custos variáveis. É o principal indicador de rentabilidade do cenário.',
  },
  ROB: {
    nome: 'Receita Operacional Bruta',
    explicacao: 'Faturamento total do cenário (preço bruto × volume), antes de descontar impostos.',
  },
  ROL: {
    nome: 'Receita Operacional Líquida',
    explicacao: 'Receita bruta menos os impostos sobre a venda.',
  },
  MB: {
    nome: 'Margem Bruta',
    explicacao: 'Receita líquida menos o custo do produto vendido, em percentual.',
  },
  PB: {
    nome: 'Preço Bruto',
    explicacao: 'Preço unitário de venda com os impostos incluídos.',
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
    nome: 'Mão de obra',
    explicacao: 'Custo de mão de obra direta na produção.',
  },
  BI: {
    nome: 'Business Intelligence',
    explicacao: 'Ferramentas de análise de dados, como Power BI, que recebem os dados exportados.',
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
