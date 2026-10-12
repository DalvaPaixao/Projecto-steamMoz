import { useState } from 'react'
import StatusMessage from '../common/StatusMessage.jsx'

const AREAS_AFETACAO = [
  "Departamento de TIC's",
  'Departamento de Manutenção Industrial',
  'Departamento de Ciências de Administração',
  'CENAD',
  "Sector TIC's",
]

const OUTRA = '__outra__'

export default function StepDados({ dados, aoAvancar }) {
  const [nome, setNome] = useState(dados.nome)

  // Se já havia uma área que não está na lista, abre em "Outra"
  const jaTemOutra = Boolean(dados.departamento) && !AREAS_AFETACAO.includes(dados.departamento)
  const [area, setArea] = useState(jaTemOutra ? OUTRA : dados.departamento)
  const [outraArea, setOutraArea] = useState(jaTemOutra ? dados.departamento : '')
  const [erro, setErro] = useState('')

  function avancar() {
    const areaFinal = area === OUTRA ? outraArea.trim() : area

    if (!nome.trim() || !areaFinal) {
      setErro(
        area === OUTRA
          ? 'Preenche o nome e escreve a área de afetação.'
          : 'Preenche o nome e selecciona a área de afetação.'
      )
      return
    }
    setErro('')
    aoAvancar({ nome: nome.trim(), departamento: areaFinal })
  }

  return (
    <div className="card">
      <h2>Dados do Funcionário</h2>
      <div className="hint">Preenche os dados básicos para iniciar o cadastro.</div>

      <label htmlFor="nome">Nome completo</label>
      <input
        id="nome"
        type="text"
        placeholder="Ex: Dalva Cristóvão Paixão"
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && avancar()}
      />

      <label htmlFor="area">Área de afetação</label>
      <select id="area" value={area} onChange={(e) => setArea(e.target.value)}>
        <option value="">Seleccione a área de afetação</option>
        {AREAS_AFETACAO.map((a) => (
          <option key={a} value={a}>{a}</option>
        ))}
        <option value={OUTRA}>Outra (escrever)</option>
      </select>

      {area === OUTRA && (
        <>
          <label htmlFor="outraArea">Qual é a área de afetação?</label>
          <input
            id="outraArea"
            type="text"
            maxLength={100}
            placeholder="Ex: Biblioteca"
            value={outraArea}
            onChange={(e) => setOutraArea(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && avancar()}
          />
        </>
      )}

      <button onClick={avancar}>Continuar</button>
      <StatusMessage tipo="error" mensagem={erro} />
    </div>
  )
}