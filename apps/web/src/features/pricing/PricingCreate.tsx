import { useState, type FormEvent } from 'react'
import { Select, type Opcao } from '../../components/form/Select'
import { Sigla } from '../../components/Sigla'

type Props = { onCancel: () => void }

const CLIENTES: Opcao[] = [
  { value: 'nutrafit', label: 'Nutrafit Distribuidora', detalhe: 'SP · Full Service Nacional' },
  { value: 'corpore', label: 'Corpore Suplementos', detalhe: 'MG · Full Service Nacional' },
  { value: 'atlas', label: 'Atlas Nutrition LLC', detalhe: 'Exportação' },
  { value: 'vitaprime', label: 'Vita Prime Indústria', detalhe: 'PR · Industrialização por Encomenda' },
]
const PRODUTOS: Opcao[] = [
  { value: 'wpc80', label: 'WPC 80 — pote 600 g' },
  { value: 'creatina', label: 'Creatina mono 300 g' },
  { value: 'bcaa', label: 'BCAA 2:1:1 — 250 g' },
]
const MODALIDADES: Opcao[] = [
  { value: 'full_service_nacional', label: 'Full Service Nacional', detalhe: 'Fabricamos e vendemos no Brasil' },
  { value: 'full_service_exportacao', label: 'Full Service Exportação', detalhe: 'Fabricamos e vendemos para fora do país' },
  { value: 'industrializacao_por_encomenda', label: 'Industrialização por Encomenda', detalhe: 'O cliente envia parte do material' },
]
const UFS: Opcao[] = [
  ...['AC','AL','AM','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO'].map((uf) => ({ value: uf, label: uf })),
  { value: 'EX', label: 'Exterior', detalhe: 'Venda para fora do país' },
]
const REGIMES: Opcao[] = [
  { value: 'lucro_real', label: 'Lucro Real' },
  { value: 'lucro_presumido', label: 'Lucro Presumido' },
  { value: 'simples_nacional', label: 'Simples Nacional' },
]
const FRETES: Opcao[] = [
  { value: 'cif', label: 'CIF', detalhe: 'Frete por conta do fabricante' },
  { value: 'fob', label: 'FOB', detalhe: 'Frete por conta do cliente' },
]

/** Select de demonstração que guarda a própria escolha (o formulário ainda não envia nada). */
function CampoSelect(props: { options: Opcao[], placeholder: string, required?: boolean }) {
  const [valor, setValor] = useState('')
  return <Select value={valor} onChange={setValor} {...props} />
}

function PricingCreate({ onCancel }: Props) {
  const [submitted, setSubmitted] = useState(false)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
  }

  return <section className="content pricing-content">
    <div className="page-intro">
      <div><span className="eyebrow">NOVO ESTUDO</span><h2>Dados da precificação</h2>
        <p>Preencha o cabeçalho comercial e fiscal para iniciar o cenário.</p></div>
      <span className="step-badge"><span>1</span> Cabeçalho <i /> Composição</span>
    </div>

    <div className="demo-notice"><span className="notice-dot" />Demonstração: opções de clientes e produtos são ilustrativas. Nenhum dado será salvo.</div>
    {submitted && <div className="success-notice" role="status"><span aria-hidden="true">✓</span><div><strong>Campos obrigatórios preenchidos</strong><p>Validação feita no navegador. Nenhum cenário foi criado ou salvo.</p></div></div>}

    <form className="pricing-form" onSubmit={handleSubmit} onChange={() => setSubmitted(false)}>
      <section className="form-card">
        <div className="card-heading"><span className="heading-icon" aria-hidden="true">▤</span><div><h3>Informações comerciais e fiscais</h3><p>Campos do cabeçalho previstos na US29</p></div></div>
        <div className="form-grid">
          <label className="field"><span>Cliente <b>*</b></span><CampoSelect required placeholder="Selecione um cliente" options={CLIENTES} /></label>
          <label className="field"><span>Produto <b>*</b></span><CampoSelect required placeholder="Selecione um produto" options={PRODUTOS} /></label>
          <label className="field"><span>Modalidade comercial <b>*</b></span><CampoSelect required placeholder="Selecione a modalidade" options={MODALIDADES} /></label>
          <label className="field"><span><Sigla termo="UF" /> de destino <b>*</b></span><CampoSelect required placeholder="Selecione a UF" options={UFS} /></label>
          <label className="field"><span>Regime tributário do cliente <b>*</b></span><CampoSelect required placeholder="Selecione o regime" options={REGIMES} /></label>
          <label className="field"><span>Frete <b>*</b></span><CampoSelect required placeholder="Selecione a modalidade de frete" options={FRETES} /></label>
          <label className="field"><span>Prazo médio de pagamento <small>(dias)</small></span><div className="input-suffix"><input type="number" min="0" step="1" placeholder="Ex.: 45" /><span>dias</span></div></label>
          <label className="field"><span>Volume negociado <small>(opcional)</small></span><input type="number" min="0" step="1" placeholder="Quantidade de unidades" /></label>
        </div>
        <div className="form-footer"><p><b>*</b> Campos obrigatórios</p><div><button className="button secondary" type="button" onClick={onCancel}>Cancelar</button><button className="button primary" type="submit">Validar cabeçalho <span aria-hidden="true">→</span></button></div></div>
      </section>

      <aside className="side-info">
        <section className="form-card info-card">
          <div className="card-heading"><span className="heading-icon tax-icon" aria-hidden="true">%</span><div><h3>Tributação</h3><p>Resolução após integração</p></div></div>
          <p>As alíquotas serão resolvidas pelo cadastro fiscal conforme UF de destino, NCM do produto e regime tributário do cliente.</p>
          <div className="pending-state"><span aria-hidden="true">◷</span><div><strong>Não consultada</strong><small>Cadastro fiscal e API ainda não integrados</small></div></div>
          <p className="field-hint">Nenhuma alíquota ou resultado fiscal fictício é exibido nesta etapa.</p>
        </section>
        <section className="form-card help-card"><span className="eyebrow">PRÓXIMA ETAPA</span><h3>Composição do produto</h3><p>A seleção de matérias-primas, embalagens e quantidades entra na etapa de composição do cenário.</p><span className="coming-soon">Em desenvolvimento</span></section>
      </aside>
    </form>
  </section>
}

export default PricingCreate
