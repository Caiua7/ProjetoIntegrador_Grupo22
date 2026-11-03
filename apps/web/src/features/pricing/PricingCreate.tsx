import { useEffect, useState, type FormEvent } from 'react'
import { Select, type Opcao } from '../../components/form/Select'
import { Sigla } from '../../components/Sigla'
import { ApiError } from '../../services/apiClient'
import { criarPrecificacao, obterOpcoesPrecificacao, type OpcoesPrecificacao } from './precificacoesService'

type Props = { onCancel: () => void, onCreated?: () => void }
const MODALIDADES: Opcao[] = [
  { value: 'full_service_nacional', label: 'Full Service Nacional' },
  { value: 'full_service_exportacao', label: 'Full Service Exportação' },
  { value: 'industrializacao_por_encomenda', label: 'Industrialização por Encomenda' },
]
const UFS: Opcao[] = [...'AC AL AM BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split(' ').map((uf) => ({ value: uf, label: uf })), { value: 'EX', label: 'Exterior' }]
const REGIMES: Opcao[] = [
  { value: 'lucro_real', label: 'Lucro Real' }, { value: 'lucro_presumido', label: 'Lucro Presumido' }, { value: 'simples_nacional', label: 'Simples Nacional' },
]
const FRETES: Opcao[] = [{ value: 'cif', label: 'CIF' }, { value: 'fob', label: 'FOB' }]

function PricingCreate({ onCancel, onCreated }: Props) {
  const [opcoes, setOpcoes] = useState<OpcoesPrecificacao | null>(null)
  const [campos, setCampos] = useState({ cliente_id: '', produto_id: '', modalidade_comercial: '', uf_destino: '', regime_tributario: '', frete: '' })
  const [carregando, setCarregando] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [codigo, setCodigo] = useState<string | null>(null)

  useEffect(() => {
    let ativo = true
    obterOpcoesPrecificacao().then((resultado) => { if (ativo) setOpcoes(resultado) })
      .catch((falha: unknown) => { if (ativo) setErro(falha instanceof Error ? falha.message : 'Não foi possível carregar clientes e produtos.') })
      .finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setErro(null); setSalvando(true)
    try {
      const criada = await criarPrecificacao(campos)
      setCodigo(criada.codigo)
      onCreated?.()
    } catch (falha) {
      setErro(falha instanceof ApiError ? falha.message : 'Não foi possível salvar a precificação.')
    } finally { setSalvando(false) }
  }

  const clientes = (opcoes?.clientes ?? []).map((item) => ({ value: item.id, label: item.descricao, detalhe: item.codigo }))
  const produtos = (opcoes?.produtos ?? []).map((item) => ({ value: item.id, label: item.descricao, detalhe: item.codigo }))
  const select = (campo: keyof typeof campos, options: Opcao[], placeholder: string) => <Select value={campos[campo]} onChange={(value) => setCampos((atual) => ({ ...atual, [campo]: value }))} required disabled={carregando || salvando} options={options} placeholder={placeholder} />

  return <section className="content pricing-content">
    <div className="page-intro"><div><span className="eyebrow">NOVO ESTUDO</span><h2>Dados da precificação</h2><p>Preencha o cabeçalho comercial e fiscal para iniciar o cenário.</p></div><span className="step-badge"><span>1</span> Cabeçalho <i /> Composição</span></div>
    {erro && <p className="catalog-error" role="alert">{erro}</p>}
    {codigo && <div className="success-notice" role="status"><span aria-hidden="true">✓</span><div><strong>Precificação {codigo} criada</strong><p>Status: Em Preenchimento.</p></div></div>}
    {carregando && <p role="status">Carregando clientes e produtos…</p>}
    <form className="pricing-form" onSubmit={handleSubmit}>
      <section className="form-card">
        <div className="card-heading"><span className="heading-icon" aria-hidden="true">◧</span><div><h3>Informações comerciais e fiscais</h3><p>Dados persistidos no cabeçalho da precificação</p></div></div>
        <div className="form-grid">
          <label className="field"><span>Cliente <b>*</b></span>{select('cliente_id', clientes, 'Selecione um cliente')}</label>
          <label className="field"><span>Produto <b>*</b></span>{select('produto_id', produtos, 'Selecione um produto')}</label>
          <label className="field"><span>Modalidade comercial <b>*</b></span>{select('modalidade_comercial', MODALIDADES, 'Selecione a modalidade')}</label>
          <label className="field"><span><Sigla termo="UF" /> de destino <b>*</b></span>{select('uf_destino', UFS, 'Selecione a UF')}</label>
          <label className="field"><span>Regime tributário do cliente <b>*</b></span>{select('regime_tributario', REGIMES, 'Selecione o regime')}</label>
          <label className="field"><span>Frete <b>*</b></span>{select('frete', FRETES, 'Selecione a modalidade de frete')}</label>
        </div>
        <div className="form-footer"><p><b>*</b> Campos obrigatórios</p><div><button className="button secondary" type="button" onClick={onCancel} disabled={salvando}>Cancelar</button><button className="button primary" type="submit" disabled={salvando || carregando || !opcoes}>{salvando ? 'Salvando…' : 'Criar precificação →'}</button></div></div>
      </section>
      <aside className="side-info"><section className="form-card info-card"><div className="card-heading"><span className="heading-icon tax-icon" aria-hidden="true">%</span><div><h3>Tributação</h3><p>Resultado ainda não calculado</p></div></div><p>As alíquotas e o resultado dependem da composição e da integração com o motor homologado.</p><div className="pending-state"><span aria-hidden="true">◷</span><div><strong>Não consultada</strong><small>Nenhum cálculo foi executado nesta etapa</small></div></div></section></aside>
    </form>
  </section>
}

export default PricingCreate
