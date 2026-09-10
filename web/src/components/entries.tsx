import ReactMarkdown from "react-markdown";
import type { Entry } from "../types";

export function QuestionEntry({ text }: { text: string }) {
  return <p>&gt; {text}</p>;
}

export function TraceEntry({ entry }: { entry: Extract<Entry, { kind: "trace" }> }) {
  return (
    <div className="trace">
      {entry.calls.map((c, i) => (
        <div key={i}>{c.name} {JSON.stringify(c.args)}</div>
      ))}
      <div>
        {entry.calls.length} tools · {(entry.latencyMs / 1000).toFixed(1)}s ·{" "}
        {entry.citationsOk ? "citations ok" : "citation problems"}
      </div>
    </div>
  );
}

export function AnswerEntry({ entry }: { entry: Extract<Entry, { kind: "answer" }> }) {
  return (
    <div className="answer">
      <ReactMarkdown>{entry.text}</ReactMarkdown>
      {entry.citationProblems.length > 0 && (
        <div className="warn">{entry.citationProblems.join("; ")}</div>
      )}
    </div>
  );
}

export function ErrorEntry({ text }: { text: string }) {
  return <p>{text}</p>
}
