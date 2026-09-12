import { useEffect, useState } from "react";
import { getEvals, getMeta, type EvalResult, type Meta } from "../api";

const GITHUB = "https://github.com/Japharidze/palimpsest";

function compact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}

export function Statusbar({ onAbout }: { onAbout: () => void }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [evals, setEvals] = useState<EvalResult[] | null>(null);

  useEffect(() => {
    getMeta().then(setMeta).catch(() => { });
    getEvals().then(setEvals).catch(() => { });
  }, []);

  const passed = evals?.filter((e) => e.passed).length;

  return (
    <header className="statusbar">
      <span className="name">palimpsest</span>

      {meta && (
        <span className="corpus">
          {meta.corpus.companies} companies · {meta.corpus.filings} filings ·{" "}
          {compact(meta.corpus.facts)} facts · {compact(meta.corpus.chunks)} chunks
          {meta.corpus.latest_filing && ` · latest ${meta.corpus.latest_filing}`}
        </span>
      )}

      <span className="spacer" />

      {meta && <span className="models">{meta.agent_model}</span>}

      {evals && (
        <span className="evals">
          {passed}/{evals.length} evals
        </span>
      )}

      <button type="button" onClick={onAbout}>
        about
      </button>

      <a href={GITHUB} target="_blank" rel="noreferrer">
        github
      </a>
    </header>
  );
}
