export function AboutOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <header>
          about <button onClick={onClose}>×</button>
        </header>
        <p>Palimpsest reads SEC filings and reports what changed.</p>
      </div>
    </div>
  );
}
