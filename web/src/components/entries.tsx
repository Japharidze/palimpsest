import ReactMarkdown from "react-markdown";
import type { Entry } from "../types";

const CITE = /\[(\d{10}-\d{2}-\d{6}(?:\s*,\s*\d{10}-\d{2}-\d{6})*)\s*(?:\|\s*([a-z0-9_]+)\s*)?\]/g;

function linkify(text: string): string {
  return text.replace(CITE, (_m, accns: string, section?: string) =>
    accns
      .split(/\s*,\s*/)
      .map((a) => `[${a.slice(-6)}](cite:${a}${section ? "/" + section : ""})`)
      .join(" ")
  );
}

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

export function AnswerEntry({ entry, onCite }: {
  entry: Extract<Entry, { kind: "answer" }>;
  onCite: (accession: string, section?: string) => void;
}) {
  return (
    <div className="answer">
      <ReactMarkdown
        urlTransform={(url) => url}
        components={{
          a: ({ href, children }) => {
            if (!href?.startsWith("cite:")) return <a href={href}>{children}</a>;
            const [accession, section] = href.slice(5).split("/");
            return (
              <button type="button" className="chip" onClick={() => onCite(accession, section)}>
                {children}
              </button>
            );
          },
        }}
      >
        {linkify(entry.text)}
      </ReactMarkdown>
      {entry.citationProblems.length > 0 && (
        <div className="warn">{entry.citationProblems.join("; ")}</div>
      )}
    </div>
  );
}

export function ErrorEntry({ text }: { text: string }) {
  return <p>{text}</p>
}
