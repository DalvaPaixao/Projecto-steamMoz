import { useEffect, useState } from 'react'
import CadastroWizard from './components/cadastro/CadastroWizard.jsx'
import Reconhecimento from './components/reconhecimento/Reconhecimento.jsx'
import FuncionariosList from './components/funcionarios/FuncionariosList.jsx'
import PresencasList from './components/presencas/PresencasList.jsx'
import Login from './components/login/Login.jsx'
import './components/presencas/Presencas.css'
import { verificarSaude, obterToken, obterUtilizador, validarSessao, terminarSessao } from './api.js'

const TABS = [
  { id: 'cadastro', rotulo: 'Cadastro de Funcionário' },
  { id: 'presenca', rotulo: 'Marcar Presença' },
  { id: 'historico', rotulo: 'Presenças' },
  { id: 'funcionarios', rotulo: 'Funcionários' },
]

export default function App() {
  const [aba, setAba] = useState('presenca')
  const [servidorOnline, setServidorOnline] = useState(null)
  const [recarregarChave, setRecarregarChave] = useState(0)

  // Sessão: se já houver um token guardado, confirma com o servidor que ainda é válido.
  const [utilizador, setUtilizador] = useState(() => (obterToken() ? obterUtilizador() : null))
  const [aVerificarSessao, setAVerificarSessao] = useState(() => Boolean(obterToken()))

  useEffect(() => {
    verificarSaude()
      .then(() => setServidorOnline(true))
      .catch(() => setServidorOnline(false))
  }, [])

  useEffect(() => {
    if (!obterToken()) return
    validarSessao()
      .then((r) => setUtilizador(r.utilizador))
      .catch(() => {
        terminarSessao()
        setUtilizador(null)
      })
      .finally(() => setAVerificarSessao(false))
  }, [])

  // O api.js avisa quando o servidor responde "sessão inválida/expirada"
  useEffect(() => {
    const aoExpirar = () => setUtilizador(null)
    window.addEventListener('sessao-expirada', aoExpirar)
    return () => window.removeEventListener('sessao-expirada', aoExpirar)
  }, [])

  function sair() {
    terminarSessao()
    setUtilizador(null)
    setAba('presenca')
  }

  function aoConcluirCadastro() {
    setRecarregarChave((k) => k + 1)
    setAba('funcionarios')
  }

  if (aVerificarSessao) return null

  if (!utilizador) {
    return <Login aoEntrar={(nome) => setUtilizador(nome)} />
  }

  return (
    <div className="container">
      <header className="brand-header">
        {/* Se tiveres o logótipo em public/logo-isdb.png, usa esta linha: */}
        {/* <img src="/logo-isdb.png" alt="Instituto Superior Dom Bosco" height="52" /> */}
        <div className="brand-logo">ISDB</div>

        <h1>ISDB · Controlo de Presenças</h1>

        <div className="header-right">
          {servidorOnline !== null && (
            <span className={`server-status ${servidorOnline ? 'online' : 'offline'}`}>
              <span className="dot" /> {servidorOnline ? 'Servidor ligado' : 'Servidor indisponível'}
            </span>
          )}
          <span className="user-chip" title={utilizador}>{utilizador}</span>
          <button className="secondary logout-btn" onClick={sair}>Sair</button>
        </div>
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
      {aba === 'historico' && <PresencasList />}
      {aba === 'funcionarios' && <FuncionariosList recarregarChave={recarregarChave} />}
    </div>
  )
}