/**
 * Validação de formulário com a cara do NeoPrice, no lugar do balão nativo do
 * navegador (branco, fora do tema e mal posicionado no Select e no DatePicker,
 * que validam por um input oculto).
 *
 * Continua usando `required`, `min`, `pattern` etc.: o navegador decide o que
 * é inválido; aqui só mudamos como isso aparece. A mensagem fica embaixo do
 * campo e some assim que ele fica válido. O primeiro campo inválido de cada
 * envio recebe o foco e é rolado para a vista.
 */

const CAMPO = '.field, .catalog-ncm-field, .np-select, .np-data'
let ultimoEnvio = 0

function mensagem(el: HTMLInputElement): string {
  if (el.classList.contains('np-validacao')) return 'Selecione uma opção.'
  if (el.validity.valueMissing) return 'Preencha este campo.'
  if (el.validity.rangeUnderflow) return `Informe um valor a partir de ${el.min}.`
  if (el.validity.rangeOverflow) return `Informe um valor até ${el.max}.`
  if (el.validity.tooShort) return `Use pelo menos ${el.minLength} caracteres.`
  if (el.validity.typeMismatch && el.type === 'email') return 'Informe um e-mail válido.'
  return el.validationMessage || 'Confira este campo.'
}

function limparSeValido(campo: Element) {
  const controles = campo.querySelectorAll<HTMLInputElement>('input, select, textarea')
  if (![...controles].every((c) => c.validity.valid)) return
  campo.classList.remove('campo-invalido')
  campo.querySelector('.np-erro-campo')?.remove()
}

export function instalarValidacao() {
  document.addEventListener('invalid', (evento) => {
    evento.preventDefault()
    const el = evento.target as HTMLInputElement
    const campo = el.closest('.field') ?? el.closest(CAMPO) ?? el.parentElement
    if (!campo) return
    campo.classList.add('campo-invalido')
    let aviso = campo.querySelector('.np-erro-campo')
    if (!aviso) {
      aviso = document.createElement('small')
      aviso.className = 'np-erro-campo'
      aviso.setAttribute('role', 'alert')
      campo.appendChild(aviso)
    }
    aviso.textContent = mensagem(el)

    // só o primeiro inválido de cada envio leva o foco
    const agora = Date.now()
    if (agora - ultimoEnvio > 300) {
      ultimoEnvio = agora
      const alvo = el.classList.contains('np-validacao')
        ? campo.querySelector<HTMLElement>('.np-campo') : el
      alvo?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      alvo?.focus({ preventScroll: true })
    }
  }, true)

  const aoMudar = (evento: Event) => {
    const campo = (evento.target as Element | null)?.closest?.('.campo-invalido')
    // o Select e o DatePicker atualizam o input oculto depois do clique
    if (campo) setTimeout(() => limparSeValido(campo), 0)
  }
  for (const tipo of ['input', 'change', 'click']) document.addEventListener(tipo, aoMudar, true)
}
