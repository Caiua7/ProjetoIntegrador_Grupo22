import { useEffect, useState, type FormEvent } from 'react'
import {
  atualizarInsumo,
  buscarNcm,
  criarInsumo,
  inativarInsumo,
  listarInsumos,
  obterInsumo,
  type Insumo,
  type InsumoEntrada,
  type Ncm,
  type TipoInsumo,
} from './insumosService'

type Draft = { codigo: string, descricao: string, unidade_medida: InsumoEntrada['unidade_medida'] }

const unidades: InsumoEntrada['unidade_medida'][] = ['kg', 'g', 'l', 'ml', 'un']
const rotulos: Record<TipoInsumo, string> = {
  'materias-primas': 'Matérias-primas',
  embalagens: 'Embalagens',
}

function unidadeInicial(tipo: TipoInsumo): Draft['unidade_medida'] {
  return tipo === 'materias-primas' ? 'kg' : 'un'
}

export function InsumosPage({ canEdit }: { canEdit: boolean }) {
  const [tipo, setTipo] = useState<TipoInsumo>('materias-primas')
  const [itens, setItens] = useState<Insumo[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)
  const [versao, setVersao] = useState(0)
  const [formularioAberto, setFormularioAberto] = useState(false)
  const [editando, setEditando] = useState<Insumo | null>(null)
  const [rascunho, setRascunho] = useState<Draft>({ codigo: '', descricao: '', unidade_medida: 'kg' })
  const [ncmCodigo, setNcmCodigo] = useState('')
  const [ncmBusca, setNcmBusca] = useState('')
  const [opcoesNcm, setOpcoesNcm] = useState<Ncm[]>([])
  const [buscandoNcm, setBuscandoNcm] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [registroDetalhe, setRegistroDetalhe] = useState<Insumo | null>(null)
  const [carregandoDetalhe, setCarregandoDetalhe] = useState<string | null>(null)
  const [operandoId, setOperandoId] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    void listarInsumos(tipo).then((resultado) => {
      if (vigente) setItens(resultado)
    }).catch((falha: unknown) => {
      if (vigente) setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar os cadastros.')
    }).finally(() => {
      if (vigente) setCarregando(false)
    })
    return () => { vigente = false }
  }, [tipo, versao])

  useEffect(() => {
    const termo = ncmBusca.trim()
    if (!formularioAberto || termo.length < 2) return
    let vigente = true
    const temporizador = window.setTimeout(() => {
      setBuscandoNcm(true)
      void buscarNcm(termo).then((resultado) => {
        if (vigente) setOpcoesNcm(resultado)
      }).catch((falha: unknown) => {
        if (vigente) setErro(falha instanceof Error ? falha.message : 'Não foi possível buscar o NCM.')
      }).finally(() => {
        if (vigente) setBuscandoNcm(false)
      })
    }, 250)
    return () => {
      vigente = false
      window.clearTimeout(temporizador)
    }
  }, [formularioAberto, ncmBusca])

  function abrirNovo() {
    setEditando(null)
    setRascunho({ codigo: '', descricao: '', unidade_medida: unidadeInicial(tipo) })
    setNcmCodigo('')
    setNcmBusca('')
    setOpcoesNcm([])
    setBuscandoNcm(false)
    setMensagem(null)
    setErro(null)
    setFormularioAberto(true)
  }

  function abrirEdicao(item: Insumo) {
    setEditando(item)
    setRascunho({ codigo: item.codigo, descricao: item.descricao, unidade_medida: item.unidade_medida })
    setNcmCodigo(item.ncm_codigo)
    setNcmBusca(item.ncm_codigo)
    setOpcoesNcm([])
    setBuscandoNcm(false)
    setMensagem(null)
    setErro(null)
    setFormularioAberto(true)
  }

  async function enviarFormulario(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (!ncmCodigo) {
      setErro('Selecione um NCM válido nos resultados da busca.')
      return
    }
    setSalvando(true)
    setErro(null)
    try {
      const entrada: InsumoEntrada = { ...rascunho, ncm_codigo: ncmCodigo }
      if (editando) await atualizarInsumo(tipo, editando.id, entrada)
      else await criarInsumo(tipo, entrada)
      setMensagem(editando ? 'Cadastro atualizado.' : 'Cadastro criado.')
      setFormularioAberto(false)
      setEditando(null)
      setCarregando(true)
      setVersao((atual) => atual + 1)
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível salvar o cadastro.')
    } finally {
      setSalvando(false)
    }
  }

  async function mostrarDetalhes(id: string) {
    setCarregandoDetalhe(id)
    setErro(null)
    try {
      setRegistroDetalhe(await obterInsumo(tipo, id))
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar os detalhes.')
    } finally {
      setCarregandoDetalhe(null)
    }
  }

  async function alternarAtivo(item: Insumo) {
    const acao = item.ativo ? 'inativar' : 'reativar'
    if (item.ativo && !window.confirm(`Inativar “${item.descricao}”? O registro será preservado no histórico.`)) return
    setOperandoId(item.id)
    setErro(null)
    try {
      if (item.ativo) await inativarInsumo(tipo, item.id)
      else await atualizarInsumo(tipo, item.id, { ativo: true })
      setMensagem(item.ativo ? 'Cadastro inativado.' : 'Cadastro reativado.')
      setRegistroDetalhe(null)
      setCarregando(true)
      setVersao((atual) => atual + 1)
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : `Não foi possível ${acao} o cadastro.`)
    } finally {
      setOperandoId(null)
    }
  }

  return <section className="content catalog-content">
    <div className="list-intro">
      <div><span className="eyebrow">CADASTROS BASE</span><h2>Matérias-primas e embalagens</h2><p>Consulte e mantenha os insumos usados nos cadastros do NeoPrice.</p></div>
      {canEdit && <button className="button primary" type="button" onClick={abrirNovo}>+ Novo cadastro</button>}
    </div>

    <div className="catalog-tabs" role="group" aria-label="Tipo de cadastro">
      {(Object.keys(rotulos) as TipoInsumo[]).map((opcao) => <button
        key={opcao}
        className={`filter-chip${tipo === opcao ? ' selected' : ''}`}
        type="button"
        aria-pressed={tipo === opcao}
        onClick={() => { setTipo(opcao); setCarregando(true); setErro(null); setRegistroDetalhe(null); setFormularioAberto(false); setMensagem(null) }}
      >{rotulos[opcao]}</button>)}
    </div>

    {mensagem && <p className="catalog-success" role="status">{mensagem}</p>}
    {erro && <p className="catalog-error" role="alert">{erro}</p>}

    {formularioAberto && <section className="form-card catalog-form-card" aria-labelledby="insumo-form-title">
      <div className="list-card-heading"><h3 id="insumo-form-title">{editando ? 'Editar cadastro' : `Novo cadastro de ${rotulos[tipo].toLocaleLowerCase('pt-BR')}`}</h3></div>
      <form className="catalog-form" onSubmit={(evento) => { void enviarFormulario(evento) }}>
        <label className="field">Código <b aria-hidden="true">*</b>
          <input required maxLength={30} value={rascunho.codigo} onChange={(evento) => setRascunho({ ...rascunho, codigo: evento.target.value })} />
        </label>
        <label className="field">Descrição <b aria-hidden="true">*</b>
          <input required maxLength={200} value={rascunho.descricao} onChange={(evento) => setRascunho({ ...rascunho, descricao: evento.target.value })} />
        </label>
        <label className="field">Unidade de medida <b aria-hidden="true">*</b>
          <select required value={rascunho.unidade_medida} onChange={(evento) => setRascunho({ ...rascunho, unidade_medida: evento.target.value as Draft['unidade_medida'] })}>
            {unidades.map((unidade) => <option key={unidade} value={unidade}>{unidade}</option>)}
          </select>
        </label>
        <div className="field catalog-ncm-field">
          <label htmlFor="ncm-search">NCM <b aria-hidden="true">*</b></label>
          <input id="ncm-search" type="search" aria-describedby="ncm-instructions" aria-controls="ncm-options" autoComplete="off" required value={ncmBusca} placeholder="Busque por código ou descrição" onChange={(evento) => { setNcmBusca(evento.target.value); setNcmCodigo(''); setOpcoesNcm([]); setBuscandoNcm(false) }} />
          <small id="ncm-instructions">Digite ao menos dois caracteres e escolha um resultado para vincular o NCM.</small>
          {buscandoNcm && <small role="status">Buscando NCM…</small>}
          {ncmBusca.trim().length >= 2 && opcoesNcm.length > 0 && <div id="ncm-options" className="ncm-options" role="group" aria-label="Resultados de NCM">
            {opcoesNcm.map((ncm) => <button key={ncm.codigo} type="button" aria-pressed={ncmCodigo === ncm.codigo} onClick={() => { setNcmCodigo(ncm.codigo); setNcmBusca(ncm.codigo); setOpcoesNcm([]) }}><strong>{ncm.codigo}</strong><span>{ncm.descricao}</span></button>)}
          </div>}
          {ncmCodigo && <small>NCM selecionado: {ncmCodigo}</small>}
        </div>
        <div className="catalog-form-actions">
          <button className="button secondary" type="button" disabled={salvando} onClick={() => setFormularioAberto(false)}>Cancelar</button>
          <button className="button primary" type="submit" disabled={salvando}>{salvando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Criar cadastro'}</button>
        </div>
      </form>
    </section>}

    {registroDetalhe && <section className="form-card catalog-detail" aria-labelledby="catalog-detail-title">
      <div className="list-card-heading"><h3 id="catalog-detail-title">Detalhes do cadastro</h3><button className="button secondary" type="button" onClick={() => setRegistroDetalhe(null)}>Fechar</button></div>
      <dl><div><dt>Tipo</dt><dd>{rotulos[tipo]}</dd></div><div><dt>Código</dt><dd>{registroDetalhe.codigo}</dd></div><div><dt>Descrição</dt><dd>{registroDetalhe.descricao}</dd></div><div><dt>Unidade de medida</dt><dd>{registroDetalhe.unidade_medida}</dd></div><div><dt>NCM</dt><dd>{registroDetalhe.ncm_codigo}</dd></div><div><dt>Situação</dt><dd>{registroDetalhe.ativo ? 'Ativo' : 'Inativo'}</dd></div><div><dt>Criado em</dt><dd>{new Date(registroDetalhe.created_at).toLocaleString('pt-BR')}</dd></div><div><dt>Atualizado em</dt><dd>{new Date(registroDetalhe.updated_at).toLocaleString('pt-BR')}</dd></div></dl>
    </section>}

    <section className="form-card catalog-table-card" aria-labelledby="catalog-table-title">
      <div className="list-card-heading"><div><span className="heading-icon" aria-hidden="true">▤</span><h3 id="catalog-table-title">{rotulos[tipo]}</h3></div><span className="list-scope">{itens.length} {itens.length === 1 ? 'registro' : 'registros'}</span></div>
      {carregando ? <div className="empty-list" role="status">Carregando cadastros…</div>
        : itens.length === 0 ? <div className="empty-list" role="status"><span className="empty-icon" aria-hidden="true">⌕</span><h3>Nenhum cadastro encontrado</h3><p>Esta lista ainda não possui registros.</p>{canEdit && <button className="button primary" type="button" onClick={abrirNovo}>Criar primeiro cadastro</button>}</div>
          : <div className="table-scroll" role="region" aria-label={`Lista de ${rotulos[tipo].toLocaleLowerCase('pt-BR')}`} tabIndex={0}>
            <table className="pricing-table catalog-table"><caption className="sr-only">{rotulos[tipo]} cadastradas, incluindo código, descrição, unidade, NCM, situação e ações</caption>
              <thead><tr><th scope="col">Código</th><th scope="col">Descrição</th><th scope="col">Unidade</th><th scope="col">NCM</th><th scope="col">Situação</th><th scope="col">Ações</th></tr></thead>
              <tbody>{itens.map((item) => <tr key={item.id}>
                <th scope="row" className="code-cell">{item.codigo}</th><td>{item.descricao}</td><td>{item.unidade_medida}</td><td className="mono-cell">{item.ncm_codigo}</td><td><span className={`status-pill ${item.ativo ? 'status-approved' : 'status-neutral'}`}><i />{item.ativo ? 'Ativo' : 'Inativo'}</span></td>
                <td className="catalog-actions"><button className="button secondary" type="button" disabled={carregandoDetalhe === item.id} onClick={() => { void mostrarDetalhes(item.id) }}>{carregandoDetalhe === item.id ? 'Abrindo…' : 'Visualizar'}</button>{canEdit && <><button className="button secondary" type="button" onClick={() => abrirEdicao(item)}>Editar</button><button className="button secondary" type="button" disabled={operandoId === item.id} onClick={() => { void alternarAtivo(item) }}>{operandoId === item.id ? 'Aguarde…' : item.ativo ? 'Inativar' : 'Reativar'}</button></>}</td>
              </tr>)}</tbody>
            </table>
          </div>}
    </section>
  </section>
}
