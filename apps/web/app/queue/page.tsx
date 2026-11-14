"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCwIcon, ListTodoIcon, PauseCircleIcon } from "lucide-react";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cancelAction, KIND_LABELS, STATUS_LABELS, STATUS_STYLES, stageLabel } from "@/lib/jobs";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/components/filter-select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { JobDetails } from "@/components/queue/job-details";
import type { AutomationSettings, Job, JobPage, JobStats, QueueQuery } from "@/types/api";

const STATUSES = Object.keys(STATUS_LABELS) as Job["status"][];
const PAGE_SIZE = 25;

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
      const [list, counts, settings] = await Promise.all([api.queueJobs(query), api.queueStats(), api.automation()]);
      if (number !== requestNumber.current) return;
      // Gdy liczba wyników maleje podczas pracy, wracamy na istniejącą stronę.
      const lastPage = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
      if ((query.page ?? 1) > lastPage) { setQuery((current) => ({ ...current, page: lastPage })); return; }
      setPage(list); setStats(counts); setAutomation(settings); setError(null); setUpdatedAt(new Date().toISOString());
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
  const pages = Math.max(1, Math.ceil((page?.total ?? 0) / PAGE_SIZE));

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight"><ListTodoIcon />Kolejka zadań</h1>
        <p className="mt-1 text-sm text-muted-foreground">Bieżąca praca i historia wszystkich zadań AI. Stan pochodzi z bazy. Zadania działają w tle także po zamknięciu przeglądarki.</p>
      </div>
      <Button variant="outline" size="sm" disabled={refreshing} onClick={() => void load()}><RefreshCwIcon className={refreshing ? "animate-spin" : ""} />Odśwież</Button>
    </div>

    {automation?.paused_at && <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
      <p className="flex items-center gap-2"><PauseCircleIcon className="size-5" />Workspace jest wstrzymany od {formatDate(automation.paused_at)}. Worker nie bierze jego zadań, a nowe nie są przyjmowane.</p>
      {automation.can_edit && <Button size="sm" disabled={busy === "resume"} onClick={() => void resume()}>{busy === "resume" ? "Wznawianie…" : "Wznów"}</Button>}
    </div>}
    {notice && <p role="status" className="rounded-lg bg-muted p-3 text-sm">{notice}</p>}
    {automation?.can_edit && waiting > 0 && <div className="flex flex-wrap items-center gap-2">
      {!confirmCancelAll
        ? <Button size="sm" variant="outline" onClick={() => setConfirmCancelAll(true)}>Anuluj wszystkie oczekujące ({waiting})</Button>
        : <><Button size="sm" variant="destructive" disabled={busy === "cancel-all"} onClick={() => void cancelAll()}>{busy === "cancel-all" ? "Anulowanie…" : `Potwierdź anulowanie ${waiting} zadań`}</Button>
          <Button size="sm" variant="ghost" onClick={() => setConfirmCancelAll(false)}>Nie anuluj</Button></>}
      <p className="text-xs text-muted-foreground">Dotyczy zadań w kolejce i czekających na ponowienie. Trwające zadania zatrzymasz pojedynczo.</p>
    </div>}
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
      <CountCard label="Wszystkie" value={stats?.total} selected={query.status === "all"} onClick={() => filter({ status: "all" })} />
      {STATUSES.map((status) => <CountCard key={status} label={STATUS_LABELS[status]} value={stats?.[status]} selected={query.status === status} onClick={() => filter({ status })} />)}
    </div>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-2">
        <FilterSelect label="Status" allowAll={false} value={query.status} options={[
          { value: "all", label: "Wszystkie statusy" }, { value: "active", label: "Aktywne zadania" },
          ...STATUSES.map((status) => ({ value: status, label: STATUS_LABELS[status] })),
        ]} onChange={(value) => filter({ status: value as QueueQuery["status"] })} />
        <FilterSelect label="Etap" allowAll={false} value={query.kind ?? "all"} options={[
          { value: "all", label: "Wszystkie etapy" }, ...Object.entries(KIND_LABELS).map(([value, label]) => ({ value, label })),
        ]} onChange={(value) => filter({ kind: value === "all" ? undefined : value as Job["kind"] })} />
      </div>
      <p className="text-xs text-muted-foreground" role="status">Co 2 s · {updatedAt ? `odświeżono ${formatDate(updatedAt)}` : "Ładowanie…"}</p>
    </div>
    <p className="text-xs text-muted-foreground">Liczniki obejmują całą historię. Filtry dotyczą listy poniżej.</p>
    {error && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">Nie udało się odświeżyć kolejki: {error}. Ostatni odczyt pozostaje widoczny.</p>}
    <div className="min-w-0 rounded-xl border bg-card">
      <Table aria-label="Zadania w kolejce">
        <TableHeader><TableRow><TableHead scope="col">Temat / zadanie</TableHead><TableHead scope="col">Etap</TableHead><TableHead scope="col">Status</TableHead><TableHead scope="col">Postęp</TableHead><TableHead scope="col">Próby</TableHead><TableHead scope="col">Utworzono</TableHead><TableHead scope="col"><span className="sr-only">Szczegóły</span></TableHead></TableRow></TableHeader>
        <TableBody>
          {!page && <TableRow><TableCell colSpan={7}>Ładowanie zadań…</TableCell></TableRow>}
          {page?.items.length === 0 && <TableRow><TableCell colSpan={7} className="py-12 text-center text-muted-foreground">Brak zadań pasujących do filtrów.</TableCell></TableRow>}
          {page?.items.map((job) => <TableRow key={job.id}>
            <TableCell className="max-w-80 whitespace-normal">
              <Link href={`/candidates/${job.candidate_id}`} className="line-clamp-2 font-medium hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">{job.candidate_title ?? `Temat #${job.candidate_id}`}</Link>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{job.id.slice(0, 8)}…</p>
              {job.error_code && job.status !== "succeeded" && <p className="mt-1 text-xs text-destructive" title={job.error_code}>{job.error_message ?? job.error_code}</p>}
            </TableCell>
            <TableCell>{KIND_LABELS[job.kind]}</TableCell>
            <TableCell><span className={`rounded-full px-2 py-1 text-xs font-medium ring-1 ${STATUS_STYLES[job.status]}`}>{STATUS_LABELS[job.status]}</span></TableCell>
            <TableCell>{stageLabel(job.stage)}{job.status === "retrying" && <p className="text-xs text-muted-foreground">Najwcześniej {formatDate(job.available_at)}</p>}</TableCell>
            <TableCell className="font-mono">{job.attempt_count}/{job.max_attempts}</TableCell>
            <TableCell className="text-xs text-muted-foreground">{formatDate(job.created_at)}</TableCell>
            <TableCell className="whitespace-nowrap">
              <CancelButton job={job} busy={busy === job.id} onCancel={() => void cancelJob(job)} />
              <Button size="sm" variant="ghost" aria-label={`Szczegóły zadania ${job.id}`} onClick={() => setSelected(job)}>Szczegóły</Button>
            </TableCell>
          </TableRow>)}
        </TableBody>
      </Table>
    </div>
    {page && <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
      <p>{page.total} zadań · strona {currentPage}/{pages}</p>
      <div className="flex gap-2"><Button size="sm" variant="outline" disabled={currentPage <= 1} onClick={() => setQuery((current) => ({ ...current, page: currentPage-1 }))}>Poprzednia</Button>
        <Button size="sm" variant="outline" disabled={currentPage >= pages} onClick={() => setQuery((current) => ({ ...current, page: currentPage+1 }))}>Następna</Button></div>
    </div>}
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
  return <Button size="sm" variant="outline" disabled={busy || action === "stopping"} aria-label={`${label}: zadanie ${job.id}`} onClick={onCancel}>{busy ? "…" : label}</Button>;
}

function CountCard({ label, value, selected, onClick }: { label: string; value?: number; selected: boolean; onClick: () => void }) {
  return <button onClick={onClick} aria-pressed={selected} aria-label={`Filtr: ${label}`} className={`rounded-xl border bg-card p-4 text-left transition-colors hover:bg-muted/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${selected ? "border-primary ring-1 ring-primary" : ""}`}>
    <p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tabular-nums">{value ?? "—"}</p>
  </button>;
}
