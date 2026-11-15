
import { useState } from 'react'
import { baixarArquivo } from '../../services/apiClient'

type FormatoExportacao = 'csv' | 'xlsx'

export function ExportBIPage() {
  const [exportando, setExportando] = useState<FormatoExportacao | null>(null)
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState('')

  async function exportar(formato: FormatoExportacao) {
    setExportando(formato)
    setErro('')
    setSucesso('')

    try {
      const arquivo = await baixarArquivo(
        `/exportacoes/cenarios?formato=${formato}`,
      )

      const url = URL.createObjectURL(arquivo)
      const link = document.createElement('a')

      link.href = url
      link.download = `neoprice-cenarios.${formato}`

      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      URL.revokeObjectURL(url)

      setSucesso(
        `Arquivo ${formato.toUpperCase()} gerado e baixado com sucesso.`,
      )
    } catch (error) {
      setErro(
        error instanceof Error
          ? error.message
          : 'Não foi possível exportar os dados.',
      )
    } finally {
      setExportando(null)
    }
  }

  return (
    <section className="content">
      <div className="list-intro">
        <div>
          <h2>Exportar para BI</h2>
          <p>
            Exporte os dados de precificação do NeoPrice para utilizar em
            ferramentas de Business Intelligence, como Power BI.
          </p>
        </div>
      </div>

      <div className="form-card">
        <h3>Exportação de cenários</h3>

        <p>
          Gere um arquivo com os cenários de precificação aos quais você
          possui acesso. Escolha o formato desejado para utilizar os dados
          em suas análises.
        </p>

        <div className="form-actions">
          <button
            type="button"
            className="button primary"
            onClick={() => exportar('xlsx')}
            disabled={exportando !== null}
          >
            {exportando === 'xlsx' ? 'Gerando Excel...' : 'Exportar Excel (.xlsx)'}
          </button>

          <button
            type="button"
            className="button secondary"
            onClick={() => exportar('csv')}
            disabled={exportando !== null}
          >
            {exportando === 'csv' ? 'Gerando CSV...' : 'Exportar CSV (.csv)'}
          </button>
        </div>

        {erro && (
          <div className="catalog-error" role="alert">
            {erro}
          </div>
        )}

        {sucesso && (
          <div className="catalog-success" role="status">
            {sucesso}
          </div>
        )}
      </div>
    </section>
  )
}
