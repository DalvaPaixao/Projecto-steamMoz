import { useEffect, useState } from 'react'
import { useCamera } from '../../hooks/useCamera.js'
import StatusMessage from '../common/StatusMessage.jsx'

export default function StepCaptura({ dados, aoAvancar, aoVoltar }) {
  const { videoRef, activa, erro: erroCamera, iniciar, parar, capturar } = useCamera()
  const [frontal, setFrontal] = useState(dados.facial.frontal)
  const [erro, setErro] = useState('')

  useEffect(() => {
    iniciar()
    return () => parar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function capturarFoto() {
    const dataUrl = capturar()
    if (!dataUrl) {
      setErro('A câmara ainda não está pronta. Aguarda um instante e tenta novamente.')
      return
    }
    setFrontal(dataUrl)
    setErro('')
  }

  function refazer() {
    setFrontal(null)
  }

  function avancar() {
    if (!frontal) {
      setErro('Captura o rosto antes de continuar.')
      return
    }
    aoAvancar({ facial: { frontal } })
  }

  return (
    <div className="card">
      <h2>Captura Facial</h2>
      <div className="hint">
        O sistema é automático: basta captar o rosto de frente para a câmara. As características
        faciais serão extraídas a partir desta única imagem.
      </div>

      <div className="capture-instruction">
        {frontal ? 'Rosto capturado ✓' : 'Posiciona o rosto de frente para a câmara'}
      </div>

      <div className="camera-wrap">
        {!frontal ? (
          <video ref={videoRef} autoPlay playsInline muted />
        ) : (
          <img src={frontal} alt="Foto facial capturada" />
        )}
      </div>

      <div className="angle-thumbs">
        <div className="angle-thumb">
          <div className={`box ${frontal ? 'filled' : ''}`}>
            {frontal ? <img src={frontal} alt="frontal" /> : 'Frontal'}
          </div>
          <div className="label">Foto Facial</div>
        </div>
      </div>

      <div className="camera-btn-row">
        {!activa && !frontal && <button className="secondary" onClick={iniciar}>Activar Câmara</button>}
        {activa && !frontal && <button onClick={capturarFoto}>Capturar</button>}
        {frontal && <button className="secondary" onClick={refazer}>Capturar novamente</button>}
      </div>
      <div className="camera-btn-row">
        <button className="secondary" onClick={aoVoltar}>Voltar</button>
        <button onClick={avancar} disabled={!frontal}>Continuar</button>
      </div>
      <StatusMessage tipo="error" mensagem={erroCamera || erro} />
      {activa && !erroCamera && !frontal && (
        <StatusMessage tipo="success" mensagem="Câmara activa. Posiciona o rosto de frente e captura." />
      )}
    </div>
  )
}
