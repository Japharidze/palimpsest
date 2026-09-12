import { useEffect, useRef } from "react";
import type { Entry } from "../types";
import { AnswerEntry, ErrorEntry, QuestionEntry, TraceEntry } from "./entries";

export function Transcript({ entries, onCite, busy }: {
  entries: Entry[];
  onCite: (accession: string, section?: string) => void;
  busy: boolean
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div className="transcript">
      {entries.map((e, i) => {
        switch (e.kind) {
          case "question": return <QuestionEntry key={i} text={e.text} />;
          case "trace": return <TraceEntry key={i} entry={e} />;
          case "answer": return <AnswerEntry key={i} entry={e} onCite={onCite} />;
          case "error": return <ErrorEntry key={i} text={e.text} />;
          default: return null;
        }
      })}
      {busy && <div className="thinking">thinking…</div>}
      <div ref={endRef} />
    </div>
  );
}
