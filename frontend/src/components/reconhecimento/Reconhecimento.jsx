import { useEffect, useState } from 'react'
import { useCamera } from '../../hooks/useCamera.js'
import { pesquisarPorFace } from '../../api.js'
import StatusMessage from '../common/StatusMessage.jsx'
import Spinner from '../common/Spinner.jsx'
import ImagemProtegida from '../common/ImagemProtegida.jsx'

export default function Reconhecimento() {
  const { videoRef, activa, erro: erroCamera, iniciar, parar, capturar } = useCamera()
  const [foto, setFoto] = useState(null)
  const [aVerificar, setAVerificar] = useState(false)
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

  useEffect(() => {
    if (!resultado) return undefined
    const temporizador = setTimeout(refazer, 8000)
    return () => clearTimeout(temporizador)
  }, [resultado])

  async function verificar() {
    if (!foto) return
    setAVerificar(true)
    setStatus({ tipo: '', mensagem: '' })
    setResultado(null)
    try {
      const resposta = await pesquisarPorFace(foto)
      setResultado(resposta)
      if (resposta.encontrado) {
        setStatus({ tipo: 'success', mensagem: `Rosto reconhecido: ${resposta.funcionario.nome} é funcionário(a) do ISDB e está presente aqui.` })
      } else {
        setStatus({ tipo: 'error', mensagem: resposta.mensagem || 'Rosto não reconhecido. Esta pessoa não está registada.' })
      }
    } catch (erro) {
      setStatus({ tipo: 'error', mensagem: erro.message })
    } finally {
      setAVerificar(false)
    }
  }

  return (
    <div className="card">
      <h2>Verificar Rosto</h2>
      <div className="hint">
        Posiciona o rosto de frente para a câmara, captura e confirma. O sistema verifica se a
        pessoa é funcionário do ISDB e mostra os dados dela. Esta verificação não guarda nenhum registo.
      </div>

      <div className="camera-wrap">
        {!foto ? (<video ref={videoRef} autoPlay playsInline muted />) : (<img src={foto} alt="Rosto capturado para verificação" />)}
      </div>

      <div className="camera-btn-row">
        {!activa && !foto && <button className="secondary" onClick={iniciar}>Activar Câmara</button>}
        {activa && !foto && <button onClick={capturarFoto}>Capturar</button>}
        {foto && <button className="secondary" onClick={refazer} disabled={aVerificar}>Nova captura</button>}
        {foto && !resultado && (
          <button onClick={verificar} disabled={aVerificar}>
            {aVerificar ? <Spinner label="A verificar..." /> : 'Verificar Rosto'}
          </button>
        )}
      </div>

      <StatusMessage tipo="error" mensagem={erroCamera} />
      <StatusMessage tipo={status.tipo} mensagem={status.mensagem} />

      {resultado?.encontrado && resultado.funcionario && (
        <div className="match-card">
          <ImagemProtegida caminho={resultado.funcionario.fotoFacialUrl} alt={resultado.funcionario.nome} />
          <div className="match-info">
            <div className="match-name">{resultado.funcionario.nome}</div>
            <div className="match-detail">{resultado.funcionario.departamento} · {resultado.funcionario.codigo}</div>
            <span className="badge badge-success">Funcionário reconhecido · presente</span>
          </div>
        </div>
      )}

      <div className="camera-btn-row">
        <button className="secondary" onClick={parar} disabled={!activa}>Desligar Câmara</button>
      </div>
    </div>
  )
}
