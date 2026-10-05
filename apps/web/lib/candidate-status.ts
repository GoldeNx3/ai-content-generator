import type { CandidateWorkflowStatus } from "@/types/api";

export const CANDIDATE_WORKFLOW_LABELS: Record<CandidateWorkflowStatus, string> = {
  pending: "Oczekuje",
  ignored: "Pominięty",
  approved: "Zatwierdzony",
  draft: "Draft",
  published: "Opublikowane",
  scheduled: "Zaplanowane",
};
