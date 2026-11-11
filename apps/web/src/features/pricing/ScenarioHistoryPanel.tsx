import { useEffect, useState, type FormEvent } from 'react'
import { Modal } from '../../components/modal/Modal'
import { Select } from '../../components/form/Select'
import { MODALIDADE, REGIME, rotulo } from './rotulos'
import { ApiError } from '../../services/apiClient'
import { arredondarCentavos } from './centavos'
import { calcularCenario, calcularCenarioDemo } from './calculateService'
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
  formulaRevision?: number
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
// Exibição: o motor devolve decimais exatos; na tela, centavos e 2 casas no percentual.
const formatoMoeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const moeda = (value: string | null | undefined) => value == null || value === '' ? '—' : Number.isFinite(Number(value)) ? formatoMoeda.format(Number(value)) : value
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
  const arredondado = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(Number(`${sign}${shifted}`))
  return `${arredondado}${variacao ? ' p.p.' : '%'}`
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

function ScenarioHistoryPanel({ precificacaoId, codigo, precificacao, canViewCost, canEdit, canReadCatalog, canReadCambio, canReadParametros, canReadImpostos, formulaRevision = 0, onClose }: Props) {
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

  async function prepararEntrada(): Promise<{ entrada: Record<string, unknown>, pendencias: string[] } | null> {
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
      if (!precificacao) pendencias.push('Os dados da precificação não estão disponíveis nesta tela.')
      const candidato: Record<string, unknown> = { ...manual }
      if (precificacao?.uf_destino) candidato.cliente_uf = precificacao.uf_destino
      else if (!candidato.cliente_uf) pendencias.push('Preencha a UF de destino no cabeçalho da precificação.')
      if (precificacao?.modalidade_comercial) candidato.modalidade_comercial = precificacao.modalidade_comercial
      else if (!candidato.modalidade_comercial) pendencias.push('Preencha a modalidade comercial no cabeçalho.')
      if (precificacao?.regime_tributario) candidato.regime_tributario = precificacao.regime_tributario
      else if (!candidato.regime_tributario) pendencias.push('Preencha o regime tributário do cliente no cabeçalho.')

      let formulario: Awaited<ReturnType<typeof obterFormulacao>> | null = null
      if (precificacao?.produto_id) {
        try { formulario = await obterFormulacao(precificacao.produto_id) }
        catch (falha) { pendencias.push(falha instanceof ApiError && falha.status === 404 ? 'O produto ainda não tem formulação. Monte a composição em Formulações.' : `Formulação do produto: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`) }
      } else pendencias.push('A precificação não tem produto associado.')

      const materiais: Record<string, unknown>[] = []
      const embalagens: Record<string, unknown>[] = []
      if (formulario) {
        for (const item of formulario.itens) {
          const isMateria = item.tipo_insumo === 'materia_prima'
          const id = isMateria ? item.materia_prima_id : item.embalagem_id
          if (!id || !canReadCatalog) {
            pendencias.push(canReadCatalog ? 'Há um item da formulação sem insumo vinculado.' : 'Seu perfil não pode consultar os insumos da formulação.')
            continue
          }
          let insumo
          try { insumo = await obterInsumo(isMateria ? 'materias-primas' : 'embalagens', id) }
          catch (falha) { pendencias.push(`Dados do insumo ${id}: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`); continue }
          const listaManual = isMateria ? manual.materiais_primas : manual.embalagens
          const itemManual = Array.isArray(listaManual) ? listaManual.find((linha) => isRecord(linha) && linha.codigo === insumo.codigo) : undefined
          const entradaItem: Record<string, unknown> = { ...(isRecord(itemManual) ? itemManual : {}), codigo: insumo.codigo, descricao: insumo.descricao, quantidade: item.quantidade, origem_material: item.origem_material }
          if (isMateria) {
            entradaItem.margem_seguranca_percentual ??= ''
            if (canViewCost && item.unidade_medida === 'kg' && insumo.unidade_medida === 'kg' && volume) {
              try {
                const cotacao = await resolverCotacao(id, multiplicarDecimais(item.quantidade, volume))
                entradaItem.preco_negociado = cotacao.preco
                entradaItem.moeda = cotacao.moeda
                if (cotacao.moeda === 'BRL') entradaItem.cambio = '1'
                else if (canReadCambio) entradaItem.cambio = (await consultarCambioVigente(cotacao.moeda)).taxa_com_margem
                else { entradaItem.cambio = ''; pendencias.push(`Seu perfil não pode consultar o câmbio de ${cotacao.moeda}, usado em ${insumo.descricao}.`) }
              } catch {
                entradaItem.preco_negociado ??= ''
                entradaItem.moeda ??= ''
                entradaItem.cambio ??= ''
                pendencias.push(`Sem cotação vigente de ${insumo.descricao} para esse volume. Cadastre ou atualize em Cotações.`)
              }
            } else if (!canViewCost) {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push('Seu perfil não pode ver custos, então o preço de compra dos insumos não entra no cálculo.')
            } else if (item.unidade_medida !== 'kg' || insumo.unidade_medida !== 'kg') {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push(`${insumo.descricao}: a cotação é por kg, então use kg na formulação.`)
            } else {
              entradaItem.preco_negociado ??= ''; entradaItem.moeda ??= ''; entradaItem.cambio ??= ''
              pendencias.push('Informe o volume negociado para escolher a faixa de cotação dos insumos.')
            }
            materiais.push(entradaItem)
          } else {
            entradaItem.preco_negociado ??= ''
            entradaItem.moeda ??= ''
            entradaItem.cambio ??= ''
            entradaItem.margem_seguranca_percentual ??= ''
            entradaItem.percentual_descarte ??= ''
            embalagens.push(entradaItem)
            pendencias.push(`Informe o preço e o descarte da embalagem ${insumo.descricao} na entrada manual (embalagens ainda não têm cotação cadastrada).`)
          }
        }
      }
      if (formulario) {
        candidato.materiais_primas = materiais
        candidato.embalagens = embalagens
        const origens = new Set(formulario.itens.map((item) => item.origem_material).filter((origem) => origem !== null))
        if (origens.size === 1 && origens.has('fabricante') && formulario.itens.every((item) => item.origem_material)) {
          candidato.material_fornecido_pelo_cliente = false
          candidato.valor_material_cliente = '0'
        } else if (origens.size === 1 && origens.has('cliente') && formulario.itens.every((item) => item.origem_material)) {
          candidato.material_fornecido_pelo_cliente = true
          if (candidato.valor_material_cliente == null || candidato.valor_material_cliente === '') {
            pendencias.push('Informe o valor do material fornecido pelo cliente na entrada manual.')
          }
        } else if (formulario.itens.length > 0) {
          pendencias.push('Todos os itens da formulação precisam ter a mesma origem (fabricante ou cliente).')
        }
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
            if (vigentes.faltando.includes(codigo)) pendencias.push(`Falta um valor vigente de ${{ perda_percentual: 'perda padrão', taxa_financeira_mensal_percentual: 'taxa financeira mensal', prazo_medio_padrao_dias: 'prazo médio' }[codigo]} em Câmbio e parâmetros.`)
          }
        } catch (falha) { pendencias.push(`Parâmetros globais: ${falha instanceof ApiError ? falha.message : 'não foi possível consultar.'}`) }
      } else pendencias.push('Seu perfil não pode consultar os parâmetros globais (perda, taxa financeira e prazo).')
      for (const [campo, label] of [
        ['taxa_financeira_mensal_percentual', 'Taxa financeira mensal'], ['prazo_medio_dias', 'Prazo médio'],
      ] as const) {
        if (comercial[campo] == null || comercial[campo] === '') {
          comercial[campo] = ''
          pendencias.push(`Informe a ${label.toLowerCase()} (sem valor vigente em Câmbio e parâmetros).`)
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
        } catch { pendencias.push(`Não há alíquota cadastrada para ${precificacao.uf_destino}, NCM ${ncm} e ${rotulo(REGIME, precificacao.regime_tributario)}. Cadastre em Tributos.`) }
      } else if (!canReadImpostos) pendencias.push('Seu perfil não pode consultar os tributos, então os impostos não são preenchidos.')
      else if (!ncm) pendencias.push('O produto não tem NCM cadastrado, então os impostos não são preenchidos.')

      const producaoManual = isRecord(manual.producao) ? manual.producao : {}
      candidato.producao = {
        taxa_mod: producaoManual.taxa_mod ?? '', taxa_ggf: producaoManual.taxa_ggf ?? '',
        produtividade: producaoManual.produtividade ?? '', numero_funcionarios: producaoManual.numero_funcionarios ?? '',
      }
      for (const campo of ['taxa_mod', 'taxa_ggf', 'produtividade', 'numero_funcionarios']) {
        if (producaoManual[campo] == null || producaoManual[campo] === '') pendencias.push(`Informe ${{ taxa_mod: 'a taxa de mão de obra (MOD)', taxa_ggf: 'a taxa de GGF', produtividade: 'a produtividade', numero_funcionarios: 'o número de funcionários' }[campo]} na entrada manual.`)
      }
      for (const campo of ['margem_desejada_percentual', 'comissao_percentual', 'frete_percentual']) {
        if (comercial[campo] == null || comercial[campo] === '') {
          comercial[campo] = ''
          const label = campo === 'margem_desejada_percentual' ? 'a margem desejada' : campo === 'comissao_percentual' ? 'a comissão' : 'o frete em %'
          pendencias.push(`Informe ${label} na entrada manual.`)
        }
      }
      for (const campo of TAX_FIELDS) if (impostos[campo] == null || impostos[campo] === '') impostos[campo] = ''
      if (TAX_FIELDS.some((campo) => impostos[campo] === '') && pendencias.every((p) => !p.includes('impostos') && !p.includes('alíquota'))) pendencias.push('Faltam alíquotas de impostos para este destino.')
      if (candidato.perda_percentual == null || candidato.perda_percentual === '') candidato.perda_percentual = ''
      if (candidato.material_fornecido_pelo_cliente == null) candidato.material_fornecido_pelo_cliente = ''
      if (candidato.valor_material_cliente == null || candidato.valor_material_cliente === '') candidato.valor_material_cliente = ''
      if (candidato.perda_percentual === '') pendencias.push('Falta a perda padrão vigente em Câmbio e parâmetros.')
      if (candidato.material_fornecido_pelo_cliente === '' && formulario && formulario.itens.length > 0) pendencias.push('Defina a origem (fabricante ou cliente) de cada item da formulação.')

      candidato.comercial = comercial
      candidato.impostos = impostos
      setEntradaJson(JSON.stringify(candidato, null, 2))
      setPendenciasPreparacao([...new Set(pendencias)])
      return { entrada: candidato, pendencias: [...new Set(pendencias)] }
    } catch (falha) {
      setErroSimulacao(falha instanceof SyntaxError ? 'A entrada manual não é um JSON válido.' : falha instanceof Error ? falha.message : 'Não foi possível reunir os dados cadastrados.')
      return null
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
      setErroSimulacao(falha instanceof ApiError ? falha.message : falha instanceof SyntaxError ? 'A entrada manual não é um JSON válido.' : 'Não foi possível calcular.')
    } finally { setSimulando(false) }
  }

  async function prepararECalcular() {
    setResultadoSimulacao(null); setEntradaCalculada(null)
    const preparado = await prepararEntrada()
    if (!preparado || preparado.pendencias.length > 0) return
    setSimulando(true); setErroSimulacao(null)
    try {
      const entrada = preparado.entrada as unknown as CalculateRequest
      const resposta = await calcularCenario(entrada)
      setResultadoSimulacao(resposta)
      setEntradaCalculada(entrada)
    } catch (falha) {
      setErroSimulacao(falha instanceof ApiError ? falha.message : 'Não foi possível calcular com os dados cadastrados.')
    } finally { setSimulando(false) }
  }

  async function simularDemo() {
    setErroSimulacao(null); setResultadoSimulacao(null); setEntradaCalculada(null); setSimulando(true)
    try {
      let dados: Record<string, unknown> = {}
      if (entradaJson.trim()) {
        const parseado: unknown = JSON.parse(entradaJson)
        if (!isRecord(parseado)) throw new Error('A entrada atual precisa ser um objeto JSON.')
        dados = parseado
      }
      const comCabecalho = {
        ...dados,
        ...(precificacao?.uf_destino ? { cliente_uf: precificacao.uf_destino } : {}),
        ...(precificacao?.modalidade_comercial ? { modalidade_comercial: precificacao.modalidade_comercial } : {}),
        ...(precificacao?.regime_tributario ? { regime_tributario: precificacao.regime_tributario } : {}),
      }
      setResultadoSimulacao(await calcularCenarioDemo(comCabecalho))
    } catch (falha) {
      setErroSimulacao(falha instanceof ApiError ? falha.message : falha instanceof SyntaxError ? 'A entrada precisa ser um JSON válido.' : falha instanceof Error ? falha.message : 'Não foi possível executar a demonstração.')
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
    if (formulaRevision === 0) return
    let ativo = true
    void (async () => {
      const preparado = await prepararEntrada()
      if (!ativo || !preparado || preparado.pendencias.length > 0) return
      setSimulando(true); setErroSimulacao(null)
      try {
        const resposta = await calcularCenario(preparado.entrada as unknown as CalculateRequest)
        if (!ativo) return
        setResultadoSimulacao(resposta)
        setEntradaCalculada(preparado.entrada as unknown as CalculateRequest)
      } catch (falha) {
        if (ativo) setErroSimulacao(falha instanceof ApiError ? falha.message : 'A formulação foi salva, mas ainda faltam dados para recalcular o cenário.')
      } finally { if (ativo) setSimulando(false) }
    })()
    return () => { ativo = false }
  // A função usa a formulação persistida e os dados do cabeçalho, e só executa o motor real.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formulaRevision])

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

  const opcoesVersao = versoes.map((item) => ({ value: String(item.versao), label: `v${item.versao}`, detalhe: item.vigente ? 'vigente' : undefined }))
  const ocupado = preparando || simulando || salvandoCenario

  return <Modal tamanho="grande" titulo={`Cenários de ${codigo}`}
    subtitulo={precificacao ? [precificacao.cliente?.razao_social, precificacao.produto?.descricao].filter(Boolean).join(' · ') : undefined}
    onFechar={onClose}>
    {canEdit && <section className="scenario-simulation" aria-label="Nova simulação">
      <div className="scenario-sim-topo">
        <h4>Nova simulação</h4>
        {precificacao && <p className="scenario-cabecalho">
          <span>{rotulo(MODALIDADE, precificacao.modalidade_comercial)}</span>
          <span>{precificacao.uf_destino ?? <em>UF não informada</em>}</span>
          <span>{precificacao.regime_tributario ? rotulo(REGIME, precificacao.regime_tributario) : <em>regime não informado</em>}</span>
        </p>}
      </div>
      <p className="field-hint">O NeoPrice reúne a formulação, as cotações, os parâmetros e os tributos cadastrados e calcula o preço no motor. Informe o volume para escolher a faixa de cotação.</p>
      <form onSubmit={(event) => { void simular(event) }}>
        <div className="scenario-sim-campos">
          <label className="field"><span>Volume negociado <small>(unidades)</small></span><input inputMode="decimal" placeholder="Ex.: 1000" value={volume} onChange={(event) => setVolume(event.target.value)} /></label>
          <label className="field"><span>Observação <small>(opcional)</small></span><input maxLength={500} placeholder="Aparece no histórico da versão" value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
          <button className="button primary" type="button" disabled={ocupado} onClick={() => { void prepararECalcular() }}>{preparando ? 'Reunindo dados…' : simulando ? 'Calculando…' : 'Calcular cenário'}</button>
        </div>

        {pendenciasPreparacao.length > 0 && <div className="np-pendencias" role="status">
          <strong>Para calcular, falta resolver {pendenciasPreparacao.length === 1 ? '1 item' : `${pendenciasPreparacao.length} itens`}:</strong>
          <ul>{pendenciasPreparacao.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>}

        <details className="np-avancado">
          <summary>Entrada manual (avançado)</summary>
          <p className="field-hint">Para completar o que ainda não tem cadastro, como produção, margem desejada e comissão. O botão “Calcular cenário” preenche este campo com os dados encontrados; ajuste e calcule de novo.</p>
          <label className="field"><span>Entrada do cálculo (JSON)</span><textarea rows={12} spellCheck={false} value={entradaJson} onChange={(event) => setEntradaJson(event.target.value)} placeholder="Clique em “Calcular cenário” para gerar a entrada com os dados cadastrados." /></label>
          <div className="np-avancado-acoes">
            <button className="button secondary" type="button" disabled={ocupado} onClick={() => { void simularDemo() }}>{simulando ? 'Calculando…' : 'Simular com valores de demonstração'}</button>
            <button className="button primary" type="submit" disabled={ocupado || !entradaJson.trim()}>{simulando ? 'Calculando…' : 'Calcular com a entrada manual'}</button>
          </div>
          <p className="field-hint">A demonstração completa os campos vazios com valores fictícios. O resultado não pode ser salvo nem enviado para aprovação.</p>
        </details>
      </form>
      {erroSimulacao && <p className="catalog-error" role="alert">{erroSimulacao}</p>}
      {resultadoSimulacao && <div className="scenario-resultado" aria-live="polite">
        {resultadoSimulacao.metadata.is_mock && <div className="demo-notice"><span className="notice-dot" />
          <span><strong>Demonstração.</strong> {resultadoSimulacao.metadata.classificacao === 'inteiramente_simulado' ? 'Todos os valores são fictícios.' : 'Parte dos valores é fictícia.'} Este resultado não pode ser salvo nem enviado para aprovação.</span>
        </div>}
        <dl className="scenario-result-grid">{([
          ['preco_bruto', 'Preço bruto'], ['preco_bruto_com_ipi', 'Preço com IPI'], ['preco_bruto_sem_ipi', 'Preço sem IPI'], ['preco_bruto_sem_ipi_sem_encargo', 'Preço sem IPI e sem encargo'], ['receita_operacional_liquida', 'Receita líquida (ROL)'],
        ] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{moeda(resultadoSimulacao[key])}</dd></div>)}
          {canViewCost && 'custo_total' in resultadoSimulacao && <>{([
            ['custo_mp', 'Matéria-prima'], ['custo_embalagem', 'Embalagem'], ['custo_perda', 'Perda'], ['custo_mod', 'Mão de obra (MOD)'], ['custo_ggf', 'GGF'], ['custo_total', 'Custo total'],
          ] as const).map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{moeda(resultadoSimulacao[key])}</dd></div>)}
          <div className="destaque"><dt>Margem de contribuição</dt><dd>{moeda(resultadoSimulacao.margem_contribuicao_valor)} · {percentual(resultadoSimulacao.margem_contribuicao_percentual)}</dd></div></>}
        </dl>
        <div className="scenario-tax-list"><h4>Impostos destacados</h4>{Object.entries(resultadoSimulacao.impostos_destacados).map(([key, value]) => <p key={key}>{rotuloImposto(key)}: <b>{moeda(value)}</b></p>)}</div>
        <div className="scenario-resultado-rodape">
          <span className="field-hint">Motor {resultadoSimulacao.metadata.versao_motor}</span>
          {!resultadoSimulacao.metadata.is_mock && <button className="button primary" type="button" disabled={salvandoCenario} onClick={() => { void persistirSimulacao() }}>{salvandoCenario ? 'Salvando…' : 'Salvar como nova versão'}</button>}
        </div>
      </div>}
    </section>}

    <h4 className="np-secao">Versões salvas</h4>
    {erro && <div className="catalog-error" role="alert"><p>{erro}</p>{versoes.length === 0 && <button className="button secondary compacto" type="button" onClick={() => { void atualizar() }}>Tentar novamente</button>}</div>}
    {carregando ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando versões…</div> : erro && versoes.length === 0 ? null : versoes.length === 0 ? <div className="empty-list compacta" role="status"><h3>Nenhuma versão salva</h3><p>Calcule um cenário e salve para ele aparecer aqui.</p></div> : <>
      <div className="table-scroll" role="region" aria-label="Versões salvas" tabIndex={0}>
        <table className="pricing-table"><thead><tr><th>Versão</th><th>Situação</th><th>Data</th><th className="numeric">Volume</th><th className="numeric">Preço bruto</th><th className="numeric">Preço sem IPI</th>{canViewCost && <th className="numeric">Custo total</th>}{canViewCost && <th>Origem</th>}<th><span className="sr-only">Ações</span></th></tr></thead>
          <tbody>{versoes.map((item) => <tr key={item.versao}>
            <th scope="row">v{item.versao}</th><td><span className={`status-pill ${item.vigente ? 'status-approved' : 'status-neutral'}`}><i />{item.vigente ? 'Vigente' : 'Anterior'}</span>{item.versao_motor?.includes('mock') && <small className="status-demo">Demonstração</small>}</td>
            <td className="updated-cell">{new Intl.DateTimeFormat('pt-BR').format(new Date(`${item.data_calculo}T12:00:00`))}</td><td className="numeric">{decimal(item.volume)}</td>
            <td className="numeric">{moeda(item.preco_bruto)}</td><td className="numeric">{moeda(item.preco_bruto_sem_ipi)}</td>{canViewCost && <td className="numeric">{moeda(item.custo_total)}</td>}
            {canViewCost && <td>{item.cenario_origem_id ? 'Duplicada' : 'Original'}</td>}<td className="cell-acoes"><div className="row-actions">
              {canViewCost && <button className="button secondary compacto" type="button" aria-pressed={versaoDetalhe === item.versao} onClick={() => setVersaoDetalhe(versaoDetalhe === item.versao ? null : item.versao)}>{versaoDetalhe === item.versao ? 'Ocultar' : 'Detalhes'}</button>}
              {canEdit && <button className="button secondary compacto" type="button" disabled={duplicando != null} onClick={() => { void duplicar(item.versao) }}>{duplicando === item.versao ? 'Duplicando…' : 'Duplicar'}</button>}
            </div></td>
          </tr>)}</tbody></table>
      </div>
      {canEdit && versoes.some((item) => item.versao_motor?.includes('mock')) && <p className="field-hint">Versões de demonstração não valem como preço. Duplique para recalcular com o motor atual.</p>}

      {versaoDetalhe != null && !detalheAtual && !erroDetalhe && <div className="empty-list compacta" role="status"><span className="np-carregando" aria-hidden="true" />Carregando a versão…</div>}
      {erroDetalhe && <p className="catalog-error" role="alert">{erroDetalhe} <button className="button secondary compacto" type="button" onClick={() => { setErroDetalhe(null); setRepetirDetalhe((atual) => atual + 1) }}>Tentar novamente</button></p>}
      {detalheAtual && <section className="scenario-detail" aria-label={`Detalhes da versão ${detalheAtual.versao}`}>
        <div className="list-card-heading"><div><h4>Versão v{detalheAtual.versao}</h4>{detalheAtual.observacao && <p className="field-hint">{detalheAtual.observacao}</p>}</div></div>
        {metadata?.is_mock && <div className="demo-notice"><span className="notice-dot" />Versão de demonstração: não use como preço comercial.</div>}
        <section className="scenario-profitability" aria-label="Rentabilidade da operação">
          <h4>Rentabilidade da operação</h4>
          {detalheAtual.rentabilidade ? <>
            <p className="field-hint">Em reais, para o volume de {decimal(detalheAtual.rentabilidade.volume)} unidades.</p>
            <dl className="scenario-result-grid">{linhasRentabilidade.map(([key, nome, ajuda]) => {
              const valor = detalheAtual.rentabilidade?.[key] ?? null
              return <div key={key} title={ajuda}><dt>{nome}</dt><dd className={valor?.startsWith('-') ? 'negative' : undefined}>{moeda(arredondarCentavos(valor))}</dd></div>
            })}</dl>
          </> : <p className="field-hint">Esta versão foi salva sem volume, então não há rentabilidade em reais.</p>}
        </section>
        <dl className="scenario-result-grid">{(Object.keys(ROTULO_RESULTADO) as (keyof typeof ROTULO_RESULTADO)[]).map((key) => <div key={key}><dt>{ROTULO_RESULTADO[key]}</dt><dd>{key === 'margem_contribuicao_percentual' ? percentual(String(resultado?.[key] ?? '')) : moeda(String(resultado?.[key] ?? ''))}</dd></div>)}</dl>
        {impostos && <div className="scenario-tax-list"><h4>Impostos destacados</h4>{Object.entries(impostos).map(([key, value]) => <p key={key}>{rotuloImposto(key)}: <b>{moeda(value)}</b></p>)}</div>}
      </section>}

      {canViewCost && versoes.length > 1 && <section className="scenario-compare" aria-label="Comparar versões">
        <h4>Comparar versões</h4><div className="scenario-compare-controls">
          <label className="field"><span>De</span><Select compacto value={de} options={opcoesVersao} onChange={(valor) => { setErroComparacao(null); setDe(valor) }} /></label>
          <label className="field"><span>Para</span><Select compacto value={para} options={opcoesVersao} onChange={(valor) => { setErroComparacao(null); setPara(valor) }} /></label>
        </div>
        {erroComparacao && <p className="catalog-error" role="alert">{erroComparacao} <button className="button secondary compacto" type="button" onClick={() => { setErroComparacao(null); setRepetirComparacao((atual) => atual + 1) }}>Tentar novamente</button></p>}
        {de === para ? <p className="field-hint">Escolha duas versões diferentes.</p> : comparacao && comparacao.versao_de === Number(de) && comparacao.versao_para === Number(para) ? <div className="table-scroll"><table className="pricing-table"><thead><tr><th>Indicador</th><th className="numeric">v{comparacao.versao_de}</th><th className="numeric">v{comparacao.versao_para}</th><th className="numeric">Variação</th><th className="numeric">Variação %</th><th>Sentido</th></tr></thead><tbody>
          {comparacao.indicadores.map((item) => {
            const format = item.unidade === 'brl' ? moeda : decimal
            return <tr key={item.codigo}><th scope="row">{item.rotulo}</th><td className="numeric">{item.unidade === 'percentual' ? percentual(item.valor_de) : format(item.valor_de)}</td><td className="numeric">{item.unidade === 'percentual' ? percentual(item.valor_para) : format(item.valor_para)}</td><td className="numeric">{item.unidade === 'percentual' ? percentual(item.variacao, true) : format(item.variacao)}</td><td className="numeric">{percentual(item.variacao_percentual)}</td><td>{sentido[item.sentido]}</td></tr>
          })}
        </tbody></table></div> : erroComparacao ? null : <p className="np-carregando-linha" role="status"><span className="np-carregando" aria-hidden="true" />Comparando…</p>}
      </section>}
    </>}
  </Modal>
}

const ROTULO_RESULTADO = {
  custo_mp: 'Matéria-prima', custo_embalagem: 'Embalagem', custo_perda: 'Perda', custo_mod: 'Mão de obra (MOD)', custo_ggf: 'GGF', custo_total: 'Custo total',
  preco_bruto: 'Preço bruto', preco_bruto_sem_ipi: 'Preço sem IPI', receita_operacional_liquida: 'Receita líquida (ROL)',
  margem_contribuicao_valor: 'Margem de contribuição', margem_contribuicao_percentual: 'Margem de contribuição (%)',
} as const

const IMPOSTOS: Record<string, string> = {
  pis: 'PIS', cofins: 'COFINS', icms: 'ICMS', ipi: 'IPI', icms_st: 'ICMS-ST', fcp: 'FCP', difal: 'DIFAL',
}
/** "icms_st_valor" → "ICMS-ST" */
function rotuloImposto(chave: string): string {
  const base = chave.replace(/_(valor|unitario|total)$/, '')
  return IMPOSTOS[base] ?? base.replaceAll('_', ' ').toUpperCase()
}

export default ScenarioHistoryPanel
