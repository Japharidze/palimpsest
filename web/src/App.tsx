import { useState } from "react";
import { type Entry } from "./types.ts"
import { ask, getChanges, getMetrics, type QuarterlyRow } from "./api";
import { Watchlist } from "./components/Watchlist";
import { Statusbar } from "./components/Statusbar.tsx";
import { Transcript } from "./components/Transcript.tsx";
import { Input } from "./components/Input.tsx";
import { PassageOverlay } from "./components/PassageOverlay.tsx";
import { Feed } from "./components/Feed.tsx";

function App() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [busy, setBusy] = useState<boolean>(false);
  const [citation, setCitation] = useState<{ accession: string; section?: string } | null>(null);

  async function handleAsk(question: string) {
    setEntries((prev) => [...prev, { kind: "question", text: question }]);
    setBusy(true);

    try {
      const r = await ask(question, conversationId);
      setConversationId(r.conversation_id);
      setEntries((prev) => [
        ...prev,
        {
          kind: "trace",
          calls: r.tool_calls,
          latencyMs: r.latency_ms,
          citationsOk: r.citation_problems.length === 0,
        },
        { kind: "answer", text: r.answer, citationProblems: r.citation_problems },
      ]);
    } catch (e) {
      setEntries((prev) => [...prev, { kind: "error", text: String(e) }]);
    } finally {
      setBusy(false)
    }
  }

  async function handleCompany(ticker: string, name: string) {
    const [metrics, changes] = await Promise.all([
      getMetrics(ticker),
      getChanges(ticker, undefined, 5)
    ]);

    setEntries((prev) => [...prev, { kind: "company", ticker, name, metrics, changes }]);
  }

  return (
    <div className="layout">
      <Statusbar />
      <main>
        <Transcript entries={entries} onCite={(accession, section) => setCitation({ accession, section })} busy={busy} />
        <Input onSubmit={handleAsk} disabled={busy} />
      </main>
      <aside>
        <Watchlist onSelect={handleCompany} />
        <Feed onCite={(accession, section) => setCitation({ accession, section })} />
      </aside>
      {citation && (
        <PassageOverlay
          accession={citation.accession}
          section={citation.section}
          onClose={() => setCitation(null)}
        />
      )}
      <footer> Made by Japharidze </footer>
    </div>
  );
}

export default App;
