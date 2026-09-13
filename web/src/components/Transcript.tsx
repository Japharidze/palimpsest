import { useEffect, useRef } from "react";
import type { Entry } from "../types";
import { AnswerEntry, CompanyEntry, ErrorEntry, QuestionEntry, TraceEntry } from "./entries";

const EXAMPLES = [
  "Has NVIDIA's gross margin recovered from its 2025 dip?",
  "What risk factors did Reddit add in its most recent 10-Q?",
  "Why did Coca-Cola's operating income change last quarter?",
];

export function Transcript({ entries, onCite, onPick, busy }: {
  entries: Entry[];
  onCite: (accession: string, section?: string, quote?: string) => void;
  onPick: (question: string) => void;
  busy: boolean
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div className="transcript empty">
        <div className="placeholder">
          <p className="lead">Ask about a filing, or pick a company from the watchlist.</p>
          <p className="hint">Examples</p>
          <ul>
            {EXAMPLES.map((q) => (
              <li key={q} onClick={() => onPick(q)}>
                {q}
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript">
      {entries.map((e, i) => {
        switch (e.kind) {
          case "question": return <QuestionEntry key={i} text={e.text} />;
          case "trace": return <TraceEntry key={i} entry={e} />;
          case "answer": return <AnswerEntry key={i} entry={e} onCite={onCite} />;
          case "error": return <ErrorEntry key={i} text={e.text} />;
          case "company": return <CompanyEntry key={i} entry={e} onCite={onCite} />;
          default: return null;
        }
      })}
      {busy && <div className="thinking">thinking…</div>}
      <div ref={endRef} />
    </div>
  );
}
