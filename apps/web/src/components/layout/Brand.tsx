import logoClaro from '../../assets/brand/neoprice-claro.png'
import logoEscuro from '../../assets/brand/neoprice-escuro.png'
import marca from '../../assets/brand/neoprice-n.png'

/**
 * Logo do NeoPrice. `tema` diz sobre que fundo ela fica: 'escuro' usa o
 * texto branco, 'claro' o texto escuro e 'sistema' segue o tema do sistema
 * operacional (telas de acesso, que não têm alternador de tema).
 */
export function Brand({ tema = 'sistema', altura = 26, className = '' }: {
  tema?: 'claro' | 'escuro' | 'sistema'
  altura?: number
  className?: string
}) {
  const largura = Math.round(altura * 5.02)
  const img = (src: string) => <img src={src} alt="NeoPrice" width={largura} height={altura} className={`brand-logo ${className}`.trim()} />

  if (tema === 'claro') return img(logoClaro)
  if (tema === 'escuro') return img(logoEscuro)
  return <picture>
    <source srcSet={logoClaro} media="(prefers-color-scheme: light)" />
    {img(logoEscuro)}
  </picture>
}

/** Só o "N", para espaços pequenos (carregamento, avatar da marca). */
export function BrandMark({ tamanho = 40, className = '' }: { tamanho?: number, className?: string }) {
  return <img src={marca} alt="" aria-hidden="true" width={tamanho} height={tamanho} className={`brand-mark ${className}`.trim()} />
}
