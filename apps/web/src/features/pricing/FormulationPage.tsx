import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../../services/apiClient'
import { listarInsumos, type Insumo, type TipoInsumo } from '../cadastros/insumosService'
import { normalizarDecimal, perdaValida, quantidadeValida } from './decimalInput'
import type { ConsultaInsumos } from '../cadastros/insumosQuery'
import { listarProdutos, obterFormulacao, salvarFormulacao, type FormulacaoItem, type OrigemMaterial, type Produto, type TipoItem, type Unidade } from './formulacoesService'
import { listarPrecificacoes, type Precificacao } from './precificacoesService'
import ScenarioHistoryPanel from './ScenarioHistoryPanel'
import { Select } from '../../components/form/Select'
import { formatarDecimalBr } from '../../app/decimal'

type Draft = Omit<FormulacaoItem, 'quantidade' | 'perda_percentual'> & { quantidade: string, perda_percentual: string }
type ItemDraft = Draft
const unidades: Unidade[] = ['kg', 'g', 'l', 'ml', 'un']
const vazio = (tipo: TipoItem = 'materia_prima'): Draft => ({
  tipo_insumo: tipo, materia_prima_id: null, embalagem_id: null, quantidade: '', unidade_medida: tipo === 'embalagem' ? 'un' : 'kg', perda_percentual: '', origem_material: null,
})

async function listarTodosInsumos(tipo: TipoInsumo): Promise<Insumo[]> {
  const consulta: Omit<ConsultaInsumos, 'pagina'> = {
    busca: '', ativo: 'todos', unidade_medida: 'todas', tamanho_pagina: 100,
  }
  const registros: Insumo[] = []
  let pagina = 1
  while (true) {
    const resposta = await listarInsumos(tipo, { ...consulta, pagina })
    registros.push(...resposta.registros)
    if (pagina >= resposta.total_paginas) break
    pagina += 1
  }
  return registros
}

export function FormulationPage({ canEdit, canViewCost, canReadCatalog, canReadCambio, canReadParametros, canReadImpostos }: {
  canEdit: boolean, canViewCost: boolean, canReadCatalog: boolean, canReadCambio: boolean, canReadParametros: boolean, canReadImpostos: boolean
}) {
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [materias, setMaterias] = useState<Insumo[]>([])
  const [embalagens, setEmbalagens] = useState<Insumo[]>([])
  const [produtoId, setProdutoId] = useState('')
  const [itens, setItens] = useState<ItemDraft[]>([])
  const [novo, setNovo] = useState<Draft>(vazio())
  const [carregandoCatalogos, setCarregandoCatalogos] = useState(true)
  const [carregandoFormulacao, setCarregandoFormulacao] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)
  const [erroAdicionar, setErroAdicionar] = useState<string | null>(null)
  const [erroSalvar, setErroSalvar] = useState<string | null>(null)
  const [precificacoes, setPrecificacoes] = useState<Precificacao[]>([])
  const [precificacaoCenario, setPrecificacaoCenario] = useState<Precificacao | null>(null)
  const [formulaRevision, setFormulaRevision] = useState(0)

  useEffect(() => {
    let vigente = true
    if (!canReadCatalog) return () => { vigente = false }
    Promise.all([listarProdutos(), listarTodosInsumos('materias-primas'), listarTodosInsumos('embalagens')])
      .then(([listaProdutos, listaMaterias, listaEmbalagens]) => {
        if (!vigente) return
        setProdutos(listaProdutos); setMaterias(listaMaterias); setEmbalagens(listaEmbalagens)
      }).catch((falha: unknown) => { if (vigente) setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar produtos e insumos.') })
      .finally(() => { if (vigente) setCarregandoCatalogos(false) })
    return () => { vigente = false }
  }, [canReadCatalog])

  useEffect(() => {
    if (!canReadCatalog) return
    let vigente = true
    listarPrecificacoes().then((lista) => { if (vigente) setPrecificacoes(lista) })
      .catch((falha: unknown) => { if (vigente) setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar cenários relacionados.') })
    return () => { vigente = false }
  }, [canReadCatalog])

  useEffect(() => {
    if (!produtoId) return
    let vigente = true
    obterFormulacao(produtoId).then((formulacao) => { if (vigente) setItens(formulacao.itens.map((item) => ({ ...item,
      quantidade: item.quantidade, perda_percentual: item.perda_percentual ?? '' }))) })
      .catch((falha: unknown) => {
        if (!vigente) return
        if (falha instanceof ApiError && falha.status === 404) setItens([])
        else { setItens([]); setErro(falha instanceof Error ? falha.message : 'Não foi possível recuperar a formulação.') }
      }).finally(() => { if (vigente) setCarregandoFormulacao(false) })
    return () => { vigente = false }
  }, [produtoId])

  const opcoes = (novo.tipo_insumo === 'materia_prima' ? materias : embalagens).filter((item) => item.ativo)
  const insumosPorId = useMemo(() => new Map([...materias, ...embalagens].map((item) => [item.id, item])), [materias, embalagens])
  const precificacoesProduto = useMemo(() => precificacoes.filter((item) => item.produto_id === produtoId), [precificacoes, produtoId])

  function mudarTipo(tipo_insumo: TipoItem) { setNovo({ ...vazio(tipo_insumo) }) }
  function adicionar() {
    const id = novo.tipo_insumo === 'materia_prima' ? novo.materia_prima_id : novo.embalagem_id
    if (!id || !novo.origem_material || !quantidadeValida(novo.quantidade) || (novo.perda_percentual !== '' && !perdaValida(novo.perda_percentual))) {
      setErroAdicionar('Escolha o insumo e a origem do material, informe a quantidade (maior que zero) e, se quiser, a perda entre 0 e 100%.'); return
    }
    setItens((atuais) => [...atuais, { tipo_insumo: novo.tipo_insumo, materia_prima_id: novo.tipo_insumo === 'materia_prima' ? id : null,
      embalagem_id: novo.tipo_insumo === 'embalagem' ? id : null, quantidade: normalizarDecimal(novo.quantidade), unidade_medida: novo.unidade_medida, origem_material: novo.origem_material,
      perda_percentual: novo.perda_percentual === '' ? '' : normalizarDecimal(novo.perda_percentual) }])
    setNovo(vazio(novo.tipo_insumo)); setErroAdicionar(null); setMensagem(null)
  }
  function editar(index: number, patch: Partial<ItemDraft>) {
    setItens((atuais) => atuais.map((item, posicao) => posicao === index ? { ...item, ...patch } : item)); setMensagem(null)
  }
  async function salvar() {
    if (!produtoId) return
    if (itens.some((item) => !item.origem_material || !quantidadeValida(item.quantidade) ||
      (item.perda_percentual !== '' && !perdaValida(item.perda_percentual)))) {
      setErroSalvar('Revise a origem, as quantidades e as perdas antes de salvar.'); return
    }
    setSalvando(true); setErroSalvar(null); setMensagem(null)
    try { const salva = await salvarFormulacao(produtoId, itens.map((item) => ({ tipo_insumo: item.tipo_insumo,
      materia_prima_id: item.materia_prima_id, embalagem_id: item.embalagem_id, quantidade: normalizarDecimal(item.quantidade),
      unidade_medida: item.unidade_medida, perda_percentual: item.perda_percentual === '' ? null : normalizarDecimal(item.perda_percentual), origem_material: item.origem_material })))
      setItens(salva.itens.map((item) => ({ ...item, quantidade: item.quantidade, perda_percentual: item.perda_percentual ?? '' })))
      setMensagem('Formulação salva.')
      setFormulaRevision((revision) => revision + 1) }
    catch (falha) { setErroSalvar(falha instanceof Error ? falha.message : 'Não foi possível salvar a formulação.') }
    finally { setSalvando(false) }
  }

  const produto = produtos.find((item) => item.id === produtoId)
  const opcoesUnidade = unidades.map((unidade) => ({ value: unidade, label: unidade }))
  const opcoesOrigem = [{ value: 'fabricante', label: 'Fabricante' }, { value: 'cliente', label: 'Cliente' }]

  return <section className="content catalog-content">
    <div className="list-intro"><div><span className="eyebrow">COMPOSIÇÃO DO PRODUTO</span><h2>Formulações</h2><p>Monte e mantenha os insumos associados a cada produto.</p></div></div>
    {erro && <p className="catalog-error" role="alert">{erro}</p>}
    <section className="form-card formulation-selector">
      <label className="field"><span>Produto</span>
        <Select pesquisavel value={produtoId} disabled={salvando || carregandoCatalogos || !canReadCatalog}
          placeholder={carregandoCatalogos ? 'Carregando produtos…' : 'Selecione um produto ativo'}
          options={produtos.map((item) => ({ value: item.id, label: `${item.codigo} — ${item.descricao}` }))}
          onChange={(valor) => { setProdutoId(valor); setItens([]); setCarregandoFormulacao(Boolean(valor)); setErro(null); setErroAdicionar(null); setErroSalvar(null); setMensagem(null); setPrecificacaoCenario(null) }} />
      </label>
      {!canReadCatalog && <p className="field-hint" role="status">Seu perfil não pode consultar os cadastros, então não é possível montar formulações.</p>}
      {produto && <p className="field-hint">{[produto.categoria, produto.peso_liquido_g ? `${formatarDecimalBr(String(produto.peso_liquido_g))} g` : ''].filter(Boolean).join(' · ')}</p>}
    </section>

    {produtoId && <div className="formulation-workspace">
      <div className="formulation-editor">
      {canEdit && <section className="form-card formulation-add">
        <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">＋</span><h3>Adicionar componente</h3></div></div>
        <div className="formulation-add-grid">
          <label className="field"><span>Tipo</span><Select value={novo.tipo_insumo} onChange={(valor) => mudarTipo(valor as TipoItem)}
            options={[{ value: 'materia_prima', label: 'Matéria-prima' }, { value: 'embalagem', label: 'Embalagem' }]} /></label>
          <label className="field"><span>Insumo</span><Select pesquisavel placeholder="Selecione um insumo"
            value={novo.tipo_insumo === 'materia_prima' ? novo.materia_prima_id ?? '' : novo.embalagem_id ?? ''}
            options={opcoes.map((item) => ({ value: item.id, label: item.descricao, detalhe: item.codigo }))}
            onChange={(valor) => { const found = opcoes.find((item) => item.id === valor); setNovo({ ...novo, materia_prima_id: novo.tipo_insumo === 'materia_prima' ? valor || null : null, embalagem_id: novo.tipo_insumo === 'embalagem' ? valor || null : null, unidade_medida: found?.unidade_medida ?? novo.unidade_medida }) }} /></label>
          <label className="field"><span>Quantidade</span><input type="text" inputMode="decimal" placeholder="0,000" value={novo.quantidade} onChange={(event) => setNovo({ ...novo, quantidade: event.target.value })} /></label>
          <label className="field"><span>Unidade</span><Select value={novo.unidade_medida} options={opcoesUnidade} onChange={(valor) => setNovo({ ...novo, unidade_medida: valor as Unidade })} /></label>
          <label className="field"><span>Origem do material</span><Select value={novo.origem_material ?? ''} options={opcoesOrigem} onChange={(valor) => setNovo({ ...novo, origem_material: (valor || null) as OrigemMaterial | null })} /></label>
          <label className="field"><span>Perda <small>(opcional, %)</small></span><input type="text" inputMode="decimal" placeholder="0" value={novo.perda_percentual} onChange={(event) => setNovo({ ...novo, perda_percentual: event.target.value })} /></label>
        </div>
        <div className="formulation-add-footer">
          {erroAdicionar ? <p className="np-erro-campo" role="alert">{erroAdicionar}</p> : <span />}
          <button className="button primary" type="button" onClick={adicionar}>Adicionar à composição</button>
        </div>
      </section>}
      <section className="form-card catalog-table-card">
        <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">▤</span><h3>Componentes da formulação</h3></div><span className="list-scope">{itens.length} {itens.length === 1 ? 'item' : 'itens'}</span></div>
        {carregandoCatalogos || carregandoFormulacao ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando formulação…</div> : itens.length === 0 ? <div className="empty-list"><h3>Composição vazia</h3><p>Adicione matérias-primas ou embalagens para iniciar.</p></div> : <div className="table-scroll" role="region" aria-label="Itens da formulação" tabIndex={0}>
          <table className="pricing-table formulation-table"><thead><tr><th>Tipo</th><th>Insumo</th><th>Origem</th><th>Quantidade</th><th>Unidade</th><th>Perda (%)</th>{canEdit && <th><span className="sr-only">Ações</span></th>}</tr></thead><tbody>
            {itens.map((item, index) => { const id = item.tipo_insumo === 'materia_prima' ? item.materia_prima_id : item.embalagem_id; const insumo = id ? insumosPorId.get(id) : undefined
              return <tr key={item.id ?? `${id}-${index}`}><td>{item.tipo_insumo === 'materia_prima' ? 'Matéria-prima' : 'Embalagem'}</td><td>{insumo ? <>{insumo.descricao}<small className="cell-sub">{insumo.codigo}</small></> : 'Insumo indisponível'}</td>
                <td>{canEdit ? <Select compacto ariaLabel={`Origem do material de ${insumo?.descricao ?? 'insumo'}`} value={item.origem_material ?? ''} options={opcoesOrigem} onChange={(valor) => editar(index, { origem_material: (valor || null) as OrigemMaterial | null })} /> : item.origem_material === 'fabricante' ? 'Fabricante' : item.origem_material === 'cliente' ? 'Cliente' : 'Não definida'}</td>
                <td>{canEdit ? <input aria-label={`Quantidade de ${insumo?.descricao ?? 'insumo'}`} type="text" inputMode="decimal" value={item.quantidade} onChange={(event) => editar(index, { quantidade: event.target.value })} /> : formatarDecimalBr(item.quantidade)}</td>
                <td>{canEdit ? <Select compacto ariaLabel={`Unidade de ${insumo?.descricao ?? 'insumo'}`} value={item.unidade_medida} options={opcoesUnidade} onChange={(valor) => editar(index, { unidade_medida: valor as Unidade })} /> : item.unidade_medida}</td>
                <td>{canEdit ? <input aria-label={`Perda de ${insumo?.descricao ?? 'insumo'}`} type="text" inputMode="decimal" value={item.perda_percentual} onChange={(event) => editar(index, { perda_percentual: event.target.value })} /> : item.perda_percentual ? formatarDecimalBr(item.perda_percentual) : '—'}</td>
                {canEdit && <td className="cell-acoes"><button type="button" className="button secondary compacto" onClick={() => { setItens((atuais) => atuais.filter((_, posicao) => posicao !== index)); setMensagem(null) }}>Remover</button></td>}</tr>
            })}
          </tbody></table></div>}
        {canEdit && <div className="formulation-add-footer">
          {mensagem ? <p className="np-sucesso" role="status">{mensagem}</p> : erroSalvar ? <p className="np-erro-campo" role="alert">{erroSalvar}</p> : <span />}
          <button className="button primary" type="button" disabled={salvando || carregandoCatalogos || carregandoFormulacao} onClick={() => { void salvar() }}>{salvando ? 'Salvando…' : 'Salvar formulação'}</button>
        </div>}
      </section>
      </div>
      <aside className="formulation-sidebar" aria-label="Rentabilidade dos cenários salvos">
        <section className="form-card scenario-profitability">
          <div className="card-heading"><span className="heading-icon" aria-hidden="true">%</span><div><h3>Rentabilidade</h3><p>Cenários salvos das precificações deste produto.</p></div></div>
          {precificacoesProduto.length === 0
            ? <p className="field-hint">Nenhuma precificação usa este produto ainda.</p>
            : <label className="field"><span>Precificação</span><Select placeholder="Selecione uma precificação" value={precificacaoCenario?.id ?? ''}
                options={precificacoesProduto.map((item) => ({ value: item.id, label: item.codigo, detalhe: item.cliente?.razao_social ?? undefined }))}
                onChange={(valor) => setPrecificacaoCenario(precificacoesProduto.find((item) => item.id === valor) ?? null)} /></label>}
        </section>
      </aside>
    </div>}
    {precificacaoCenario && <ScenarioHistoryPanel key={precificacaoCenario.id} precificacaoId={precificacaoCenario.id} codigo={precificacaoCenario.codigo} precificacao={precificacaoCenario}
      canViewCost={canViewCost} canEdit={canEdit} canReadCatalog={canReadCatalog} canReadCambio={canReadCambio}
      canReadParametros={canReadParametros} canReadImpostos={canReadImpostos} formulaRevision={formulaRevision} onClose={() => setPrecificacaoCenario(null)} />}
  </section>
}
