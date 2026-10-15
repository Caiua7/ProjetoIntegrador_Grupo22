import { Icon } from '../../components/icons/Icon'

export function Dashboard({ canCreate, onNewPricing }: { canCreate: boolean, onNewPricing: () => void }) {
  return <section className="content">
    <div className="welcome">
      <div><span className="eyebrow">VISÃO GERAL</span><h2>Visão geral da precificação</h2>
        <p>Acompanhe os cenários, a rentabilidade e as aprovações da sua carteira.</p></div>
      {canCreate && <button className="button primary" onClick={onNewPricing}><Icon name="mais" size={16} /> Nova precificação</button>}
    </div>
    <div className="demo-notice"><span className="notice-dot" />Painel demonstrativo · os indicadores abaixo são dados ilustrativos do protótipo.</div>
    <div className="metrics">
      <article className="metric featured"><span>MaCo média — setembro</span><strong>26,8%</strong><small>Política mínima: 24% · 3 cenários abaixo</small></article>
      <article className="metric"><span>Cenários no mês</span><strong>34</strong><small>6 a mais que agosto</small></article>
      <article className="metric"><span>Aguardando aprovação</span><strong>7</strong><small>Mais antigo parado há 3 dias</small></article>
      <article className="metric"><span>ROB aprovada — trimestre</span><strong>R$ 2,43 mi</strong><small>MaCo absoluta de R$ 490 mil</small></article>
    </div>
    {canCreate && <article className="panel">
      <div><span className="eyebrow">PRÓXIMA ETAPA</span><h3>Comece um estudo de preço</h3><p>Informe os dados comerciais e fiscais para abrir uma nova precificação.</p></div>
      <button className="button secondary" onClick={onNewPricing}>Criar precificação <Icon name="seta" size={16} /></button>
    </article>}
  </section>
}
