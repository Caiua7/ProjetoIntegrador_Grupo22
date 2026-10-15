/** Ícones dos itens de menu. Partes `a-*` animadas em icons.css. */
import { PL } from './pathLength'

export const navegacao = {
  painel: <>
    <rect className="a-b1" x="4" y="4" width="7" height="9" rx="1.5" />
    <rect className="a-b2" x="13" y="4" width="7" height="5" rx="1.5" />
    <rect className="a-b3" x="13" y="11" width="7" height="9" rx="1.5" />
    <rect className="a-b4" x="4" y="15" width="7" height="5" rx="1.5" />
  </>,
  precificacoes: <>
    <path d="M7 3.5h7l4.5 4.5v12.5h-11.5z" />
    <path d="M14 3.5V8h4.5" />
    <path className="a-escreve a-l1" {...PL} d="M9.5 12h5" />
    <path className="a-escreve a-l2" {...PL} d="M9.5 15.5h3" />
  </>,
  nova: <>
    <g className="a-folha"><path d="M7 3.5h7l4.5 4.5v12.5h-11.5z" /><path className="a-orelha" d="M14 3.5V8h4.5" /></g>
    <path className="a-mais" d="M12 11v6M9 14h6" />
  </>,
  cenario: <>
    <circle className="a-alvo" cx="12" cy="12" r="8.5" />
    <circle className="a-meio" cx="12" cy="12" r="4.5" />
    <circle className="a-ponto" cx="12" cy="12" r=".6" fill="currentColor" />
  </>,
  inverso: <>
    <path className="a-ida" d="M4 8.5h14M14.5 5 18 8.5 14.5 12" />
    <path className="a-volta" d="M20 15.5H6M9.5 12 6 15.5 9.5 19" />
  </>,
  comparar: <>
    <path d="M4 20.5h16" />
    <path className="a-barra a-c1" d="M7 20.5v-8" />
    <path className="a-barra a-c2" d="M12 20.5V6" />
    <path className="a-barra a-c3" d="M17 20.5v-11" />
  </>,
  aprovacoes: <>
    <rect x="4" y="4" width="16" height="16" rx="3" />
    <path className="a-check" {...PL} d="m8.5 12.2 2.4 2.4 4.8-5" />
  </>,
  proposta: <g className="a-envelope">
    <rect x="3.5" y="5.5" width="17" height="13" rx="2" />
    <path className="a-aba" d="m4 7 8 6 8-6" />
  </g>,
  equilibrio: <>
    <path d="M4 20.5h16M4 20.5V4" />
    <path className="a-escreve" {...PL} d="M6.5 17.5 18.5 6.5" />
    <path className="a-escreve a-l2" {...PL} d="M6.5 11h13" />
    <circle className="a-ponto" cx="11.5" cy="12.9" r="1.2" fill="currentColor" stroke="none" />
  </>,
  sensibilidade: <path className="a-onda" {...PL} d="M3.5 12c2.2 0 2.2-6 4.3-6s2.1 12 4.2 12 2.1-12 4.2-12 2.1 6 4.3 6" />,
  exportar: <>
    <path d="M10 4.5H6a1.5 1.5 0 0 0-1.5 1.5v12A1.5 1.5 0 0 0 6 19.5h12a1.5 1.5 0 0 0 1.5-1.5v-4" />
    <path className="a-seta" d="M13.5 4.5h6v6M19.5 4.5l-8 8" />
  </>,
  cadastros: <>
    <ellipse className="a-d1" cx="12" cy="6" rx="7.5" ry="2.5" />
    <path className="a-d2" d="M4.5 6v6c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5V6" />
    <path className="a-d3" d="M4.5 12v6c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-6" />
  </>,
  cotacoes: <path className="a-giro" d="M19.5 11a7.5 7.5 0 0 0-13.4-4.2L4.5 8.5M4.5 4v4.5H9M4.5 13a7.5 7.5 0 0 0 13.4 4.2l1.6-1.7M19.5 20v-4.5H15" />,
  importar: <>
    <path className="a-seta" d="M12 15V4M7.5 8.5 12 4l4.5 4.5" />
    <path d="M4.5 14v4.5A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5V14" />
  </>,
  tributos: <>
    <path className="a-risco" {...PL} d="M18 6 6 18" />
    <circle className="a-p1" cx="7.5" cy="7.5" r="2.5" />
    <circle className="a-p2" cx="16.5" cy="16.5" r="2.5" />
  </>,
  usuarios: <>
    <g className="a-p1"><circle className="a-cabeca" cx="9" cy="8.5" r="3.5" /><path d="M3 20c.6-3.4 3.1-5.5 6-5.5s5.4 2.1 6 5.5" /></g>
    <path className="a-p2" d="M15.5 5.2a3.5 3.5 0 0 1 0 6.6M18 14.8c1.6.8 2.7 2.6 3 5.2" />
  </>,
  metadados: <>
    <path className="a-escreve" {...PL} d="M4 7h9M4 12h5M4 17h9" />
    <g className="a-engrenagem">
      <circle cx="17" cy="12" r="2.2" />
      <path d="M17 7.5v1.6M17 14.9v1.6M21.5 12h-1.6M14.1 12h-1.6M20.2 8.8l-1.1 1.1M14.9 14.1l-1.1 1.1M20.2 15.2l-1.1-1.1M14.9 9.9l-1.1-1.1" />
    </g>
  </>,
  auditoria: <>
    <path className="a-escudo" d="M12 3.5 19.5 6v5.5c0 4.5-3.2 7.8-7.5 9-4.3-1.2-7.5-4.5-7.5-9V6z" />
    <path className="a-check" {...PL} d="m9 12 2.2 2.2L15.5 10" />
  </>,
  ajustes: <>
    <path d="M4 7h7M15 7h5M4 17h3M11 17h9" />
    <circle className="a-k1" cx="13" cy="7" r="2" />
    <circle className="a-k2" cx="9" cy="17" r="2" />
  </>,
}
