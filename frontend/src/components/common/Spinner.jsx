export default function Spinner({ label }) {
  return (
    <span className="spinner-inline">
      <span className="spinner" aria-hidden="true" />
      {label && <span>{label}</span>}
    </span>
  )
}
