import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../../services/apiClient'
import { arredondarCentavos } from './centavos'
import { calcularCenario } from './calculateService'
import type { CalculateRequest, CalculateResponseAutorizada } from '../../types/calculate.generated'
import type { Precificacao } from './precificacoesService'
import { obterInsumo } from '../cadastros/insumosService'
import { obterFormulacao } from './formulacoesService'
import { resolverCotacao } from './cotacoesService'
import { multiplicarDecimais } from './decimalMath'
import { consultarCambioVigente, consultarParametrosVigentes } from '../parametros/parametrosService'
import { resolverAliquota } from '../taxes/taxRatesService'
import {
  compararCenarios,
  consultarCenario,
  duplicarCenario,
  listarCenarios,
  salvarCenario,
  type CenarioDetalhe,
  type CenarioResumo,
  type ComparacaoCenarios,
} from './cenariosService'

type Props = {
  precificacaoId: string
  codigo: string
  precificacao?: Precificacao
  canViewCost: boolean
  canEdit: boolean
  canReadCatalog: boolean
  canReadCambio: boolean
  canReadParametros: boolean
  canReadImpostos: boolean
  onClose: () => void
}

function decimal(value: string | null | undefined, maxDigits = 20): string {
  if (value == null) return '—'
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!match) return value
  const [, sign, whole, rawFraction = ''] = match
  const integer = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(BigInt(whole))
  const fraction = rawFraction.slice(0, maxDigits).replace(/0+$/, '')
  return `${sign}${integer}${fraction ? `,${fraction}` : ''}`
}
const moeda = (value: string | null | undefined) => value == null ? '—' : `R$ ${decimal(value)}`
function percentual(value: string | null, variacao = false): string {
  if (value == null) return '—'
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(value)
  if (!match) return value
  const [, sign, whole, fraction = ''] = match
  const digits = `${whole}${fraction}`
  const point = whole.length + 2
  const shifted = point >= digits.length
    ? `${digits}${'0'.repeat(point - digits.length)}`
    : `${digits.slice(0, point).replace(/^0+(?=\d)/, '')}.${digits.slice(point)}`
  return `${decimal(`${sign}${shifted}`)}${variacao ? ' p.p.' : '%'}`
}
const TAX_FIELDS = ['pis_percentual', 'cofins_percentual', 'icms_percentual', 'ipi_percentual', 'icms_interno_percentual', 'fcp_percentual', 'mva_percentual'] as const
const isRecord = (value: unknown): value is Record<string, unknown> => Boolean(value && typeof value === 'object' && !Array.isArray(value))
function dataLocalISO(): string {
  const agora = new Date()
  return `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, '0')}-${String(agora.getDate()).padStart(2, '0')}`
}
const linhasRentabilidade = [
  ['receita_operacional_bruta', 'ROB', 'Receita operacional bruta: preço sem IPI × volume'],
  ['deducoes', 'Deduções', 'PIS, COFINS e ICMS sobre a receita'],
  ['receita_operacional_liquida', 'ROL', 'Receita operacional líquida'],
  ['margem_contribuicao', 'MaCo absoluta', 'Margem de contribuição unitária × volume'],
  ['margem_bruta', 'Margem bruta', 'ROL menos o custo do produto'],
] as const
const sentido: Record<string, string> = { subiu: 'Subiu', desceu: 'Desceu', igual: 'Sem variação', sem_base: 'Sem base' }

function ScenarioHistoryPanel({ precificacaoId, codigo, precificacao, canViewCost, canEdit, canReadCatalog, canReadCambio, canReadParametros, canReadImpostos, onClose }: Props) {
  const [versoes, setVersoes] = useState<CenarioResumo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [erroDetalhe, setErroDetalhe] = useState<string | null>(null)
  const [erroComparacao, setErroComparacao] = useState<string | null>(null)
  const [versaoDetalhe, setVersaoDetalhe] = useState<number | null>(null)
  const [detalhe, setDetalhe] = useState<CenarioDetalhe | null>(null)
  const [de, setDe] = useState('')
  const [para, setPara] = useState('')
  const [comparacao, setComparacao] = useState<ComparacaoCenarios | null>(null)
  const [repetirDetalhe, setRepetirDetalhe] = useState(0)
  const [repetirComparacao, setRepetirComparacao] = useState(0)
  const [duplicando, setDuplicando] = useState<number | null>(null)
  const [entradaJson, setEntradaJson] = useState('')
  const [volume, setVolume] = useState('')
  const [observacao, setObservacao] = useState('')
  const [simulando, setSimulando] = useState(false)
  const [salvandoCenario, setSalvandoCenario] = useState(false)
  const [resultadoSimulacao, setResultadoSimulacao] = useState<CalculateResponseAutorizada | null>(null)
  const [erroSimulacao, setErroSimulacao] = useState<string | null>(null)
  const [entradaCalculada, setEntradaCalculada] = useState<CalculateRequest | null>(null)
  const [preparando, setPreparando] = useState(false)
  const [pendenciasPreparacao, setPendenciasPreparacao] = useState<string[]>([])

  async function prepararEntrada() {
    setPreparando(true); setErroSimulacao(null); setPendenciasPreparacao([])
    const pendencias: string[] = []
    let manual: Record<string, unknown> = {}
    try {
      const texto = entradaJson.trim()
      if (texto) {
        const parseado: unknown = JSON.parse(texto)
        if (!parseado || typeof parseado !== 'object' || Array.isArray(parseado)) throw new Error('A entrada atual precisa ser um objeto JSON.')
        manual = parseado as Record<string, unknown>
      }
      if (!precificacao) pendencias.push('Cabeçalho da precificação não disponível nesta tela.')
      const candidato: Record<string, unknown> = { ...manual }
      if (precificacao?.uf_destino) candidato.cliente_uf = precificacao.uf_destino
      else if (!candidato.cliente_uf) pendencias.push('UF de destino (cliente_uf).')
      if (precificacao?.modalidade_comercial) candidato.modalidade_comercial = precificacao.modalidade_comercial
      else if (!candidato.modalidade_comercial) pendencias.push('Modalidade comercial.')
      if (precificacao?.regime_tributario) candidato.regime_tributario = precificacao.regime_tributario
      else if (!candidato.regime_tributario) pendencias.push('Regime tributário do cliente.')

      let formulario: Awaited<ReturnType<typeof obterFormulacao>> | null = null
      if (precificacao?.produto_id) {
        try { formulario = await obterFormulacao(precificacao.produto_id) }
        catch (falha) { pendencias.push(`Formulação do produto: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`) }
      } else pendencias.push('Produto associado à precificação.')

      const materiais: Record<string, unknown>[] = []
      const embalagens: Record<string, unknown>[] = []
      if (formulario) {
        for (const item of formulario.itens) {
          const isMateria = item.tipo_insumo === 'materia_prima'
          const id = isMateria ? item.materia_prima_id : item.embalagem_id
          if (!id || !canReadCatalog) {
            pendencias.push(`${isMateria ? 'Código' : 'Código'} do insumo ${id ?? '(sem referência)'}.`)
            continue
          }
          let insumo
          try { insumo = await obterInsumo(isMateria ? 'materias-primas' : 'embalagens', id) }
          catch (falha) { pendencias.push(`Dados do insumo ${id}: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`); continue }
          const listaManual = isMateria ? manual.materiais_primas : manual.embalagens
          const itemManual = Array.isArray(listaManual) ? listaManual.find((linha) => isRecord(linha) && linha.codigo === insumo.codigo) : undefined
          const entradaItem: Record<string, unknown> = { ...(isRecord(itemManual) ? itemManual : {}), codigo: insumo.codigo, descricao: insumo.descricao, quantidade: item.quantidade }
          if (isMateria) {
            entradaItem.margem_seguranca_percentual ??= ''
            if (canViewCost && item.unidade_medida === 'kg' && insumo.unidade_medida === 'kg' && volume) {
              try {
                const cotacao = await resolverCotacao(id, multiplicarDecimais(item.quantidade, volume))
                entradaItem.preco_negociado = cotacao.preco
                entradaItem.moeda = cotacao.moeda
                if (cotacao.moeda === 'BRL') entradaItem.cambio = '1'
                else if (canReadCambio) entradaItem.cambio = (await consultarCambioVigente(cotacao.moeda)).taxa_com_margem
                else { entradaItem.cambio = ''; pendencias.push(`Câmbio vigente de ${cotacao.moeda} para ${insumo.codigo}; falta a permissão cambio.ler.`) }
              } catch (falha) {
                entradaItem.preco_negociado ??= ''
                entradaItem.moeda ??= ''
                entradaItem.cambio ??= ''
                pendencias.push(`Cotação de ${insumo.codigo}: ${falha instanceof ApiError ? falha.message : 'não foi possível resolver; verifique vigência, volume e fornecedor.'}`)
              }
            } else if (!canViewCost) {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push(`Preço de compra de ${insumo.codigo}; cotação exige custo.ler.`)
            } else if (item.unidade_medida !== 'kg' || insumo.unidade_medida !== 'kg') {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push(`Cotação de ${insumo.codigo}; unidade da formulação deve corresponder à unidade de volume suportada pela cotação.`)
            } else {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push(`Cotação de ${insumo.codigo}; informe o volume negociado para resolver a faixa.`)
            }
            materiais.push(entradaItem)
          } else {
            entradaItem.preco_negociado ??= ''
            entradaItem.moeda ??= ''
            entradaItem.cambio ??= ''
            entradaItem.margem_seguranca_percentual ??= ''
            entradaItem.percentual_descarte ??= ''
            embalagens.push(entradaItem)
            pendencias.push(`Preço negociado da embalagem ${insumo.codigo}; a API de cotações não oferece cotação de embalagens.`)
            pendencias.push(`Descarte da embalagem ${insumo.codigo}; a formulação armazena perda percentual, cujo mapeamento para percentual_descarte precisa ser confirmado.`)
          }
        }
      }
      if (formulario) {
        candidato.materiais_primas = materiais
        candidato.embalagens = embalagens
      }

      const comerciais = manual.comercial && typeof manual.comercial === 'object' && !Array.isArray(manual.comercial) ? manual.comercial as Record<string, unknown> : {}
      const impostosManuais = manual.impostos && typeof manual.impostos === 'object' && !Array.isArray(manual.impostos) ? manual.impostos as Record<string, unknown> : {}
      const comercial: Record<string, unknown> = { ...comerciais }
      let impostos: Record<string, unknown> = { ...impostosManuais }
      if (canReadParametros) {
        try {
          const vigentes = await consultarParametrosVigentes()
          const perda = vigentes.parametros.perda_percentual?.valor
          const taxa = vigentes.parametros.taxa_financeira_mensal_percentual?.valor
          const prazo = vigentes.parametros.prazo_medio_padrao_dias?.valor
          if (perda) candidato.perda_percentual = perda
          if (taxa) comercial.taxa_financeira_mensal_percentual = taxa
          if (prazo) comercial.prazo_medio_dias = prazo
          for (const codigo of ['perda_percentual', 'taxa_financeira_mensal_percentual', 'prazo_medio_padrao_dias'] as const) {
            if (vigentes.faltando.includes(codigo)) pendencias.push(`Parâmetro global sem vigência: ${codigo}.`)
          }
        } catch (falha) { pendencias.push(`Parâmetros globais: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`) }
      } else pendencias.push('Parâmetros globais; falta a permissão parametro_global.ler.')
      for (const [campo, label] of [
        ['taxa_financeira_mensal_percentual', 'Taxa financeira mensal'], ['prazo_medio_dias', 'Prazo médio'],
      ] as const) {
        if (comercial[campo] == null || comercial[campo] === '') {
          comercial[campo] = ''
          pendencias.push(`${label}; informe o valor global vigente ou o valor aprovado para o cenário.`)
        }
      }

      const ncm = precificacao?.produto?.ncm_codigo
      if (canReadImpostos && precificacao?.uf_destino && precificacao.regime_tributario && ncm) {
        try {
          const aliquota = await resolverAliquota({ uf_destino: precificacao.uf_destino, ncm_codigo: ncm, regime_tributario: precificacao.regime_tributario, data_referencia: dataLocalISO() })
          impostos = {
            ...impostos,
            pis_percentual: aliquota.pis_percentual,
            cofins_percentual: aliquota.cofins_percentual,
            icms_percentual: aliquota.icms_percentual,
            ipi_percentual: aliquota.ipi_percentual,
            icms_interno_percentual: aliquota.icms_interno_percentual,
            fcp_percentual: aliquota.fcp_percentual,
            mva_percentual: aliquota.mva_percentual,
          }
        } catch (falha) { pendencias.push(`Alíquota de venda: ${falha instanceof ApiError ? falha.message : 'não foi possível resolver para UF, NCM e regime.'}`) }
      } else pendencias.push('NCM do produto, UF, regime e permissão parametro_fiscal.ler para resolver impostos de venda.')

      const producaoManual = isRecord(manual.producao) ? manual.producao : {}
      candidato.producao = {
        taxa_mod: producaoManual.taxa_mod ?? '', taxa_ggf: producaoManual.taxa_ggf ?? '',
        produtividade: producaoManual.produtividade ?? '', numero_funcionarios: producaoManual.numero_funcionarios ?? '',
      }
      for (const campo of ['taxa_mod', 'taxa_ggf', 'produtividade', 'numero_funcionarios']) {
        if (producaoManual[campo] == null || producaoManual[campo] === '') pendencias.push(`Parâmetro de produção ${campo}; não há API cadastrada para esse campo.`)
      }
      for (const campo of ['margem_desejada_percentual', 'comissao_percentual', 'frete_percentual']) {
        if (comercial[campo] == null || comercial[campo] === '') {
          comercial[campo] = ''
          const label = campo === 'margem_desejada_percentual' ? 'Margem desejada' : campo === 'comissao_percentual' ? 'Comissão percentual' : 'Frete percentual (o cabeçalho só informa CIF/FOB)'
          pendencias.push(`${label}; não há valor correspondente no cabeçalho nem parâmetro vigente.`)
        }
      }
      for (const campo of TAX_FIELDS) if (impostos[campo] == null || impostos[campo] === '') impostos[campo] = ''
      for (const campo of TAX_FIELDS) if (impostos[campo] === '') pendencias.push(`Alíquota ${campo}; não foi resolvida automaticamente.`)
      if (candidato.perda_percentual == null || candidato.perda_percentual === '') candidato.perda_percentual = ''
      if (candidato.material_fornecido_pelo_cliente == null) candidato.material_fornecido_pelo_cliente = ''
      if (candidato.valor_material_cliente == null || candidato.valor_material_cliente === '') candidato.valor_material_cliente = ''
      if (candidato.perda_percentual === '') pendencias.push('Perda percentual; informe a vigência global ou o valor aprovado para este cenário.')
      if (candidato.material_fornecido_pelo_cliente === '') pendencias.push('Informe se há material fornecido pelo cliente; o formulário não presume false.')
      if (candidato.valor_material_cliente === '') pendencias.push('Valor do material fornecido pelo cliente; o motor ainda recebe um valor global, não por matéria-prima.')

      candidato.comercial = comercial
      candidato.impostos = impostos
      setEntradaJson(JSON.stringify(candidato, null, 2))
      setPendenciasPreparacao([...new Set(pendencias)])
    } catch (falha) {
      setErroSimulacao(falha instanceof Error ? falha.message : 'Não foi possível preparar a entrada com as APIs disponíveis.')
    } finally { setPreparando(false) }
  }

  async function simular(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErroSimulacao(null); setResultadoSimulacao(null); setEntradaCalculada(null); setSimulando(true)
    try {
      const campos = JSON.parse(entradaJson) as Partial<CalculateRequest>
      const entrada = {
        ...campos,
        ...(precificacao?.uf_destino ? { cliente_uf: precificacao.uf_destino } : {}),
        ...(precificacao?.modalidade_comercial ? { modalidade_comercial: precificacao.modalidade_comercial } : {}),
        ...(precificacao?.regime_tributario ? { regime_tributario: precificacao.regime_tributario } : {}),
      } as CalculateRequest
      const resposta = await calcularCenario(entrada)
      setResultadoSimulacao(resposta)
      setEntradaCalculada(entrada)
    } catch (falha) {
      setErroSimulacao(falha instanceof ApiError ? falha.message : falha instanceof SyntaxError ? 'A entrada precisa ser um JSON válido no formato de POST /calculate.' : 'Não foi possível executar a simulação.')
    } finally { setSimulando(false) }
  }

  async function persistirSimulacao() {
    if (!entradaCalculada || !resultadoSimulacao || resultadoSimulacao.metadata.is_mock) return
    setErroSimulacao(null); setSalvandoCenario(true)
    try {
      await salvarCenario(precificacaoId, { entrada: entradaCalculada, volume: volume || null, observacao: observacao || null })
      await atualizar()
      setResultadoSimulacao(null); setEntradaCalculada(null); setEntradaJson(''); setVolume(''); setObservacao('')
    } catch (falha) { setErroSimulacao(falha instanceof ApiError ? falha.message : 'Não foi possível salvar o cenário.') }
    finally { setSalvandoCenario(false) }
  }

  async function atualizar(): Promise<CenarioResumo[] | null> {
    setErro(null)
    setCarregando(true)
    try {
      const lista = await listarCenarios(precificacaoId, canViewCost)
      setVersoes(lista)
      setDe((atual) => lista.some((item) => String(item.versao) === atual) ? atual : (lista.length > 1 ? String(lista[1].versao) : ''))
      setPara((atual) => lista.some((item) => String(item.versao) === atual) ? atual : (lista.length > 0 ? String(lista[0].versao) : ''))
      return lista
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : 'Não foi possível carregar as versões.')
      return null
    } finally {
      setCarregando(false)
    }
  }

  useEffect(() => {
    let ativo = true
    listarCenarios(precificacaoId, canViewCost).then((lista) => {
      if (!ativo) return
      setVersoes(lista)
      setDe((atual) => lista.some((item) => String(item.versao) === atual) ? atual : (lista.length > 1 ? String(lista[1].versao) : ''))
      setPara((atual) => lista.some((item) => String(item.versao) === atual) ? atual : (lista.length > 0 ? String(lista[0].versao) : ''))
    }).catch((falha: unknown) => {
      if (ativo) setErro(falha instanceof ApiError ? falha.message : 'Não foi possível carregar as versões.')
    }).finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
  }, [precificacaoId, canViewCost])

  useEffect(() => {
    if (versaoDetalhe == null || !canViewCost) {
      return
    }
    let ativo = true
    consultarCenario(precificacaoId, versaoDetalhe).then((value) => { if (ativo) setDetalhe(value) })
      .catch((falha: unknown) => { if (ativo) setErroDetalhe(falha instanceof ApiError ? falha.message : 'Não foi possível abrir a versão.') })
    return () => { ativo = false }
  }, [precificacaoId, versaoDetalhe, canViewCost, repetirDetalhe])

  useEffect(() => {
    if (!canViewCost || !de || !para || de === para) {
      return
    }
    let ativo = true
    compararCenarios(precificacaoId, Number(de), Number(para)).then((value) => { if (ativo) setComparacao(value) })
      .catch((falha: unknown) => { if (ativo) { setComparacao(null); setErroComparacao(falha instanceof ApiError ? falha.message : 'Não foi possível comparar as versões.') } })
    return () => { ativo = false }
  }, [precificacaoId, canViewCost, de, para, repetirComparacao])

  async function duplicar(versao: number) {
    setDuplicando(versao)
    setErro(null)
    try {
      const novo = await duplicarCenario(precificacaoId, versao)
      setVersaoDetalhe(null)
      const lista = await atualizar()
      if (lista?.some((item) => item.versao === novo.versao)) {
        if (canViewCost) {
          setVersaoDetalhe(novo.versao)
          setPara(String(novo.versao))
        }
      } else if (lista) {
        setErro('A versão foi criada, mas não apareceu na atualização do histórico.')
      }
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : 'Não foi possível duplicar a versão.')
    } finally {
      setDuplicando(null)
    }
  }

  const resultado = detalhe?.resultado
  const metadata = resultado?.metadata as { is_mock?: boolean; versao_motor?: string } | undefined
  const impostos = resultado?.impostos_destacados as Record<string, string> | undefined
  const detalheAtual = detalhe?.versao === versaoDetalhe ? detalhe : null

  return <section className="form-card scenario-history" aria-labelledby="scenario-history-title">
    <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">◷</span><h3 id="scenario-history-title">Cenários de {codigo}</h3></div><button className="button secondary" type="button" onClick={onClose}>Fechar</button></div>
    {canEdit && <section className="scenario-simulation" aria-label="Simular com o motor de precificação">
      <h4>Nova simulação</h4>
      {precificacao && <p className="field-hint">UF de destino, modalidade comercial e regime tributário serão preenchidos do cabeçalho salvo. {precificacao.uf_destino ? `UF: ${precificacao.uf_destino}. ` : 'UF de destino ausente no cabeçalho. '}{precificacao.modalidade_comercial} · {precificacao.regime_tributario ?? 'regime ausente'}.</p>}
      <p className="field-hint">Complete os demais campos de <code>CalculateRequest</code>. A formulação não contém preços unitários; embalagens não têm endpoint de cotação; e faltam parâmetros de produção, NCM do produto, margem desejada, comissão e frete percentual. Os valores são enviados à API; nenhum cálculo é feito no navegador.</p>
      <button className="button secondary" type="button" disabled={preparando || simulando || salvandoCenario} onClick={() => { void prepararEntrada() }}>{preparando ? 'Consultando APIs…' : 'Preparar entrada com dados existentes'}</button>
      {pendenciasPreparacao.length > 0 && <div className="catalog-error" role="status"><strong>Informações que ainda precisam ser preenchidas ou resolvidas:</strong><ul>{pendenciasPreparacao.map((item) => <li key={item}>{item}</li>)}</ul></div>}
      <form onSubmit={(event) => { void simular(event) }}>
        <label className="field">Demais campos da entrada JSON<textarea rows={12} required value={entradaJson} onChange={(event) => setEntradaJson(event.target.value)} placeholder="Informe materiais_primas, embalagens, perda_percentual, origem/valor de material do cliente, producao, impostos e comercial. O cabeçalho é aplicado automaticamente quando disponível." /></label>
        <div className="scenario-compare-controls">
          <label className="field">Volume negociado (opcional)<input inputMode="decimal" value={volume} onChange={(event) => setVolume(event.target.value)} /></label>
          <label className="field">Observação (opcional)<input maxLength={500} value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
        </div>
        <button className="button primary" type="submit" disabled={simulando || salvandoCenario}>{simulando ? 'Calculando…' : 'Calcular no motor'}</button>
      </form>
      {erroSimulacao && <p className="catalog-error" role="alert">{erroSimulacao}</p>}
      {resultadoSimulacao && <div className="scenario-detail" aria-live="polite">
        {resultadoSimulacao.metadata.is_mock && <p className="catalog-error" role="status">A API identificou este resultado como mock. Ele não será tratado como resultado real nem poderá ser salvo.</p>}
        <p className="field-hint">Motor {resultadoSimulacao.metadata.versao_motor} · {resultadoSimulacao.metadata.is_mock ? 'demonstrativo' : 'resposta da API'}</p>
        <dl className="scenario-result-grid">{([
          ['preco_bruto_sem_ipi_sem_encargo', 'PBsIPIsEncargo'], ['preco_bruto_sem_ipi', 'PBsIPI'], ['preco_bruto_com_ipi', 'PBcIPI'], ['preco_bruto', 'PB'], ['receita_operacional_liquida', 'ROL'],
        ] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{moeda(resultadoSimulacao[key])}</dd></div>)}
          {canViewCost && 'custo_total' in resultadoSimulacao && <>{([
            ['custo_mp', 'Custo MP'], ['custo_embalagem', 'Custo embalagem'], ['custo_perda', 'Custo perda'], ['custo_mod', 'Custo MOD'], ['custo_ggf', 'Custo GGF'], ['custo_total', 'Custo total'],
          ] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{moeda(resultadoSimulacao[key])}</dd></div>)}
          <div><dt>MaCo</dt><dd>{moeda(resultadoSimulacao.margem_contribuicao_valor)}</dd></div><div><dt>MaCo percentual</dt><dd>{percentual(resultadoSimulacao.margem_contribuicao_percentual)}</dd></div></>}
        </dl>
        <div className="scenario-tax-list"><h4>Impostos destacados</h4>{Object.entries(resultadoSimulacao.impostos_destacados).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: {moeda(value)}</p>)}</div>
        {!resultadoSimulacao.metadata.is_mock && <button className="button secondary" type="button" disabled={salvandoCenario} onClick={() => { void persistirSimulacao() }}>{salvandoCenario ? 'Salvando versão…' : 'Salvar como nova versão'}</button>}
      </div>}
    </section>}
    {erro && <div className="catalog-error" role="alert"><p>{erro}</p>{versoes.length === 0 && <button className="button secondary" type="button" onClick={() => { void atualizar() }}>Tentar novamente</button>}</div>}
    {carregando ? <div className="empty-list" role="status">Carregando versões…</div> : erro && versoes.length === 0 ? null : versoes.length === 0 ? <div className="empty-list" role="status"><h3>Nenhum cenário salvo</h3><p>As versões aparecerão aqui quando forem persistidas pela API.</p></div> : <>
      <div className="table-scroll" role="region" aria-label="Histórico de cenários" tabIndex={0}>
        <table className="pricing-table"><thead><tr><th>Versão</th><th>Situação</th><th>Data</th><th>Volume</th><th>Preço bruto</th><th>Preço sem IPI</th>{canViewCost && <th>Custo total</th>}{canViewCost && <th>Origem</th>}<th>Ações</th></tr></thead>
          <tbody>{versoes.map((item) => <tr key={item.versao}>
            <th scope="row">v{item.versao}</th><td>{item.vigente ? 'Vigente' : 'Anterior'}{item.versao_motor?.includes('mock') ? ' · mock' : ''}</td>
            <td>{new Intl.DateTimeFormat('pt-BR').format(new Date(`${item.data_calculo}T12:00:00`))}</td><td>{decimal(item.volume)}</td>
            <td>{moeda(item.preco_bruto)}</td><td>{moeda(item.preco_bruto_sem_ipi)}</td>{canViewCost && <td>{moeda(item.custo_total)}</td>}
            {canViewCost && <td>{item.cenario_origem_id ? 'Duplicado' : 'Original'}</td>}<td className="scenario-actions">
              {canViewCost && <button className="button secondary" type="button" onClick={() => setVersaoDetalhe(item.versao)}>Detalhes</button>}
              {canEdit && <button className="button secondary" type="button" disabled={duplicando != null} onClick={() => { void duplicar(item.versao) }}>{duplicando === item.versao ? 'Duplicando…' : 'Duplicar'}</button>}
            </td>
          </tr>)}</tbody></table>
      </div>
      {canEdit && versoes.some((item) => item.versao_motor?.includes('mock')) && <p className="field-hint">Há versões históricas calculadas por uma versão mock do motor. Duplicar recalcula a versão pela API com o motor atual.</p>}
      {canViewCost && versoes.length > 1 && <section className="scenario-compare" aria-label="Comparar cenários">
        <h4>Comparar versões</h4><div className="scenario-compare-controls">
          <label className="field">De<select value={de} onChange={(event) => { setErroComparacao(null); setDe(event.target.value) }}>{versoes.map((item) => <option key={item.versao} value={item.versao}>v{item.versao}</option>)}</select></label>
          <label className="field">Para<select value={para} onChange={(event) => { setErroComparacao(null); setPara(event.target.value) }}>{versoes.map((item) => <option key={item.versao} value={item.versao}>v{item.versao}</option>)}</select></label>
        </div>
        {erroComparacao && <p className="catalog-error" role="alert">{erroComparacao} <button className="button secondary" type="button" onClick={() => { setErroComparacao(null); setRepetirComparacao((atual) => atual + 1) }}>Tentar novamente</button></p>}
        {de === para ? <p className="field-hint">Selecione duas versões diferentes.</p> : comparacao && comparacao.versao_de === Number(de) && comparacao.versao_para === Number(para) ? <div className="table-scroll"><table className="pricing-table"><thead><tr><th>Indicador</th><th>De v{comparacao.versao_de}</th><th>Para v{comparacao.versao_para}</th><th>Variação</th><th>Variação %</th><th>Sentido</th></tr></thead><tbody>
          {comparacao.indicadores.map((item) => {
            const format = item.unidade === 'brl' ? moeda : decimal
            return <tr key={item.codigo}><th scope="row">{item.rotulo}</th><td>{item.unidade === 'percentual' ? percentual(item.valor_de) : format(item.valor_de)}</td><td>{item.unidade === 'percentual' ? percentual(item.valor_para) : format(item.valor_para)}</td><td>{item.unidade === 'percentual' ? percentual(item.variacao, true) : format(item.variacao)}</td><td>{percentual(item.variacao_percentual)}</td><td>{sentido[item.sentido]}</td></tr>
          })}
        </tbody></table></div> : erroComparacao ? null : <p role="status">Comparando…</p>}
      </section>}
      {versaoDetalhe != null && !detalheAtual && !erroDetalhe && <p className="empty-list" role="status">Carregando detalhes da versão…</p>}
      {erroDetalhe && <p className="catalog-error" role="alert">{erroDetalhe} <button className="button secondary" type="button" onClick={() => { setErroDetalhe(null); setRepetirDetalhe((atual) => atual + 1) }}>Tentar novamente</button></p>}
      {detalheAtual && <section className="scenario-detail" aria-label={`Detalhes da versão ${detalheAtual.versao}`}>
        <div className="list-card-heading"><div><h4>Detalhes da versão v{detalheAtual.versao}</h4>{detalheAtual.observacao && <p>{detalheAtual.observacao}</p>}</div><button className="button secondary" type="button" onClick={() => setVersaoDetalhe(null)}>Fechar detalhes</button></div>
        {metadata?.is_mock && <p className="catalog-error" role="status">Resultado demonstrativo: esta versão foi calculada pelo mock ({metadata.versao_motor ?? detalheAtual.versao_motor}) e não deve ser usada como preço comercial.</p>}
        <section className="scenario-profitability" aria-label="Rentabilidade da operação">
          <h4>Rentabilidade da operação</h4>
          {detalheAtual.rentabilidade ? <>
            <p className="field-hint">Valores em reais para o volume negociado de {decimal(detalheAtual.rentabilidade.volume)} unidades.</p>
            <dl className="scenario-result-grid">{linhasRentabilidade.map(([key, rotulo, ajuda]) => {
              const valor = detalheAtual.rentabilidade?.[key] ?? null
              return <div key={key} title={ajuda}><dt>{rotulo}</dt><dd className={valor?.startsWith('-') ? 'negative' : undefined}>{moeda(arredondarCentavos(valor))}</dd></div>
            })}</dl>
          </> : <p className="field-hint">Informe o volume negociado ao salvar a versão para ver ROB, MaCo absoluta e margem bruta em reais.</p>}
        </section>
        <dl className="scenario-result-grid">{(['custo_mp', 'custo_embalagem', 'custo_perda', 'custo_mod', 'custo_ggf', 'custo_total', 'preco_bruto', 'preco_bruto_sem_ipi', 'receita_operacional_liquida', 'margem_contribuicao_valor', 'margem_contribuicao_percentual'] as const).map((key) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{key === 'margem_contribuicao_percentual' ? percentual(String(resultado?.[key] ?? '')) : moeda(String(resultado?.[key] ?? ''))}</dd></div>)}</dl>
        {impostos && <div className="scenario-tax-list"><h4>Impostos destacados</h4>{Object.entries(impostos).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: {moeda(value)}</p>)}</div>}
      </section>}
    </>}
  </section>
}

export default ScenarioHistoryPanel
