import { useState, type FormEvent } from 'react'

type Props = { onCancel: () => void }

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
    {submitted && <div className="success-notice" role="status"><span aria-hidden="true">✓</span><div><strong>Validação concluída</strong><p>O cabeçalho está válido. O rascunho não foi persistido; a criação será conectada à API quando disponível.</p></div></div>}

    <form className="pricing-form" onSubmit={handleSubmit}>
      <section className="form-card">
        <div className="card-heading"><span className="heading-icon" aria-hidden="true">▤</span><div><h3>Informações comerciais e fiscais</h3><p>Campos do cabeçalho previstos na US29</p></div></div>
        <div className="form-grid">
          <label className="field"><span>Cliente <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione um cliente</option><option>Nutrafit Distribuidora — SP</option><option>Corpore Suplementos — MG</option><option>Atlas Nutrition LLC — Exportação</option><option>Vita Prime Indústria — PR</option></select></label>
          <label className="field"><span>Produto <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione um produto</option><option>WPC 80 — pote 600 g</option><option>Creatina mono 300 g</option><option>BCAA 2:1:1 — 250 g</option></select></label>
          <label className="field"><span>Modalidade comercial <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione a modalidade</option><option value="full_service_nacional">Full Service Nacional</option><option value="full_service_exportacao">Full Service Exportação</option><option value="industrializacao_por_encomenda">Industrialização por Encomenda</option></select></label>
          <label className="field"><span>UF de destino <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione a UF</option>{['AC','AL','AM','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO'].map((uf) => <option key={uf}>{uf}</option>)}<option value="EX">Exterior</option></select></label>
          <label className="field"><span>Regime tributário do cliente <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione o regime</option><option>Lucro Real</option><option>Lucro Presumido</option><option>Simples Nacional</option></select></label>
          <label className="field"><span>Frete <b>*</b></span><select defaultValue="" required><option value="" disabled>Selecione a modalidade de frete</option><option value="cif">CIF — por conta do fabricante</option><option value="fob">FOB — por conta do cliente</option></select></label>
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
