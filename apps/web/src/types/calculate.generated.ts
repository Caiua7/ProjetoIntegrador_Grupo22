// GERADO A PARTIR DE packages/pricing-core/pricing_core/contracts.py
// NÃO EDITAR À MÃO — regenerar com `python scripts/generate_ts_types.py`.
//
// Esta versão foi escrita manualmente na Sprint 1 (antes do toolchain de
// geração estar rodando no CI) para o Squad B não ficar bloqueado. Ao
// rodar o script pela primeira vez, o diff contra este arquivo deve ser
// mínimo — se não for, o script está desatualizado, não este arquivo.
//
// Todo campo monetário/percentual é `string` (não `number`): o back-end
// serializa Decimal como string para não perder precisão em JSON/JS. Faça
// o parse com uma lib decimal (ex.: decimal.js), nunca com `Number()`
// direto, ou você reintroduz o mesmo problema de arredondamento que o
// motor foi desenhado para evitar (ver README.md, seção "Arquitetura").

export const ENGINE_CONTRACT_VERSION = "0.1.0-mock";

export type ModalidadeComercial =
  | "full_service_nacional"
  | "full_service_exportacao"
  | "industrializacao_por_encomenda";

export interface ItemInsumo {
  codigo: string;
  descricao?: string | null;
  preco_negociado: string;
  moeda: string;
  cambio: string;
  margem_seguranca_percentual: string;
  quantidade: string;
  percentual_descarte: string;
}

export interface ParametrosProducao {
  taxa_mod: string;
  taxa_ggf: string;
  produtividade: string;
  numero_funcionarios: string;
}

export interface ParametrosImpostos {
  pis_percentual: string;
  cofins_percentual: string;
  icms_percentual: string;
  ipi_percentual: string;
  icms_interno_percentual: string;
  fcp_percentual: string;
  mva_percentual: string;
}

export interface ParametrosComerciais {
  margem_desejada_percentual: string;
  comissao_percentual: string;
  frete_percentual: string;
  prazo_medio_dias: string;
  taxa_financeira_mensal_percentual: string;
}

export interface CalculateRequest {
  cenario_id?: string | null; // UUID
  cliente_uf: string; // 2 letras maiúsculas
  modalidade_comercial: ModalidadeComercial;
  regime_tributario: string;
  materiais_primas: ItemInsumo[];
  embalagens: ItemInsumo[];
  perda_percentual: string;
  material_fornecido_pelo_cliente: boolean;
  valor_material_cliente: string;
  producao: ParametrosProducao;
  impostos: ParametrosImpostos;
  comercial: ParametrosComerciais;
}

export interface ImpostosDestacados {
  pis_valor: string;
  cofins_valor: string;
  icms_valor: string;
  ipi_valor: string;
  icms_st_valor: string;
}

export interface IsencaoMaoDeObraInfo {
  aplicada: boolean;
  valor: string;
}

export interface CalculateMetadata {
  versao_motor: string;
  calculado_em: string; // ISO 8601
  /** true enquanto o motor real (US16/US19, Sprint 3) não estiver integrado */
  is_mock: boolean;
}

export interface CalculateResponse {
  custo_mp: string;
  custo_embalagem: string;
  custo_perda: string;
  custo_mod: string;
  custo_ggf: string;
  custo_total: string;
  denominador: string;
  encargo_financeiro_percentual: string;
  encargo_financeiro_valor: string;
  preco_bruto_sem_ipi_sem_encargo: string;
  preco_bruto_sem_ipi: string;
  preco_bruto_com_ipi: string;
  preco_bruto: string;
  preco_indicado: string;
  receita_operacional_liquida: string;
  margem_contribuicao_valor: string;
  margem_contribuicao_percentual: string;
  isencao_mao_de_obra: IsencaoMaoDeObraInfo;
  impostos_destacados: ImpostosDestacados;
  metadata: CalculateMetadata;
}

export type DomainErrorCodigo = "DENOMINADOR_INVALIDO" | "ENTRADA_INVALIDA";

export interface DomainErrorResponse {
  codigo: DomainErrorCodigo;
  mensagem: string;
  detalhes: Record<string, unknown>;
}
