import fixture from "./fixtures/ask.json";

export interface Company {
  ticker: string;
  name: string;
  period_end: string;
  margin_compression: boolean;
  inventory_buildup: boolean;
  receivables_buildup: boolean;
  roa_deterioration: boolean;
  short_runway: boolean;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  id: string;
  type: string;
}

export interface AskResponse {
  answer: string;
  citation_problems: string[];
  tool_calls: ToolCall[];
  latency_ms: number;
  conversation_id: string;
}

export interface RecentChange {
  label: string;
  change_type: string;
  from_accession: string;
  to_accession: string;
  from_filing_date: string;
  to_filing_date: string;
  similarity: number | null;
  summary: string | null;
  from_text: string | null;
  to_text: string | null;
}

export interface QuarterlyRow {
  period_end: string;
  source_accn: string | null;
  revenue: number | null;
  net_income: number | null;
  gross_margin_pct: number | null;
  roa_pct: number | null;
  roe_pct: number | null;
  revenue_growth_yoy_pct: number | null;
  inventory_growth_yoy_pct: number | null;
  receivables_growth_yoy_pct: number | null;
  runway_quarters: number | null;
  revenue_is_derived: boolean | null;
  flag_margin_compression: boolean;
  flag_inventory_buildup: boolean;
  flag_receivables_buildup: boolean;
  flag_roa_deterioration: boolean;
  flag_short_runway: boolean;
  }

export async function getCompanies(): Promise<Company[]> {
  const r = await fetch("/api/companies");
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

const MOCK = true; // TODO: false before deploy

export async function ask(question: string, conversationId?: string): Promise<AskResponse> {

  if (MOCK) {
    await new Promise((r) => setTimeout(r, 1500));
    return fixture as AskResponse
  }

  const r = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}
