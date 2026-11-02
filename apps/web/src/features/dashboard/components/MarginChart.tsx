import { useState } from 'react'
import { Sigla } from '../../../components/Sigla'
import { MARGEM_POR_MES, POLITICA_MACO, percentual } from '../dashboard.data'

const ALTURA = 190
const TETO = 30
const PISO = 18

/**
 * MaCo média por mês com a linha da política mínima: o que está abaixo dela
 * salta à vista. Passar o mouse (ou o foco) num mês mostra os números dele.
 */
export function MarginChart() {
  const [mesAtivo, setMesAtivo] = useState<number | null>(null)
  const y = (valor: number) => ALTURA - ((valor - PISO) / (TETO - PISO)) * ALTURA
  const largura = 100 / MARGEM_POR_MES.length
  const ativo = mesAtivo === null ? null : MARGEM_POR_MES[mesAtivo]

  return <section className="dash-card dash-grafico" aria-labelledby="grafico-maco">
    <header className="dash-card-cabecalho">
      <div>
        <h3 id="grafico-maco"><Sigla termo="MaCo" /> média por mês</h3>
        <p>Comparada com a <Sigla termo="Política">política mínima</Sigla>. Passe o mouse num mês para ver os detalhes.</p>
      </div>
      <ul className="legenda" aria-label="Legenda">
        <li><i className="legenda-barra" />Acima</li>
        <li><i className="legenda-barra abaixo" />Abaixo</li>
        <li><i className="legenda-linha" />Política {POLITICA_MACO}%</li>
      </ul>
    </header>

    <div className="grafico" onMouseLeave={() => setMesAtivo(null)}>
      <div className="grafico-eixo" aria-hidden="true">
        {[30, 26, 22, 18].map((v) => <span key={v} style={{ top: y(v) }}>{v}%</span>)}
      </div>
      <div className="grafico-plano">
        <svg className="grafico-area" viewBox={`0 0 100 ${ALTURA}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
          {[30, 26, 22].map((v) => <line key={v} className="grafico-grade" x1="0" x2="100" y1={y(v)} y2={y(v)} />)}
          {MARGEM_POR_MES.map((m, i) => {
            const topo = y(m.maco)
            const classes = ['grafico-barra', m.maco < POLITICA_MACO && 'abaixo', mesAtivo !== null && mesAtivo !== i && 'apagada'].filter(Boolean).join(' ')
            return <rect key={m.mes} className={classes} x={i * largura + largura * 0.24} width={largura * 0.52}
              y={topo} height={ALTURA - topo} rx="1.4" style={{ animationDelay: `${.1 + i * .06}s` }} />
          })}
          <line className="grafico-politica" x1="0" x2="100" y1={y(POLITICA_MACO)} y2={y(POLITICA_MACO)} />
        </svg>
        <div className="grafico-alvos">
          {MARGEM_POR_MES.map((m, i) => <button key={m.mes} type="button" className="grafico-alvo"
            aria-label={`${m.mes}: MaCo média de ${percentual(m.maco)} em ${m.cenarios} cenários${m.maco < POLITICA_MACO ? ', abaixo da política' : ''}`}
            onMouseEnter={() => setMesAtivo(i)} onFocus={() => setMesAtivo(i)} onBlur={() => setMesAtivo(null)} />)}
        </div>
        {ativo && <div className="grafico-dica" style={{ left: `${(mesAtivo! + 0.5) * largura}%`, top: y(ativo.maco) }} aria-hidden="true">
          <strong>{percentual(ativo.maco)}</strong>
          <span>{ativo.cenarios} cenários em {ativo.mes}</span>
          <span className={ativo.maco < POLITICA_MACO ? 'ruim' : 'boa'}>
            {ativo.maco < POLITICA_MACO ? 'Abaixo' : 'Acima'} da política em {Math.abs(ativo.maco - POLITICA_MACO).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} p.p.
          </span>
        </div>}
      </div>
      <ol className="grafico-rotulos" aria-hidden="true">
        {MARGEM_POR_MES.map((m, i) => <li key={m.mes} className={mesAtivo === i ? 'ativo' : ''}><strong>{percentual(m.maco)}</strong><span>{m.mes}</span></li>)}
      </ol>
    </div>
  </section>
}
