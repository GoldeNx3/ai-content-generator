"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "@/lib/api";
import type { Job } from "@/types/api";

export const isActiveJob = (job: Job) => ["queued", "running", "retrying"].includes(job.status);

// Przeglądarka jedynie odczytuje stan. Worker działa niezależnie od tego hooka.
// Powrót do zakładki natychmiast odświeża historię zapisaną w PostgreSQL.
export function useCandidateJobs(candidateId: number, kind: Job["kind"], onChange: () => Promise<unknown>, articleId?: number) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const callback = useRef(onChange);
  const signature = useRef("");
  useEffect(() => { callback.current = onChange; }, [onChange]);

  const refresh = useCallback(async () => {
    try {
      const page = await api.listJobs(candidateId);
      setJobs(page.items);
      setLoaded(true);
      setError(null);
      const next = JSON.stringify(page.items.filter((job) => job.kind === kind && (articleId === undefined || job.article_id === articleId))
        .map((job) => [job.id, job.status, job.stage, job.attempt_count]));
      if (signature.current !== next) {
        if (await callback.current() !== false) signature.current = next;
      }
      return page.items;
    } catch (failure) {
      setError(errorText(failure));
      return null;
    }
  }, [candidateId, kind, articleId]);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      const list = await refresh();
      if (!disposed) timer = setTimeout(() => void poll(), list?.some(isActiveJob) ? 2000 : 10000);
    }
    const visible = () => { if (document.visibilityState === "visible") void refresh(); };
    void poll();
    document.addEventListener("visibilitychange", visible);
    return () => { disposed = true; clearTimeout(timer); document.removeEventListener("visibilitychange", visible); };
  }, [refresh]);

  async function enqueue(action: () => Promise<Job>) {
    try {
      const job = await action();
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      return job;
    } finally {
      // Także przy utraconej odpowiedzi POST szukamy zadania zapisanego w bazie.
      await refresh();
    }
  }

  const history = jobs.filter((job) => job.kind === kind && (articleId === undefined || job.article_id === articleId));
  return { history, latest: history[0], active: jobs.find(isActiveJob), loaded, error, refresh, enqueue };
}
