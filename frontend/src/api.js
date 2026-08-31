export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

async function pedido(caminho, opcoes = {}) {
  let resposta
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opcoes,
    })
  } catch (erro) {
    throw new Error(`Não foi possível ligar ao servidor (${API_URL}). Confirma que o backend Flask está a correr.`)
  }

  const dados = await resposta.json().catch(() => ({}))
  if (!resposta.ok) {
    throw new Error(dados.erro || 'Ocorreu um erro inesperado no servidor.')
  }
  return dados
}
export function verificarSaude() {
  return pedido('/api/saude')  
}
export function listarFuncionarios() {
  return pedido('/api/funcionarios')
}
export function cadastrarFuncionario(payload) {
  return pedido('/api/funcionarios', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export function pesquisarPorFace(foto) {
  return pedido('/api/reconhecimento', {
    method: 'POST',
    body: JSON.stringify({ foto }),
  })
}
export function urlImagem(caminhoRelativo) {
  if (!caminhoRelativo) return ''
  return `${API_URL}${caminhoRelativo}`
}
