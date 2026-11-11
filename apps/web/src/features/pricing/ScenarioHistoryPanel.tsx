import { useEffect, useState, type FormEvent } from 'react'
import { Modal } from '../../components/modal/Modal'
import { Select } from '../../components/form/Select'
import { MODALIDADE, REGIME, rotulo } from './rotulos'
import { ApiError } from '../../services/apiClient'
import { arredondarCentavos } from './centavos'
import { calcularCenario, calcularCenarioDemo } from './calculateService'
import type { CalculateRequest, CalculateResponseAutorizada } from '../../types/calculate.generated'
import { obterEntradaCalculo, type Precificacao } from './precificacoesService'
import { deslocarDecimal } from '../../app/decimal'
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
/** Campos sem cadastro no sistema, digitados no modal em unidades de tela (R$, %, unidades). */
type CamposManuais = {
  taxa_mod: string, taxa_ggf: string, produtividade: string, numero_funcionarios: string
  margem: string, comissao: string, frete: string, valor_material_cliente: string
  embalagens: Record<string, { preco: string, descarte: string }>
}
const CAMPOS_VAZIOS: CamposManuais = { taxa_mod: '', taxa_ggf: '', produtividade: '', numero_funcionarios: '', margem: '', comissao: '', frete: '', valor_material_cliente: '', embalagens: {} }
/** "1.234,5" → "1234.5"; "1.85" continua "1.85". */
const lerNumero = (valor: string) => { const t = valor.trim(); return t.includes(',') ? t.replace(/\./g, '').replace(',', '.') : t }
/** "18" (%) → "0.18" (fração que o motor espera). */
const lerPercentual = (valor: string) => (lerNumero(valor) ? deslocarDecimal(lerNumero(valor), -2) : '')

/** Junta os campos do modal à entrada (o que foi digitado vence o JSON). */
function aplicarManuais(base: Record<string, unknown>, campos: CamposManuais): Record<string, unknown> {
  const resultado: Record<string, unknown> = { ...base }
  const producao: Record<string, unknown> = isRecord(base.producao) ? { ...base.producao } : {}
  for (const chave of ['taxa_mod', 'taxa_ggf', 'produtividade', 'numero_funcionarios'] as const) if (campos[chave].trim()) producao[chave] = lerNumero(campos[chave])
  resultado.producao = producao
  const comercial: Record<string, unknown> = isRecord(base.comercial) ? { ...base.comercial } : {}
  if (campos.margem.trim()) comercial.margem_desejada_percentual = lerPercentual(campos.margem)
  if (campos.comissao.trim()) comercial.comissao_percentual = lerPercentual(campos.comissao)
  if (campos.frete.trim()) comercial.frete_percentual = lerPercentual(campos.frete)
  resultado.comercial = comercial
  if (campos.valor_material_cliente.trim()) resultado.valor_material_cliente = lerNumero(campos.valor_material_cliente)
  const atuais = Array.isArray(base.embalagens) ? base.embalagens.filter(isRecord) : []
  const codigos = new Set([...atuais.map((linha) => String(linha.codigo)), ...Object.keys(campos.embalagens)])
  resultado.embalagens = [...codigos].map((codigo) => {
    const linha: Record<string, unknown> = { ...(atuais.find((item) => item.codigo === codigo) ?? { codigo }) }
    const digitado = campos.embalagens[codigo]
    if (digitado?.preco.trim()) Object.assign(linha, { preco_negociado: lerNumero(digitado.preco), moeda: 'BRL', cambio: '1' })
    if (digitado?.descarte.trim()) linha.percentual_descarte = lerPercentual(digitado.descarte)
    return linha
  })
  return resultado
}

const vazio = (valor: unknown) => valor == null || valor === ''
const preenchidos = (objeto: Record<string, unknown>) => Object.fromEntries(Object.entries(objeto).filter(([, valor]) => !vazio(valor)))
const TEXTO_PRODUCAO = { taxa_mod: 'a taxa de mão de obra (MOD)', taxa_ggf: 'a taxa de GGF', produtividade: 'a produtividade', numero_funcionarios: 'o número de funcionários' } as const
const TEXTO_COMERCIAL = { margem_desejada_percentual: 'a margem desejada', comissao_percentual: 'a comissão', frete_percentual: 'o frete em %' } as const

/** O que veio do cadastro vence; o que o analista digitou preenche o que ficou em branco. */
function combinarItens(base: unknown, manual: unknown): Record<string, unknown>[] {
  const digitados = Array.isArray(manual) ? manual.filter(isRecord) : []
  return (Array.isArray(base) ? base.filter(isRecord) : []).map((linha) => {
    const digitado = digitados.find((item) => item.codigo === linha.codigo) ?? {}
    const item: Record<string, unknown> = { ...linha, ...preenchidos(digitado), ...preenchidos(linha) }
    if (vazio(item.margem_seguranca_percentual)) item.margem_seguranca_percentual = '0'
    return item
  })
}

/** Junta a entrada montada pela API com os campos manuais e aponta o que ainda falta digitar. */
function combinarEntrada(base: Record<string, unknown>, manual: Record<string, unknown>) {
  const pendencias: string[] = []
  const entrada: Record<string, unknown> = { ...manual, ...preenchidos(base) }
  if ('materiais_primas' in base) entrada.materiais_primas = combinarItens(base.materiais_primas, manual.materiais_primas)
  if ('embalagens' in base) entrada.embalagens = combinarItens(base.embalagens, manual.embalagens)
  const objeto = (valor: unknown) => (isRecord(valor) ? valor : {})

  const producaoManual = objeto(manual.producao)
  const producao: Record<string, unknown> = {}
  for (const campo of Object.keys(TEXTO_PRODUCAO) as (keyof typeof TEXTO_PRODUCAO)[]) {
    producao[campo] = producaoManual[campo] ?? ''
    if (vazio(producao[campo])) pendencias.push(`Informe ${TEXTO_PRODUCAO[campo]} nos campos abaixo.`)
  }
  entrada.producao = producao

  const comercial: Record<string, unknown> = { ...objeto(manual.comercial), ...preenchidos(objeto(base.comercial)) }
  for (const [campo, texto] of [['taxa_financeira_mensal_percentual', 'a taxa financeira mensal'], ['prazo_medio_dias', 'o prazo médio']] as const) {
    if (vazio(comercial[campo])) { comercial[campo] = ''; pendencias.push(`Informe ${texto} (sem valor vigente em Câmbio e parâmetros).`) }
  }
  for (const campo of Object.keys(TEXTO_COMERCIAL) as (keyof typeof TEXTO_COMERCIAL)[]) {
    if (vazio(comercial[campo])) { comercial[campo] = ''; pendencias.push(`Informe ${TEXTO_COMERCIAL[campo]} nos campos abaixo.`) }
  }
  entrada.comercial = comercial

  const impostos: Record<string, unknown> = { ...objeto(manual.impostos), ...preenchidos(objeto(base.impostos)) }
  for (const campo of TAX_FIELDS) if (vazio(impostos[campo])) impostos[campo] = ''
  entrada.impostos = impostos

  const embalagens = Array.isArray(entrada.embalagens) ? entrada.embalagens.filter(isRecord) : []
  for (const linha of embalagens) {
    if (vazio(linha.preco_negociado) || vazio(linha.percentual_descarte)) pendencias.push(`Informe o preço e o descarte de ${String(linha.descricao ?? linha.codigo)} nos campos abaixo.`)
  }
  if (vazio(entrada.perda_percentual)) entrada.perda_percentual = ''
  if (entrada.material_fornecido_pelo_cliente == null) entrada.material_fornecido_pelo_cliente = ''
  if (vazio(entrada.valor_material_cliente)) {
    entrada.valor_material_cliente = ''
    if (entrada.material_fornecido_pelo_cliente === true) pendencias.push('Informe o valor do material fornecido pelo cliente nos campos abaixo.')
  }
  return {
    entrada,
    pendencias,
    embalagens: embalagens.map((linha) => ({ codigo: String(linha.codigo), descricao: String(linha.descricao ?? linha.codigo) })),
  }
}

const linhasRentabilidade = [
  ['receita_operacional_bruta', 'ROB', 'Receita operacional bruta: preço sem IPI × volume'],
  ['deducoes', 'Deduções', 'PIS, COFINS e ICMS sobre a receita'],
  ['receita_operacional_liquida', 'ROL', 'Receita operacional líquida'],
  ['margem_contribuicao', 'MaCo absoluta', 'Margem de contribuição unitária × volume'],
  ['margem_bruta', 'Margem bruta', 'ROL menos o custo do produto'],
] as const
const sentido: Record<string, string> = { subiu: 'Subiu', desceu: 'Desceu', igual: 'Sem variação', sem_base: 'Sem base' }

function ScenarioHistoryPanel({ precificacaoId, codigo, precificacao, canViewCost, canEdit, formulaRevision = 0, onClose }: Props) {
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
  const [manuais, setManuais] = useState<CamposManuais>(CAMPOS_VAZIOS)
  const [embalagensForm, setEmbalagensForm] = useState<{ codigo: string, descricao: string }[]>([])
  const [precisaValorCliente, setPrecisaValorCliente] = useState(false)

  async function prepararEntrada(): Promise<{ entrada: Record<string, unknown>, pendencias: string[] } | null> {
    setPreparando(true); setErroSimulacao(null); setPendenciasPreparacao([])
    try {
      let manual: Record<string, unknown> = {}
      const texto = entradaJson.trim()
      if (texto) {
        const parseado: unknown = JSON.parse(texto)
        if (!isRecord(parseado)) throw new Error('A entrada atual precisa ser um objeto JSON.')
        manual = parseado
      }
      manual = aplicarManuais(manual, manuais)
      // Uma chamada: a API reúne formulação, cotações, câmbio, parâmetros e alíquota.
      const volumeApi = lerNumero(volume)
      const base = await obterEntradaCalculo(precificacaoId, volumeApi && Number(volumeApi) > 0 ? volumeApi : null)
      const combinado = combinarEntrada(base.entrada, manual)
      const pendencias = [...new Set([...base.pendencias, ...combinado.pendencias])]
      setEmbalagensForm(combinado.embalagens)
      setPrecisaValorCliente(combinado.entrada.material_fornecido_pelo_cliente === true)
      setEntradaJson(JSON.stringify(combinado.entrada, null, 2))
      setPendenciasPreparacao(pendencias)
      return { entrada: combinado.entrada, pendencias }
    } catch (falha) {
      setErroSimulacao(falha instanceof SyntaxError ? 'A entrada manual não é um JSON válido.' : falha instanceof Error ? falha.message : 'Não foi possível reunir os dados cadastrados.')
      return null
    } finally { setPreparando(false) }
  }

  const campoManual = (chave: Exclude<keyof CamposManuais, 'embalagens'>, titulo: string, unidade: string, exemplo: string, modo: 'decimal' | 'numeric' = 'decimal') =>
    <label className="field"><span>{titulo} <small>({unidade})</small></span><input inputMode={modo} placeholder={exemplo} value={manuais[chave]} onChange={(event) => { const valor = event.target.value; setManuais((atual) => ({ ...atual, [chave]: valor })) }} /></label>
  const alterarEmbalagem = (codigo: string, campo: 'preco' | 'descarte', valor: string) =>
    setManuais((atual) => ({ ...atual, embalagens: { ...atual.embalagens, [codigo]: { ...(atual.embalagens[codigo] ?? { preco: '', descarte: '' }), [campo]: valor } } }))

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

        <fieldset className="scenario-manuais">
          <legend>Dados do cenário <small>ainda sem cadastro no sistema</small></legend>
          <div className="scenario-manuais-grupo"><h5>Produção</h5><div className="scenario-manuais-campos">
            {campoManual('taxa_mod', 'Taxa de MOD', 'R$/h por funcionário', 'Ex.: 38,00')}
            {campoManual('taxa_ggf', 'Taxa de GGF', 'R$/h', 'Ex.: 52,00')}
            {campoManual('produtividade', 'Produtividade', 'unidades/h', 'Ex.: 1200')}
            {campoManual('numero_funcionarios', 'Funcionários na linha', 'pessoas', 'Ex.: 6', 'numeric')}
          </div></div>
          <div className="scenario-manuais-grupo"><h5>Comercial</h5><div className="scenario-manuais-campos">
            {campoManual('margem', 'Margem desejada', '%', 'Ex.: 18')}
            {campoManual('comissao', 'Comissão', '%', 'Ex.: 3')}
            {campoManual('frete', 'Frete', '% do preço', 'Ex.: 2')}
            {precisaValorCliente && campoManual('valor_material_cliente', 'Material do cliente', 'R$ por unidade', 'Ex.: 12,50')}
          </div></div>
          <div className="scenario-manuais-grupo"><h5>Embalagens</h5>
            {embalagensForm.length
              ? <div className="scenario-embalagens">{embalagensForm.map((emb) => <div key={emb.codigo} className="scenario-embalagem">
                  <span className="scenario-embalagem-nome">{emb.descricao}<small>{emb.codigo}</small></span>
                  <label className="field"><span>Preço <small>(R$/un)</small></span><input inputMode="decimal" placeholder="Ex.: 1,85" value={manuais.embalagens[emb.codigo]?.preco ?? ''} onChange={(event) => alterarEmbalagem(emb.codigo, 'preco', event.target.value)} /></label>
                  <label className="field"><span>Descarte <small>(%)</small></span><input inputMode="decimal" placeholder="Ex.: 1" value={manuais.embalagens[emb.codigo]?.descarte ?? ''} onChange={(event) => alterarEmbalagem(emb.codigo, 'descarte', event.target.value)} /></label>
                </div>)}</div>
              : <p className="field-hint">As embalagens da formulação aparecem aqui depois do primeiro “Calcular cenário”.</p>}
          </div>
        </fieldset>


        <details className="np-avancado">
          <summary>Entrada manual (avançado)</summary>
          <p className="field-hint">A entrada completa que vai para o motor, já com os campos acima. Ajuste à mão só se precisar de algo fora do formulário.</p>
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
