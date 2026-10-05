import { cn } from "@/lib/utils";
import type { CandidateWorkflowStatus } from "@/types/api";
import { CANDIDATE_WORKFLOW_LABELS } from "@/lib/candidate-status";

const STATUS_STYLES: Record<CandidateWorkflowStatus, string> = {
  pending: "bg-sky-50 text-sky-800 ring-sky-200",
  approved: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  ignored: "bg-zinc-100 text-zinc-500 ring-zinc-200",
  draft: "bg-amber-50 text-amber-800 ring-amber-200",
  published: "bg-emerald-100 text-emerald-900 ring-emerald-300",
  scheduled: "bg-violet-50 text-violet-800 ring-violet-200",
};

export function StatusBadge({ status }: { status: CandidateWorkflowStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ring-1",
        STATUS_STYLES[status],
      )}
    >
      {CANDIDATE_WORKFLOW_LABELS[status]}
    </span>
  );
}

export function CategoryBadge({ category }: { category: string | null }) {
  if (!category) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center rounded-md bg-violet-50 px-2 py-0.5 font-mono text-xs text-violet-800 ring-1 ring-violet-200">
      {({news:"Wiadomości",guide:"Poradnik",comparison:"Porównanie",case_study:"Studium przypadku",explainer:"Wyjaśnienie"} as Record<string,string>)[category] ?? category}
    </span>
  );
}
