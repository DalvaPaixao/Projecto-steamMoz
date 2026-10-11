export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

// A sessão (token) fica guardada só enquanto o separador/janela estiver aberto:
// ao fechar o navegador, é preciso entrar novamente.
const CHAVE_TOKEN = 'stemmoz_token'
const CHAVE_UTILIZADOR = 'stemmoz_utilizador'

// Fotos já descarregadas nesta sessão (caminho -> Promise com o endereço local da imagem)
const cacheImagens = new Map()

export function obterToken() {
  try {
    return sessionStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function obterUtilizador() {
  try {
    return sessionStorage.getItem(CHAVE_UTILIZADOR)
  } catch {
    return null
  }
}

function guardarSessao(token, utilizador) {
  try {
    sessionStorage.setItem(CHAVE_TOKEN, token)
    sessionStorage.setItem(CHAVE_UTILIZADOR, utilizador)
  } catch {
    // sem armazenamento disponível: a sessão não sobrevive a um refresh
  }
}

function limparCacheImagens() {
  cacheImagens.forEach((promessa) => {
    promessa.then((url) => URL.revokeObjectURL(url)).catch(() => {})
  })
  cacheImagens.clear()
}

export function terminarSessao() {
  try {
    sessionStorage.removeItem(CHAVE_TOKEN)
    sessionStorage.removeItem(CHAVE_UTILIZADOR)
  } catch {
    // nada a fazer
  }
  limparCacheImagens()
}

function avisarSessaoExpirada() {
  terminarSessao()
  window.dispatchEvent(new Event('sessao-expirada'))
}

async function pedido(caminho, opcoes = {}) {
  const cabecalhos = { 'Content-Type': 'application/json', ...(opcoes.headers || {}) }
  const token = obterToken()
  if (token) cabecalhos.Authorization = `Bearer ${token}`

  let resposta
  try {
    resposta = await fetch(`${API_URL}${caminho}`, {
      ...opcoes,
      headers: cabecalhos,
    })
  } catch (erro) {
    throw new Error(`Não foi possível ligar ao servidor (${API_URL}). Confirma que o backend Flask está a correr.`)
  }

  const dados = await resposta.json().catch(() => ({}))

  // Sessão expirada ou inválida (não conta o próprio login, onde 401 = senha errada)
  if (resposta.status === 401 && caminho !== '/api/login') {
    avisarSessaoExpirada()
    throw new Error(dados.erro || 'A sessão terminou. Entra novamente.')
  }

  if (!resposta.ok) {
    throw new Error(dados.erro || 'Ocorreu um erro inesperado no servidor.')
  }
  return dados
}
export function verificarSaude() {
  return pedido('/api/saude')  
}
export async function iniciarSessao(utilizador, senha) {
  const dados = await pedido('/api/login', {
    method: 'POST',
    body: JSON.stringify({ utilizador, senha }),
  })
  guardarSessao(dados.token, dados.utilizador)
  return dados
}
export function validarSessao() {
  return pedido('/api/sessao')
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
export function marcarPresenca(foto) {
  return pedido('/api/presencas/marcar', {
    method: 'POST',
    body: JSON.stringify({ foto }),
  })
}
export function listarPresencas(de, ate) {
  const parametros = new URLSearchParams()
  if (de) parametros.set('de', de)
  if (ate) parametros.set('ate', ate)
  const texto = parametros.toString()
  return pedido(`/api/presencas${texto ? `?${texto}` : ''}`)
}
export function urlImagem(caminhoRelativo) {
  if (!caminhoRelativo) return ''
  return `${API_URL}${caminhoRelativo}`
}

// As fotos só podem ser pedidas com o cabeçalho Authorization, que o navegador
// não envia num <img src>. Por isso a imagem é descarregada com fetch (com o
// token no cabeçalho) e mostrada através de um endereço local (blob:). Assim o
// token nunca aparece no endereço da imagem, nem nos registos do servidor.
export function obterImagemProtegida(caminhoRelativo) {
  if (!caminhoRelativo) return Promise.reject(new Error('Imagem sem endereço.'))

  if (!cacheImagens.has(caminhoRelativo)) {
    const promessa = fetch(urlImagem(caminhoRelativo), {
      headers: { Authorization: `Bearer ${obterToken() || ''}` },
    })
      .then(async (resposta) => {
        if (resposta.status === 401) {
          avisarSessaoExpirada()
          throw new Error('A sessão terminou. Entra novamente.')
        }
        if (!resposta.ok) throw new Error('Imagem indisponível.')
        return URL.createObjectURL(await resposta.blob())
      })
      .catch((erro) => {
        cacheImagens.delete(caminhoRelativo)
        throw erro
      })
    cacheImagens.set(caminhoRelativo, promessa)
  }
  return cacheImagens.get(caminhoRelativo)
}