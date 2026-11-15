"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  BanIcon, CircleCheckIcon, CircleXIcon, ClockIcon, FilterXIcon, InboxIcon, LayersIcon, Loader2Icon, PauseCircleIcon,
  InfoIcon, RefreshCwIcon, RotateCwIcon, type LucideIcon,
} from "lucide-react";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { plural } from "@/lib/pagination";
import { cn } from "@/lib/utils";
import { cancelAction, KIND_LABELS, STATUS_LABELS, STATUS_STYLES, stageLabel } from "@/lib/jobs";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { STAT_TONES, type StatTone } from "@/components/ui/stat-tile";
import { RunSummary } from "@/components/run-summary";
import { FilterSelect } from "@/components/filter-select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { JobDetails } from "@/components/queue/job-details";
import type { AutomationSettings, Job, JobPage, JobStats, QueueQuery } from "@/types/api";

const STATUSES = Object.keys(STATUS_LABELS) as Job["status"][];
const PAGE_SIZE = 25;
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const STATUS_ICONS: Record<Job["status"], LucideIcon> = {
  queued: ClockIcon, running: Loader2Icon, retrying: RotateCwIcon, succeeded: CircleCheckIcon, failed: CircleXIcon, cancelled: BanIcon,
};
const STATUS_TONES: Record<Job["status"], StatTone> = {
  queued: "zinc", running: "sky", retrying: "amber", succeeded: "emerald", failed: "rose", cancelled: "zinc",
};

export default function QueuePage() {
  const [query, setQuery] = useState<QueueQuery>({ status: "all", page: 1, page_size: PAGE_SIZE });
  const [page, setPage] = useState<JobPage | null>(null);
  const [stats, setStats] = useState<JobStats | null>(null);
  const [selected, setSelected] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [automation, setAutomation] = useState<AutomationSettings | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmCancelAll, setConfirmCancelAll] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const requestNumber = useRef(0);

  const load = useCallback(async () => {
    // Starsza odpowiedź nie może nadpisać nowszego filtra ani strony.
    const number = ++requestNumber.current;
    setRefreshing(true);
    try {
      // Ustawienia automatyki są pomocnicze: ich błąd nie może zablokować listy zadań.
      api.automation().then((settings) => { if (number === requestNumber.current) setAutomation(settings); }, () => undefined);
      const [list, counts] = await Promise.all([api.queueJobs(query), api.queueStats()]);
      if (number !== requestNumber.current) return;
      // Gdy liczba wyników maleje podczas pracy, wracamy na istniejącą stronę.
      const lastPage = Math.max(1, Math.ceil(list.total / (query.page_size ?? PAGE_SIZE)));
      if ((query.page ?? 1) > lastPage) { setQuery((current) => ({ ...current, page: lastPage })); return; }
      setPage(list); setStats(counts); setError(null); setUpdatedAt(new Date().toISOString());
    } catch (failure) { if (number === requestNumber.current) setError(errorText(failure)); }
    finally { if (number === requestNumber.current) setRefreshing(false); }
  }, [query]);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      await load();
      if (!disposed) timer = setTimeout(() => void poll(), 2000);
    }
    void poll();
    const visible = () => { if (document.visibilityState === "visible") void load(); };
    document.addEventListener("visibilitychange", visible);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- licznik unieważnia odpowiedzi HTTP; nie jest referencją DOM
    return () => { disposed = true; ++requestNumber.current; clearTimeout(timer); document.removeEventListener("visibilitychange", visible); };
  }, [load]);

  async function act(key: string, action: () => Promise<string | null>) {
    setBusy(key);
    try { setNotice(await action()); setError(null); await load(); }
    catch (failure) { setError(errorText(failure)); }
    finally { setBusy(null); }
  }
  const cancelJob = (job: Job) => act(job.id, async () => { await api.cancelJob(job.id); return null; });
  const cancelAll = () => act("cancel-all", async () => {
    const { cancelled } = await api.cancelPendingJobs();
    setConfirmCancelAll(false);
    return `Anulowano oczekujące zadania: ${cancelled}.`;
  });
  const resume = () => act("resume", async () => {
    const { resumed_jobs } = await api.resumeWorkspace();
    return `Workspace wznowiony. Wróciło do kolejki: ${resumed_jobs}.`;
  });
  const waiting = (stats?.queued ?? 0) + (stats?.retrying ?? 0);

  const filter = (patch: Partial<QueueQuery>) => setQuery((current) => ({ ...current, ...patch, page: 1 }));
  const currentPage = query.page ?? 1;
  const pageSize = query.page_size ?? PAGE_SIZE;
  const pages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));
  const filtersActive = query.status !== "all" || query.kind !== undefined;
  const running = stats?.running ?? 0;

  return <div className="space-y-6">
    <PageHeader
      eyebrow="Operacje"
      title="Kolejka zadań"
      description="Bieżąca praca i historia wszystkich zadań AI. Stan pochodzi z bazy – zadania działają w tle także po zamknięciu przeglądarki."
      actions={<Button size="lg" variant="outline" className="bg-card" disabled={refreshing} onClick={() => void load()}><RefreshCwIcon className={refreshing ? "animate-spin" : ""} />Odśwież</Button>}
      actionsNote={<span className="inline-flex items-center gap-2">
        <span className="relative flex size-2" aria-hidden="true">
          {running > 0 && <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
          <span className={cn("relative inline-flex size-2 rounded-full", error ? "bg-rose-500" : "bg-emerald-500")} />
        </span>
        Na żywo · co 2 s · {updatedAt ? `odświeżono ${formatDate(updatedAt)}` : "Ładowanie…"}
      </span>}
    />

    {automation?.paused_at && <div role="status" className="flex flex-wrap items-center gap-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-950 ring-1 ring-amber-300">
      <PauseCircleIcon className="size-5 shrink-0" aria-hidden="true" />
      <p className="min-w-0 flex-1">Workspace jest wstrzymany od {formatDate(automation.paused_at)}. Worker nie bierze jego zadań, a nowe nie są przyjmowane.</p>
      <Button size="sm" className="bg-amber-900 text-white hover:bg-amber-950" disabled={busy === "resume"} onClick={() => void resume()}>{busy === "resume" ? "Wznawianie…" : "Wznów"}</Button>
    </div>}

    <RunSummary title="Ostatnia akcja" lines={notice ? [{ text: notice }] : []} onClear={() => setNotice(null)} />

    <section aria-label="Liczniki zadań" className="space-y-2">
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 sm:gap-3 xl:grid-cols-7">
        <CountCard label="Wszystkie" icon={LayersIcon} tone="violet" value={stats?.total} selected={query.status === "all"} onClick={() => filter({ status: "all" })} />
        {STATUSES.map((status) => <CountCard key={status} label={STATUS_LABELS[status]} icon={STATUS_ICONS[status]} tone={STATUS_TONES[status]} spin={status === "running" && (stats?.running ?? 0) > 0} value={stats?.[status]} selected={query.status === status} onClick={() => filter({ status })} />)}
      </div>
      <p className="text-xs text-muted-foreground">Liczniki obejmują całą historię. Kliknij kafel, aby przefiltrować listę.</p>
    </section>

    {waiting > 0 && <div className="flex flex-wrap items-center gap-3 rounded-xl bg-card px-4 py-3 shadow-xs ring-1 ring-foreground/8">
      <ClockIcon className="size-5 shrink-0 text-amber-600" aria-hidden="true" />
      <p className="min-w-0 flex-1 text-sm text-muted-foreground"><span className="font-medium text-foreground">Czeka {waiting} {plural(waiting, "zadanie", "zadania", "zadań")}.</span> Anulowanie obejmuje zadania w kolejce i czekające na ponowienie. Trwające zatrzymasz pojedynczo.</p>
      <div className="flex flex-wrap gap-2">
        {!confirmCancelAll
          ? <Button size="sm" variant="outline" onClick={() => setConfirmCancelAll(true)}>Anuluj wszystkie oczekujące ({waiting})</Button>
          : <><Button size="sm" variant="destructive" disabled={busy === "cancel-all"} onClick={() => void cancelAll()}>{busy === "cancel-all" ? "Anulowanie…" : `Potwierdź anulowanie ${waiting} zadań`}</Button>
            <Button size="sm" variant="ghost" onClick={() => setConfirmCancelAll(false)}>Nie anuluj</Button></>}
      </div>
    </div>}

    <section aria-labelledby="jobs-heading" className="overflow-hidden rounded-xl bg-card shadow-xs ring-1 ring-foreground/8">
      <div className="space-y-4 border-b p-4 sm:p-5">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="jobs-heading" className="text-lg font-semibold">Lista zadań</h2>
          <span className="text-sm text-muted-foreground tabular-nums">{page ? `${page.total} ${plural(page.total, "zadanie", "zadania", "zadań")}` : "Wczytywanie…"}</span>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <FilterSelect label="Status" allowAll={false} value={query.status} options={[
            { value: "all", label: "Wszystkie statusy" }, { value: "active", label: "Aktywne zadania" },
            ...STATUSES.map((status) => ({ value: status, label: STATUS_LABELS[status] })),
          ]} onChange={(value) => filter({ status: value as QueueQuery["status"] })} />
          <FilterSelect label="Etap" allowAll={false} value={query.kind ?? "all"} options={[
            { value: "all", label: "Wszystkie etapy" }, ...Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label })),
          ]} onChange={(value) => filter({ kind: value === "all" ? undefined : value as Job["kind"] })} />
          {filtersActive && <Button variant="ghost" className="text-muted-foreground" onClick={() => filter({ status: "all", kind: undefined })}><FilterXIcon /> Wyczyść filtry</Button>}
        </div>
      </div>

      {error && <p role="alert" className="m-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">Nie udało się odświeżyć kolejki: {error}. Ostatni odczyt pozostaje widoczny.</p>}

      <div className="min-w-0 overflow-x-auto">
        <Table aria-label="Zadania w kolejce">
          <TableHeader><TableRow className="bg-muted/40 hover:bg-muted/40 [&>th]:h-10 [&>th]:text-xs [&>th]:font-medium [&>th]:uppercase [&>th]:tracking-wider [&>th]:text-muted-foreground">
            <TableHead scope="col" className="pl-4 sm:pl-5">Temat / zadanie</TableHead>
            <TableHead scope="col" className="hidden md:table-cell">Etap</TableHead>
            <TableHead scope="col" className="hidden sm:table-cell">Status</TableHead>
            <TableHead scope="col" className="hidden lg:table-cell">Postęp</TableHead>
            <TableHead scope="col" className="hidden md:table-cell">Próby</TableHead>
            <TableHead scope="col" className="hidden lg:table-cell">Utworzono</TableHead>
            <TableHead scope="col" className="pr-4 sm:pr-5"><span className="sr-only">Akcje</span></TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {!page && <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground"><Loader2Icon className="mr-2 inline size-4 animate-spin" aria-hidden="true" />Ładowanie zadań…</TableCell></TableRow>}
            {page?.items.length === 0 && <TableRow><TableCell colSpan={7} className="py-16 text-center whitespace-normal">
              <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground" aria-hidden="true"><InboxIcon className="size-6" /></span>
              <p className="text-muted-foreground">Brak zadań pasujących do filtrów.</p>
            </TableCell></TableRow>}
            {page?.items.map((job) => {
              return <TableRow key={job.id}>
                <TableCell className="max-w-80 py-3 pl-4 whitespace-normal sm:min-w-48 sm:pl-5">
                  <Link href={`/candidates/${job.candidate_id}`} className="line-clamp-2 font-medium underline-offset-4 hover:text-emerald-800 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">{job.candidate_title ?? `Temat #${job.candidate_id}`}</Link>
                  <p className="mt-1 text-xs text-muted-foreground"><span className="md:hidden">{KIND_LABELS[job.kind]}<span className="lg:hidden"> · {formatDate(job.created_at)}</span></span><span className="hidden font-mono md:inline">{job.id.slice(0, 8)}…<span className="lg:hidden"> · {formatDate(job.created_at)}</span></span></p>
                  {job.error_code && job.status !== "succeeded" && <p className="mt-1 line-clamp-2 text-xs text-destructive" title={job.error_code}>{job.error_message ?? job.error_code}</p>}
                  <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground sm:hidden">
                    <StatusBadge status={job.status} />{stageLabel(job.stage)}
                  </p>
                </TableCell>
                <TableCell className="hidden md:table-cell">{KIND_LABELS[job.kind]}</TableCell>
                <TableCell className="hidden sm:table-cell">
                  <StatusBadge status={job.status} />
                  <p className="mt-1 text-xs text-muted-foreground lg:hidden">{stageLabel(job.stage)}</p>
                </TableCell>
                <TableCell className="hidden text-sm lg:table-cell">{stageLabel(job.stage)}{job.status === "retrying" && <p className="text-xs text-muted-foreground">Najwcześniej {formatDate(job.available_at)}</p>}</TableCell>
                <TableCell className="hidden md:table-cell"><Attempts count={job.attempt_count} max={job.max_attempts} /></TableCell>
                <TableCell className="hidden text-xs text-muted-foreground lg:table-cell">{formatDate(job.created_at)}</TableCell>
                <TableCell className="pr-4 sm:pr-5">
                  <div className="flex flex-col items-end gap-1 whitespace-nowrap sm:flex-row sm:justify-end">
                    <CancelButton job={job} busy={busy === job.id} onCancel={() => void cancelJob(job)} />
                    <Button size="sm" variant="ghost" aria-label={`Szczegóły zadania ${job.id}`} onClick={() => setSelected(job)}><InfoIcon className="sm:hidden" aria-hidden="true" /><span className="hidden sm:inline">Szczegóły</span></Button>
                  </div>
                </TableCell>
              </TableRow>;
            })}
          </TableBody>
        </Table>
      </div>

      {page && <Pagination
        className="border-t px-4 py-3 sm:px-5"
        label="Paginacja kolejki zadań"
        page={currentPage}
        pageSize={pageSize}
        total={page.total}
        summary={`${page.total} zadań · strona ${currentPage}/${pages}`}
        onPageChange={(next) => setQuery((current) => ({ ...current, page: next }))}
        pageSizeOptions={PAGE_SIZE_OPTIONS}
        onPageSizeChange={(size) => filter({ page_size: size })}
      />}
    </section>

    <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null); }}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader><DialogTitle>Szczegóły zadania</DialogTitle><DialogDescription>Postęp, błędy i wywołania zapisane dla każdej próby.</DialogDescription></DialogHeader>
        {selected && <JobDetails key={selected.id} initial={selected} onRetried={(job) => { setSelected(job); void load(); }} onCancelled={() => void load()} />}
      </DialogContent>
    </Dialog>
  </div>;
}

function CancelButton({ job, busy, onCancel }: { job: Job; busy: boolean; onCancel: () => void }) {
  const action = cancelAction(job);
  if (!action) return null;
  const label = action === "cancel" ? "Anuluj" : action === "stop" ? "Zatrzymaj po bieżącym kroku" : "Zatrzymywanie…";
  const short = action === "stop" ? "Zatrzymaj" : label;
  return <Button size="sm" variant="outline" className="hover:bg-rose-50 hover:text-rose-700" disabled={busy || action === "stopping"} aria-label={`${label}: zadanie ${job.id}`} title={label} onClick={onCancel}>
    {busy ? "…" : <><span className="lg:hidden">{short}</span><span className="hidden lg:inline">{label}</span></>}
  </Button>;
}

function StatusBadge({ status }: { status: Job["status"] }) {
  const Icon = STATUS_ICONS[status];
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${STATUS_STYLES[status]}`}>
    <Icon className={cn("size-3", status === "running" && "animate-spin")} aria-hidden="true" />{STATUS_LABELS[status]}
  </span>;
}

function Attempts({ count, max }: { count: number; max: number }) {
  return <span className="flex items-center gap-2" title={`Próba ${count} z ${max}`}>
    <span className="font-mono text-sm tabular-nums">{count}/{max}</span>
    <span className="flex gap-0.5" aria-hidden="true">
      {Array.from({ length: Math.min(max, 6) }, (_, index) => <span key={index} className={cn("h-1.5 w-2 rounded-full", index < count ? (count > 1 ? "bg-amber-400" : "bg-emerald-500") : "bg-muted")} />)}
    </span>
  </span>;
}

function CountCard({ label, value, selected, onClick, icon: Icon, tone, spin = false }: {
  label: string; value?: number; selected: boolean; onClick: () => void; icon: LucideIcon; tone: StatTone; spin?: boolean;
}) {
  return <button type="button" onClick={onClick} aria-pressed={selected} aria-label={`Filtr: ${label}`}
    className={cn("flex min-w-0 flex-col gap-2 rounded-xl bg-card p-3 text-left shadow-xs sm:gap-3 sm:p-4 ring-1 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
      selected ? "ring-2 ring-emerald-600" : "ring-foreground/8 hover:-translate-y-0.5 hover:shadow-sm")}>
    <span className="flex items-center justify-between gap-2">
      <span className="truncate text-xs font-medium text-muted-foreground sm:text-sm">{label}</span>
      <span className={cn("hidden size-8 shrink-0 items-center justify-center sm:flex rounded-lg ring-1", STAT_TONES[tone])} aria-hidden="true"><Icon className={cn("size-4", spin && "animate-spin")} /></span>
    </span>
    {value === undefined ? <Skeleton className="h-8 w-12" /> : <span className="text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">{value}</span>}
  </button>;
}
