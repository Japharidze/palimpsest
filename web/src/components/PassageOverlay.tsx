import { useEffect, useState } from "react";
import { getFacts, getSection, type Fact, type FilingSection } from "../api";


export function PassageOverlay({ accession, section, onClose }: {
  accession: string;
  section?: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<FilingSection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facts, setFacts] = useState<Fact[] | null>(null);

useEffect(() => {
  setData(null);
  setFacts(null);
  setError(null);

  if (section) {
    getSection(accession, section, section).then(setData).catch((e) => setError(String(e)));
  } else {
    getFacts(accession).then(setFacts).catch((e) => setError(String(e)));
  }
}, [accession, section]);

  return (
    <div className="overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()}>
        <header>{accession} · {section ?? "—"} <button onClick={onClose}>×</button></header>
        {error && <div>not found: {error}</div>}
        {!data && !error && <div>loading…</div>}
        {data && <pre>{data.content}</pre>}
      </div>
    </div>
  );
}
