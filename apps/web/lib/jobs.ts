import type { Job, JobStatus } from "@/types/api";

// Wspólne nazwy dla listy kolejki i szczegółów tematu.
export const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Oczekujące", running: "W toku", retrying: "Ponawiane", succeeded: "Sukcesy", failed: "Błędy", cancelled: "Anulowane",
};
export const KIND_LABELS: Record<Job["kind"], string> = {
  prepare_wordpress: "Przygotowanie SEO", publish_wordpress: "WordPress Publisher", classify: "Ocena tematu", research: "Research", write: "Pisanie artykułu", qa_article: "QA / Fact Checker", auto_fix_article: "Auto Fix",
};
export const STAGE_LABELS: Record<string, string> = {
  preparing_seo: "Przygotowanie SEO", publishing_wordpress: "Synchronizacja WordPress", fact_checking: "Weryfikacja faktów", validating_references: "Sprawdzanie referencji", validating_qa: "Walidacja raportu QA",
  fixing_article: "Poprawianie artykułu", validating_fix: "Walidacja poprawek",
  classifying: "Ocena tematu", comparing_topics: "Porównanie z innymi tematami", fetching_original: "Pobieranie oryginału",
  discovering_sources: "Szukanie źródeł", searching_sources: "Wyszukiwanie (Tavily)", fetching_sources: "Pobieranie źródeł",
  analysing: "Analiza faktów", building_brief: "Przygotowanie briefu",
  writing: "Pisanie artykułu", validating: "Sprawdzenie artykułu", saving: "Zapis wyniku",
};
export const stageLabel = (stage: string | null) => stage ? STAGE_LABELS[stage] ?? stage : "Czeka na workera";
type CallUsageView = { usage?: { model?: string; input_tokens: number; output_tokens: number; recorded?: boolean; provider?: string; search_credits?: number } | null };
const credits = (count: number) => count === 1 ? "kredyt" : count % 10 >= 2 && count % 10 <= 4 && (count % 100 < 10 || count % 100 >= 20) ? "kredyty" : "kredytów";
export const callModelLabel = (call: CallUsageView): string | null => {
  if (!call.usage) return null;
  if (call.usage.search_credits !== undefined) return `Tavily · ${call.usage.search_credits} ${credits(call.usage.search_credits)}`;
  return call.usage.model ?? null;
};
export const callTokensLabel = (call: CallUsageView): string => {
  if (!call.usage || call.usage.recorded === false) return "nieznane";
  if (call.usage.search_credits !== undefined) return "nie dotyczy";
  return `${call.usage.input_tokens} / ${call.usage.output_tokens}`;
};
export const STATUS_STYLES: Record<JobStatus, string> = {
  queued: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  running: "bg-sky-50 text-sky-800 ring-sky-200",
  retrying: "bg-amber-50 text-amber-900 ring-amber-200",
  succeeded: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
  cancelled: "bg-zinc-50 text-zinc-500 ring-zinc-200",
};

export const isActiveJob = (job: Job) => ["queued", "running", "retrying"].includes(job.status);

// "stop" zatrzymuje biegnący job przed kolejnym płatnym krokiem AI. Publikacji WP nie wolno przerwać w trakcie
// (zapis wpisu i meta SEO musi się dokończyć), więc dla niej przycisku nie ma, a API zwraca job_not_stoppable.
export type CancelAction = "cancel" | "stop" | "stopping" | null;
export function cancelAction(job: Pick<Job, "status" | "kind" | "cancel_requested_at">): CancelAction {
  if (job.status === "queued" || job.status === "retrying") return "cancel";
  if (job.status !== "running" || job.kind === "publish_wordpress") return null;
  return job.cancel_requested_at ? "stopping" : "stop";
}

// Candidate-wide activity guards mutations; stage activity describes only this agent/version.
export function selectStageJobs(jobs: Job[], kind: Job["kind"], articleId?: number) {
  const history = jobs.filter(job => job.kind === kind && (articleId === undefined || job.article_id === articleId));
  return { history, latest: history[0], active: jobs.find(isActiveJob), ownActive: history.find(isActiveJob) };
}

export function jobElapsedSeconds(job: Pick<Job, "status" | "created_at" | "started_at">, now: number): number | null {
  const since = job.status === "queued" ? job.created_at : job.started_at ?? job.created_at;
  const started = Date.parse(since);
  return Number.isFinite(started) ? Math.max(0, Math.floor((now - started) / 1000)) : null;
}
