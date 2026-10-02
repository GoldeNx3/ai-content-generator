import type { ResearchSource } from "@/types/api";

export function sourceLabel(source: ResearchSource): string {
  return source.publisher || hostname(source.url);
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Publisher plus a short title, so two pages from the same site are distinguishable. */
export function citationLabel(source: ResearchSource, maxTitle = 48): string {
  const title = source.title?.trim();
  if (!title) return sourceLabel(source);
  const short = title.length > maxTitle ? `${title.slice(0, maxTitle - 1)}…` : title;
  return `${sourceLabel(source)} · ${short}`;
}
