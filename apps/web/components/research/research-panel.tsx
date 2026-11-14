"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangleIcon, FlaskConicalIcon, Loader2Icon, SplitIcon } from "lucide-react";
import { toast } from "sonner";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { navigateStage } from "@/components/pipeline-state";
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
  const [updateMode, setUpdateMode] = useState<"start" | "retry" | null>(null);

  const load = useCallback(async () => {
    try {
      setResearch(await api.getResearch(candidateId));
      setLoadError(null);
      setLoaded(true);
        return true;
    } catch (error) {
      setLoadError(errorText(error));
      toast.error("Nie udało się wczytać Research", { description: errorText(error) });
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
  const running = Boolean(jobs.ownActive);
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
      toast.error("Nie udało się uruchomić Research", { description: errorText(error) });
    } finally {
      setStarting(false);
    }
  }

  const busy = starting || Boolean(jobs.active) || !jobs.loaded;
  const hasReport = research?.status === "completed";
  const hasSources = Boolean(research?.sources.length);
  const mode = hasSources ? updateMode ?? "retry" : "start";
  const generationReady = hasReport && Boolean(research?.facts.length);

  return (
    <WorkflowSection progressJob={jobs.ownActive} number={3} title="Research — baza faktów" description="Źródła, zweryfikowane fakty i kontekst do napisania artykułu." paid
      initiallyCollapsed={loaded ? hasReport : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : startError ? "Ostatnie uruchomienie: błąd" : starting ? "Uruchamianie…" : researchState(research, loaded)}
      actionTitle="Praca z researchem" actionDescription={hasReport ? "Przejrzyj raport i źródła. Możesz przejść do artykułu lub zaktualizować bazę faktów." : "Zbierz źródła i przygotuj bazę faktów do artykułu."}
      actionDetails={research && <p className="rounded-lg bg-muted/50 p-3 text-sm">{research.sources.length} źródeł · {research.facts.length} faktów · {research.uncertainties.length + research.conflicts.length} luk i konfliktów</p>}
      actions={<>
        <Button variant={generationReady ? "default" : "outline"} disabled={!generationReady || busy} onClick={() => navigateStage(4)}>Przejdź do generowania</Button>
        {!generationReady && <p className="action-hint">Wymaga ukończonego researchu ze zweryfikowanymi faktami.</p>}
        <div className="action-group">
          {research && <fieldset disabled={busy || !loaded} className="grid gap-2">
            <legend className="mb-2 text-sm font-semibold">Sposób aktualizacji</legend>
            <label className="research-mode" data-selected={mode === "retry"}>
              <input type="radio" name={`research-mode-${candidateId}`} checked={mode === "retry"} disabled={!hasSources} onChange={() => setUpdateMode("retry")} />
              <span><span className="block font-medium">Analizuj zapisane źródła</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">{hasSources ? "Zachowuje źródła, uwzględnia dodane linki i aktualizuje fakty." : "Dostępne po zapisaniu przynajmniej jednego źródła."}</span></span>
            </label>
            <label className="research-mode" data-selected={mode === "start"}>
              <input type="radio" name={`research-mode-${candidateId}`} checked={mode === "start"} onChange={() => setUpdateMode("start")} />
              <span><span className="block font-medium">Wyszukaj źródła od nowa</span><span className="mt-1 block text-xs leading-5 text-muted-foreground">Wyszukuje nowe materiały i zastępuje raport. Zachowuje ręcznie dodane źródła.</span></span>
            </label>
          </fieldset>}
          <Button variant={generationReady ? "outline" : "default"} onClick={() => trigger(mode)} disabled={busy || !loaded}>
            {starting || jobs.ownActive ? <Loader2Icon className="animate-spin" /> : <FlaskConicalIcon />}
            {starting || jobs.ownActive ? "Research w toku…" : `${research ? "Zaktualizuj research" : "Uruchom research"} · ${demo ? "demo · bezpłatne" : "płatne"}`}
          </Button>
          <p className="action-hint">{demo ? "Demo: bez kosztów AI." : "Każde uruchomienie nalicza nowy koszt AI."}</p>
        </div>
      </>}
      activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label: "Wyszukiwanie i analiza źródeł", aggregated: true, configured: "research", model: research?.llm_model, input: research?.llm_model ? research.llm_input_tokens : null, output: research?.llm_model ? research.llm_output_tokens : null, cost: research?.estimated_cost_usd}]} note="Dane dotyczą aktualnego raportu. Nowy research zastępuje raport; ponowna analiza korzysta z zachowanych źródeł. Każde uruchomienie nalicza nowy koszt. Koszt obejmuje też zapytania Tavily (kredyty)." />}>
      <div className="space-y-8">

        <div className="space-y-1 text-sm text-muted-foreground">          {startError && <p className="text-destructive">{startError} — możesz ponowić uruchomienie; kolejne wywołanie może naliczyć koszt.</p>}
          {loadError && <p className="text-destructive">{loadError}</p>}
          <p>{research?.started_at ? `Uruchomiono: ${formatDate(research.started_at)}` : "Research nie został jeszcze uruchomiony."}</p>
          {research?.completed_at && <p>Zakończono: {formatDate(research.completed_at)}</p>}
          {research && <p>{research.sources.length} źródeł · {research.facts.length} faktów</p>}
          <p className="mt-2">{generationReady ? "Kolejny krok: przejdź do generowania artykułu." : hasReport ? "Raport nie zawiera zweryfikowanych faktów. Uzupełnij źródła i zaktualizuj research." : "Do wygenerowania artykułu potrzebny jest ukończony research."}</p>
</div>
        {!loaded && <p className="text-sm text-muted-foreground">Ładowanie…</p>}

        {loaded && !research && (
          <p className="text-sm text-muted-foreground">
            Uruchom research, aby pobrać artykuł, zebrać dodatkowe źródła i opracować bazę faktów za pomocą AI.
          </p>
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

          <section className="space-y-3">
            <h3 className="font-semibold">
              Źródła <span className="font-normal text-muted-foreground">({research?.sources.length ?? 0})</span>
            </h3>
            <SourceList sources={research?.sources ?? []} />
            <ManualSourceForm candidateId={candidateId} disabled={busy || !loaded} onAdded={load} />
            {research && research.search_queries.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Zapytania użyte w Research: {research.search_queries.map((query) => `“${query}”`).join(", ")}
              </p>
            )}
          </section>

        {hasReport && research && (
          <>
            <div className="space-y-4">
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



      </div>
    </WorkflowSection>
  );
}

function ReportText({ title, text }: { title: string; text: string | null }) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-foreground/90">{text ?? "—"}</p>
    </section>
  );
}
