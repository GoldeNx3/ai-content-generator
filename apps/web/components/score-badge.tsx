import { cn } from "@/lib/utils";
import { SCORE_LEVEL_LABEL, scoreLevel, type ScoreLevel } from "@/lib/format";

const LEVEL_STYLES: Record<ScoreLevel, string> = {
  "very-high": "bg-emerald-600 text-white ring-emerald-700",
  high: "bg-emerald-100 text-emerald-900 ring-emerald-300",
  medium: "bg-amber-100 text-amber-900 ring-amber-300",
  low: "bg-zinc-100 text-zinc-500 ring-zinc-200",
};

interface ScoreBadgeProps {
  score: number | null;
  size?: "sm" | "lg";
}

export function ScoreBadge({ score, size = "sm" }: ScoreBadgeProps) {
  const dimensions = size === "lg" ? "size-16 text-2xl rounded-xl" : "size-9 text-sm rounded-md";

  if (score === null) {
    return (
      <span
        title="Jeszcze nie oceniono"
        className={cn(
          "inline-flex items-center justify-center font-mono text-zinc-400 ring-1 ring-dashed ring-zinc-300",
          dimensions,
        )}
      >
        —
      </span>
    );
  }

  const level = scoreLevel(score);
  return (
    <span
      title={`${SCORE_LEVEL_LABEL[level]} (${score}/100)`}
      className={cn(
        "inline-flex items-center justify-center font-mono font-semibold tabular-nums ring-1",
        LEVEL_STYLES[level],
        dimensions,
      )}
    >
      {score}
    </span>
  );
}

export function ScoreBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono font-medium tabular-nums">{value ?? "—"}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
        {value !== null && (
          <div
            className={cn(
              "h-full rounded-full",
              {
                "very-high": "bg-emerald-600",
                high: "bg-emerald-400",
                medium: "bg-amber-400",
                low: "bg-zinc-400",
              }[scoreLevel(value)],
            )}
            style={{ width: `${value}%` }}
          />
        )}
      </div>
    </div>
  );
}
