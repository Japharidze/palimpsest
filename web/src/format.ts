const CITE = /\[(\d{10}-\d{2}-\d{6}(?:\s*,\s*\d{10}-\d{2}-\d{6})*)\s*(?:\|\s*([a-z0-9_]+)\s*)?\]/g;

export function tidy(name: string): string {
  return name
    .replace(/\s+(CORP|INC|CO|LTD|PLC|NV|SA|AG)\.?$/i, "")
    .replace(/,$/, "")
    .replace(/\s*&\s*$/, "");
}

export function daysSince(iso: string): number {
  return (Date.now() - new Date(iso).getTime()) / 86_400_000;
}

export function linkify(text: string): string {
  return text.replace(CITE, (_m, accns: string, section?: string) =>
    accns
      .split(/\s*,\s*/)
      .map((a) => `[${a.slice(-6)}](cite:${a}${section ? "/" + section : ""})`)
      .join(" ")
  );
}
