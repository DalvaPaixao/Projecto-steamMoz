import { useState } from 'react'
import './Login.css'
import StatusMessage from '../common/StatusMessage.jsx'
import Spinner from '../common/Spinner.jsx'
import { iniciarSessao } from '../../api.js'

// O emblema deve estar em  frontend/public/logo-isdb.png
const LOGO = '/logo-isdb.png'

function IconeOlho({ aberto }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
      <circle cx="12" cy="12" r="3" />
      {!aberto && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  )
}

export default function Login({ aoEntrar }) {
  const [utilizador, setUtilizador] = useState('')
  const [senha, setSenha] = useState('')
  const [verSenha, setVerSenha] = useState(false)
  const [aEntrar, setAEntrar] = useState(false)
  const [erro, setErro] = useState('')
  const [semLogo, setSemLogo] = useState(false)

  async function submeter(evento) {
    evento.preventDefault()
    if (!utilizador.trim() || !senha) {
      setErro('Preenche o nome de utilizador e a senha.')
      return
    }
    setAEntrar(true)
    setErro('')
    try {
      const resposta = await iniciarSessao(utilizador, senha)
      aoEntrar(resposta.utilizador)
    } catch (err) {
      setErro(err.message)
      setAEntrar(false)
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submeter}>
        <div className="login-logo">
          {semLogo ? (
            <div className="brand-logo">ISDB</div>
          ) : (
            <img src={LOGO} alt="Instituto Superior Dom Bosco" onError={() => setSemLogo(true)} />
          )}
        </div>

        <h1 className="login-titulo">Controlo de Presenças</h1>
        <p className="login-subtitulo">Entra com a tua conta para continuar</p>

        <input
          className="login-input"
          type="text"
          placeholder="Nome de utilizador"
          autoComplete="username"
          autoFocus
          value={utilizador}
          onChange={(e) => setUtilizador(e.target.value)}
          disabled={aEntrar}
        />

        <div className="login-senha">
          <input
            className="login-input"
            type={verSenha ? 'text' : 'password'}
            placeholder="Senha"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            disabled={aEntrar}
          />
          <button
            type="button"
            className="login-olho"
            onClick={() => setVerSenha((v) => !v)}
            aria-label={verSenha ? 'Esconder senha' : 'Mostrar senha'}
            title={verSenha ? 'Esconder senha' : 'Mostrar senha'}
          >
            <IconeOlho aberto={verSenha} />
          </button>
        </div>

        <button type="submit" className="login-entrar" disabled={aEntrar}>
          {aEntrar ? <Spinner label="A entrar..." /> : 'Entrar'}
        </button>

        <StatusMessage tipo="error" mensagem={erro} />
      </form>
    </div>
  )
}