"use client";

import { useEffect, useState } from "react";
import { Loader2Icon } from "lucide-react";
import { isActiveJob, jobElapsedSeconds, KIND_LABELS, stageLabel } from "@/lib/jobs";
import type { Job } from "@/types/api";

export function AgentProgress({ job }: { job: Job }) {
  const [now, setNow] = useState(() => Date.now());
  const active = isActiveJob(job);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active, job.id]);
  if (!active) return null;
  const seconds = jobElapsedSeconds(job, now);
  const label = job.status === "queued" ? "Oczekiwanie w kolejce" : job.status === "retrying" ? "Oczekuje na ponowienie" : "Agent pracuje";
  return (
    <div data-agent-progress={job.kind} className="flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100">
      <Loader2Icon aria-hidden="true" className="mt-0.5 size-5 shrink-0 animate-spin" />
      <div className="min-w-0 flex-1 space-y-2">
        <p role="status" className="font-semibold">{KIND_LABELS[job.kind]} · {label}</p>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p>{job.status === "running" ? stageLabel(job.stage) : job.status === "retrying" ? "Ponowienie bieżącego zadania" : "Zadanie czeka na dostępnego workera"}</p>
          <span data-job-elapsed={seconds ?? ""} aria-live="off" className="shrink-0 rounded-md bg-white/70 px-2.5 py-1 font-mono text-xs tabular-nums dark:bg-sky-900">
            {job.status === "queued" ? "Czas w kolejce" : "Czas pracy"}: {seconds === null ? "—" : `${seconds} s`}
          </span>
        </div>
        <p className="text-xs leading-5 text-sky-800 dark:text-sky-200">Możesz opuścić ten ekran. Wynik pojawi się po zakończeniu zadania.</p>
      </div>
    </div>
  );
}
