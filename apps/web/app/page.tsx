"use client";

import { useCallback, useEffect, useState } from "react";
import { DownloadIcon, Loader2Icon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { CandidatesTable } from "@/components/candidates-table";
import { FilterSelect } from "@/components/filter-select";
import { StatsCards } from "@/components/stats-cards";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import {
  CANDIDATE_CATEGORIES,
  CANDIDATE_STATUSES,
  type Candidate,
  type CandidateCategory,
  type CandidatePage,
  type CandidateQuery,
  type CandidateSort,
  type CandidateStatus,
  type DashboardStats,
  type Source,
} from "@/types/api";

const PAGE_SIZE = 25;

const SCORE_OPTIONS = [
  { value: "90", label: "Score ≥ 90" },
  { value: "75", label: "Score ≥ 75" },
  { value: "50", label: "Score ≥ 50" },
];

const SORT_OPTIONS: { value: CandidateSort; label: string }[] = [
  { value: "total_score", label: "Sort: score" },
  { value: "original_published_at", label: "Sort: published" },
  { value: "created_at", label: "Sort: fetched" },
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
  const [loadError, setLoadError] = useState<string | null>(null);

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
  }, []);

  const updateQuery = (patch: Partial<CandidateQuery>) =>
    setQuery((current) => ({ ...current, page: 1, ...patch }));

  async function handleFetchAll() {
    setAction("fetch");
    try {
      const result = await api.fetchAllSources();
      toast.success(`Fetched ${result.sources_processed} sources`, {
        description: `${result.new_candidates} new · ${result.duplicates} duplicates · ${result.skipped_old} too old · ${result.errors} errors`,
      });
      await load();
    } catch (error) {
      toast.error("Fetch failed", { description: errorText(error) });
    } finally {
      setAction(null);
    }
  }

  async function handleClassifyPending() {
    setAction("classify");
    try {
      const result = await api.classifyPending();
      toast.success(`Classified ${result.classified} of ${result.processed}`, {
        description: result.errors ? `${result.errors} errors — see API logs` : undefined,
      });
      await load();
    } catch (error) {
      toast.error("Classification failed", { description: errorText(error) });
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
      toast.error("Action failed", { description: errorText(error) });
    } finally {
      setBusyId(null);
    }
  }

  const totalPages = page ? Math.max(1, Math.ceil(page.total / PAGE_SIZE)) : 1;
  const currentPage = query.page ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
          <p className="text-sm text-muted-foreground">
            New topics from RSS sources, scored by the LLM classifier.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleFetchAll} disabled={action !== null}>
            {action === "fetch" ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />}
            Fetch all
          </Button>
          <Button onClick={handleClassifyPending} disabled={action !== null}>
            {action === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
            Classify pending
          </Button>
        </div>
      </div>

      <StatsCards stats={stats} />

      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect
          label="Statuses"
          value={query.status}
          options={CANDIDATE_STATUSES.map((value) => ({ value, label: value }))}
          onChange={(value) => updateQuery({ status: value as CandidateStatus | undefined })}
        />
        <FilterSelect
          label="Categories"
          value={query.category}
          options={CANDIDATE_CATEGORIES.map((value) => ({ value, label: value }))}
          onChange={(value) => updateQuery({ category: value as CandidateCategory | undefined })}
        />
        <FilterSelect
          label="Sources"
          value={query.source_id?.toString()}
          options={sources.map((source) => ({ value: String(source.id), label: source.name }))}
          onChange={(value) => updateQuery({ source_id: value ? Number(value) : undefined })}
        />
        <FilterSelect
          label="Scores"
          value={query.min_score?.toString()}
          options={SCORE_OPTIONS}
          onChange={(value) => updateQuery({ min_score: value ? Number(value) : undefined })}
        />
        <FilterSelect
          label="Sort"
          allowAll={false}
          value={query.sort}
          options={SORT_OPTIONS}
          onChange={(value) => updateQuery({ sort: (value as CandidateSort) ?? "total_score" })}
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => updateQuery({ order: query.order === "desc" ? "asc" : "desc" })}
        >
          {query.order === "desc" ? "↓ Desc" : "↑ Asc"}
        </Button>
      </div>

      {loadError && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {loadError}
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
              `Marked as ${status}`,
            )
          }
          onClassify={(candidate) =>
            runRowAction(candidate, () => api.classifyCandidate(candidate.id), "Classified")
          }
        />
      )}

      {page && page.total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {page.total} {page.total === 1 ? "candidate" : "candidates"} · page {currentPage} of {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => setQuery((q) => ({ ...q, page: currentPage - 1 }))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setQuery((q) => ({ ...q, page: currentPage + 1 }))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
