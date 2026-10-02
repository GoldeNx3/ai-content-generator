import { cn } from "@/lib/utils";
import type { CandidateStatus } from "@/types/api";

const STATUS_STYLES: Record<CandidateStatus, string> = {
  pending: "bg-sky-50 text-sky-800 ring-sky-200",
  approved: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  ignored: "bg-zinc-100 text-zinc-500 ring-zinc-200",
};

export function StatusBadge({ status }: { status: CandidateStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1",
        STATUS_STYLES[status],
      )}
    >
      {status}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string | null }) {
  if (!category) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center rounded-md bg-violet-50 px-2 py-0.5 font-mono text-xs text-violet-800 ring-1 ring-violet-200">
      {category}
    </span>
  );
}
