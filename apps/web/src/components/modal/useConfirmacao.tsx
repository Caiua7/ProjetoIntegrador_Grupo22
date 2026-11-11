import { useCallback, useRef, useState, type ReactNode } from 'react'
import { Icon } from '../icons/Icon'
import { Modal } from './Modal'

type Pedido = {
  titulo: string
  mensagem: ReactNode
  confirmar?: string
  cancelar?: string
  perigo?: boolean
}

/**
 * Confirmação com a cara do NeoPrice, no lugar do `window.confirm` nativo.
 *
 *   const [confirmar, dialogo] = useConfirmacao()
 *   if (!await confirmar({ titulo: 'Inativar?', mensagem: '...' })) return
 *   ...
 *   return <>{dialogo}...</>
 */
export function useConfirmacao(): [(pedido: Pedido) => Promise<boolean>, ReactNode] {
  const [pedido, setPedido] = useState<Pedido | null>(null)
  const resolver = useRef<(resposta: boolean) => void>(() => {})

  const confirmar = useCallback((novo: Pedido) => new Promise<boolean>((resolve) => {
    resolver.current = resolve
    setPedido(novo)
  }), [])

  const responder = (resposta: boolean) => { setPedido(null); resolver.current(resposta) }

  const dialogo = pedido && <Modal tamanho="pequeno" titulo={pedido.titulo} onFechar={() => responder(false)}
    rodape={<>
      <button type="button" className="button secondary" onClick={() => responder(false)}>{pedido.cancelar ?? 'Cancelar'}</button>
      <button type="button" data-autofocus className={`button ${pedido.perigo ? 'perigo' : 'primary'}`} onClick={() => responder(true)}>{pedido.confirmar ?? 'Confirmar'}</button>
    </>}>
    <div className="np-confirma">
      <span className={`np-confirma-icone${pedido.perigo ? ' perigo' : ''}`} aria-hidden="true"><Icon name="alerta" size={20} /></span>
      <p>{pedido.mensagem}</p>
    </div>
  </Modal>

  return [confirmar, dialogo]
}
