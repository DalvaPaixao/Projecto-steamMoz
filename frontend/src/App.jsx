import { useEffect, useState } from 'react'
import CadastroWizard from './components/cadastro/CadastroWizard.jsx'
import Reconhecimento from './components/reconhecimento/Reconhecimento.jsx'
import FuncionariosList from './components/funcionarios/FuncionariosList.jsx'
import { verificarSaude } from './api.js'

const TABS = [
  { id: 'cadastro', rotulo: 'Cadastro de Funcionário' },
  { id: 'presenca', rotulo: 'Marcar Presença' },
  { id: 'funcionarios', rotulo: 'Funcionários' },
]

export default function App() {
  const [aba, setAba] = useState('presenca')
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
        {/* Se tiveres o logótipo em public/logo-isdb.png, usa esta linha: */}
        {/* <img src="/logo-isdb.png" alt="Instituto Superior Dom Bosco" height="52" /> */}
        <div className="brand-logo">ISDB</div>

        <h1>ISDB · Controlo de Presenças</h1>

        {servidorOnline !== null && (
          <span className={`server-status ${servidorOnline ? 'online' : 'offline'}`}>
            <span className="dot" /> {servidorOnline ? 'Servidor ligado' : 'Servidor indisponível'}
          </span>
        )}
      </header>

      <div className="subtitle">
        Sistema de Marcação de Presença dos Funcionários do ISDB por Reconhecimento Facial
      </div>

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
      {aba === 'presenca' && <Reconhecimento />}
      {aba === 'funcionarios' && <FuncionariosList recarregarChave={recarregarChave} />}
    </div>
  )
}