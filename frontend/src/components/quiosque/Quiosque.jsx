import { useCallback, useEffect, useRef, useState } from 'react'
import { useCamera } from '../../hooks/useCamera.js'
import { API_URL } from '../../api.js'

// Ajustes (em milissegundos)
const INTERVALO_MS = 3000          // de quanto em quanto tempo tenta reconhecer um rosto
const MOSTRAR_MS = 4000            // quanto tempo a mensagem fica no ecrã
const PAUSA_APOS_MARCAR_MS = 6000  // pausa depois de reconhecer alguém
const LARGURA_ENVIO = 960          // largura máxima da foto enviada ao servidor

const ESPERA = { tipo: 'espera', titulo: 'Aproxima-te da câmara', detalhe: 'Fica de frente, com o rosto visível.' }
const CORES = { espera: 'rgba(15, 23, 42, 0.85)', sucesso: '#16a34a', aviso: '#d97706', erro: '#dc2626' }

// O endereço é  /#marcar?chave=XXXX  (o que vem depois de # nunca chega aos registos do servidor)
function lerChave() {
  const hash = window.location.hash
  const i = hash.indexOf('?')
  if (i === -1) return ''
  return new URLSearchParams(hash.slice(i + 1)).get('chave') || ''
}

function capturarJpeg(video) {
  if (!video || !video.videoWidth) return null
  const escala = Math.min(1, LARGURA_ENVIO / video.videoWidth)
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(video.videoWidth * escala)
  canvas.height = Math.round(video.videoHeight * escala)
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/jpeg', 0.85)
}

async function enviarMarcacao(foto, chave) {
  let resposta
  try {
    resposta = await fetch(`${API_URL}/api/presencas/marcar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Quiosque-Chave': chave },
      body: JSON.stringify({ foto }),
    })
  } catch {
    return { status: 0, dados: {} }
  }
  const dados = await resposta.json().catch(() => ({}))
  return { status: resposta.status, dados }
}

export default function Quiosque() {
  const chave = lerChave()
  const { videoRef, erro: erroCamera, iniciar } = useCamera()
  const meuVideo = useRef(null)
  const ligarVideo = useCallback((elemento) => {
    meuVideo.current = elemento
    videoRef(elemento)
  }, [videoRef])

  const [ecra, setEcra] = useState(ESPERA)
  const [hora, setHora] = useState(new Date())
  const ocupado = useRef(false)
  const pausaAte = useRef(0)
  const temporizador = useRef(null)

  const mostrar = useCallback((novo, ms = MOSTRAR_MS) => {
    setEcra(novo)
    clearTimeout(temporizador.current)
    temporizador.current = setTimeout(() => setEcra(ESPERA), ms)
  }, [])

  // Liga a câmara assim que a página abre
  useEffect(() => {
    if (chave) iniciar()
  }, [chave, iniciar])

  // Relógio no topo
  useEffect(() => {
    const id = setInterval(() => setHora(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  // Impede o ecrã de apagar
  useEffect(() => {
    let bloqueio = null
    async function pedir() {
      try {
        bloqueio = await navigator.wakeLock?.request('screen')
      } catch {
        // sem suporte neste navegador
      }
    }
    pedir()
    const aoVoltar = () => {
      if (document.visibilityState === 'visible') pedir()
    }
    document.addEventListener('visibilitychange', aoVoltar)
    return () => {
      document.removeEventListener('visibilitychange', aoVoltar)
      bloqueio?.release?.()
      clearTimeout(temporizador.current)
    }
  }, [])

  const tentar = useCallback(async () => {
    if (ocupado.current || Date.now() < pausaAte.current) return
    const foto = capturarJpeg(meuVideo.current)
    if (!foto) return

    ocupado.current = true
    try {
      const { status, dados } = await enviarMarcacao(foto, chave)
      const agora = Date.now()

      if (status === 0) {
        mostrar({ tipo: 'erro', titulo: 'Sem ligação ao servidor', detalhe: 'A tentar de novo...' }, 3000)
        return
      }
      if (status === 401) {
        pausaAte.current = agora + 30000
        mostrar({ tipo: 'erro', titulo: 'Chave inválida', detalhe: 'Confirma o endereço do link com o administrador.' }, 30000)
        return
      }
      if (status === 201 && dados.registado) {
        pausaAte.current = agora + PAUSA_APOS_MARCAR_MS
        const rotulo = dados.tipo === 'entrada' ? 'Entrada registada' : 'Saída registada'
        mostrar({ tipo: 'sucesso', titulo: rotulo, detalhe: `${dados.funcionario.nome} · ${dados.hora}` })
        return
      }
      if (status === 200 && dados.registado === false) {
        pausaAte.current = agora + 8000
        mostrar({ tipo: 'aviso', titulo: 'Já registado', detalhe: dados.mensagem })
        return
      }
      if (status === 404 && dados.encontrado === false) {
        pausaAte.current = agora + 3000
        mostrar({ tipo: 'erro', titulo: 'Rosto não reconhecido', detalhe: 'Tenta de novo, de frente para a câmara.' }, 3000)
        return
      }
      if (status === 422) {
        // Sem rosto na imagem: continua à espera em silêncio. Só avisa se houver mais do que um.
        if ((dados.erro || '').includes('mais do que um rosto')) {
          mostrar({ tipo: 'aviso', titulo: 'Uma pessoa de cada vez', detalhe: 'Só um rosto deve aparecer na câmara.' }, 3000)
        }
        return
      }
      mostrar({ tipo: 'erro', titulo: 'Ocorreu um erro', detalhe: dados.erro || 'Tenta novamente.' }, 3000)
    } finally {
      ocupado.current = false
    }
  }, [chave, mostrar])

  useEffect(() => {
    if (!chave) return undefined
    const id = setInterval(tentar, INTERVALO_MS)
    return () => clearInterval(id)
  }, [chave, tentar])

  if (!chave) {
    return (
      <div style={estilos.pagina}>
        <div style={{ ...estilos.painel, position: 'static', background: CORES.erro }}>
          <div style={estilos.titulo}>Link incompleto</div>
          <div style={estilos.detalhe}>Falta a chave no endereço. Pede o link completo ao administrador.</div>
        </div>
      </div>
    )
  }

  const painel = erroCamera
    ? { tipo: 'erro', titulo: 'Câmara indisponível', detalhe: erroCamera }
    : ecra

  return (
    <div style={estilos.pagina} onDoubleClick={() => document.documentElement.requestFullscreen?.()}>
      <div style={estilos.topo}>
        <div style={estilos.marca}>
          <img src="/logo.png" alt="" height="40" style={{ marginRight: 12, verticalAlign: 'middle' }} />
          ISDB · Marcação de Presença
        </div>
        <div style={estilos.relogio}>{hora.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })}</div>
      </div>

      <div style={estilos.palco}>
        <video ref={ligarVideo} autoPlay playsInline muted style={estilos.video} />
        <div style={{ ...estilos.painel, background: CORES[painel.tipo] }}>
          <div style={estilos.titulo}>{painel.titulo}</div>
          {painel.detalhe && <div style={estilos.detalhe}>{painel.detalhe}</div>}
        </div>
      </div>
    </div>
  )
}

const estilos = {
  pagina: { position: 'fixed', inset: 0, background: '#0f172a', color: '#fff', display: 'flex', flexDirection: 'column', fontFamily: 'system-ui, sans-serif' },
  topo: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 24px', background: 'rgba(0, 0, 0, 0.35)' },
  marca: { fontSize: '1.4rem', fontWeight: 700 },
  relogio: { fontSize: '1.8rem', fontWeight: 700 },
  palco: { flex: 1, position: 'relative', overflow: 'hidden' },
  video: { width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' },
  painel: { position: 'absolute', left: 0, right: 0, bottom: 0, padding: '28px 24px', textAlign: 'center', transition: 'background 0.2s' },
  titulo: { fontSize: 'clamp(1.8rem, 5vw, 3.5rem)', fontWeight: 800 },
  detalhe: { fontSize: 'clamp(1.1rem, 2.6vw, 1.8rem)', marginTop: 8, opacity: 0.95 },
}