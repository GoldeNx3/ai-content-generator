import type { Research } from "@/types/api";

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
