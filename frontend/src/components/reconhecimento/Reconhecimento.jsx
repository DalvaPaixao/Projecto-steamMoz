import { useEffect, useState } from 'react'
import { useCamera } from '../../hooks/useCamera.js'
import { marcarPresenca } from '../../api.js'
import StatusMessage from '../common/StatusMessage.jsx'
import Spinner from '../common/Spinner.jsx'
import ImagemProtegida from '../common/ImagemProtegida.jsx'

export default function Reconhecimento() {
  const { videoRef, activa, erro: erroCamera, iniciar, parar, capturar } = useCamera()
  const [foto, setFoto] = useState(null)
  const [aMarcar, setAMarcar] = useState(false)
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

  // Depois de uma marcação, o ecrã volta sozinho ao início (para a pessoa seguinte)
  useEffect(() => {
    if (!resultado) return undefined
    const temporizador = setTimeout(refazer, 8000)
    return () => clearTimeout(temporizador)
  }, [resultado])

  async function marcar() {
    if (!foto) return
    setAMarcar(true)
    setStatus({ tipo: '', mensagem: '' })
    setResultado(null)
    try {
      const resposta = await marcarPresenca(foto)
      setResultado(resposta)
      setStatus({ tipo: resposta.registado ? 'success' : 'info', mensagem: resposta.mensagem })
    } catch (erro) {
      setStatus({ tipo: 'error', mensagem: erro.message })
    } finally {
      setAMarcar(false)
    }
  }

  const rotuloTipo = resultado?.tipo === 'saida' ? 'Saída' : 'Entrada'

  return (
    <div className="card">
      <h2>Marcar Presença</h2>
      <div className="hint">
        Posiciona o rosto de frente para a câmara, captura e confirma. O sistema identifica o
        funcionário e regista a entrada (primeira marcação do dia) ou a saída (segunda marcação).
      </div>

      <div className="camera-wrap">
        {!foto ? (
          <video ref={videoRef} autoPlay playsInline muted />
        ) : (
          <img src={foto} alt="Rosto capturado para marcar a presença" />
        )}
      </div>

      <div className="camera-btn-row">
        {!activa && !foto && <button className="secondary" onClick={iniciar}>Activar Câmara</button>}
        {activa && !foto && <button onClick={capturarFoto}>Capturar</button>}
        {foto && <button className="secondary" onClick={refazer} disabled={aMarcar}>Nova captura</button>}
        {foto && !resultado && (
          <button onClick={marcar} disabled={aMarcar}>
            {aMarcar ? <Spinner label="A identificar..." /> : 'Marcar Presença'}
          </button>
        )}
      </div>

      <StatusMessage tipo="error" mensagem={erroCamera} />
      <StatusMessage tipo={status.tipo} mensagem={status.mensagem} />

      {resultado?.funcionario && (
        <div className="match-card">
          <ImagemProtegida caminho={resultado.funcionario.fotoFacialUrl} alt={resultado.funcionario.nome} />
          <div className="match-info">
            <div className="match-name">{resultado.funcionario.nome}</div>
            <div className="match-detail">{resultado.funcionario.departamento} · {resultado.funcionario.codigo}</div>
            {resultado.registado ? (
              <span className="badge badge-success">{rotuloTipo} registada às {resultado.hora}</span>
            ) : (
              <span className="badge badge-info">Nada novo a registar</span>
            )}
          </div>
        </div>
      )}

      <div className="camera-btn-row">
        <button className="secondary" onClick={parar} disabled={!activa}>Desligar Câmara</button>
      </div>
    </div>
  )
}