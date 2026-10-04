"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangleIcon, FlaskConicalIcon, Loader2Icon, RefreshCwIcon, SplitIcon } from "lucide-react";
import { toast } from "sonner";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { researchState } from "@/lib/workflow";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Research } from "@/types/api";

import { FactList } from "./fact-list";
import { ManualSourceForm } from "./manual-source-form";
import { hostname } from "./research-utils";
import { SourceList } from "./source-list";

const POLL_INTERVAL_MS = 2000;

interface ResearchPanelProps {
  candidateId: number;
  onResearchChange?: (research: Research | null) => void;
}

export function ResearchPanel({ candidateId, onResearchChange }: ResearchPanelProps) {
  const demo = useDemoMode();
  const [research, setResearch] = useState<Research | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    try {
      setResearch(await api.getResearch(candidateId));
      setLoadError(null);
      setLoaded(true);
        return true;
    } catch (error) {
      setLoadError(errorText(error));
      toast.error("Could not load research", { description: errorText(error) });
      return false;
    }
  }, [candidateId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void load();
  }, [load]);

  useEffect(() => {
    onResearchChange?.(research);
  }, [research, onResearchChange]);

  const jobs = useCandidateJobs(candidateId, "research", load);
  const running = jobs.active?.kind === "research";
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [running, load]);

  async function trigger(kind: "start" | "retry") {
    setStarting(true);
    setStartError(null);
    try {
      await jobs.enqueue(() => kind === "start" ? api.startResearch(candidateId) : api.retryResearch(candidateId));
      toast.success("Research zapisany w kolejce");
    } catch (error) {
      setStartError(errorText(error));
      toast.error("Could not start research", { description: errorText(error) });
    } finally {
      setStarting(false);
    }
  }

  const busy = starting || Boolean(jobs.active) || !jobs.loaded;
  const hasReport = research?.status === "completed";
  const researchHasRun = research !== null || jobs.history.length > 0;

  return (
    <WorkflowSection number={3} title="Research — baza faktów" description="Źródła, zweryfikowane fakty i kontekst do napisania artykułu." paid
      initiallyCollapsed={loaded ? hasReport : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : startError ? "Ostatnie uruchomienie: błąd" : starting ? "Uruchamianie…" : researchState(research, loaded)}
      actions={<div className="flex flex-wrap gap-2">
          {research && research.sources.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => trigger("retry")} disabled={busy || !loaded}>
              <RefreshCwIcon />
              Ponów analizę · {demo ? "demo · bezpłatne" : "płatne"}
            </Button>
          )}
          <Button variant={researchHasRun ? "outline" : "default"} size="sm" onClick={() => trigger("start")} disabled={busy || !loaded}>
            {busy ? <Loader2Icon className="animate-spin" /> : <FlaskConicalIcon />}
            {busy ? "Research w toku…" : researchHasRun ? `Nowy research · ${demo ? "demo · bezpłatne" : "płatne"}` : `Uruchom research · ${demo ? "demo · bezpłatne" : "płatne"}`}
          </Button>
        </div>}
      activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label: "Wyszukiwanie i analiza źródeł", aggregated: true, configured: "research", model: research?.llm_model, input: research?.llm_model ? research.llm_input_tokens : null, output: research?.llm_model ? research.llm_output_tokens : null, cost: research?.estimated_cost_usd}]} note="Dane dotyczą aktualnego raportu. Nowy research zastępuje raport; ponowna analiza korzysta z zachowanych źródeł. Każde uruchomienie nalicza nowy koszt. Opłaty wyszukiwarki nie są ujęte." />}>
      <div className="space-y-8">

        <div className="space-y-1 text-sm text-muted-foreground">          {startError && <p className="text-destructive">{startError} — możesz ponowić uruchomienie; kolejne wywołanie może naliczyć koszt.</p>}
          {loadError && <p className="text-destructive">{loadError}</p>}
          <p>{research?.started_at ? `Uruchomiono: ${formatDate(research.started_at)}` : "Research nie został jeszcze uruchomiony."}</p>
          {research?.completed_at && <p>Zakończono: {formatDate(research.completed_at)}</p>}
          {research && <p>{research.sources.length} źródeł · {research.facts.length} faktów</p>}
          <p className="mt-2">{hasReport ? "Kolejny krok: wygeneruj artykuł w sekcji poniżej." : "Do wygenerowania artykułu potrzebny jest ukończony research."}</p>
</div>
        {!loaded && <p className="text-sm text-muted-foreground">Ładowanie…</p>}

        {loaded && !research && (
          <p className="text-sm text-muted-foreground">
            Uruchom research, aby pobrać artykuł, zebrać dodatkowe źródła i opracować bazę faktów za pomocą AI.
          </p>
        )}

        {running && (
          <div className="flex items-center gap-3 rounded-lg bg-sky-50 px-4 py-3 text-sm text-sky-900">
            <Loader2Icon className="size-4 animate-spin" />
            <span>
              Pobieranie źródeł i analiza… <Elapsed since={jobs.active?.started_at ?? null} />{" "}
              {research && research.sources.length > 0 && `· ${research.sources.length} źródeł`}
              <span className="block text-xs text-sky-800/80">
                Zwykle 20–90 s; większe modele mogą potrzebować kilku minut.
              </span>
            </span>
          </div>
        )}

        {research?.status === "failed" && (
          <div className="flex gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-900">
            <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">Research zakończony błędem</p>
              <p>{research.error}</p>
              <p className="mt-1 text-rose-800/80">Pobrane źródła zachowano. Dodaj źródło ręcznie lub ponów analizę.</p>
            </div>
          </div>
        )}

        {hasReport && research && (
          <>
            <div className="grid gap-6 md:grid-cols-3">
              <ReportText title="Podsumowanie" text={research.summary} />
              <ReportText title="Dlaczego to ważne" text={research.why_it_matters} />
              <ReportText title="Proponowana perspektywa" text={research.suggested_angle} />
            </div>

            <section className="space-y-3">
              <h3 className="font-semibold">
                Zweryfikowane fakty <span className="font-normal text-muted-foreground">({research.facts.length})</span>
              </h3>
              <FactList facts={research.facts} sources={research.sources} />
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-3">
                <h3 className="font-semibold">
                  Niepewności{" "}
                  <span className="font-normal text-muted-foreground">({research.uncertainties.length})</span>
                </h3>
                {research.uncertainties.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nie zgłoszono.</p>
                ) : (
                  <ul className="space-y-2">
                    {research.uncertainties.map((item, index) => (
                      <li key={index} className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-sm">
                        <p>{item.claim}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="space-y-3">
                <h3 className="font-semibold">
                  Sprzeczności <span className="font-normal text-muted-foreground">({research.conflicts.length})</span>
                </h3>
                {research.conflicts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nie wykryto sprzeczności pomiędzy źródłami.</p>
                ) : (
                  <ul className="space-y-2">
                    {research.conflicts.map((conflict, index) => (
                      <li key={index} className="rounded-lg border border-rose-200 bg-rose-50/40 p-3 text-sm">
                        <p className="flex items-center gap-1.5 font-medium">
                          <SplitIcon className="size-3.5" />
                          {conflict.topic}
                        </p>
                        <ul className="mt-2 space-y-1">
                          {conflict.sources.map((item, itemIndex) => (
                            <li key={itemIndex} className="text-xs">
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium hover:underline"
                              >
                                {hostname(item.url)}
                              </a>
                              : {item.claim}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        )}

        {research && (
          <section className="space-y-3">
            <h3 className="font-semibold">
              Źródła <span className="font-normal text-muted-foreground">({research.sources.length})</span>
            </h3>
            <SourceList sources={research.sources} />
            <ManualSourceForm candidateId={candidateId} disabled={busy} onAdded={load} />
            {research.search_queries.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Search queries: {research.search_queries.map((query) => `“${query}”`).join(", ")}
              </p>
            )}
          </section>
        )}

      </div>
    </WorkflowSection>
  );
}

function Elapsed({ since }: { since: string | null }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (!since) return null;
  const seconds = Math.max(0, Math.round((now - new Date(since).getTime()) / 1000));
  return <span className="font-mono tabular-nums">{seconds} s</span>;
}

function ReportText({ title, text }: { title: string; text: string | null }) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-foreground/90">{text ?? "—"}</p>
    </section>
  );
}
