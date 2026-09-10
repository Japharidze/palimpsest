import { useState } from "react";
import { type Entry } from "./types.ts"
import { ask } from "./api";
import { Watchlist } from "./components/Watchlist";
import { Statusbar } from "./components/Statusbar.tsx";
import { Transcript } from "./components/Transcript.tsx";
import { Input } from "./components/Input.tsx";

function App() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [busy, setBusy] = useState<boolean>(false);

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

  return (
    <div className="layout">
      <Statusbar />
      <main>
        <Transcript entries={entries}/>
        <Input onSubmit={handleAsk} disabled={busy} />
      </main>
      <aside>
        <Watchlist />
      </aside>
    </div>
  );
}

export default App;
