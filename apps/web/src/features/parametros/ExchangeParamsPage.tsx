import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { formatarDecimalBr } from '../../app/decimal'
import { DatePicker } from '../../components/form/DatePicker'
import { Select } from '../../components/form/Select'
import { Modal } from '../../components/modal/Modal'
import {
  definicaoParametro,
  editavel,
  fracaoParaPercentual,
  hojeIso,
  margemParaApi,
  moedaValida,
  PARAMETROS,
  taxaComMargem,
  taxaParaApi,
  valorParametroParaApi,
  valorParametroParaTela,
  vigentesPorChave,
} from './parametrosRules'
import {
  consultarParametrosVigentes,
  corrigirCambio,
  corrigirVigenciaParametro,
  criarCambio,
  criarVigenciaParametro,
  listarCambios,
  listarParametros,
  type Cambio,
  type CodigoParametro,
  type FonteCambio,
  type ParametroGlobal,
  type ParametrosVigentes,
} from './parametrosService'

type Props = { canEditCambio: boolean, canReadParametros: boolean, canEditParametros: boolean }

type RascunhoCambio = { moeda: string, data_referencia: string, taxa: string, margem: string, fonte: FonteCambio }
type RascunhoParametro = { codigo: CodigoParametro, vigencia_inicio: string, valor: string }

const fontes: { value: FonteCambio, label: string }[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'ptax', label: 'PTAX (Banco Central)' },
]

function dataBr(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('pt-BR')
}

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof Error ? falha.message : padrao
}

function exibirParametro(codigo: CodigoParametro, valor: string): string {
  const texto = formatarDecimalBr(valorParametroParaTela(codigo, valor))
  return definicaoParametro(codigo).unidade === 'dias' ? `${texto} dias` : `${texto}%`
}

export function ExchangeParamsPage({ canEditCambio, canReadParametros, canEditParametros }: Props) {
  const hoje = hojeIso()
  const [dataRef, setDataRef] = useState(hoje)
  const [mensagem, setMensagem] = useState<string | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)

  // ---------------------------------------------------------- câmbio
  const [cambios, setCambios] = useState<Cambio[]>([])
  const [carregandoCambio, setCarregandoCambio] = useState(true)
  const [filtroMoeda, setFiltroMoeda] = useState('')
  const [versaoCambio, setVersaoCambio] = useState(0)
  const [formCambio, setFormCambio] = useState<{ editando: Cambio | null, rascunho: RascunhoCambio } | null>(null)

  useEffect(() => {
    let ativo = true
    void listarCambios().then((linhas) => { if (ativo) setCambios(linhas) })
      .catch((falha: unknown) => { if (ativo) setErro(mensagemDe(falha, 'Não foi possível carregar o câmbio.')) })
      .finally(() => { if (ativo) setCarregandoCambio(false) })
    return () => { ativo = false }
  }, [versaoCambio])

  const moedas = useMemo(() => [...new Set(cambios.map((c) => c.moeda))].sort(), [cambios])
  const cambiosVigentes = useMemo(() => vigentesPorChave(cambios, (c) => c.moeda, (c) => c.data_referencia, dataRef), [cambios, dataRef])
  const historicoCambio = filtroMoeda ? cambios.filter((c) => c.moeda === filtroMoeda) : cambios

  function novoCambio() {
    setErro(null)
    setMensagem(null)
    setFormCambio({ editando: null, rascunho: { moeda: filtroMoeda || 'USD', data_referencia: hoje, taxa: '', margem: '0', fonte: 'manual' } })
  }

  function editarCambio(item: Cambio) {
    setErro(null)
    setMensagem(null)
    setFormCambio({
      editando: item,
      rascunho: { moeda: item.moeda, data_referencia: item.data_referencia, taxa: formatarDecimalBr(item.taxa), margem: formatarDecimalBr(fracaoParaPercentual(item.margem_seguranca_percentual)), fonte: item.fonte },
    })
  }

  async function salvarCambio(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (!formCambio) return
    const { editando, rascunho } = formCambio
    const taxa = taxaParaApi(rascunho.taxa)
    const margem = margemParaApi(rascunho.margem)
    if (!editando && !moedaValida(rascunho.moeda)) return setErro('Informe a moeda em código ISO de 3 letras (ex.: USD). O real não tem câmbio.')
    if (!editando && !editavel(rascunho.data_referencia, hoje)) return setErro('A data do câmbio não pode ser anterior a hoje: isso mudaria cálculos já feitos.')
    if (!taxa) return setErro('Informe a taxa em reais por unidade da moeda, maior que zero e com até 6 casas.')
    if (margem === null) return setErro('A margem de segurança vai de 0% a 100%, com até 4 casas.')
    setErro(null)
    setSalvando(true)
    try {
      if (editando) await corrigirCambio(editando.id, { taxa, margem_seguranca_percentual: margem, fonte: rascunho.fonte })
      else await criarCambio({ moeda: rascunho.moeda, data_referencia: rascunho.data_referencia, taxa, margem_seguranca_percentual: margem, fonte: rascunho.fonte })
      setMensagem(editando ? `Câmbio de ${editando.moeda} em ${dataBr(editando.data_referencia)} corrigido.` : `Câmbio de ${rascunho.moeda} cadastrado a partir de ${dataBr(rascunho.data_referencia)}.`)
      setFormCambio(null)
      setCarregandoCambio(true)
      setVersaoCambio((v) => v + 1)
    } catch (falha) {
      setErro(mensagemDe(falha, 'Não foi possível salvar o câmbio.'))
    } finally {
      setSalvando(false)
    }
  }

  // ---------------------------------------------------------- parâmetros
  const [parametros, setParametros] = useState<ParametroGlobal[]>([])
  const [vigentes, setVigentes] = useState<ParametrosVigentes | null>(null)
  const [carregandoParametros, setCarregandoParametros] = useState(canReadParametros)
  const [versaoParametros, setVersaoParametros] = useState(0)
  const [formParametro, setFormParametro] = useState<{ editando: ParametroGlobal | null, rascunho: RascunhoParametro } | null>(null)

  useEffect(() => {
    if (!canReadParametros) return
    let ativo = true
    void Promise.all([listarParametros(), consultarParametrosVigentes(dataRef)])
      .then(([linhas, resumo]) => { if (ativo) { setParametros(linhas); setVigentes(resumo) } })
      .catch((falha: unknown) => { if (ativo) setErro(mensagemDe(falha, 'Não foi possível carregar os parâmetros globais.')) })
      .finally(() => { if (ativo) setCarregandoParametros(false) })
    return () => { ativo = false }
  }, [canReadParametros, dataRef, versaoParametros])

  function novoParametro(codigo: CodigoParametro = 'perda_percentual') {
    setErro(null)
    setMensagem(null)
    setFormParametro({ editando: null, rascunho: { codigo, vigencia_inicio: hoje, valor: '' } })
  }

  function editarParametro(item: ParametroGlobal) {
    setErro(null)
    setMensagem(null)
    setFormParametro({ editando: item, rascunho: { codigo: item.codigo, vigencia_inicio: item.vigencia_inicio, valor: formatarDecimalBr(valorParametroParaTela(item.codigo, item.valor)) } })
  }

  async function salvarParametro(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (!formParametro) return
    const { editando, rascunho } = formParametro
    const valor = valorParametroParaApi(rascunho.codigo, rascunho.valor)
    const definicao = definicaoParametro(rascunho.codigo)
    if (!editando && !editavel(rascunho.vigencia_inicio, hoje)) return setErro('A vigência não pode começar antes de hoje: isso mudaria cálculos já feitos.')
    if (valor === null) return setErro(definicao.unidade === 'dias' ? 'O prazo é em dias inteiros.' : 'Informe um percentual de 0% a 100%, com até 4 casas.')
    setErro(null)
    setSalvando(true)
    try {
      if (editando) await corrigirVigenciaParametro(editando.id, valor)
      else await criarVigenciaParametro({ codigo: rascunho.codigo, vigencia_inicio: rascunho.vigencia_inicio, valor })
      setMensagem(editando ? `${definicao.rotulo} corrigido na vigência de ${dataBr(editando.vigencia_inicio)}.` : `${definicao.rotulo} passa a valer a partir de ${dataBr(rascunho.vigencia_inicio)}.`)
      setFormParametro(null)
      setCarregandoParametros(true)
      setVersaoParametros((v) => v + 1)
    } catch (falha) {
      setErro(mensagemDe(falha, 'Não foi possível salvar o parâmetro.'))
    } finally {
      setSalvando(false)
    }
  }

  return <section className="content catalog-content exchange-content">
    <div className="list-intro">
      <div><span className="eyebrow">PARÂMETROS DO CÁLCULO</span><h2>Câmbio e parâmetros globais</h2><p>Valores com vigência por data que alimentam o custo e o encargo financeiro.</p></div>
      <label className="field exchange-ref">Vigente em<DatePicker value={dataRef} onChange={(v) => { setDataRef(v || hoje); if (canReadParametros) setCarregandoParametros(true) }} /></label>
    </div>
    <div className="demo-notice"><span className="notice-dot" />O histórico é imutável: para mudar um valor, cadastre uma nova vigência. Registros com data anterior a hoje ficam só para consulta.</div>
    {mensagem && <p className="catalog-success" role="status">{mensagem}</p>}
    {erro && !formCambio && !formParametro && <p className="catalog-error" role="alert">{erro}</p>}

    {/* ------------------------------------------------ câmbio */}
    <section className="form-card catalog-table-card" aria-labelledby="exchange-title">
      <div className="list-card-heading">
        <div><span className="heading-icon" aria-hidden="true">$</span><h3 id="exchange-title">Câmbio</h3></div>
        {canEditCambio && <button className="button primary" type="button" onClick={novoCambio}>+ Novo câmbio</button>}
      </div>

      {carregandoCambio ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando câmbio…</div> : <>
        <div className="exchange-cards" aria-label={`Câmbio vigente em ${dataBr(dataRef)}`}>
          {cambiosVigentes.size === 0
            ? <p className="exchange-empty">Nenhuma moeda tem câmbio vigente em {dataBr(dataRef)}.</p>
            : [...cambiosVigentes.values()].map((c) => <article className="exchange-card" key={c.moeda}>
              <header><strong>{c.moeda}</strong><small>desde {dataBr(c.data_referencia)} · {c.fonte === 'ptax' ? 'PTAX' : 'manual'}</small></header>
              <dl>
                <div><dt>Taxa</dt><dd className="mono-cell">R$ {formatarDecimalBr(c.taxa, 4)}</dd></div>
                <div><dt>Margem de segurança</dt><dd className="mono-cell">{formatarDecimalBr(fracaoParaPercentual(c.margem_seguranca_percentual))}%</dd></div>
                <div className="exchange-highlight"><dt>Taxa no custo</dt><dd className="mono-cell">R$ {formatarDecimalBr(taxaComMargem(c.taxa, c.margem_seguranca_percentual), 6)}</dd></div>
              </dl>
            </article>)}
        </div>

        {formCambio && <Modal titulo={formCambio.editando ? `Corrigir ${formCambio.editando.moeda} de ${dataBr(formCambio.editando.data_referencia)}` : 'Novo câmbio'} ocupado={salvando} onFechar={() => { setFormCambio(null); setErro(null) }}>
        {erro && <p className="catalog-error" role="alert">{erro}</p>}
        <form className="catalog-form exchange-form" onSubmit={(e) => { void salvarCambio(e) }}>
          <label className="field"><span>Moeda <b aria-hidden="true">*</b></span><input required maxLength={3} disabled={!!formCambio.editando} placeholder="USD" value={formCambio.rascunho.moeda}
            onChange={(e) => setFormCambio({ ...formCambio, rascunho: { ...formCambio.rascunho, moeda: e.target.value.toUpperCase().replace(/[^A-Z]/g, '') } })} /></label>
          <label className="field"><span>Data de referência <b aria-hidden="true">*</b></span><DatePicker required disabled={!!formCambio.editando} value={formCambio.rascunho.data_referencia}
            onChange={(v) => setFormCambio({ ...formCambio, rascunho: { ...formCambio.rascunho, data_referencia: v } })} /></label>
          <label className="field"><span>Taxa (R$ por unidade) <b aria-hidden="true">*</b></span><input required inputMode="decimal" placeholder="5,1234" value={formCambio.rascunho.taxa}
            onChange={(e) => setFormCambio({ ...formCambio, rascunho: { ...formCambio.rascunho, taxa: e.target.value } })} /></label>
          <label className="field"><span>Margem de segurança (%)</span><input inputMode="decimal" placeholder="0" value={formCambio.rascunho.margem}
            onChange={(e) => setFormCambio({ ...formCambio, rascunho: { ...formCambio.rascunho, margem: e.target.value } })} /></label>
          <label className="field"><span>Fonte</span><Select value={formCambio.rascunho.fonte} options={fontes}
            onChange={(v) => setFormCambio({ ...formCambio, rascunho: { ...formCambio.rascunho, fonte: v as FonteCambio } })} /></label>
          <div className="catalog-form-actions"><button className="button secondary" type="button" disabled={salvando} onClick={() => setFormCambio(null)}>Cancelar</button><button className="button primary" type="submit" disabled={salvando}>{salvando ? 'Salvando…' : formCambio.editando ? 'Salvar correção' : 'Cadastrar câmbio'}</button></div>
        </form></Modal>}

        <div className="exchange-history-heading">
          <h4>Histórico</h4>
          <label className="field"><span>Moeda</span><Select compacto value={filtroMoeda} onChange={setFiltroMoeda} options={[{ value: '', label: 'Todas' }, ...moedas.map((m) => ({ value: m, label: m }))]} /></label>
        </div>
        {historicoCambio.length === 0
          ? <div className="empty-list" role="status"><h3>Nenhum câmbio cadastrado</h3>{canEditCambio && <p>Cadastre a primeira cotação de moeda.</p>}</div>
          : <div className="table-scroll" role="region" aria-label="Histórico de câmbio" tabIndex={0}><table className="pricing-table exchange-table"><caption className="sr-only">Câmbio por moeda e data</caption>
            <thead><tr><th scope="col">Moeda</th><th scope="col">Data</th><th className="numeric" scope="col">Taxa</th><th className="numeric" scope="col">Margem</th><th className="numeric" scope="col">Taxa no custo</th><th scope="col">Fonte</th><th scope="col">Situação</th>{canEditCambio && <th scope="col"><span className="sr-only">Ações</span></th>}</tr></thead>
            <tbody>{historicoCambio.map((c) => <tr key={c.id}>
              <th scope="row">{c.moeda}</th><td className="mono-cell">{dataBr(c.data_referencia)}</td>
              <td className="numeric mono-cell">{formatarDecimalBr(c.taxa, 4)}</td>
              <td className="numeric mono-cell">{formatarDecimalBr(fracaoParaPercentual(c.margem_seguranca_percentual))}%</td>
              <td className="numeric mono-cell">{formatarDecimalBr(taxaComMargem(c.taxa, c.margem_seguranca_percentual), 6)}</td>
              <td>{c.fonte === 'ptax' ? 'PTAX' : 'Manual'}</td>
              <td><Situacao vigente={cambiosVigentes.get(c.moeda)?.id === c.id} futura={c.data_referencia > dataRef} /></td>
              {canEditCambio && <td className="cell-acoes">{editavel(c.data_referencia, hoje) && <button className="button secondary compacto" type="button" onClick={() => editarCambio(c)}>Corrigir</button>}</td>}
            </tr>)}</tbody>
          </table></div>}
      </>}
    </section>

    {/* ------------------------------------------------ parâmetros globais */}
    {canReadParametros && <section className="form-card catalog-table-card" aria-labelledby="params-title">
      <div className="list-card-heading">
        <div><span className="heading-icon" aria-hidden="true">%</span><h3 id="params-title">Parâmetros globais</h3></div>
        {canEditParametros && <button className="button primary" type="button" onClick={() => novoParametro()}>+ Nova vigência</button>}
      </div>

      {carregandoParametros ? <div className="empty-list" role="status"><span className="np-carregando" aria-hidden="true" />Carregando parâmetros…</div> : <>
        {vigentes && vigentes.faltando.length > 0 && <p className="catalog-error" role="alert">
          Sem valor vigente em {dataBr(dataRef)}: {vigentes.faltando.map((c) => definicaoParametro(c).rotulo).join(', ')}. O cálculo não fecha sem eles.
        </p>}
        <div className="exchange-cards">
          {PARAMETROS.map((p) => {
            const atual = vigentes?.parametros[p.codigo]
            return <article className={`exchange-card${atual ? '' : ' exchange-card-missing'}`} key={p.codigo}>
              <header><strong>{p.rotulo}</strong><small>{atual ? `desde ${dataBr(atual.vigencia_inicio)}` : 'sem vigência'}</small></header>
              <p className="exchange-value mono-cell">{atual ? exibirParametro(p.codigo, atual.valor) : '—'}</p>
              <p className="exchange-desc">{p.descricao}</p>
              {canEditParametros && <button className="button secondary compacto" type="button" onClick={() => novoParametro(p.codigo)}>Nova vigência</button>}
            </article>
          })}
        </div>

        {formParametro && <Modal titulo={formParametro.editando ? `Corrigir ${definicaoParametro(formParametro.editando.codigo).rotulo.toLowerCase()} de ${dataBr(formParametro.editando.vigencia_inicio)}` : 'Nova vigência de parâmetro'}
          subtitulo="O valor passa a valer a partir da data de início; as vigências anteriores ficam no histórico." ocupado={salvando} onFechar={() => { setFormParametro(null); setErro(null) }}>
        {erro && <p className="catalog-error" role="alert">{erro}</p>}
        <form className="catalog-form exchange-form" onSubmit={(e) => { void salvarParametro(e) }}>
          <label className="field"><span>Parâmetro <b aria-hidden="true">*</b></span><Select required disabled={!!formParametro.editando} value={formParametro.rascunho.codigo}
            options={PARAMETROS.map((p) => ({ value: p.codigo, label: p.rotulo }))}
            onChange={(v) => setFormParametro({ ...formParametro, rascunho: { ...formParametro.rascunho, codigo: v as CodigoParametro, valor: '' } })} /></label>
          <label className="field"><span>Início da vigência <b aria-hidden="true">*</b></span><DatePicker required disabled={!!formParametro.editando} value={formParametro.rascunho.vigencia_inicio}
            onChange={(v) => setFormParametro({ ...formParametro, rascunho: { ...formParametro.rascunho, vigencia_inicio: v } })} /></label>
          <label className="field"><span>{definicaoParametro(formParametro.rascunho.codigo).unidade === 'dias' ? 'Valor (dias)' : 'Valor (%)'} <b aria-hidden="true">*</b></span><input required inputMode="decimal" value={formParametro.rascunho.valor}
            onChange={(e) => setFormParametro({ ...formParametro, rascunho: { ...formParametro.rascunho, valor: e.target.value } })} /></label>
          <div className="catalog-form-actions"><button className="button secondary" type="button" disabled={salvando} onClick={() => setFormParametro(null)}>Cancelar</button><button className="button primary" type="submit" disabled={salvando}>{salvando ? 'Salvando…' : formParametro.editando ? 'Salvar correção' : 'Criar vigência'}</button></div>
        </form></Modal>}

        <div className="exchange-history-heading"><h4>Histórico de vigências</h4></div>
        {parametros.length === 0
          ? <div className="empty-list" role="status"><h3>Nenhuma vigência cadastrada</h3></div>
          : <div className="table-scroll" role="region" aria-label="Histórico de parâmetros globais" tabIndex={0}><table className="pricing-table exchange-table"><caption className="sr-only">Parâmetros globais por vigência</caption>
            <thead><tr><th scope="col">Parâmetro</th><th scope="col">Vigência</th><th className="numeric" scope="col">Valor</th><th scope="col">Situação</th>{canEditParametros && <th scope="col"><span className="sr-only">Ações</span></th>}</tr></thead>
            <tbody>{parametros.map((p) => <tr key={p.id}>
              <th scope="row">{definicaoParametro(p.codigo).rotulo}</th><td className="mono-cell">{dataBr(p.vigencia_inicio)}</td>
              <td className="numeric mono-cell">{exibirParametro(p.codigo, p.valor)}</td>
              <td><Situacao vigente={vigentes?.parametros[p.codigo]?.id === p.id} futura={p.vigencia_inicio > dataRef} /></td>
              {canEditParametros && <td className="cell-acoes">{editavel(p.vigencia_inicio, hoje) && <button className="button secondary compacto" type="button" onClick={() => editarParametro(p)}>Corrigir</button>}</td>}
            </tr>)}</tbody>
          </table></div>}
      </>}
    </section>}
    <p className="list-footnote">A taxa no custo é taxa × (1 + margem de segurança). Percentuais são gravados em fração (1,2% = 0,012), como no contrato do motor.</p>
  </section>
}

/** Situação da vigência na data consultada, em vez de pintar a linha inteira. */
function Situacao({ vigente, futura }: { vigente: boolean, futura: boolean }) {
  if (vigente) return <span className="status-pill status-approved"><i />Vigente</span>
  if (futura) return <span className="status-pill status-review"><i />Agendada</span>
  return <span className="status-pill status-neutral"><i />Encerrada</span>
}
