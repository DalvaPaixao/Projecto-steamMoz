import { useState } from 'react'
import StatusMessage from '../common/StatusMessage.jsx'

const DEPARTAMENTOS = [
  'Recursos Humanos',
  'Tecnologias de Informação',
  'Pedagógico',
  'Administração',
  'Financeiro',
]

export default function StepDados({ dados, aoAvancar }) {
  const [nome, setNome] = useState(dados.nome)
  const [departamento, setDepartamento] = useState(dados.departamento)
  const [erro, setErro] = useState('')

  function avancar() {
    if (!nome.trim() || !departamento) {
      setErro('Preenche o nome e selecciona o departamento.')
      return
    }
    setErro('')
    aoAvancar({ nome: nome.trim(), departamento })
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

      <label htmlFor="departamento">Departamento</label>
      <select id="departamento" value={departamento} onChange={(e) => setDepartamento(e.target.value)}>
        <option value="">Seleccione o departamento</option>
        {DEPARTAMENTOS.map((d) => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>

      <button onClick={avancar}>Continuar</button>
      <StatusMessage tipo="error" mensagem={erro} />
    </div>
  )
}
