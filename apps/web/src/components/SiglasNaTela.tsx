import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { CONTAS, GLOSSARIO, type Termo } from '../app/glossario'
import './sigla.css'

const UFS: Record<string, string> = {
  AC: 'Acre', AL: 'Alagoas', AP: 'Amapá', AM: 'Amazonas', BA: 'Bahia', CE: 'Ceará', DF: 'Distrito Federal',
  ES: 'Espírito Santo', GO: 'Goiás', MA: 'Maranhão', MT: 'Mato Grosso', MS: 'Mato Grosso do Sul', MG: 'Minas Gerais',
  PA: 'Pará', PB: 'Paraíba', PR: 'Paraná', PE: 'Pernambuco', PI: 'Piauí', RJ: 'Rio de Janeiro', RN: 'Rio Grande do Norte',
  RS: 'Rio Grande do Sul', RO: 'Rondônia', RR: 'Roraima', SC: 'Santa Catarina', SP: 'São Paulo', SE: 'Sergipe', TO: 'Tocantins',
}

/** Códigos que aparecem como prefixo de identificador (PA-0003, MP-0001, PRC-2026-0145). */
const PREFIXOS = new Set(['PA', 'MP', 'EMB', 'PRC'])

const termos = GLOSSARIO as Record<string, Termo>

// Palavra sob o cursor: letras (com acento), com sufixo de sigla opcional (ICMS-ST) ou prefixo de código (PA-0003).
const LETRA = /[A-Za-zÀ-ÿ]/

function termoPara(palavra: string, depois: string): Termo | null {
  if (/^-\d/.test(depois) && PREFIXOS.has(palavra)) return termos[palavra] ?? null
  const glossario = termos[palavra]
  const uf = UFS[palavra]
  if (uf && glossario) return { nome: `${uf} (UF) · ${glossario.nome}`, explicacao: `Como estado, é ${uf}. ${glossario.explicacao}` }
  if (uf) return { nome: uf, explicacao: 'Unidade Federativa (estado). Define as alíquotas de ICMS da venda.' }
  return glossario ?? null
}

const CHAVES_CONTAS = Object.keys(CONTAS).sort((a, b) => b.length - a.length)

/** Nome de conta do cálculo ("Preço bruto", "Custo total") que contém a posição do cursor. */
function contaNoPonto(texto: string, offset: number): { inicio: number, fim: number, termo: Termo } | null {
  const minusculo = texto.toLocaleLowerCase('pt-BR')
  for (const chave of CHAVES_CONTAS) {
    let i = minusculo.indexOf(chave)
    while (i !== -1) {
      const fim = i + chave.length
      const separadoAntes = i === 0 || !LETRA.test(texto[i - 1])
      const separadoDepois = fim === texto.length || !LETRA.test(texto[fim])
      if (separadoAntes && separadoDepois && offset >= i && offset <= fim) return { inicio: i, fim, termo: CONTAS[chave] }
      i = minusculo.indexOf(chave, i + 1)
    }
  }
  return null
}

function textoNoPonto(x: number, y: number): { no: Text, offset: number } | null {
  const doc = document as Document & {
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node, offset: number } | null
    caretRangeFromPoint?: (x: number, y: number) => Range | null
  }
  const pos = doc.caretPositionFromPoint?.(x, y)
  if (pos) return pos.offsetNode.nodeType === Node.TEXT_NODE ? { no: pos.offsetNode as Text, offset: pos.offset } : null
  const r = doc.caretRangeFromPoint?.(x, y)
  if (r && r.startContainer.nodeType === Node.TEXT_NODE) return { no: r.startContainer as Text, offset: r.startOffset }
  return null
}

type Dica = { termo: Termo, x: number, y: number, abaixo: boolean }

/**
 * Mostra o significado de qualquer sigla do glossário ao passar o mouse sobre ela, em qualquer tela,
 * sem precisar marcar o texto com <Sigla>. Lê a palavra sob o cursor e não altera o DOM do React.
 */
export function SiglasNaTela({ raiz }: { raiz: () => Element | null }) {
  const [dica, setDica] = useState<Dica | null>(null)

  useEffect(() => {
    let quadro = 0
    let chaveAtual = ''

    function avaliar(x: number, y: number, alvo: Element | null) {
      const html = document.documentElement
      const limpar = () => { if (chaveAtual) { chaveAtual = ''; setDica(null); html.classList.remove('sigla-sob-cursor') } }
      if (!alvo || alvo.closest('.sigla, .sigla-dica, input, textarea, select, [contenteditable="true"]')) return limpar()

      const ponto = textoNoPonto(x, y)
      if (!ponto) return limpar()
      const texto = ponto.no.data
      const conta = contaNoPonto(texto, ponto.offset)
      let inicio = conta ? conta.inicio : ponto.offset
      let fim = conta ? conta.fim : ponto.offset
      if (!conta) {
        while (inicio > 0 && LETRA.test(texto[inicio - 1])) inicio--
        while (fim < texto.length && LETRA.test(texto[fim])) fim++
      }
      // ICMS-ST: junta o sufixo de duas letras maiúsculas
      if (conta) { /* nome de conta já delimitado */ }
      else if (/^-[A-Z]{2}\b/.test(texto.slice(fim)) && termos[texto.slice(inicio, fim + 3)]) fim += 3
      else if (texto.slice(inicio, fim) === 'ST' && texto.slice(Math.max(0, inicio - 5), inicio) === 'ICMS-') inicio -= 5
      const palavra = texto.slice(inicio, fim)
      if (palavra.length < 2) return limpar()
      const termo = conta ? conta.termo : termoPara(palavra, texto.slice(fim))
      if (!termo) return limpar()

      // Confirma que o cursor está mesmo sobre a palavra (e não no fim da linha)
      const faixa = document.createRange()
      faixa.setStart(ponto.no, inicio)
      faixa.setEnd(ponto.no, fim)
      const caixa = faixa.getBoundingClientRect()
      if (x < caixa.left - 1 || x > caixa.right + 1 || y < caixa.top - 1 || y > caixa.bottom + 1) return limpar()

      const chave = `${palavra}@${Math.round(caixa.left)},${Math.round(caixa.top)}`
      if (chave === chaveAtual) return
      chaveAtual = chave
      html.classList.add('sigla-sob-cursor')
      const abaixo = caixa.top < 120
      setDica({
        termo,
        x: Math.min(Math.max(caixa.left + caixa.width / 2, 140), window.innerWidth - 140),
        y: abaixo ? caixa.bottom : caixa.top,
        abaixo,
      })
    }

    function mover(event: MouseEvent) {
      const { clientX, clientY, target } = event
      cancelAnimationFrame(quadro)
      quadro = requestAnimationFrame(() => avaliar(clientX, clientY, target instanceof Element ? target : null))
    }
    function esconder() {
      cancelAnimationFrame(quadro)
      chaveAtual = ''
      setDica(null)
      document.documentElement.classList.remove('sigla-sob-cursor')
    }

    document.addEventListener('mousemove', mover, { passive: true })
    document.addEventListener('scroll', esconder, { passive: true, capture: true })
    document.addEventListener('mouseleave', esconder)
    return () => {
      cancelAnimationFrame(quadro)
      document.removeEventListener('mousemove', mover)
      document.removeEventListener('scroll', esconder, { capture: true })
      document.removeEventListener('mouseleave', esconder)
      document.documentElement.classList.remove('sigla-sob-cursor')
    }
  }, [])

  if (!dica) return null
  return createPortal(
    <span className={`sigla-dica${dica.abaixo ? ' abaixo' : ''}`} role="tooltip" style={{ left: dica.x, top: dica.y }}>
      <strong>{dica.termo.nome}</strong>
      <span>{dica.termo.explicacao}</span>
      {dica.termo.calculo && <code className="sigla-calculo">{dica.termo.calculo}</code>}
    </span>,
    raiz() ?? document.body,
  )
}
