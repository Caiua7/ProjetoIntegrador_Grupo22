import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { formatarDecimalBr } from '../../app/decimal'
import { DatePicker } from '../../components/form/DatePicker'
import { Select } from '../../components/form/Select'
import { ApiError } from '../../services/apiClient'
import { listarInsumos, type Insumo } from '../cadastros/insumosService'
import { custoEstimado, faixaDe, faixas, fornecedores, precisaFornecedor, quantidadeParaApi, rotuloFornecedor } from './cotacoesRules'
import { listarCotacoesVigentes, resolverCotacao, type Cotacao } from './cotacoesService'

function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function dataBr(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR')
}

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof Error ? falha.message : padrao
}

function moeda(codigo: string, valor: string, casas = 2): string {
  const simbolo = codigo === 'BRL' ? 'R$' : codigo
  return `${simbolo} ${formatarDecimalBr(valor, casas)}`
}

type Resultado = { tipo: 'ok', cotacao: Cotacao, quantidade: string } | { tipo: 'erro', mensagem: string, empate: boolean }

export function QuotesPage() {
  const [busca, setBusca] = useState('')
  const [materias, setMaterias] = useState<Insumo[]>([])
  const [mp, setMp] = useState<Insumo | null>(null)
  const mpId = mp?.id ?? ''
  const [dataRef, setDataRef] = useState(hojeIso)
  const [cotacoes, setCotacoes] = useState<Cotacao[]>([])
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const [quantidade, setQuantidade] = useState('')
  const [fornecedorId, setFornecedorId] = useState('')
  const [resolvendo, setResolvendo] = useState(false)
  const [resultado, setResultado] = useState<Resultado | null>(null)

  // Busca de MP no cadastro (debounce curto; a API pagina em até 100).
  useEffect(() => {
    let ativo = true
    const espera = setTimeout(() => {
      void listarInsumos('materias-primas', { busca, ativo: 'ativos', unidade_medida: 'todas', pagina: 1, tamanho_pagina: 50 })
        .then((pagina) => { if (ativo) setMaterias(pagina.registros) })
        .catch((falha: unknown) => { if (ativo) setErro(mensagemDe(falha, 'Não foi possível buscar as matérias-primas.')) })
    }, 250)
    return () => { ativo = false; clearTimeout(espera) }
  }, [busca])

  useEffect(() => {
    if (!mpId) return
    let ativo = true
    void listarCotacoesVigentes(mpId, dataRef)
      .then((linhas) => { if (ativo) setCotacoes(linhas) })
      .catch((falha: unknown) => { if (ativo) { setCotacoes([]); setErro(mensagemDe(falha, 'Não foi possível carregar as cotações.')) } })
      .finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
  }, [mpId, dataRef])

  const listaFaixas = useMemo(() => faixas(cotacoes), [cotacoes])
  const listaFornecedores = useMemo(() => fornecedores(cotacoes), [cotacoes])
  const opcoesMp = useMemo(() => {
    // A escolhida continua na lista mesmo que a busca mude.
    const lista = mp && !materias.some((m) => m.id === mp.id) ? [mp, ...materias] : materias
    return lista.map((m) => ({ value: m.id, label: `${m.codigo} · ${m.descricao}`, detalhe: m.unidade_medida }))
  }, [materias, mp])

  function trocarMp(id: string) {
    setMp(materias.find((m) => m.id === id) ?? (mp?.id === id ? mp : null))
    setErro(null)
    setResultado(null)
    setFornecedorId('')
    setCotacoes([])
    setCarregando(!!id)
  }

  function trocarData(v: string) {
    setDataRef(v || hojeIso())
    setResultado(null)
    if (mpId) setCarregando(true)
  }

  async function simular(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    const qtd = quantidadeParaApi(quantidade)
    if (!mpId) return setErro('Escolha a matéria-prima.')
    if (!qtd) return setErro('Informe uma quantidade maior que zero, com até 3 casas decimais.')
    setErro(null)
    setResolvendo(true)
    try {
      const cotacao = await resolverCotacao({ materiaPrimaId: mpId, quantidade: qtd, dataReferencia: dataRef, fornecedorId: fornecedorId || undefined })
      setResultado({ tipo: 'ok', cotacao, quantidade: qtd })
    } catch (falha) {
      const status = falha instanceof ApiError ? falha.status : 0
      setResultado({ tipo: 'erro', mensagem: mensagemDe(falha, 'Não foi possível resolver a cotação.'), empate: precisaFornecedor(status) })
    } finally {
      setResolvendo(false)
    }
  }

  const resolvidaId = resultado?.tipo === 'ok' ? resultado.cotacao.id : null
  const unidade = mp?.unidade_medida ?? ''

  return <section className="content catalog-content quotes-content">
    <div className="list-intro">
      <div><span className="eyebrow">COTAÇÃO DE INSUMOS</span><h2>Cotações vigentes</h2><p>Faixas de volume negociadas por fornecedor e qual cotação vale para a quantidade do estudo.</p></div>
    </div>
    {erro && <p className="catalog-error" role="alert">{erro}</p>}

    <section className="form-card tax-filter-card" aria-label="Matéria-prima e data">
      <div className="catalog-form quotes-filters">
        <label className="field">Buscar matéria-prima<input placeholder="Código, descrição ou NCM" value={busca} maxLength={100} onChange={(e) => setBusca(e.target.value)} /></label>
        <label className="field"><span>Matéria-prima <b aria-hidden="true">*</b></span><Select pesquisavel value={mpId} onChange={trocarMp} placeholder={opcoesMp.length ? 'Selecione' : 'Nenhuma encontrada'} options={opcoesMp} /></label>
        <label className="field">Vigente em<DatePicker value={dataRef} onChange={trocarData} /></label>
      </div>
    </section>

    {!mpId ? <section className="form-card catalog-table-card"><div className="empty-list" role="status"><span className="empty-icon" aria-hidden="true">⇅</span><h3>Escolha uma matéria-prima</h3><p>As cotações vigentes e o simulador aparecem aqui.</p></div></section> : <>
      <section className="form-card catalog-table-card" aria-labelledby="quotes-sim-title">
        <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">≈</span><h3 id="quotes-sim-title">Simulador por volume</h3></div></div>
        <form className="catalog-form quotes-sim" onSubmit={(e) => { void simular(e) }}>
          <label className="field"><span>Quantidade{unidade ? ` (${unidade})` : ''} <b aria-hidden="true">*</b></span><input required inputMode="decimal" placeholder="250" value={quantidade} onChange={(e) => { setQuantidade(e.target.value); setResultado(null) }} /></label>
          <label className="field">Fornecedor<Select value={fornecedorId} onChange={(v) => { setFornecedorId(v); setResultado(null) }} options={[{ value: '', label: 'Qualquer (o sistema escolhe)' }, ...listaFornecedores.map((f) => ({ value: f.id, label: f.rotulo }))]} /></label>
          <div className="catalog-form-actions"><button className="button primary" type="submit" disabled={resolvendo || carregando}>{resolvendo ? 'Resolvendo…' : 'Resolver cotação'}</button></div>
        </form>
        {resultado?.tipo === 'ok' && <div className="pending-state tax-resolved quotes-result" role="status">
          <span aria-hidden="true">✓</span>
          <div>
            <strong>{rotuloFornecedor(resultado.cotacao)} · {moeda(resultado.cotacao.moeda, resultado.cotacao.preco, 4)}/{unidade || 'un'}</strong>
            <small>
              Faixa a partir de {formatarDecimalBr(resultado.cotacao.volume_minimo)}{unidade && ` ${unidade}`}
              {(() => { const f = faixaDe(resultado.cotacao.volume_minimo, listaFaixas); return f?.ateExclusive ? ` até menos de ${formatarDecimalBr(f.ateExclusive)}` : ' (última faixa)' })()}
              {' · '}validade {dataBr(resultado.cotacao.validade_inicio)}{resultado.cotacao.validade_fim ? ` a ${dataBr(resultado.cotacao.validade_fim)}` : ' sem fim'}
              {' · '}entrega em {resultado.cotacao.prazo_entrega_dias} dias
            </small>
            <small className="quotes-total">Custo estimado de {formatarDecimalBr(resultado.quantidade)}{unidade && ` ${unidade}`}: <b className="mono-cell">{moeda(resultado.cotacao.moeda, custoEstimado(resultado.cotacao.preco, resultado.quantidade), 2)}</b>{resultado.cotacao.moeda !== 'BRL' && ' (antes do câmbio)'}</small>
          </div>
        </div>}
        {resultado?.tipo === 'erro' && <p className="catalog-error quotes-result" role="alert">{resultado.mensagem}{resultado.empate && ' Escolha o fornecedor acima e resolva de novo.'}</p>}
      </section>

      <section className="form-card catalog-table-card" aria-labelledby="quotes-table-title">
        <div className="list-card-heading">
          <div><span className="heading-icon" aria-hidden="true">⇅</span><h3 id="quotes-table-title">Vigentes em {dataBr(dataRef)}</h3></div>
          <span className="list-scope">{cotacoes.length} {cotacoes.length === 1 ? 'cotação' : 'cotações'} · {listaFaixas.length} {listaFaixas.length === 1 ? 'faixa' : 'faixas'}</span>
        </div>
        {carregando ? <div className="empty-list" role="status">Carregando cotações…</div>
          : cotacoes.length === 0 ? <div className="empty-list" role="status"><h3>Nenhuma cotação vigente</h3><p>Não há cotação ativa desta matéria-prima em {dataBr(dataRef)}.</p></div>
            : <div className="table-scroll" role="region" aria-label="Cotações vigentes" tabIndex={0}><table className="pricing-table quotes-table"><caption className="sr-only">Cotações vigentes por faixa de volume</caption>
              <thead><tr><th scope="col">Faixa{unidade && ` (${unidade})`}</th><th scope="col">Fornecedor</th><th className="numeric" scope="col">Preço</th><th scope="col">Validade</th><th className="numeric" scope="col">Entrega</th></tr></thead>
              <tbody>{cotacoes.map((c) => {
                const f = faixaDe(c.volume_minimo, listaFaixas)
                return <tr key={c.id} className={c.id === resolvidaId ? 'quotes-resolved' : undefined} aria-current={c.id === resolvidaId ? 'true' : undefined}>
                  <th scope="row" className="mono-cell">{formatarDecimalBr(c.volume_minimo)}{f?.ateExclusive ? ` a < ${formatarDecimalBr(f.ateExclusive)}` : ' ou mais'}</th>
                  <td>{rotuloFornecedor(c)}</td>
                  <td className="numeric mono-cell">{moeda(c.moeda, c.preco, 4)}</td>
                  <td className="mono-cell">{dataBr(c.validade_inicio)} – {c.validade_fim ? dataBr(c.validade_fim) : 'sem fim'}</td>
                  <td className="numeric mono-cell">{c.prazo_entrega_dias} d</td>
                </tr>
              })}</tbody>
            </table></div>}
      </section>
    </>}
    <p className="list-footnote">A cotação aplicável é a da maior faixa cujo mínimo não passa da quantidade; na mesma faixa, vence a validade mais recente. Se dois fornecedores empatarem, informe qual usar. Preço em moeda estrangeira entra no custo convertido pelo câmbio vigente.</p>
  </section>
}
