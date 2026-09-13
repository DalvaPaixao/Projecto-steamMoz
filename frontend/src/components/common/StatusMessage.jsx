export default function StatusMessage({ tipo, mensagem }) {
  if (!mensagem) return null
  return <div className={`status status-${tipo}`}>{mensagem}</div>
}
