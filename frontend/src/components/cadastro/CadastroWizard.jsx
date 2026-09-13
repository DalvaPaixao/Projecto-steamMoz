import { useState } from 'react'
import StepDados from './StepDados.jsx'
import StepDocumento from './StepDocumento.jsx'
import StepCaptura from './StepCaptura.jsx'
import StepConfirmacao from './StepConfirmacao.jsx'

const FORM_INICIAL = {
  nome: '',
  departamento: '',
  fotoBI: null,
  facial: { frontal: null },
}

const ETAPAS = ['Dados', 'Documento', 'Captura Facial', 'Confirmação']

export default function CadastroWizard({ aoConcluirCadastro }) {
  const [passo, setPasso] = useState(1)
  const [dados, setDados] = useState(FORM_INICIAL)

  function avancarComDados(parciais) {
    setDados((anterior) => ({ ...anterior, ...parciais }))
    setPasso((p) => p + 1)
  }

  function reiniciar() {
    setDados(FORM_INICIAL)
    setPasso(1)
    aoConcluirCadastro()
  }

  return (
    <div>
      <div className="steps">
        {ETAPAS.map((etapa, i) => {
          const n = i + 1
          const classe = n === passo ? 'active' : n < passo ? 'done' : ''
          return (
            <div key={etapa} className={`step-pill ${classe}`}>
              {n}. {etapa}
            </div>
          )
        })}
      </div>

      {passo === 1 && <StepDados dados={dados} aoAvancar={avancarComDados} />}
      {passo === 2 && (
        <StepDocumento dados={dados} aoAvancar={avancarComDados} aoVoltar={() => setPasso(1)} />
      )}
      {passo === 3 && (
        <StepCaptura dados={dados} aoAvancar={avancarComDados} aoVoltar={() => setPasso(2)} />
      )}
      {passo === 4 && (
        <StepConfirmacao dados={dados} aoVoltar={() => setPasso(3)} aoConcluir={reiniciar} />
      )}
    </div>
  )
}
