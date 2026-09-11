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
    <ul>
      {changes.map((c, i) => (
        <li key={`${i}`} onClick={() => onCite(c.change_type === "removed" ? c.from_accession : c.to_accession, c.label)}>
          {c.ticker} - {c.label} {c.change_type} {c.to_filing_date} {c.summary}
        </li>
      ))}
    </ul>
  );
}
