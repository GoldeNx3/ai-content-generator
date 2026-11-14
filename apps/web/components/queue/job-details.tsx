"use client";

import Link from "next/link";
import { AgentProgress } from "@/components/agent-progress";
import { useEffect, useState } from "react";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cancelAction, KIND_LABELS, STATUS_LABELS, stageLabel } from "@/lib/jobs";
import { Button } from "@/components/ui/button";
import type { Job, JobAttempt } from "@/types/api";

const OUTCOMES: Record<string, string> = {
  running: "W toku", succeeded: "Sukces", retryable_error: "Błąd przejściowy",
  failed: "Błąd", interrupted: "Przerwana próba", cancelled: "Anulowana",
};

// Ten widok odczytuje historię z bazy, również jeśli proces lub przeglądarka były restartowane.
export function JobDetails({ initial, onRetried, onCancelled }: { initial: Job; onRetried: (job: Job) => void; onCancelled?: () => void }) {
  const [job, setJob] = useState(initial);
  const [attempts, setAttempts] = useState<JobAttempt[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    async function load() {
      try {
        const [current, history] = await Promise.all([api.getJob(initial.id), api.jobAttempts(initial.id)]);
        if (disposed) return;
        setJob(current); setAttempts(history); setLoaded(true); setError(null);
        // Dwa GET mogą trafić po różnych stronach końcowego commitu.
        // Odpytujemy także wynik końcowy, by historia prób dogoniła status.
        timer = setTimeout(() => void load(), 2000);
      } catch (failure) {
        if (!disposed) { setError(errorText(failure)); timer = setTimeout(() => void load(), 5000); }
      }
    }
    void load();
    return () => { disposed = true; clearTimeout(timer); };
  }, [initial.id]);

  async function retry() {
    setRetrying(true);
    try { onRetried(await api.retryJob(job.id)); }
    catch (failure) { setError(errorText(failure)); }
    finally { setRetrying(false); }
  }

  async function cancel() {
    setCancelling(true);
    try { setJob(await api.cancelJob(job.id)); onCancelled?.(); }
    catch (failure) { setError(errorText(failure)); }
    finally { setCancelling(false); }
  }
  const action = cancelAction(job);

  return <div className="space-y-5">
    <AgentProgress key={job.id} job={job} />
    <div className="space-y-1 text-sm">
      <p className="font-medium">{KIND_LABELS[job.kind]} · {STATUS_LABELS[job.status]}</p>
      <p>{stageLabel(job.stage)} · próba {job.attempt_count}/{job.max_attempts}</p>
      <p className="break-all font-mono text-xs text-muted-foreground">{job.id}</p>
      <Link href={`/candidates/${job.candidate_id}`} className="text-primary underline">Otwórz temat #{job.candidate_id}</Link>
    </div>
    <dl className="grid grid-cols-2 gap-2 text-xs">
      <dt>Utworzono</dt><dd>{formatDate(job.created_at)}</dd>
      <dt>Rozpoczęto</dt><dd>{formatDate(job.started_at)}</dd>
      <dt>Zakończono</dt><dd>{formatDate(job.finished_at)}</dd>
      {job.status === "retrying" && <><dt>Następna próba najwcześniej</dt><dd>{formatDate(job.available_at)}</dd></>}
      {job.result_id !== null && <><dt>Zapisany wynik</dt><dd>{job.result_type} #{job.result_id}</dd></>}
    </dl>
    {job.error_message && !["succeeded", "cancelled"].includes(job.status) && <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
      <p>{job.error_message}</p><p className="mt-1 font-mono text-xs">{job.error_code}</p>
    </div>}
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {job.status === "cancelled" && <p className="text-sm text-muted-foreground">{job.error_message ?? "Anulowano."} Etap możesz zlecić ponownie na stronie tematu.</p>}
    {job.status === "failed" && <Button disabled={retrying} onClick={() => void retry()}>{retrying ? "Zlecanie…" : "Ponów zadanie · płatne"}</Button>}
    {action && <div className="space-y-1">
      <Button variant="outline" disabled={cancelling || action === "stopping"} onClick={() => void cancel()}>
        {action === "cancel" ? (cancelling ? "Anulowanie…" : "Anuluj zadanie") : action === "stop" ? (cancelling ? "Zatrzymywanie…" : "Zatrzymaj po bieżącym kroku") : "Zatrzymywanie…"}
      </Button>
      {action !== "cancel" && <p className="text-xs text-muted-foreground">Trwające wywołanie AI zostanie dokończone i policzone; kolejne kroki nie ruszą.</p>}
    </div>}
    <section className="space-y-3">
      <h3 className="font-semibold">Historia prób</h3>
      {!loaded && <p className="text-sm text-muted-foreground">Ładowanie historii…</p>}
      {loaded && attempts.length === 0 && <p className="text-sm text-muted-foreground">Worker jeszcze nie rozpoczął tego zadania.</p>}
      {attempts.map((attempt) => <div key={attempt.number} className="space-y-2 rounded-lg border p-3">
        <p className="text-sm font-medium">Próba {attempt.number} · {OUTCOMES[attempt.outcome] ?? attempt.outcome}</p>
        <p className="text-xs text-muted-foreground">{formatDate(attempt.started_at)} → {formatDate(attempt.finished_at)}</p>
        {attempt.error_message && <p className="text-xs text-destructive">{attempt.error_message}</p>}
        {attempt.llm_calls.length === 0 && <p className="text-xs text-muted-foreground">Brak wywołań AI w tej próbie.</p>}
        {attempt.llm_calls.map((call, index) => <div key={index} className="rounded-md bg-muted/40 p-2 text-xs">
          <p className="font-medium">{stageLabel(call.stage)} · {call.finished ? "Odpowiedź zapisana" : "Przerwane lub nadal wykonywane"}</p>
          <p className="mt-1">Model: {call.usage?.model ?? "nieznany"}</p>
          <p>Tokeny wejścia / wyjścia: {call.usage && call.usage.recorded !== false ? `${call.usage.input_tokens} / ${call.usage.output_tokens}` : "nieznane"}</p>
          <p>{call.estimated_cost_usd === null ? "Koszt nieznany" : `Zapisany koszt: ≈ $${call.estimated_cost_usd}`}</p>
        </div>)}
      </div>)}
      <p className="text-xs text-muted-foreground">Brak zapisanej odpowiedzi może oznaczać naliczony koszt. Historia nie obejmuje opłat wyszukiwarki.</p>
    </section>
  </div>;
}
