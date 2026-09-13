import { useEffect, useState } from 'react'
import CadastroWizard from './components/cadastro/CadastroWizard.jsx'
import Reconhecimento from './components/reconhecimento/Reconhecimento.jsx'
import FuncionariosList from './components/funcionarios/FuncionariosList.jsx'
import { verificarSaude } from './api.js'

const TABS = [
  { id: 'cadastro', rotulo: 'Cadastro' },
  { id: 'reconhecimento', rotulo: 'Reconhecimento Facial' },
  { id: 'funcionarios', rotulo: 'Funcionários' },
]

export default function App() {
  const [aba, setAba] = useState('cadastro')
  const [servidorOnline, setServidorOnline] = useState(null)
  const [recarregarChave, setRecarregarChave] = useState(0)

  useEffect(() => {
    verificarSaude()
      .then(() => setServidorOnline(true))
      .catch(() => setServidorOnline(false))
  }, [])

  function aoConcluirCadastro() {
    setRecarregarChave((k) => k + 1)
    setAba('funcionarios')
  }

  return (
    <div className="container">
      <header className="brand-header">
        <svg width="52" height="52" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
          <path d="M15,15 L15,2 A13,13 0 0,0 2,15 Z" fill="#39BAA1" />
          <path d="M17,15 L30,15 A13,13 0 0,0 17,2 Z" fill="#4D7BFF" />
          <path d="M15,17 L2,17 A13,13 0 0,0 15,30 Z" fill="#4D7BFF" />
          <path d="M17,17 L17,30 A13,13 0 0,0 30,17 Z" fill="#39BAA1" />
        </svg>
        <h1>Stemmoz</h1>
        {servidorOnline !== null && (
          <span className={`server-status ${servidorOnline ? 'online' : 'offline'}`}>
            <span className="dot" /> {servidorOnline ? 'Servidor ligado' : 'Servidor indisponível'}
          </span>
        )}
      </header>
      <div className="subtitle">Sistema de Cadastro e Reconhecimento Facial de Funcionários</div>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab ${aba === t.id ? 'active' : ''}`}
            onClick={() => setAba(t.id)}
          >
            {t.rotulo}
          </button>
        ))}
      </nav>

      {aba === 'cadastro' && <CadastroWizard aoConcluirCadastro={aoConcluirCadastro} />}
      {aba === 'reconhecimento' && <Reconhecimento />}
      {aba === 'funcionarios' && <FuncionariosList recarregarChave={recarregarChave} />}
    </div>
  )
}
