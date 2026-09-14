import { useEffect, useState } from "react";
import { getEvals, getMeta, type EvalResult, type Meta } from "../api";
import { Popover } from "./Popover";

const GITHUB = "https://github.com/Japharidze/palimpsest";

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}

export function Statusbar({ onAbout, onMenu }: { onAbout: () => void; onMenu: () => void }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [evals, setEvals] = useState<EvalResult[] | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => { });
    getEvals().then(setEvals).catch(() => { });
  }, []);

  const passed = evals?.filter((e) => e.passed).length ?? 0;

  const byShape = new Map<string, { passed: number; total: number }>();
  for (const e of evals ?? []) {
    const s = byShape.get(e.shape) ?? { passed: 0, total: 0 };
    s.total += 1;
    if (e.passed) s.passed += 1;
    byShape.set(e.shape, s);
  }

  return (
    <header className="statusbar">
      <a className="name" href={GITHUB} target="_blank" rel="noreferrer">
        palimpsest
      </a>

      {meta && (
        <span className="corpus">
          {compact(meta.corpus.chunks)} chunks · {compact(meta.corpus.facts)} facts ·{" "}
          {meta.corpus.companies} companies · {meta.corpus.filings} filings
          {meta.corpus.latest_filing && ` · latest ${meta.corpus.latest_filing}`}
        </span>
      )}

      <span className="spacer" />

      {meta && (
        <Popover label={meta.agent_model}>
          <table className="models">
            <tbody>
              <tr>
                <td>agent</td>
                <td className="provider">{meta.agent_provider}</td>
                <td>{meta.agent_model}</td>
              </tr>
              <tr>
                <td>summarizer</td>
                <td className="provider">{meta.summarizer_provider}</td>
                <td>{meta.summarizer_model}</td>
              </tr>
              <tr>
                <td>embedding</td>
                <td className="provider">{meta.embedding_provider}</td>
                <td>{meta.embedding_model}</td>
              </tr>
            </tbody>
          </table>
        </Popover>
      )}

      {evals && (
        <Popover label={`${passed}/${evals.length} evals`}>
          <table className="results">
            {meta && (
              <thead>
                <tr>
                  <th colSpan={3}>{meta.agent_model}</th>
                </tr>
              </thead>
            )}
            <tbody>
              {evals.map((e) => (
                <tr key={e.id}>
                  <td><span className={e.passed ? "dot ok" : "dot fail"} /></td>
                  <td>{e.id.replace(/_/g, " ")}</td>
                  <td className="shape">{e.shape.replace(/_/g, " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Popover>
      )}

      <button type="button" onClick={onAbout}>
        about
      </button>

      <button type="button" className="menu" onClick={onMenu} aria-label="menu">
        ☰
      </button>

      <a href={GITHUB} target="_blank" rel="noreferrer" aria-label="github">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor">
          <path d="M10.226 17.284c-2.965-.36-5.054-2.493-5.054-5.256 0-1.123.404-2.3361.078-3.144-.292-.741-.247-2.314.09-2.965.898-.112 2.111.36 2.83 1.01.853-.269 1.752-.404 2.853-.404 1.1 0 1.999.135 2.807.382.696-.629 1.932-1.1 2.83-.988.315.606.36 2.179.067 2.942.72.854 1.101 2 1.101 3.167 0 2.763-2.089 4.852-5.098 5.234.763.494 1.28 1.572 1.28 2.807v2.336c0 .674.561 1.056 1.235.786 4.066-1.55 7.255-5.615 7.255-10.646C23.5 6.188 18.334 1 11.978 1 5.62 1 .5 6.188.5 12.545c0 4.986 3.167 9.12 7.435 10.669.606.225 1.19-.18 1.19-.786V20.63a2.9 2.9 0 0 1-1.078.224c-1.483 0-2.359-.808-2.987-2.313-.247-.607-.517-.966-1.034-1.033-.27-.023-.359-.135-.359-.27 0-.27.45-.471.898-.471.652 0 1.213.404 1.797 1.235.45.651.921.943 1.483.943.561 0 .92-.202 1.437-.719.382-.381.674-.718.944-.943"></path>
        </svg>
      </a>
    </header>
  );
}
