import type { Job, JobStatus } from "@/types/api";

// Wspólne nazwy dla listy kolejki i szczegółów tematu.
export const STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Oczekujące", running: "W toku", retrying: "Ponawiane", succeeded: "Sukcesy", failed: "Błędy",
};
export const KIND_LABELS: Record<Job["kind"], string> = {
  classify: "Ocena tematu", research: "Research", write: "Pisanie artykułu",
};
export const STAGE_LABELS: Record<string, string> = {
  classifying: "Ocena tematu", fetching_original: "Pobieranie oryginału",
  discovering_sources: "Szukanie źródeł", fetching_sources: "Pobieranie źródeł",
  analysing: "Analiza faktów", building_brief: "Przygotowanie briefu",
  writing: "Pisanie artykułu", validating: "Sprawdzenie artykułu", saving: "Zapis wyniku",
};
export const stageLabel = (stage: string | null) => stage ? STAGE_LABELS[stage] ?? stage : "Czeka na workera";
export const STATUS_STYLES: Record<JobStatus, string> = {
  queued: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  running: "bg-sky-50 text-sky-800 ring-sky-200",
  retrying: "bg-amber-50 text-amber-900 ring-amber-200",
  succeeded: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
};
