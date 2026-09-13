import { useEffect, useMemo, useState } from 'react'
import { listarFuncionarios, urlImagem } from '../../api.js'
import StatusMessage from '../common/StatusMessage.jsx'

export default function FuncionariosList({ recarregarChave }) {
  const [funcionarios, setFuncionarios] = useState([])
  const [aCarregar, setACarregar] = useState(true)
  const [erro, setErro] = useState('')
  const [pesquisa, setPesquisa] = useState('')
  const [departamento, setDepartamento] = useState('')
  const [ordenacao, setOrdenacao] = useState({ campo: 'dataCadastro', asc: false })

  useEffect(() => {
    carregar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recarregarChave])

  async function carregar() {
    setACarregar(true)
    setErro('')
    try {
      const resposta = await listarFuncionarios()
      setFuncionarios(resposta.funcionarios)
    } catch (err) {
      setErro(err.message)
    } finally {
      setACarregar(false)
    }
  }

  const departamentos = useMemo(
    () => [...new Set(funcionarios.map((f) => f.departamento))].sort(),
    [funcionarios]
  )

  const listaFiltrada = useMemo(() => {
    const termo = pesquisa.trim().toLowerCase()
    let lista = funcionarios.filter((f) => {
      const correspondeTermo = !termo
        || f.nome.toLowerCase().includes(termo)
        || f.codigo.toLowerCase().includes(termo)
      const correspondeDepartamento = !departamento || f.departamento === departamento
      return correspondeTermo && correspondeDepartamento
    })

    lista = [...lista].sort((a, b) => {
      const valorA = a[ordenacao.campo]
      const valorB = b[ordenacao.campo]
      const comparacao = String(valorA).localeCompare(String(valorB))
      return ordenacao.asc ? comparacao : -comparacao
    })

    return lista
  }, [funcionarios, pesquisa, departamento, ordenacao])

  function alternarOrdenacao(campo) {
    setOrdenacao((anterior) =>
      anterior.campo === campo ? { campo, asc: !anterior.asc } : { campo, asc: true }
    )
  }

  function setaOrdenacao(campo) {
    if (ordenacao.campo !== campo) return ''
    return ordenacao.asc ? ' ▲' : ' ▼'
  }

  return (
    <div className="card">
      <h2>Funcionários Registados <span className="badge">{funcionarios.length}</span></h2>

      <div className="filters-row">
        <input
          type="text"
          placeholder="Pesquisar por nome ou código..."
          value={pesquisa}
          onChange={(e) => setPesquisa(e.target.value)}
        />
        <select value={departamento} onChange={(e) => setDepartamento(e.target.value)}>
          <option value="">Todos os departamentos</option>
          {departamentos.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <button className="secondary" onClick={carregar}>Actualizar</button>
      </div>

      {aCarregar && <div className="empty-state">A carregar funcionários...</div>}
      <StatusMessage tipo="error" mensagem={erro} />

      {!aCarregar && !erro && listaFiltrada.length === 0 && (
        <div className="empty-state">
          {funcionarios.length === 0 ? 'Ainda não há funcionários registados.' : 'Nenhum resultado para esta pesquisa.'}
        </div>
      )}

      {!aCarregar && !erro && listaFiltrada.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Foto</th>
              <th className="ordenavel" onClick={() => alternarOrdenacao('codigo')}>Código{setaOrdenacao('codigo')}</th>
              <th className="ordenavel" onClick={() => alternarOrdenacao('nome')}>Nome{setaOrdenacao('nome')}</th>
              <th className="ordenavel" onClick={() => alternarOrdenacao('departamento')}>Departamento{setaOrdenacao('departamento')}</th>
              <th className="ordenavel" onClick={() => alternarOrdenacao('dataCadastro')}>Data{setaOrdenacao('dataCadastro')}</th>
            </tr>
          </thead>
          <tbody>
            {listaFiltrada.map((f) => (
              <tr key={f.id}>
                <td className="foto"><img src={urlImagem(f.fotoFacialUrl)} alt={f.nome} /></td>
                <td>{f.codigo}</td>
                <td>{f.nome}</td>
                <td>{f.departamento}</td>
                <td>{f.dataCadastro}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
