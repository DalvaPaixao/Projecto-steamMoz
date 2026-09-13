import { useState } from 'react'
import { useCamera } from '../../hooks/useCamera.js'
import { pesquisarPorFace, urlImagem } from '../../api.js'
import StatusMessage from '../common/StatusMessage.jsx'
import Spinner from '../common/Spinner.jsx'

export default function Reconhecimento() {
  const { videoRef, activa, erro: erroCamera, iniciar, parar, capturar } = useCamera()
  const [foto, setFoto] = useState(null)
  const [aPesquisar, setAPesquisar] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [status, setStatus] = useState({ tipo: '', mensagem: '' })

  function capturarFoto() {
    const dataUrl = capturar()
    if (!dataUrl) {
      setStatus({ tipo: 'error', mensagem: 'A câmara ainda não está pronta. Aguarda um instante.' })
      return
    }
    setFoto(dataUrl)
    setResultado(null)
    setStatus({ tipo: '', mensagem: '' })
  }

  function refazer() {
    setFoto(null)
    setResultado(null)
    setStatus({ tipo: '', mensagem: '' })
  }

  async function pesquisar() {
    if (!foto) return
    setAPesquisar(true)
    setStatus({ tipo: '', mensagem: '' })
    setResultado(null)
    try {
      const resposta = await pesquisarPorFace(foto)
      setResultado(resposta)
      if (!resposta.encontrado) {
        setStatus({ tipo: 'error', mensagem: resposta.mensagem || 'Nenhum funcionário corresponde a este rosto.' })
      }
    } catch (erro) {
      setStatus({ tipo: 'error', mensagem: erro.message })
    } finally {
      setAPesquisar(false)
    }
  }

  return (
    <div className="card">
      <h2>Reconhecimento Facial</h2>
      <div className="hint">
        Captura um rosto pela câmara para pesquisar, em tempo real, se corresponde a algum
        funcionário já cadastrado na base de dados.
      </div>

      <div className="camera-wrap">
        {!foto ? (
          <video ref={videoRef} autoPlay playsInline muted />
        ) : (
          <img src={foto} alt="Rosto capturado para pesquisa" />
        )}
      </div>

      <div className="camera-btn-row">
        {!activa && !foto && <button className="secondary" onClick={iniciar}>Activar Câmara</button>}
        {activa && !foto && <button onClick={capturarFoto}>Capturar</button>}
        {foto && <button className="secondary" onClick={refazer}>Nova captura</button>}
        {foto && (
          <button onClick={pesquisar} disabled={aPesquisar}>
            {aPesquisar ? <Spinner label="A pesquisar..." /> : 'Pesquisar'}
          </button>
        )}
      </div>

      <StatusMessage tipo="error" mensagem={erroCamera} />
      <StatusMessage tipo={status.tipo} mensagem={status.mensagem} />

      {resultado?.encontrado && (
        <div className="match-card">
          <img src={urlImagem(resultado.funcionario.fotoFacialUrl)} alt={resultado.funcionario.nome} />
          <div className="match-info">
            <div className="match-name">{resultado.funcionario.nome}</div>
            <div className="match-detail">{resultado.funcionario.departamento} · {resultado.funcionario.codigo}</div>
            <div className="match-detail">Cadastrado em {resultado.funcionario.dataCadastro}</div>
            <span className="badge badge-success">Correspondência encontrada</span>
          </div>
        </div>
      )}

      <div className="camera-btn-row">
        <button className="secondary" onClick={parar} disabled={!activa}>Desligar Câmara</button>
      </div>
    </div>
  )
}
