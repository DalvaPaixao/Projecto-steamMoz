import { useCallback, useEffect, useRef, useState } from 'react'

export function useCamera() {
  const elementoVideo = useRef(null)
  const streamRef = useRef(null)
  const [activa, setActiva] = useState(false)
  const [erro, setErro] = useState('')

  // "ref" para o <video> (usa-se como  ref={videoRef}): sempre que o elemento
  // é (re)criado — por exemplo depois de "Nova captura" — liga-lhe a câmara
  // que já está activa. Sem isto, o vídeo ficava preto na segunda captura.
  const videoRef = useCallback((elemento) => {
    elementoVideo.current = elemento
    if (elemento && streamRef.current) {
      elemento.srcObject = streamRef.current
    }
  }, [])

  const iniciar = useCallback(async () => {
    if (streamRef.current) return
    setErro('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      streamRef.current = stream
      if (elementoVideo.current) {
        elementoVideo.current.srcObject = stream
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
    if (elementoVideo.current) {
      elementoVideo.current.srcObject = null
    }
    setActiva(false)
  }, [])

  const capturar = useCallback(() => {
    const video = elementoVideo.current
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