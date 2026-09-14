import { useState } from "react";
import { type Entry } from "./types.ts"
import { ask, getChanges, getMetrics } from "./api";
import { Watchlist } from "./components/Watchlist";
import { Statusbar } from "./components/Statusbar.tsx";
import { Transcript } from "./components/Transcript.tsx";
import { Input } from "./components/Input.tsx";
import { PassageOverlay } from "./components/PassageOverlay.tsx";
import { Feed } from "./components/Feed.tsx";
import { AboutOverlay } from "./components/AboutOverlay.tsx";

function App() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [busy, setBusy] = useState<boolean>(false);
  const [citation, setCitation] = useState<{ accession: string; section?: string; quote?: string } | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [draft, setDraft] = useState<string>("");
  const [navOpen, setNavOpen] = useState<boolean>(false)

  function handleCite(accession: string, section?: string, quote?: string) {
    setCitation({ accession, section, quote })
    setNavOpen(false);
  }

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
      setDraft("");
    }
  }

  async function handleCompany(ticker: string, name: string) {
    const [metrics, changes] = await Promise.all([
      getMetrics(ticker),
      getChanges(ticker, undefined, 5)
    ]);

    setEntries((prev) => [...prev, { kind: "company", ticker, name, metrics, changes }]);
    setNavOpen(false);
  }

  return (
    <div className="layout">
      <Statusbar onAbout={() => setAboutOpen(true)} onMenu={() => setNavOpen((o) => !o)} />
      <main>
        <h2>conversation</h2>
        <Transcript entries={entries} onCite={handleCite} onPick={setDraft} busy={busy} />
        <Input value={draft} onChange={setDraft} onSubmit={handleAsk} disabled={busy} />
      </main>
      {navOpen && <div className="scrim" onClick={() => setNavOpen(false)} />}
      <aside className={navOpen ? "open" : undefined}>
        <Watchlist onSelect={handleCompany} />
        <Feed onCite={handleCite} />
      </aside>
      {citation && (
        <PassageOverlay
          accession={citation.accession}
          section={citation.section}
          quote={citation.quote}
          onClose={() => setCitation(null)}
        />
      )}
      {aboutOpen && <AboutOverlay onClose={() => setAboutOpen(false)} />}
    </div>
  );
}

export default App;
