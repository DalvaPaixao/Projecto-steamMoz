import { useState } from 'react'
import StatusMessage from '../common/StatusMessage.jsx'
import Spinner from '../common/Spinner.jsx'
import { cadastrarFuncionario } from '../../api.js'

export default function StepConfirmacao({ dados, aoVoltar, aoConcluir }) {
  const [aEnviar, setAEnviar] = useState(false)
  const [status, setStatus] = useState({ tipo: '', mensagem: '' })

  async function finalizar() {
    setAEnviar(true)
    setStatus({ tipo: '', mensagem: '' })
    try {
      const resposta = await cadastrarFuncionario({
        nome: dados.nome,
        departamento: dados.departamento,
        fotoBI: dados.fotoBI,
        fotoFacial: dados.facial.frontal,
      })
      setStatus({ tipo: 'success', mensagem: `${resposta.mensagem} Código: ${resposta.funcionario.codigo}` })
      setTimeout(() => aoConcluir(), 1400)
    } catch (erro) {
      setStatus({ tipo: 'error', mensagem: erro.message })
    } finally {
      setAEnviar(false)
    }
  }

  return (
    <div className="card">
      <h2>Confirmar Cadastro</h2>
      <div className="hint">Revê os dados antes de finalizar o registo.</div>

      <div className="review-row"><span>Nome</span><span>{dados.nome}</span></div>
      <div className="review-row"><span>Departamento</span><span>{dados.departamento}</span></div>
      <div className="preview" style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <img src={dados.fotoBI} alt="BI" style={{ width: 90, height: 90, objectFit: 'cover', borderRadius: 8, border: '1px solid #e5e7eb' }} />
          <img src={dados.facial.frontal} alt="Frontal" style={{ width: 90, height: 90, objectFit: 'cover', borderRadius: 8, border: '1px solid #e5e7eb' }} />
        </div>
      </div>

      <div className="camera-btn-row">
        <button className="secondary" onClick={aoVoltar} disabled={aEnviar}>Voltar</button>
        <button onClick={finalizar} disabled={aEnviar}>
          {aEnviar ? <Spinner label="A registar..." /> : 'Finalizar Cadastro'}
        </button>
      </div>
      <StatusMessage tipo={status.tipo} mensagem={status.mensagem} />
    </div>
  )
}
