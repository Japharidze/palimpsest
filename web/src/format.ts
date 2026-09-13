const CITE = /\[(\d{10}-\d{2}-\d{6}(?:\s*,\s*\d{10}-\d{2}-\d{6})*)\s*(?:\|\s*([a-z0-9_]+)\s*)?\]/g;

function norm(s: string): string {
  return s.replace(/[\s\u00a0]+/g, " ").trim();
}

function quoteBefore(text: string, at: number): string | undefined {
  const head = text.slice(Math.max(0, at - 2000), at);
  const quotes = head.match(/["“]([^"”]{25,})["”]/g);
  if (!quotes) return undefined;

  const last = quotes[quotes.length - 1];
  if (head.length - head.lastIndexOf(last) - last.length > 80) return undefined;

  return last.slice(1, -1);
}

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
  return text.replace(CITE, (_m, accns: string, section: string | undefined, offset: number) => {
    const quote = quoteBefore(text, offset);
    const q = quote ? `?q=${encodeURIComponent(quote)}` : "";

    return accns
      .split(/\s*,\s*/)
      .map((a) => `[¶](cite:${a.trim()}${section ? "/" + section : "/"}${q})`)
      .join(" ");
  });
}

/** Locate a quote in the content, tolerating whitespace differences. */
export function findQuote(content: string, quote: string): [number, number] | null {
  const direct = content.indexOf(quote);
  if (direct >= 0) return [direct, direct + quote.length];

  // fall back to matching on the first few words, normalised
  const head = norm(quote).split(" ").slice(0, 8).join(" ");
  if (head.length < 20) return null;

  const normContent = norm(content);
  const at = normContent.indexOf(head);
  if (at < 0) return null;

  // normalised index is close enough for a window; widen to be safe
  return [Math.max(0, at - 50), Math.min(content.length, at + quote.length + 50)];
}
