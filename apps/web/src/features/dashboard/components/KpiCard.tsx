import type { ReactNode } from 'react'
import { Icon } from '../../../components/icons/Icon'
import type { ListPreset } from '../../pricing/listPreset'
import { formatar, type Indicador } from '../dashboard.data'
import { useContagem } from '../useContagem'
import { Sparkline } from './Sparkline'

const seta = { alta: '↑', baixa: '↓', neutra: '' }

type Props = {
  titulo: ReactNode
  indicador: Indicador
  destaque?: ReactNode
  onAbrir: (preset: ListPreset) => void
}

/** Indicador clicável: número que conta até o valor, tendência e atalho para a lista já filtrada. */
export function KpiCard({ titulo, indicador, destaque, onAbrir }: Props) {
  const { variacao } = indicador
  const animado = useContagem(indicador.numero)

  return <article className={`kpi${destaque ? ' kpi-destaque' : ''}`}>
    <header className="kpi-titulo">{titulo}</header>
    <div className="kpi-corpo">
      <strong className="kpi-valor" aria-label={formatar(indicador.numero, indicador.formato)}>{formatar(animado, indicador.formato)}</strong>
      <Sparkline valores={indicador.serie} />
    </div>
    {destaque}
    <footer className="kpi-rodape">
      <span className={`kpi-variacao ${variacao.tendencia === 'neutra' ? 'neutra' : variacao.boa ? 'boa' : 'ruim'}`}>
        {seta[variacao.tendencia] && <span aria-hidden="true">{seta[variacao.tendencia]} </span>}{variacao.texto}
      </span>
      <span className="kpi-ajuda">{indicador.ajuda}</span>
    </footer>
    {/* O botão cobre o cartão todo; o texto dele é o que aparece no hover */}
    <button className="kpi-acao" type="button" onClick={() => onAbrir(indicador.destino)}>
      <span>{indicador.acao}</span><Icon name="seta" size={14} />
    </button>
  </article>
}
