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

export async function getCompanies(): Promise<Company[]> {
  const r = await fetch("/api/companies");
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}
