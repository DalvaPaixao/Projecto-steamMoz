import { useEffect, useMemo, useState } from 'react'
import { listarPresencas } from '../../api.js'
import StatusMessage from '../common/StatusMessage.jsx'

function hojeISO() {
  const d = new Date()
  const mes = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mes}-${dia}`
}

export default function PresencasList() {
  const [de, setDe] = useState(hojeISO())
  const [ate, setAte] = useState(hojeISO())
  const [pesquisa, setPesquisa] = useState('')
  const [presencas, setPresencas] = useState([])
  const [aCarregar, setACarregar] = useState(true)
  const [erro, setErro] = useState('')

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function carregar() {
    setACarregar(true)
    setErro('')
    try {
      const resposta = await listarPresencas(de, ate)
      setPresencas(resposta.presencas)
    } catch (err) {
      setPresencas([])
      setErro(err.message)
    } finally {
      setACarregar(false)
    }
  }

  const listaFiltrada = useMemo(() => {
    const termo = pesquisa.trim().toLowerCase()
    if (!termo) return presencas
    return presencas.filter(
      (p) => p.nome.toLowerCase().includes(termo) || p.codigo.toLowerCase().includes(termo)
    )
  }, [presencas, pesquisa])

  return (
    <div className="card">
      <h2>Histórico de Presenças <span className="badge">{listaFiltrada.length}</span></h2>
      <div className="hint">Entradas e saídas registadas, por funcionário e por dia.</div>

      <div className="filters-row">
        <input type="date" value={de} max={ate} onChange={(e) => setDe(e.target.value)} aria-label="Data inicial" />
        <input type="date" value={ate} min={de} onChange={(e) => setAte(e.target.value)} aria-label="Data final" />
        <button className="secondary" onClick={carregar} disabled={aCarregar}>Pesquisar</button>
      </div>
      <div className="filters-row">
        <input
          type="text"
          placeholder="Filtrar por nome ou código..."
          value={pesquisa}
          onChange={(e) => setPesquisa(e.target.value)}
        />
      </div>

      {aCarregar && <div className="empty-state">A carregar presenças...</div>}
      <StatusMessage tipo="error" mensagem={erro} />

      {!aCarregar && !erro && listaFiltrada.length === 0 && (
        <div className="empty-state">
          {presencas.length === 0 ? 'Não há presenças registadas neste período.' : 'Nenhum resultado para este filtro.'}
        </div>
      )}

      {!aCarregar && !erro && listaFiltrada.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Código</th>
              <th>Nome</th>
              <th>Área de afetação</th>
              <th>Entrada</th>
              <th>Saída</th>
              <th>Horas</th>
            </tr>
          </thead>
          <tbody>
            {listaFiltrada.map((p) => (
              <tr key={`${p.data}-${p.funcionarioId}`}>
                <td>{p.data}</td>
                <td>{p.codigo}</td>
                <td>{p.nome}</td>
                <td>{p.departamento}</td>
                <td>{p.entrada || <span className="cell-vazio">—</span>}</td>
                <td>{p.saida || <span className="cell-vazio">—</span>}</td>
                <td>{p.horasTrabalhadas || <span className="cell-vazio">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}