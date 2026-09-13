import { useState } from 'react'
import StatusMessage from '../common/StatusMessage.jsx'

export default function StepDocumento({ dados, aoAvancar, aoVoltar }) {
  const [fotoBI, setFotoBI] = useState(dados.fotoBI)
  const [erro, setErro] = useState('')

  function lerFicheiro(ficheiro) {
    if (!ficheiro) return
    const leitor = new FileReader()
    leitor.onload = (e) => setFotoBI(e.target.result)
    leitor.readAsDataURL(ficheiro)
  }

  function avancar() {
    if (!fotoBI) {
      setErro('Por favor carrega a foto do documento de identificação.')
      return
    }
    setErro('')
    aoAvancar({ fotoBI })
  }

  return (
    <div className="card">
      <h2>Documento de Identificação</h2>
      <div className="hint">Carrega uma imagem legível de um documento oficial de identificação.</div>

      <div
        className="file-drop"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          lerFicheiro(e.dataTransfer.files[0])
        }}
      >
        <input type="file" accept="image/*" onChange={(e) => lerFicheiro(e.target.files[0])} />
        {fotoBI && (
          <div className="preview">
            <img src={fotoBI} alt="Pré-visualização do documento" />
          </div>
        )}
      </div>

      <div className="camera-btn-row">
        <button className="secondary" onClick={aoVoltar}>Voltar</button>
        <button onClick={avancar}>Continuar</button>
      </div>
      <StatusMessage tipo="error" mensagem={erro} />
    </div>
  )
}
