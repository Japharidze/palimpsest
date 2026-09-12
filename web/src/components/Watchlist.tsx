import { useEffect, useState } from "react";
import { getCompanies, type Company } from "../api";

export function Watchlist({ onSelect }: { onSelect: (ticker: string, name: string) => void; }) {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanies()
      .then(setCompanies)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div>failed to load: {error}</div>

  return (
    <ul>
      {companies.map((c) => (
        <li key={c.ticker} onClick={() => onSelect(c.ticker, c.name)}>
          {c.ticker.split("; ")[0]} {c.name} {c.period_end}
        </li>
      ))}
    </ul>
  );
}
