import { useEffect, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import {
  compararCenarios,
  consultarCenario,
  duplicarCenario,
  listarCenarios,
  type CenarioDetalhe,
  type CenarioResumo,
  type ComparacaoCenarios,
} from './cenariosService'

type Props = {
  precificacaoId: string
  codigo: string
  canViewCost: boolean
  canEdit: boolean
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
const sentido: Record<string, string> = { subiu: 'Subiu', desceu: 'Desceu', igual: 'Sem variação', sem_base: 'Sem base' }

function ScenarioHistoryPanel({ precificacaoId, codigo, canViewCost, canEdit, onClose }: Props) {
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
      {canEdit && versoes.some((item) => item.versao_motor?.includes('mock')) && <p className="field-hint">Duplicar recalcula a versao pela API. O motor atual esta identificado como mock; os resultados permanecem demonstrativos.</p>}
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
        <dl className="scenario-result-grid">{(['custo_mp', 'custo_embalagem', 'custo_perda', 'custo_mod', 'custo_ggf', 'custo_total', 'preco_bruto', 'preco_bruto_sem_ipi', 'receita_operacional_liquida', 'margem_contribuicao_valor', 'margem_contribuicao_percentual'] as const).map((key) => <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{key === 'margem_contribuicao_percentual' ? percentual(String(resultado?.[key] ?? '')) : moeda(String(resultado?.[key] ?? ''))}</dd></div>)}</dl>
        {impostos && <div className="scenario-tax-list"><h4>Impostos destacados</h4>{Object.entries(impostos).map(([key, value]) => <p key={key}>{key.replaceAll('_', ' ')}: {moeda(value)}</p>)}</div>}
      </section>}
    </>}
  </section>
}

export default ScenarioHistoryPanel
