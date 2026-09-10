import type { Entry } from "../types";
import { AnswerEntry, ErrorEntry, QuestionEntry, TraceEntry } from "./entries";

export function Transcript({ entries }: { entries: Entry[] }) {
  return (
    <div>
      {entries.map((e, i) => {
        switch (e.kind) {
          case "question": return <QuestionEntry key={i} text={e.text} />;
          case "trace":    return <TraceEntry key={i} entry={e} />;
          case "answer":   return <AnswerEntry key={i} entry={e} />;
          case "error":    return <ErrorEntry key={i} text={e.text} />;
          default: return null;
        }
      })}
    </div>
  );
}
