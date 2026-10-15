import { useEffect, useState, type FormEvent } from 'react'
import {
  atualizarAliquota,
  criarAliquota,
  listarAliquotas,
  resolverAliquota,
  type AliquotaEntrada,
  type AliquotaFiscal,
  type FiltroAliquota,
  type RegimeTributario,
} from './taxRatesService'

const ufs = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
const regimes: { value: RegimeTributario, label: string }[] = [
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'simples_nacional', label: 'Simples Nacional' },
]
const taxas: { key: keyof Omit<AliquotaEntrada, 'uf_destino' | 'ncm_codigo' | 'regime_tributario' | 'vigencia_inicio'>, label: string, max?: number }[] = [
  { key: 'pis_percentual', label: 'PIS (%)', max: 100 },
  { key: 'cofins_percentual', label: 'COFINS (%)', max: 100 },
  { key: 'icms_percentual', label: 'ICMS (%)', max: 100 },
  { key: 'ipi_percentual', label: 'IPI (%)', max: 100 },
  { key: 'icms_interno_percentual', label: 'ICMS interno (%)', max: 100 },
  { key: 'fcp_percentual', label: 'FCP (%)', max: 100 },
  { key: 'mva_percentual', label: 'MVA (%)' },
]

type Rascunho = Omit<AliquotaEntrada, 'pis_percentual' | 'cofins_percentual' | 'icms_percentual' | 'ipi_percentual' | 'icms_interno_percentual' | 'fcp_percentual' | 'mva_percentual'> & Record<(typeof taxas)[number]['key'], string>

const vazio: Rascunho = {
  uf_destino: '', ncm_codigo: '', regime_tributario: 'lucro_real', vigencia_inicio: '',
  pis_percentual: '', cofins_percentual: '', icms_percentual: '', ipi_percentual: '',
  icms_interno_percentual: '', fcp_percentual: '', mva_percentual: '',
}

function deslocarDecimal(valor: string, casas: number): string {
  const limpo = valor.trim().replace(',', '.')
  if (!/^\d+(?:\.\d+)?$/.test(limpo)) return ''
  const [inteiro, fracao = ''] = limpo.split('.')
  const digitos = `${inteiro}${fracao}`.replace(/^0+(?=\d)/, '')
  const escala = fracao.length - casas
  if (escala <= 0) return `${digitos}${'0'.repeat(-escala)}`
  const preenchido = digitos.padStart(escala + 1, '0')
  const divisor = preenchido.length - escala
  const parteInteira = preenchido.slice(0, divisor).replace(/^0+(?=\d)/, '') || '0'
  return `${parteInteira}.${preenchido.slice(divisor)}`.replace(/\.?0+$/, (sufixo) => sufixo.startsWith('.') ? '' : sufixo)
}

function paraPercentual(valor: string): string {
  const convertido = deslocarDecimal(valor, 2)
  return convertido || '0'
}

function doBanco(r: AliquotaFiscal): Rascunho {
  return {
    uf_destino: r.uf_destino,
    ncm_codigo: r.ncm_codigo ?? '',
    regime_tributario: r.regime_tributario,
    vigencia_inicio: r.vigencia_inicio,
    pis_percentual: paraPercentual(r.pis_percentual),
    cofins_percentual: paraPercentual(r.cofins_percentual),
    icms_percentual: paraPercentual(r.icms_percentual),
    ipi_percentual: paraPercentual(r.ipi_percentual),
    icms_interno_percentual: paraPercentual(r.icms_interno_percentual),
    fcp_percentual: paraPercentual(r.fcp_percentual),
    mva_percentual: paraPercentual(r.mva_percentual),
  }
}

function paraEntrada(r: Rascunho): AliquotaEntrada {
  const entrada = {
    uf_destino: r.uf_destino,
    ncm_codigo: r.ncm_codigo || null,
    regime_tributario: r.regime_tributario,
    vigencia_inicio: r.vigencia_inicio,
  } as AliquotaEntrada
  for (const taxa of taxas) entrada[taxa.key] = deslocarDecimal(r[taxa.key], -2)
  return entrada
}

function nomeRegime(regime: RegimeTributario): string {
  return regimes.find((item) => item.value === regime)?.label ?? regime
}

function dataHoje(): string {
  const agora = new Date()
  return `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, '0')}-${String(agora.getDate()).padStart(2, '0')}`
}

export function TaxRatesPage({ canEdit }: { canEdit: boolean }) {
  const [filtro, setFiltro] = useState<FiltroAliquota>({})
  const [linhas, setLinhas] = useState<AliquotaFiscal[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [mensagem, setMensagem] = useState<string | null>(null)
  const [resolverData, setResolverData] = useState(dataHoje)
  const [resolvida, setResolvida] = useState<AliquotaFiscal | null>(null)
  const [formAberto, setFormAberto] = useState(false)
  const [editando, setEditando] = useState<AliquotaFiscal | null>(null)
  const [rascunho, setRascunho] = useState<Rascunho>(vazio)
  const [salvando, setSalvando] = useState(false)
  const [resolvendo, setResolvendo] = useState(false)
  const [versao, setVersao] = useState(0)

  useEffect(() => {
    let vigente = true
    void listarAliquotas(filtro).then((resultado) => {
      if (vigente) setLinhas(resultado)
    }).catch((falha: unknown) => {
      if (vigente) setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar as alíquotas.')
    }).finally(() => {
      if (vigente) setCarregando(false)
    })
    return () => { vigente = false }
  }, [filtro, versao])

  function abrirNovo() {
    setEditando(null)
    setRascunho({ ...vazio, vigencia_inicio: dataHoje() })
    setErro(null)
    setFormAberto(true)
  }

  function abrirEdicao(item: AliquotaFiscal) {
    setEditando(item)
    setRascunho(doBanco(item))
    setErro(null)
    setFormAberto(true)
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setErro(null)
    setSalvando(true)
    try {
      const entrada = paraEntrada(rascunho)
      if (editando) await atualizarAliquota(editando.id, entrada)
      else await criarAliquota(entrada)
      setMensagem(editando ? 'Alíquota atualizada.' : 'Alíquota criada para a vigência informada.')
      setFormAberto(false)
      setEditando(null)
      setCarregando(true)
      setVersao((atual) => atual + 1)
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível salvar a alíquota.')
    } finally {
      setSalvando(false)
    }
  }

  async function consultarAplicavel() {
    if (!filtro.uf_destino || !filtro.ncm_codigo || filtro.ncm_codigo.length !== 8 || !filtro.regime_tributario) {
      setErro('Informe UF, NCM e regime tributário para consultar a alíquota aplicável.')
      return
    }
    setErro(null)
    setResolvida(null)
    setResolvendo(true)
    try {
      setResolvida(await resolverAliquota({ ...filtro, ncm_codigo: filtro.ncm_codigo, regime_tributario: filtro.regime_tributario, uf_destino: filtro.uf_destino, data_referencia: resolverData }))
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : 'Não foi possível resolver a alíquota.')
    } finally {
      setResolvendo(false)
    }
  }

  function mudarFiltro(chave: keyof FiltroAliquota, valor: string) {
    setFiltro((atual) => ({ ...atual, [chave]: valor || undefined }))
    setCarregando(true)
    setErro(null)
    setResolvida(null)
    setMensagem(null)
  }

  return <section className="content catalog-content tax-content">
    <div className="list-intro">
      <div><span className="eyebrow">PARÂMETROS FISCAIS</span><h2>Alíquotas</h2><p>Consulte e mantenha percentuais por UF, NCM, regime e vigência.</p></div>
      {canEdit && <button className="button primary" type="button" onClick={abrirNovo}>+ Nova alíquota</button>}
    </div>
    <div className="demo-notice"><span className="notice-dot" />A área fiscal deve confirmar valores e vigências antes de usá-los em uma precificação.</div>
    {mensagem && <p className="catalog-success" role="status">{mensagem}</p>}
    {erro && <p className="catalog-error" role="alert">{erro}</p>}

    <section className="form-card tax-filter-card" aria-label="Filtros das alíquotas">
      <div className="catalog-form tax-filters">
        <label className="field">UF de destino
          <select value={filtro.uf_destino ?? ''} onChange={(e) => mudarFiltro('uf_destino', e.target.value)}><option value="">Todas as UFs</option>{ufs.map((uf) => <option key={uf}>{uf}</option>)}</select>
        </label>
        <label className="field">NCM específico
          <input inputMode="numeric" maxLength={8} placeholder="Omitir para todas" value={filtro.ncm_codigo ?? ''} onChange={(e) => mudarFiltro('ncm_codigo', e.target.value.replace(/\D/g, '').slice(0, 8))} />
        </label>
        <label className="field">Regime tributário
          <select value={filtro.regime_tributario ?? ''} onChange={(e) => mudarFiltro('regime_tributario', e.target.value)}><option value="">Todos</option>{regimes.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select>
        </label>
        <label className="field">Vigência até
          <input type="date" value={filtro.vigencia_ate ?? ''} onChange={(e) => mudarFiltro('vigencia_ate', e.target.value)} />
        </label>
      </div>
      <div className="tax-resolver"><label className="field">Data para consulta de vigência<input type="date" value={resolverData} onChange={(e) => setResolverData(e.target.value)} /></label><button className="button secondary" type="button" disabled={resolvendo} onClick={() => { void consultarAplicavel() }}>{resolvendo ? 'Consultando…' : 'Consultar aplicável'}</button></div>
      {resolvida && <div className="pending-state tax-resolved" role="status"><span aria-hidden="true">✓</span><div><strong>Regra encontrada: {resolvida.ncm_codigo ? `NCM ${resolvida.ncm_codigo}` : 'regra geral da UF'}</strong><small>{resolvida.uf_destino} · {nomeRegime(resolvida.regime_tributario)} · vigente desde {new Date(`${resolvida.vigencia_inicio}T00:00:00`).toLocaleDateString('pt-BR')}</small></div></div>}
    </section>

    {formAberto && <section className="form-card catalog-form-card" aria-labelledby="tax-form-title">
      <div className="list-card-heading"><h3 id="tax-form-title">{editando ? 'Editar alíquota' : 'Nova alíquota e vigência'}</h3></div>
      <form className="catalog-form" onSubmit={(e) => { void salvar(e) }}>
        <label className="field">UF de destino <b aria-hidden="true">*</b><select required value={rascunho.uf_destino} onChange={(e) => setRascunho({ ...rascunho, uf_destino: e.target.value })}><option value="">Selecione</option>{ufs.map((uf) => <option key={uf}>{uf}</option>)}</select></label>
        <label className="field">NCM <small>(vazio = regra geral)</small><input inputMode="numeric" maxLength={8} value={rascunho.ncm_codigo ?? ''} onChange={(e) => setRascunho({ ...rascunho, ncm_codigo: e.target.value.replace(/\D/g, '').slice(0, 8) })} /></label>
        <label className="field">Regime tributário <b aria-hidden="true">*</b><select required value={rascunho.regime_tributario} onChange={(e) => setRascunho({ ...rascunho, regime_tributario: e.target.value as RegimeTributario })}>{regimes.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></label>
        <label className="field">Início da vigência <b aria-hidden="true">*</b><input required type="date" value={rascunho.vigencia_inicio} onChange={(e) => setRascunho({ ...rascunho, vigencia_inicio: e.target.value })} /></label>
        {taxas.map((taxa) => <label className="field" key={taxa.key}>{taxa.label} <b aria-hidden="true">*</b><input required type="number" min="0" max={taxa.max} step="0.0001" value={rascunho[taxa.key]} onChange={(e) => setRascunho({ ...rascunho, [taxa.key]: e.target.value })} /></label>)}
        <div className="catalog-form-actions"><button className="button secondary" type="button" disabled={salvando} onClick={() => setFormAberto(false)}>Cancelar</button><button className="button primary" type="submit" disabled={salvando}>{salvando ? 'Salvando…' : editando ? 'Salvar alterações' : 'Criar vigência'}</button></div>
      </form>
    </section>}

    <section className="form-card catalog-table-card" aria-labelledby="tax-table-title">
      <div className="list-card-heading"><div><span className="heading-icon tax-icon" aria-hidden="true">%</span><h3 id="tax-table-title">Regras cadastradas</h3></div><span className="list-scope">{linhas.length} {linhas.length === 1 ? 'regra' : 'regras'}</span></div>
      {carregando ? <div className="empty-list" role="status">Carregando alíquotas…</div>
        : linhas.length === 0 ? <div className="empty-list" role="status"><span className="empty-icon" aria-hidden="true">%</span><h3>Nenhuma alíquota encontrada</h3><p>Ajuste os filtros ou cadastre uma regra.</p>{canEdit && <button className="button primary" type="button" onClick={abrirNovo}>Criar alíquota</button>}</div>
          : <div className="table-scroll" role="region" aria-label="Lista de alíquotas fiscais" tabIndex={0}><table className="pricing-table tax-table"><caption className="sr-only">Alíquotas fiscais por UF, NCM, regime e vigência</caption>
            <thead><tr><th scope="col">UF</th><th scope="col">NCM</th><th scope="col">Regime</th><th scope="col">Vigência</th>{taxas.map((t) => <th className="numeric" scope="col" key={t.key}>{t.label}</th>)}{canEdit && <th scope="col">Ações</th>}</tr></thead>
            <tbody>{linhas.map((item) => <tr key={item.id}><th scope="row">{item.uf_destino}</th><td className="mono-cell">{item.ncm_codigo ?? 'Geral'}</td><td>{nomeRegime(item.regime_tributario)}</td><td className="mono-cell">{new Date(`${item.vigencia_inicio}T00:00:00`).toLocaleDateString('pt-BR')}</td>{taxas.map((t) => <td className="numeric mono-cell" key={t.key}>{paraPercentual(item[t.key])}%</td>)}{canEdit && <td><button className="button secondary" type="button" onClick={() => abrirEdicao(item)}>Editar</button></td>}</tr>)}</tbody>
          </table></div>}
    </section>
    <p className="list-footnote">A consulta aplicável prioriza a regra específica de NCM; sem ela, usa a regra geral da UF. A tela preserva as vigências cadastradas e não exclui o histórico.</p>
  </section>
}
