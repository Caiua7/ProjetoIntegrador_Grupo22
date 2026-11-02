import { Sigla } from '../../../components/Sigla'
import { POLITICA_MACO, percentual } from '../dashboard.data'

const TETO = 40

/** Régua da MaCo: onde a média está em relação à política mínima. */
export function PolicyMeter({ maco }: { maco: number }) {
  const posicao = (valor: number) => `${Math.min(valor / TETO, 1) * 100}%`
  const folga = maco - POLITICA_MACO

  return <div className="regua">
    <div className="regua-trilho" role="meter" aria-valuemin={0} aria-valuemax={TETO} aria-valuenow={Number(maco.toFixed(1))}
      aria-label={`MaCo média de ${percentual(maco)} contra política de ${POLITICA_MACO}%`}>
      <span className={`regua-preenchido${folga < 0 ? ' abaixo' : ''}`} style={{ width: posicao(maco) }} />
      <span className="regua-meta" style={{ left: posicao(POLITICA_MACO) }} />
    </div>
    <small>
      {folga >= 0
        ? <>{folga.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p. acima da <Sigla termo="Política">política de {POLITICA_MACO}%</Sigla></>
        : <>{Math.abs(folga).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p. abaixo da <Sigla termo="Política">política de {POLITICA_MACO}%</Sigla></>}
    </small>
  </div>
}
