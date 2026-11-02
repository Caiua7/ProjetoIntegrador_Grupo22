import type { ReactNode } from 'react'
import { Icon, type IconName } from '../../../components/icons/Icon'
import { Sigla } from '../../../components/Sigla'
import type { ListPreset } from '../../pricing/listPreset'
import { pricingListDemo } from '../../pricing/pricingList.mock'
import { POLITICA_MACO, abaixoDaPolitica, percentual } from '../dashboard.data'

type Pendencia = { chave: string, icone: IconName, tom: 'aviso' | 'revisao' | 'neutro', titulo: ReactNode, detalhe: string, destino: ListPreset }

/** O que pede ação agora, do mais urgente para o menos. Cada item abre a lista filtrada. */
export function AttentionPanel({ onAbrir }: { onAbrir: (preset: ListPreset) => void }) {
  const pendencias: Pendencia[] = [
    ...abaixoDaPolitica().map((item): Pendencia => ({
      chave: `abaixo-${item.code}`,
      icone: 'alerta',
      tom: 'aviso',
      titulo: <>{item.code} com <Sigla termo="MaCo" /> de {percentual(item.contributionMarginPercent)}</>,
      detalhe: `${item.customer} · ${(POLITICA_MACO - item.contributionMarginPercent).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p. abaixo da política`,
      destino: { abaixoDaPolitica: true },
    })),
    ...pricingListDemo.filter((item) => item.status === 'approval').map((item): Pendencia => ({
      chave: `aprovacao-${item.code}`,
      icone: 'aprovacoes',
      tom: 'revisao',
      titulo: <>{item.code} aguardando aprovação</>,
      detalhe: `${item.customer} · enviado ${item.updatedAt}`,
      destino: { status: 'approval' },
    })),
    ...pricingListDemo.filter((item) => item.status === 'draft').map((item): Pendencia => ({
      chave: `rascunho-${item.code}`,
      icone: 'precificacoes',
      tom: 'neutro',
      titulo: <>{item.code} em preenchimento</>,
      detalhe: `${item.customer} · parado ${item.updatedAt}`,
      destino: { status: 'draft' },
    })),
  ]

  return <section className="dash-card dash-atencao" aria-labelledby="atencao-titulo">
    <header className="dash-card-cabecalho">
      <div>
        <h3 id="atencao-titulo">Precisa da sua atenção</h3>
        <p>Do mais urgente para o menos. Clique para abrir.</p>
      </div>
      <span className="contador" aria-label={`${pendencias.length} pendências`}>{pendencias.length}</span>
    </header>
    <ul className="pendencias">
      {pendencias.slice(0, 5).map((p, i) => <li key={p.chave} style={{ animationDelay: `${.15 + i * .06}s` }}>
        <button type="button" className={`pendencia ${p.tom}`} onClick={() => onAbrir(p.destino)}>
          <span className="pendencia-icone"><Icon name={p.icone} size={16} /></span>
          <span className="pendencia-texto"><strong>{p.titulo}</strong><small>{p.detalhe}</small></span>
          <Icon name="seta" size={14} className="pendencia-seta" />
        </button>
      </li>)}
    </ul>
  </section>
}
