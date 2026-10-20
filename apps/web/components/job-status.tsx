"use client";

import { useDemoMode } from "@/components/demo-mode";

import { CheckCircle2Icon, CircleIcon, AlertCircleIcon, Loader2Icon } from "lucide-react";
import { useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";
import { isActiveJob, STAGE_LABELS as stages } from "@/lib/jobs";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import type { Job, JobAttempt } from "@/types/api";

export const jobStatusLabel: Record<Job["status"], string> = {
  queued: "W kolejce", running: "W toku", retrying: "Oczekuje na ponowienie", succeeded: "Zakończono", failed: "Błąd",
};
export function JobStatus({ jobs, active, error, onRetry }: {
  jobs: Job[]; active?: Job; error: string | null; onRetry: (job: Job) => Promise<unknown>;
}) {
  const demo = useDemoMode();
  const [expanded, setExpanded] = useState(false);
  const [attempts, setAttempts] = useState<JobAttempt[]>([]);
  const [readError, setReadError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const job = jobs[0];
  useEffect(() => {
    if (!expanded || !job) return;
    let disposed = false;
    async function load() {
      try {
        const list = await api.jobAttempts(job.id);
        if (!disposed) { setAttempts(list); setReadError(null); }
      } catch (failure) { if (!disposed) setReadError(errorText(failure)); }
    }
    void load();
    const timer = isActiveJob(job) ? setInterval(() => void load(), 2000) : undefined;
    return () => { disposed = true; clearInterval(timer); };
  }, [expanded, job?.id, job?.status, job]);
  async function retry() {
    if (!job) return;
    setRetrying(true);
    try { await onRetry(job); setReadError(null); }
    catch (failure) { setReadError(errorText(failure)); }
    finally { setRetrying(false); }
  }
  const Icon = job?.status === "succeeded" ? CheckCircle2Icon : job?.status === "failed" ? AlertCircleIcon : job?.status === "running" ? Loader2Icon : CircleIcon;
  const color = job?.status === "failed" ? "text-rose-700" : job?.status === "succeeded" ? "text-emerald-700" : "text-sky-700";
  return <div className="space-y-3 text-sm" role="status">
    {error && <p className="text-destructive">Nie udało się odczytać statusu: {error}</p>}
    {active && active.kind !== job?.kind && <p>Dla tego tematu trwa inne zadanie · {jobStatusLabel[active.status]}.</p>}
    {job && <>
      <ol className="space-y-5 border-l border-slate-200 pl-5"><li className="relative"><Icon className={`absolute -left-[30px] top-0.5 size-5 bg-white ${color} ${job.status === "running" ? "animate-spin" : ""}`} /><p className={`font-medium ${color}`}>{jobStatusLabel[job.status]}{job.stage && stages[job.stage] && ` · ${stages[job.stage]}`}</p><p className="mt-1 text-xs text-muted-foreground">{formatDate(job.finished_at ?? job.started_at ?? job.created_at)}</p></li></ol>
      {job.status === "retrying" && <p>Ponowienie najwcześniej: {formatDate(job.available_at)}</p>}
      {job.error_message && job.status !== "succeeded" && <div role="alert" className="rounded-lg bg-destructive/10 p-3 text-destructive"><p>{job.error_message}</p>{job.error_code && <p className="mt-1 font-mono text-xs opacity-80">Kod błędu: {job.error_code}</p>}</div>}
      {job.status === "failed" && <Button size="sm" variant="outline" disabled={retrying || Boolean(active)} onClick={() => void retry()}>Ponów zadanie · {demo ? "demo · bezpłatne" : "płatne"}</Button>}
      <Button size="sm" variant="ghost" onClick={() => setExpanded(!expanded)}>{expanded ? "Ukryj" : "Szczegóły techniczne"}</Button>
      {expanded && <div className="space-y-3 text-xs">
        {jobs.map((item) => <p key={item.id}>{formatDate(item.created_at)} · {jobStatusLabel[item.status]} · {item.id}</p>)}
        {readError && <p className="text-destructive">{readError}</p>}
        <p className="font-medium">Wywołania ostatniego zadania</p>
        {attempts.map((attempt) => <div key={attempt.number}>
          <p>Próba {attempt.number} · {attempt.outcome}</p>
          {attempt.llm_calls.map((call, index) => <p key={index}>
            {stages[call.stage] ?? call.stage} · {call.finished ? "odpowiedź zapisana" : "brak zapisanej odpowiedzi; koszt nieznany"}
            {call.finished && <> · {call.usage?.model ?? "model nieznany"} · tokeny {call.usage?.recorded === false ? "nieznane" : call.usage ? `${call.usage.input_tokens} / ${call.usage.output_tokens}` : "nieznane"} · {call.estimated_cost_usd === null ? "koszt nieznany" : `≈ $${call.estimated_cost_usd}`}</>}
          </p>)}
        </div>)}
      </div>}
    </>}
  </div>;
}
