/** Ícones de ação e de estado. Partes `a-*` animadas em icons.css. */
import { PL } from './pathLength'

export const acoes = {
  sair: <>
    <path d="M14.5 4.5h4a1.5 1.5 0 0 1 1.5 1.5v12a1.5 1.5 0 0 1-1.5 1.5h-4" />
    <path className="a-seta" d="M10 16.5 5.5 12 10 7.5M5.5 12h10" />
  </>,
  mais: <path className="a-mais" d="M12 5v14M5 12h14" />,
  seta: <path className="a-seta" d="M5 12h14M13.5 6.5 19 12l-5.5 5.5" />,
  voltar: <path className="a-seta" d="M19 12H5M10.5 6.5 5 12l5.5 5.5" />,
  sol: <>
    <circle className="a-nucleo" cx="12" cy="12" r="4" />
    <path className="a-raios" d="M12 3v1.5M12 19.5V21M3 12h1.5M19.5 12H21M5.6 5.6l1.1 1.1M17.3 17.3l1.1 1.1M5.6 18.4l1.1-1.1M17.3 6.7l1.1-1.1" />
  </>,
  lua: <path className="a-lua" d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z" />,
  sino: <>
    <path className="a-sino" d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z" />
    <path className="a-badalo" d="M10 20.5a2 2 0 0 0 4 0" />
  </>,
  olho: <>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
    <circle className="a-pupila" cx="12" cy="12" r="3" />
  </>,
  olhoFechado: <>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
    <path className="a-risco" {...PL} d="M4 4l16 16" />
  </>,
  cadeado: <>
    <rect x="5" y="10.5" width="14" height="10" rx="2" />
    <path className="a-haste" d="M8.5 10.5V7.5a3.5 3.5 0 0 1 7 0v3" />
    <path d="M12 14.5v2" />
  </>,
  check: <path className="a-check" {...PL} d="m5.5 12.5 4 4 9-9" />,
  alerta: <>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.8v5M12 16.2h.01" />
  </>,
  info: <>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5.5M12 7.8h.01" />
  </>,
  sucesso: <>
    <circle cx="12" cy="12" r="8.5" />
    <path className="a-check" {...PL} d="m8.5 12.3 2.5 2.5 4.6-4.9" />
  </>,
}
