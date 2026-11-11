import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/figtree'
import '@fontsource-variable/sora'
import '@fontsource-variable/jetbrains-mono'
import './index.css'
import App from './App.tsx'
import { iniciarObservabilidade } from './app/observabilidade'
import { instalarValidacao } from './components/form/validacao'

iniciarObservabilidade()
instalarValidacao()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
