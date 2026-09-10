import type { ToolCall, RecentChange, QuarterlyRow } from "./api";

export type Entry =
  | { kind: "question"; text: string }
  | { kind: "trace"; calls: ToolCall[]; latencyMs: number; citationsOk: boolean }
  | { kind: "answer"; text: string; citationProblems: string[] }
  | { kind: "change"; data: RecentChange }
  | { kind: "company"; ticker: string; name: string;
      metrics: QuarterlyRow[]; changes: RecentChange[] }
  | { kind: "error"; text: string };
