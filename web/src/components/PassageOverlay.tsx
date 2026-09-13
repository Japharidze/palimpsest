import { useEffect, useRef, useState } from "react";
import { getFacts, getSection, type Fact, type FilingSection } from "../api";
import { Overlay } from "./Overlay";
import { findQuote } from "../format";

const WINDOW = 15000;
const CONTEXT = 800;

export function PassageOverlay({
  accession,
  section,
  quote,
  onClose,
}: {
  accession: string;
  section?: string;
  quote?: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<FilingSection | null>(null);
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [full, setFull] = useState(false);
  const markRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setData(null);
    setFacts(null);
    setError(null);
    setFull(false);

    if (section) {
      getSection(accession, section, section)
        .then(setData)
        .catch((e) => setError(String(e)));
    } else {
      getFacts(accession).then(setFacts).catch((e) => setError(String(e)));
    }
  }, [accession, section]);

  // ---- what to show -------------------------------------------------- //

  let before = "";
  let match = "";
  let after = "";
  let truncated = false;

  if (data) {
    const content = data.content;
    const found = quote ? findQuote(content, quote) : null;

    if (found) {
      const [from, to] = found;
      const windowStart = full ? 0 : Math.max(0, from - CONTEXT);
      const windowEnd = full ? content.length : Math.min(content.length, to + CONTEXT);

      before = (windowStart > 0 ? "…" : "") + content.slice(windowStart, from);
      match = content.slice(from, to);
      after = content.slice(to, windowEnd) + (windowEnd < content.length ? "…" : "");
      truncated = !full && (windowStart > 0 || windowEnd < content.length);
    } else if (full) {
      before = content;
    } else {
      truncated = content.length > WINDOW;
      before = truncated ? content.slice(0, WINDOW) + "…" : content;
    }
  }

  return (
    <Overlay
      title={
        <>
          {accession} · {section ?? "facts"}
          {data && <a className="chip" href={`data:text/plain;charset=utf-8,${encodeURIComponent(data.content)}`} download={`${accession}-${section}.txt`}>download</a>}
        </>
      }
      onClose={onClose}
    >
      {error && <div>not found: {error}</div>}
      {!data && !facts && !error && <div>loading…</div>}

      {data && (
        <pre>
          {before}
          {match && <mark ref={markRef}>{match}</mark>}
          {after}
          {truncated && (
            <>
              {" "}
              <button type="button" className="more" onClick={() => setFull(true)}>
                show whole section
              </button>
            </>
          )}
        </pre>
      )}

      {facts && (
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>tag</th>
              <th>period</th>
              <th>value</th>
              <th>unit</th>
            </tr>
          </thead>
          <tbody>
            {facts.map((f, i) => (
              <tr key={i}>
                <td>{f.metric}</td>
                <td>{f.tag}</td>
                <td>{f.start_date ? `${f.start_date} → ${f.end_date}` : f.end_date}</td>
                <td>{f.value.toLocaleString()}</td>
                <td>{f.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Overlay>
  );
}
