const relativeFormatter = new Intl.RelativeTimeFormat("pl", { numeric: "auto" });
const dateFormatter = new Intl.DateTimeFormat("pl-PL", {
  dateStyle: "medium",
  timeStyle: "short",
});

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

export function timeAgo(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "—";
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      return relativeFormatter.format(Math.round(seconds / size), unit);
    }
  }
  return "przed chwilą";
}

export function formatDate(iso: string | null): string {
  return iso ? dateFormatter.format(new Date(iso)) : "—";
}

export type ScoreLevel = "very-high" | "high" | "medium" | "low";

export function scoreLevel(score: number): ScoreLevel {
  if (score >= 90) return "very-high";
  if (score >= 75) return "high";
  if (score >= 50) return "medium";
  return "low";
}

export const SCORE_LEVEL_LABEL: Record<ScoreLevel, string> = {
  "very-high": "Bardzo wysoki",
  high: "Wysoki",
  medium: "Średni",
  low: "Niski",
};
