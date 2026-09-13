import { useCallback, useEffect, useRef, useState } from 'react'

export function useCamera() {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [activa, setActiva] = useState(false)
  const [erro, setErro] = useState('')

  const iniciar = useCallback(async () => {
    if (streamRef.current) return
    setErro('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setActiva(true)
    } catch (err) {
      setErro('Não foi possível aceder à câmara: ' + err.message)
      setActiva(false)
    }
  }, [])

  const parar = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((faixa) => faixa.stop())
      streamRef.current = null
    }
    setActiva(false)
  }, [])

  const capturar = useCallback(() => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return null
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/png')
  }, [])

  useEffect(() => () => parar(), [parar])

  return { videoRef, activa, erro, iniciar, parar, capturar }
}
