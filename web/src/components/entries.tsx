import ReactMarkdown from "react-markdown";
import type { Entry } from "../types";
import { daysSince, linkify, tidy } from "../format";

const STALE_DAYS = 200;

export function QuestionEntry({ text }: { text: string }) {
  return (
    <p className="question">
      <span className="prompt">&gt;</span> {text}
    </p>
  );
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

export function CompanyEntry({
  entry,
  onCite,
}: {
  entry: Extract<Entry, { kind: "company" }>;
  onCite: (accession: string, section?: string) => void;
}) {
  const latest = entry.metrics[0];
  const stale = !latest || daysSince(latest.period_end) > STALE_DAYS;
 
  const flags = latest
    ? Object.entries(latest)
        .filter(([k, v]) => k.startsWith("flag_") && v === true)
        .map(([k]) => k.replace("flag_", "").replace(/_/g, " "))
    : [];
 
  return (
    <div className="company">
      <header>
        {entry.ticker} · {tidy(entry.name)}
      </header>
 
      {stale ? (
        <p className="note">
          No recent quarterly metrics. Foreign private issuers file an annual
          report and no quarterly ones, so their figures appear in the yearly
          tables instead.
          {latest && ` Most recent period on file: ${latest.period_end}.`}
        </p>
      ) : (
        <>
          <div className="period">
            quarter ending {latest.period_end}
            {latest.source_accn && (
              <button
                type="button"
                className="chip"
                onClick={() => onCite(latest.source_accn!)}
              >
                {latest.source_accn.slice(-6)}
              </button>
            )}
          </div>
 
          <table>
            <tbody>
              <tr>
                <td>revenue</td>
                <td>{latest.revenue?.toLocaleString() ?? "—"}</td>
              </tr>
              <tr>
                <td>net income</td>
                <td>{latest.net_income?.toLocaleString() ?? "—"}</td>
              </tr>
              <tr>
                <td>gross margin</td>
                <td>
                  {latest.gross_margin_pct != null
                    ? `${latest.gross_margin_pct}%`
                    : "—"}
                </td>
              </tr>
              <tr>
                <td>roe</td>
                <td>{latest.roe_pct != null ? `${latest.roe_pct}%` : "—"}</td>
              </tr>
              <tr>
                <td>revenue growth yoy</td>
                <td>
                  {latest.revenue_growth_yoy_pct != null
                    ? `${latest.revenue_growth_yoy_pct}%`
                    : "—"}
                </td>
              </tr>
            </tbody>
          </table>
 
          {flags.length > 0 && <div className="flags">{flags.join(" · ")}</div>}
        </>
      )}
 
      {entry.changes.length > 0 && (
        <ul className="changes">
          {entry.changes.map((c, i) => (
            <li
              key={i}
              className={c.change_type}
              onClick={() =>
                onCite(
                  c.change_type === "removed" ? c.from_accession : c.to_accession,
                  c.label,
                )
              }
            >
              <div className="meta">
                {c.label} · {c.to_filing_date}
              </div>
              {c.summary && <div className="summary">{c.summary}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
