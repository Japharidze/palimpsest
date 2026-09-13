import { Overlay } from "./Overlay"

export function AboutOverlay({ onClose }: { onClose: () => void }) {
  return (
    <Overlay title="about" onClose={onClose}>
      <p>
        A palimpsest is a manuscript scraped clean and written over, with the
        earlier text still showing through. That is what a quarterly filing
        is: this quarter's risk factors are last quarter's, reworded.
        Palimpsest reads what changed.
      </p>

      <p>
        It tracks a watchlist of companies, reports what moved between their
        filings, and cites the exact passage behind every claim. Numbers come
        from XBRL and deterministic code. A language model is used only to
        read prose, and every claim it makes is checked against the filing
        before the answer is returned.
      </p>

      <img src="/pipeline.svg" alt="pipeline" />

      <h3>Data</h3>
      <p>
        A throttled EDGAR client fetches filings and XBRL facts; every
        response is written to storage before it is parsed, so a parser change
        can be replayed without refetching. dbt turns raw facts into per
        quarter and per year metrics with ratios, growth rates and red-flag
        columns. Every figure carries the accession number of the filing that
        reported it.
      </p>

      <h3>Text</h3>
      <p>
        Filing documents are split into sections, then compared paragraph by
        paragraph against the previous filing: unchanged text is skipped by
        hash, and the rest is matched by similarity to separate rewordings
        from genuine additions and removals. Only the changed paragraphs are
        sent to a model, one at a time, for a one-sentence description.
        Finding the change is mechanical; saying what it means is not.
      </p>

      <h3>Agent</h3>
      <p>
        A LangGraph state machine with tools over the warehouse — passage
        search, company metrics, recent changes. The model never touches the
        database: it emits a tool name and arguments, and the calling code
        holds the only mapping to behaviour. Answers are checked afterwards,
        mechanically: every cited filing must exist, every cited section must
        exist in it, and every quoted passage must appear verbatim in the text
        it claims to come from.
      </p>

      <h3>Interface</h3>
      <p>
        FastAPI over the agent and the warehouse; React over that. Citations
        in an answer are clickable — a passage citation opens the section it
        came from, and a figure opens the XBRL facts the filing reported, with
        the tag, the period and the value as filed.
      </p>

      <h3>Evaluation</h3>
      <p>
        A golden set of questions covers point lookups, comparisons, change
        detection, attribution, absence and cross-company queries. Each
        question asserts what the answer must contain, which tools must be
        called, and whether every citation resolves. The absence questions
        matter most: they ask about disclosures the filings do not contain, so
        a fabricated answer fails visibly.
      </p>

      <p className="warn">
        Research tool, not investment advice. All data comes from the SEC's
        public EDGAR system.
      </p>
    </Overlay>
  );
}
