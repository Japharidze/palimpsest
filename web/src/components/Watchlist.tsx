import { useEffect, useState } from "react";
import { getCompanies, type Company } from "../api";

function tidy(name: string): string {
  return name
    .replace(/\s+(CORP|INC|CO|LTD|PLC|NV|SA|AG)\.?$/i, "")
    .replace(/,$/, "")
    .replace(/\s*&\s*$/, "");
}

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
    <section className="watchlist">
      <h2>watchlist</h2>
      <ul>
        {companies.map((c) => (
          <li key={c.ticker} onClick={() => onSelect(c.ticker, c.name)}>
            <span className="ticker">{c.ticker}</span>
            <span className="name">{tidy(c.name)}</span>
            <span className="period">
              {c.period_end}
              {c.margin_compression && <span className="dot" title="margin compression" />}
              {c.inventory_buildup && <span className="dot" title="inventory buildup" />}
              {c.receivables_buildup && <span className="dot" title="receivables buildup" />}
              {c.roa_deterioration && <span className="dot" title="roa deterioration" />}
              {c.short_runway && <span className="dot" title="short runway" />}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
