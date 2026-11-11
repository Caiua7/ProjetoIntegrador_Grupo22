/** Rótulos legíveis para os códigos que a API devolve (snake_case). */

export const MODALIDADE: Record<string, string> = {
  full_service_nacional: 'Full Service Nacional',
  full_service_exportacao: 'Full Service Exportação',
  industrializacao_por_encomenda: 'Industrialização por Encomenda',
}

export const REGIME: Record<string, string> = {
  lucro_real: 'Lucro Real',
  lucro_presumido: 'Lucro Presumido',
  simples_nacional: 'Simples Nacional',
}

export const FRETE: Record<string, string> = { cif: 'CIF', fob: 'FOB' }

/** Nomes dos campos do cabeçalho, para mensagens da API como "uf_destino". */
export const CAMPO: Record<string, string> = {
  cliente_id: 'Cliente',
  produto_id: 'Produto',
  modalidade_comercial: 'Modalidade comercial',
  uf_destino: 'UF de destino',
  frete: 'Frete (CIF/FOB)',
  regime_tributario: 'Regime tributário',
}

export const rotulo = (mapa: Record<string, string>, codigo: string | null | undefined) =>
  codigo ? mapa[codigo] ?? codigo.replaceAll('_', ' ') : '—'

/** "uf_destino" → "UF de destino"; frases da API passam como vieram. */
export const rotuloCampo = (texto: string) => CAMPO[texto] ?? texto
