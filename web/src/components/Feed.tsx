import { useEffect, useState } from "react";
import { getFeed, type FeedChange } from "../api";

export function Feed({ onCite }: { onCite: (accession: string, section?: string) => void; }) {
  const [changes, setChanges] = useState<FeedChange[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFeed()
      .then(setChanges)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div>failed to load {error}</div>

  return (
    <section className="feed">
      <h2>recent changes</h2>
      <ul>
        {changes.map((c, i) => (
          <li className={c.change_type} key={`${i}`} onClick={() => onCite(c.change_type === "removed" ? c.from_accession : c.to_accession, c.label)}>
            <span className="marker" />
            <span className="meta">{c.ticker} · {c.label} · {c.to_filing_date}</span>
            <span className="summary">{c.summary}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
