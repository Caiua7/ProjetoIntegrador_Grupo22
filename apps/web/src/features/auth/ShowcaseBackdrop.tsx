/** Fundo decorativo da vitrine: grade que desliza e uma linha de margem que se desenha. */
export function ShowcaseBackdrop() {
  return <>
    <div className="auth-grid" />
    <svg className="auth-chart" viewBox="0 0 600 260" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="auth-traco" x1="0" x2="1">
          <stop offset="0" stopColor="#1f6ffa" stopOpacity="0" />
          <stop offset=".35" stopColor="#6ea2ff" />
          <stop offset="1" stopColor="#3ad6aa" />
        </linearGradient>
        <linearGradient id="auth-area" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#1f6ffa" stopOpacity=".22" />
          <stop offset="1" stopColor="#1f6ffa" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path className="meta" d="M0 120H600" />
      <path className="area" d="M0 210C70 205 110 180 160 170S250 190 300 150 390 95 440 100 540 60 600 40V260H0Z" />
      <path className="linha" pathLength={1} d="M0 210C70 205 110 180 160 170S250 190 300 150 390 95 440 100 540 60 600 40" />
      <circle cx="440" cy="100" r="5" />
    </svg>
  </>
}
