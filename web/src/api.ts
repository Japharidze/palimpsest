import fixture from "./fixtures/ask.json";

const MOCK = true;  // TODO: make false before deploy;

// ---------------------------------------------------------------- types

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

export interface FeedChange {
  ticker: string;
  company_name: string;
  cik: string;
  label: string;
  change_type: string;
  to_filing_date: string;
  to_accession: string;
  from_accession: string;
  similarity: number | null;
  summary: string;
  importance: number;
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

export interface FilingSection {
  accession: string;
  section: string;
  section_label: string | null;
  content: string;
  start_offset: number;
  end_offset: number;
  confidence: number;
}

export interface Fact {
  tag: string;
  unit: string;
  start_date: string | null;
  end_date: string;
  duration: number | null;
  value: number;
  filed: string;
  metric: string;
}

// ------------------------------------------------------------- internals

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

// ------------------------------------------------------------- endpoints

export async function getCompanies(): Promise<Company[]> {
  return get<Company[]>("/api/companies");
}

export async function getMetrics(
  ticker: string,
  since?: string,
  until?: string,
): Promise<QuarterlyRow[]> {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (until) params.set("until", until);
  return get<QuarterlyRow[]>(`/api/companies/${ticker}/metrics?${params}`);
}

export async function getChanges(
  ticker: string,
  section?: string,
  limit = 20,
): Promise<RecentChange[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (section) params.set("section", section);
  return get<RecentChange[]>(`/api/companies/${ticker}/changes?${params}`);
}

export async function getFeed(limit = 20): Promise<FeedChange[]> {
  return get<FeedChange[]>(`/api/companies/changes?limit=${limit}`);
}

export async function getSection(
  accession: string,
  section?: string,
  label?: string,
): Promise<FilingSection> {
  const params = new URLSearchParams();
  if (section) params.set("section", section);
  if (label) params.set("section_label", label);
  return get<FilingSection>(`/api/filings/${accession}?${params}`);
}

export async function getFacts(accession: string): Promise<Fact[]> {
  return get<Fact[]>(`/api/filings/${accession}/facts`);
}

export async function getEvals(): Promise<unknown> {
  return get<unknown>("/api/evals");
}

export async function ask(
  question: string,
  conversationId?: string,
): Promise<AskResponse> {
  if (MOCK) {
    await new Promise((r) => setTimeout(r, 1500));
    return fixture as AskResponse;
  }

  const r = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
