"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangleIcon, ArrowRightIcon, CircleHelpIcon, FlaskConicalIcon, LibraryIcon, LightbulbIcon, ListChecksIcon, Loader2Icon, ScaleIcon, SearchIcon, SplitIcon } from "lucide-react";
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
import { plural } from "@/lib/pagination";
import { ResultBlock, ResultOutline } from "@/components/stage/result-block";
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
    <WorkflowSection progressJob={jobs.ownActive} number={3} title="Research" description="AI zbiera źródła i ustala fakty, na których oprze się artykuł." resultTitle="Raport researchu" paid
      initiallyCollapsed={loaded ? hasReport : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : startError ? "Ostatnie uruchomienie: błąd" : starting ? "Uruchamianie…" : researchState(research, loaded)}
      actionTitle="Research" actionDescription={hasReport ? "Raport jest gotowy. Przejrzyj źródła i fakty albo zaktualizuj bazę faktów." : "Zbierz źródła i przygotuj bazę faktów, na której oprze się artykuł."}
      blocker={jobs.active && !jobs.ownActive ? "Dla tego tematu trwa inne zadanie. Research będzie dostępny po jego zakończeniu." : undefined}
      primaryTitle={research ? "Aktualizacja" : undefined}
      primary={<>
        {research && <fieldset disabled={busy || !loaded} className="grid gap-2">
          <legend className="sr-only">Sposób aktualizacji</legend>
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
        <p className="action-hint">{demo ? "Tryb demo: bez kosztów AI." : "Każde uruchomienie nalicza nowy koszt AI (model i wyszukiwanie Tavily)."}</p>
      </>}
      navigation={<>
        <Button variant={generationReady ? "default" : "outline"} onClick={() => navigateStage(4)}>Przejdź do generowania<ArrowRightIcon /></Button>
        {!generationReady && <p className="action-hint">Generowanie odblokuje się po ukończeniu researchu ze zweryfikowanymi faktami.</p>}
      </>}
      activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label: "Wyszukiwanie i analiza źródeł", aggregated: true, configured: "research", model: research?.llm_model, input: research?.llm_model ? research.llm_input_tokens : null, output: research?.llm_model ? research.llm_output_tokens : null, cost: research?.estimated_cost_usd}]} note="Dane dotyczą aktualnego raportu. Nowy research zastępuje raport; ponowna analiza korzysta z zachowanych źródeł. Każde uruchomienie nalicza nowy koszt. Koszt obejmuje też zapytania Tavily (kredyty)." />}>
      <ResearchResult research={research} loaded={loaded} startError={startError} loadError={loadError}
        sourcesSlot={<ManualSourceForm candidateId={candidateId} disabled={busy || !loaded} onAdded={load} />} />
    </WorkflowSection>
  );
}

function ResearchResult({ research, loaded, startError, loadError, sourcesSlot }: {
  research: Research | null; loaded: boolean; startError: string | null; loadError: string | null; sourcesSlot: React.ReactNode;
}) {
  const hasReport = research?.status === "completed";
  const sources = research?.sources ?? [];
  const failedSources = sources.filter((source) => source.fetch_status === "failed").length;
  const toVerify = (research?.uncertainties.length ?? 0) + (research?.conflicts.length ?? 0);
  const keyFacts = research?.facts.filter((fact) => fact.importance === "critical").length ?? 0;

  return (
    <div className="space-y-7">
      {startError && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{startError} — możesz ponowić uruchomienie; kolejne wywołanie może naliczyć koszt.</p>}
      {loadError && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{loadError}</p>}
      {!loaded && <p className="text-sm text-muted-foreground">Ładowanie…</p>}

      {research?.status === "failed" && (
        <div className="flex gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-900 ring-1 ring-rose-200">
          <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Research zakończony błędem</p>
            <p>{research.error}</p>
            <p className="mt-1 text-rose-800/80">Pobrane źródła zachowano. Dodaj źródło ręcznie lub ponów analizę.</p>
          </div>
        </div>
      )}

      {loaded && !research && (
        <div className="rounded-xl border border-dashed p-5">
          <p className="font-medium">Research nie został jeszcze uruchomiony</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">Po uruchomieniu AI pobierze oryginalny materiał, wyszuka dodatkowe źródła i przygotuje:</p>
          <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            {[[LightbulbIcon, "Wnioski", "podsumowanie i proponowane ujęcie tematu"], [ListChecksIcon, "Bazę faktów", "twierdzenia potwierdzone w źródłach"], [ScaleIcon, "Listę do weryfikacji", "niepewności i sprzeczności"], [LibraryIcon, "Źródła", "materiały z oceną wiarygodności"]].map(([Icon, title, text]) => {
              const I = Icon as typeof LightbulbIcon;
              return <li key={title as string} className="flex gap-2"><I className="mt-0.5 size-4 shrink-0 text-emerald-700" aria-hidden="true" /><span><span className="font-medium">{title as string}</span> <span className="text-muted-foreground">— {text as string}</span></span></li>;
            })}
          </ul>
        </div>
      )}

      {hasReport && research && (
          <ResultOutline label="Zawartość raportu researchu" meta={<>Raport z {formatDate(research.completed_at ?? research.updated_at)}{research.started_at && research.completed_at ? ` · trwał ${duration(research.started_at, research.completed_at)}` : ""}</>} items={[
          { target: "research-findings", label: "Wnioski", value: research.summary ? "Gotowe" : "Brak", hint: "podsumowanie i ujęcie", icon: LightbulbIcon, tone: research.summary ? "success" : "attention" },
          { target: "research-facts", label: "Fakty", value: research.facts.length, hint: `${keyFacts} ${plural(keyFacts, "kluczowy", "kluczowe", "kluczowych")}`, icon: ListChecksIcon, tone: research.facts.length ? "success" : "danger" },
          { target: "research-verify", label: "Do weryfikacji", value: toVerify, hint: toVerify ? "sprawdź przed pisaniem" : "źródła są spójne", icon: ScaleIcon, tone: toVerify ? "attention" : "neutral" },
          { target: "research-sources", label: "Źródła", value: sources.length, hint: failedSources ? `${failedSources} nie ${plural(failedSources, "pobrane", "pobrane", "pobranych")}` : "wszystkie pobrane", icon: LibraryIcon, tone: failedSources ? "attention" : "neutral" },
        ]} />
      )}

      {hasReport && research && <>
        <ResultBlock id="research-findings" icon={LightbulbIcon} title="Wnioski dla artykułu"
          description="Co ustaliło AI i jak proponuje ująć temat. Te wnioski trafią do briefu przy generowaniu.">
          <dl className="divide-y rounded-xl bg-muted/40 px-4">
            {[["Podsumowanie", research.summary], ["Dlaczego to ważne", research.why_it_matters], ["Proponowana perspektywa", research.suggested_angle]].map(([label, text]) => (
              <div key={label} className="grid gap-1 py-3 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
                <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
                <dd className="text-sm leading-6">{text ?? "—"}</dd>
              </div>
            ))}
          </dl>
        </ResultBlock>

        <ResultBlock id="research-facts" icon={ListChecksIcon} title="Baza faktów" count={research.facts.length}
          description="Twierdzenia potwierdzone w źródłach. Artykuł może opierać się tylko na tych faktach; pewność mówi, jak mocno źródła je potwierdzają.">
          <FactList facts={research.facts} sources={research.sources} />
        </ResultBlock>

        <ResultBlock id="research-verify" icon={ScaleIcon} title="Do weryfikacji" count={toVerify}
          description="Twierdzenia niepotwierdzone albo opisane w źródłach różnie. Artykuł nie powinien podawać ich jako pewnych.">
          {toVerify === 0 ? <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Brak niepewności i sprzeczności — źródła są spójne.</p> : (
            <ul className="space-y-2">
              {research.uncertainties.map((item, index) => (
                <li key={`u${index}`} className="rounded-xl bg-amber-50/70 p-4 text-sm ring-1 ring-amber-200 dark:bg-amber-950/40 dark:ring-amber-900">
                  <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300"><CircleHelpIcon className="size-3.5" aria-hidden="true" />Niepewność</p>
                  <p className="mt-1 font-medium">{item.claim}</p>
                  <p className="mt-1 text-muted-foreground">{item.reason}</p>
                </li>
              ))}
              {research.conflicts.map((conflict, index) => (
                <li key={`c${index}`} className="rounded-xl bg-rose-50/60 p-4 text-sm ring-1 ring-rose-200 dark:bg-rose-950/40 dark:ring-rose-900">
                  <p className="flex items-center gap-1.5 text-xs font-semibold text-rose-800 dark:text-rose-300"><SplitIcon className="size-3.5" aria-hidden="true" />Sprzeczność między źródłami</p>
                  <p className="mt-1 font-medium">{conflict.topic}</p>
                  <ul className="mt-2 grid gap-2 sm:grid-cols-2">
                    {conflict.sources.map((item, itemIndex) => (
                      <li key={itemIndex} className="rounded-lg bg-background p-3 ring-1 ring-foreground/8">
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline">{hostname(item.url)}</a>
                        <p className="mt-1">{item.claim}</p>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </ResultBlock>
      </>}

      <ResultBlock id="research-sources" icon={LibraryIcon} title="Źródła" count={sources.length}
        description={<>Materiały, z których AI wyciąga fakty. Numer w nawiasie, np. [1], odpowiada odwołaniom w bazie faktów.</>}>
        <SourceList sources={sources} />
        {research && research.search_queries.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><SearchIcon className="size-3.5" aria-hidden="true" />Zapytania użyte w wyszukiwaniu:</span>
            {research.search_queries.map((query) => <span key={query} className="rounded-md bg-muted px-1.5 py-0.5 text-foreground/80">{query}</span>)}
          </div>
        )}
        {sourcesSlot}
      </ResultBlock>
    </div>
  );
}

function duration(from: string, to: string): string {
  const seconds = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  return seconds % 60 ? `${minutes} min ${seconds % 60} s` : `${minutes} min`;
}
