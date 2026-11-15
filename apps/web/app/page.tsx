"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownWideNarrowIcon, ArrowUpNarrowWideIcon, DownloadIcon, FilterXIcon, Loader2Icon, SparklesIcon,
} from "lucide-react";
import { toast } from "sonner";

import { CandidatesTable } from "@/components/candidates-table";
import { PipelineOverview } from "@/components/dashboard/pipeline-overview";
import { StatusStrip } from "@/components/dashboard/status-strip";
import { FilterSelect } from "@/components/filter-select";
import { StatsCards } from "@/components/stats-cards";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { RunSummary } from "@/components/run-summary";
import { api, errorText } from "@/lib/api";
import { CANDIDATE_WORKFLOW_LABELS } from "@/lib/candidate-status";
import { plural } from "@/lib/pagination";
import {
  CANDIDATE_CATEGORIES,
  type AutomationSettings,
  type Candidate,
  type CandidateCategory,
  type CandidatePage,
  type CandidateQuery,
  type CandidateSort,
  type CandidateWorkflowStatus,
  type DashboardStats,
  type Source,
  type Usage,
} from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  news: "Wiadomości", guide: "Poradnik", comparison: "Porównanie", case_study: "Studium przypadku", explainer: "Wyjaśnienie",
};

const FETCH_KEY = "content-engine:fetch-result";
const CLASSIFY_KEY = "content-engine:classify-result";

const PAGE_SIZE = 25;
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const SCORE_OPTIONS = [
  { value: "90", label: "Wynik ≥ 90" },
  { value: "75", label: "Wynik ≥ 75" },
  { value: "50", label: "Wynik ≥ 50" },
];

const SORT_OPTIONS: { value: CandidateSort; label: string }[] = [
  { value: "total_score", label: "Wynik oceny" },
  { value: "original_published_at", label: "Data publikacji" },
  { value: "created_at", label: "Data pobrania" },
];

export default function DashboardPage() {
  const [query, setQuery] = useState<CandidateQuery>({
    sort: "total_score",
    order: "desc",
    page: 1,
    page_size: PAGE_SIZE,
  });
  const [page, setPage] = useState<CandidatePage | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [action, setAction] = useState<"fetch" | "classify" | null>(null);
  const [fetchSummary, setFetchSummary] = useState<string | null>(null);
  const [classifySummary, setClassifySummary] = useState<string | null>(null);
  const [activeCount, setActiveCount] = useState(0);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [automation, setAutomation] = useState<AutomationSettings | null>(null);

  const load = useCallback(async () => {
    try {
      const [candidates, dashboardStats] = await Promise.all([
        api.listCandidates(query),
        api.stats(),
      ]);
      setPage(candidates);
      setStats(dashboardStats);
      setLoadError(null);
    } catch (error) {
      setLoadError(errorText(error));
    }
  }, [query]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on query change
    void load();
  }, [load]);

  useEffect(() => {
    api.listSources().then(setSources).catch(() => setSources([]));
    api.automation().then(setAutomation, () => setAutomation(null));
  }, []);

  const loadUsage = useCallback(() => api.usage().then(setUsage, () => setUsage(null)), []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- restore results from this browser session
    setFetchSummary(sessionStorage.getItem(FETCH_KEY));
    setClassifySummary(sessionStorage.getItem(CLASSIFY_KEY));
  }, []);

  useEffect(() => {
    if (fetchSummary) sessionStorage.setItem(FETCH_KEY, fetchSummary);
    if (classifySummary) sessionStorage.setItem(CLASSIFY_KEY, classifySummary);
  }, [fetchSummary, classifySummary]);

  // Odczytujemy globalną kolejkę także po przeładowaniu strony.
  useEffect(() => {
    let disposed = false;
    let previous = "";
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const jobs = await api.activeJobs();
        if (disposed) return;
        setActiveCount(jobs.total);
        setQueueError(null);
        const signature = JSON.stringify(jobs.items.map((job) => [job.id, job.status]));
        if (signature !== previous) { previous = signature; void loadUsage(); await load(); }
        timer = setTimeout(() => void poll(), jobs.total ? 2000 : 10000);
      } catch (error) {
        if (!disposed) { setQueueError(errorText(error)); timer = setTimeout(() => void poll(), 5000); }
      }
    }
    void poll();
    const visible = () => { if (document.visibilityState === "visible") { clearTimeout(timer); void load(); void poll(); } };
    document.addEventListener("visibilitychange", visible);
    return () => { disposed = true; clearTimeout(timer); document.removeEventListener("visibilitychange", visible); };
  }, [load, loadUsage]);

  function clearSummaries() {
    setFetchSummary(null);
    setClassifySummary(null);
    sessionStorage.removeItem(FETCH_KEY);
    sessionStorage.removeItem(CLASSIFY_KEY);
  }

  const updateQuery = (patch: Partial<CandidateQuery>) =>
    setQuery((current) => ({ ...current, page: 1, ...patch }));

  async function handleFetchAll() {
    setAction("fetch");
    setFetchSummary(null);
    try {
      const result = await api.fetchAllSources();
      setFetchSummary(`${result.sources_processed} źródeł · ${result.new_candidates} nowych tematów · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych · ${result.errors} błędów`);
      await api.listSources().then(setSources).catch(() => undefined);
      toast.success(`Pobrano ${result.sources_processed} źródeł`, {
        description: `${result.new_candidates} nowych · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych · ${result.errors} błędów`,
      });
      await load();
    } catch (error) {
      setFetchSummary(`Błąd pobierania: ${errorText(error)}`);
      toast.error("Nie udało się pobrać RSS", { description: errorText(error) });
    } finally {
      setAction(null);
    }
  }

  async function handleClassifyPending() {
    setAction("classify");
    setClassifySummary(null);
    try {
      const result = await api.classifyPending();
      setClassifySummary(`W kolejce: ${result.enqueued} nowych zadań · ${result.existing} już zapisanych · ${result.skipped_busy} zajętych tematów`
        + (result.skipped_budget ? ` · ${result.skipped_budget} pominiętych (wyczerpany budżet AI)` : ""));
      toast.success("Ocena tematów zapisana w kolejce");
      void loadUsage();
      await load();
    } catch (error) {
      setClassifySummary(`Błąd oceny: ${errorText(error)}`);
      toast.error("Nie udało się zlecić oceny", { description: errorText(error) });
    } finally {
      setAction(null);
    }
  }

  async function runRowAction(candidate: Candidate, fn: () => Promise<unknown>, message: string) {
    setBusyId(candidate.id);
    try {
      await fn();
      toast.success(message);
      await load();
    } catch (error) {
      toast.error("Akcja nie powiodła się", { description: errorText(error) });
    } finally {
      setBusyId(null);
    }
  }

  const pageSize = query.page_size ?? PAGE_SIZE;
  const currentPage = query.page ?? 1;

  function goToPage(next: number) {
    setQuery((current) => ({ ...current, page: next }));
    document.getElementById("topics-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  const filtersActive = Boolean(query.workflow_status || query.category || query.source_id || query.min_score || query.duplicates);
  const summaryFailed = (text: string | null) => Boolean(text?.startsWith("Błąd"));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Redakcja"
        title="Tematy"
        description="Pobieraj tematy z RSS, oceniaj je z AI i prowadź najlepsze przez research i QA aż do publikacji w WordPress."
        actions={<>
          <Button size="lg" variant="outline" className="bg-card" onClick={handleFetchAll} disabled={action !== null}>
            {action === "fetch" ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />} Pobierz RSS
          </Button>
          <Button size="lg" className="bg-emerald-700 text-white shadow-sm shadow-emerald-700/20 hover:bg-emerald-800" onClick={handleClassifyPending} disabled={action !== null}>
            {action === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />} Oceń nieocenione · płatne
          </Button>
        </>}
        actionsNote={action === "fetch" ? "Pobieranie w toku…" : action === "classify" ? "Zlecanie oceny AI…" : "Obejmuje wszystkie aktywne źródła i nieocenione tematy – niezależnie od filtrów."}
      />

      <RunSummary
        title="Wyniki uruchomień w tej sesji"
        onClear={clearSummaries}
        lines={[
          ...(fetchSummary ? [{ text: `Pobieranie RSS: ${fetchSummary}`, failed: summaryFailed(fetchSummary) }] : []),
          ...(classifySummary ? [{ text: `Ocena AI: ${classifySummary}`, failed: summaryFailed(classifySummary) }] : []),
        ]}
      />

      <StatusStrip activeCount={activeCount} queueError={queueError} usage={usage} automation={automation} />
      <StatsCards stats={stats} />
      <PipelineOverview />

      <section aria-labelledby="topics-heading" className="overflow-hidden rounded-xl bg-card shadow-xs ring-1 ring-foreground/8">
        <div className="space-y-4 border-b p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="topics-heading" className="text-lg font-semibold">Lista tematów</h2>
            <span className="text-sm text-muted-foreground tabular-nums">{page ? `${page.total} ${plural(page.total, "temat", "tematy", "tematów")}` : "Wczytywanie…"}</span>
          </div>
          <div className="flex flex-wrap items-end gap-2">
            <FilterSelect
              label="Status"
              value={query.workflow_status}
              options={(Object.entries(CANDIDATE_WORKFLOW_LABELS)).map(([value, label]) => ({ value, label }))}
              onChange={(value) => updateQuery({ workflow_status: value as CandidateWorkflowStatus | undefined })}
            />
            <FilterSelect
              label="Kategoria"
              value={query.category}
              options={CANDIDATE_CATEGORIES.map((value) => ({ value, label: CATEGORY_LABELS[value] ?? value }))}
              onChange={(value) => updateQuery({ category: value as CandidateCategory | undefined })}
            />
            <FilterSelect
              label="Źródło"
              value={query.source_id?.toString()}
              options={sources.map((source) => ({ value: String(source.id), label: source.name }))}
              onChange={(value) => updateQuery({ source_id: value ? Number(value) : undefined })}
            />
            <FilterSelect
              label="Minimalny wynik"
              value={query.min_score?.toString()}
              options={SCORE_OPTIONS}
              onChange={(value) => updateQuery({ min_score: value ? Number(value) : undefined })}
            />
            <FilterSelect
              label="Sortowanie"
              allowAll={false}
              value={query.sort}
              options={SORT_OPTIONS}
              onChange={(value) => updateQuery({ sort: (value as CandidateSort) ?? "total_score" })}
            />
            <Button
              variant="outline"
              aria-label={`Kolejność sortowania: ${query.order === "desc" ? "malejąca" : "rosnąca"}. Zmień kolejność`}
              onClick={() => updateQuery({ order: query.order === "desc" ? "asc" : "desc" })}
            >
              {query.order === "desc" ? <><ArrowDownWideNarrowIcon /> Malejąco</> : <><ArrowUpNarrowWideIcon /> Rosnąco</>}
            </Button>
            <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-lg px-2 text-sm text-muted-foreground hover:text-foreground">
              <input type="checkbox" className="size-4 accent-emerald-700" checked={query.duplicates === 1} onChange={(event) => updateQuery({ duplicates: event.target.checked ? 1 : undefined })} />
              Pokaż duplikaty
            </label>
            {filtersActive && (
              <Button variant="ghost" className="text-muted-foreground" onClick={() => updateQuery({ workflow_status: undefined, category: undefined, source_id: undefined, min_score: undefined, duplicates: undefined })}>
                <FilterXIcon /> Wyczyść filtry
              </Button>
            )}
          </div>
        </div>

        {loadError && (
          <div role="alert" className="m-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {loadError}
          </div>
        )}

        {!page && !loadError && (
          <div className="space-y-2 p-5" aria-hidden="true">
            {[0, 1, 2, 3].map((row) => <div key={row} className="h-12 animate-pulse rounded-lg bg-muted" />)}
          </div>
        )}

        {page && (
          <CandidatesTable
            candidates={page.items}
            busyId={busyId}
            onStatusChange={(candidate, status) =>
              runRowAction(
                candidate,
                () => api.updateCandidateStatus(candidate.id, status),
                status === "approved" ? "Temat zatwierdzony" : "Temat pominięty",
              )
            }
            onClassify={(candidate) =>
              runRowAction(candidate, () => api.classifyCandidate(candidate.id), "Ocena zapisana w kolejce")
            }
          />
        )}

        {page && page.total > 0 && (
          <Pagination
            className="border-t px-4 py-3 sm:px-5"
            label="Paginacja listy tematów"
            page={currentPage}
            pageSize={pageSize}
            total={page.total}
            summary={`${(currentPage - 1) * pageSize + 1}–${Math.min(page.total, currentPage * pageSize)} z ${page.total} ${plural(page.total, "tematu", "tematów", "tematów")}`}
            onPageChange={goToPage}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            onPageSizeChange={(size) => updateQuery({ page_size: size })}
          />
        )}
      </section>
    </div>
  );
}
