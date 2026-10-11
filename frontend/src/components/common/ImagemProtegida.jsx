import { useEffect, useState } from 'react'
import { obterImagemProtegida } from '../../api.js'

// Mostra uma foto guardada no servidor (que exige login). Enquanto a foto
// carrega — ou se falhar — aparece um quadrado cinzento.
export default function ImagemProtegida({ caminho, alt, ...resto }) {
  const [src, setSrc] = useState('')

  useEffect(() => {
    let cancelado = false
    setSrc('')
    if (!caminho) return undefined
    obterImagemProtegida(caminho)
      .then((url) => {
        if (!cancelado) setSrc(url)
      })
      .catch(() => {
        if (!cancelado) setSrc('')
      })
    return () => {
      cancelado = true
    }
  }, [caminho])

  if (!src) return <span className="img-placeholder" role="img" aria-label={alt} />
  return <img src={src} alt={alt} {...resto} />
}