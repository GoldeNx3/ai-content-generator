import type { Candidate, Research } from "@/types/api";

type ClassificationUsage = Pick<Candidate, "llm_model" | "llm_input_tokens" | "llm_output_tokens" | "estimated_cost_usd" | "topic_group_id">;
export function classificationUsageRow(candidate: ClassificationUsage) {
  const usage = { model: candidate.llm_model, input: candidate.llm_input_tokens, output: candidate.llm_output_tokens, cost: candidate.estimated_cost_usd };
  return candidate.topic_group_id
    ? { label: "Porównanie z innymi tematami · ocena przejęta z głównego tematu", configured: "embedding" as const, ...usage }
    : { label: "Ocena tematu", configured: "classifier" as const, ...usage };
}

export function costLabel(cost: string | null): string {
  return cost !== null && Number.isFinite(Number(cost)) ? `≈ $${Number(cost).toFixed(4)}` : "Koszt nieznany";
}

export function researchState(research: Pick<Research, "status"> | null, loaded: boolean): string {
  if (!loaded) return "Ładowanie…";
  if (!research) return "Do uruchomienia";
  return { pending: "W kolejce", running: "W toku", completed: "Zakończony", failed: "Błąd" }[research.status];
}

export function articleState(hasArticle: boolean, generating: boolean, researchReady: boolean, loaded: boolean): string {
  if (generating) return "W toku";
  if (!loaded) return "Ładowanie…";
  if (hasArticle) return "Zakończony";
  return researchReady ? "Do uruchomienia" : "Najpierw ukończ research";
}


export function qaState(report: {status: "pending" | "running" | "completed" | "failed"; is_stale?: boolean} | null, loaded: boolean): string {
  if (!loaded) return "Ładowanie…";
  if (!report) return "Do uruchomienia";
  if (report.is_stale) return "Wymaga ponownej oceny";
  return {pending: "W kolejce", running: "W toku", completed: "Zakończony", failed: "Błąd"}[report.status];
}
