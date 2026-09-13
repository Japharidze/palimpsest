import { useEffect, useState } from "react";
import { getFacts, getSection, type Fact, type FilingSection } from "../api";
import { Overlay } from "./Overlay";


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
    <Overlay
      title={section ? `${accession} · ${section}` : `${accession} · facts`}
      onClose={onClose}
    >
      {error && <div>not found: {error}</div>}
      {!data && !facts && !error && <div>loading…</div>}

      {data && <pre>{data.content}</pre>}

      {facts && (
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>tag</th>
              <th>period</th>
              <th>value</th>
              <th>unit</th>
            </tr>
          </thead>
          <tbody>
            {facts.map((f, i) => (
              <tr key={i}>
                <td>{f.metric}</td>
                <td>{f.tag}</td>
                <td>{f.start_date ? `${f.start_date} → ${f.end_date}` : f.end_date}</td>
                <td>{f.value.toLocaleString()}</td>
                <td>{f.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Overlay>
  );
}
