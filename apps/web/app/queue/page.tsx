"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCwIcon, ListTodoIcon } from "lucide-react";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { KIND_LABELS, STATUS_LABELS, STATUS_STYLES, stageLabel } from "@/lib/jobs";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/components/filter-select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { JobDetails } from "@/components/queue/job-details";
import type { Job, JobPage, JobStats, QueueQuery } from "@/types/api";

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
  const requestNumber = useRef(0);

  const load = useCallback(async () => {
    // Starsza odpowiedź nie może nadpisać nowszego filtra ani strony.
    const number = ++requestNumber.current;
    setRefreshing(true);
    try {
      const [list, counts] = await Promise.all([api.queueJobs(query), api.queueStats()]);
      if (number !== requestNumber.current) return;
      // Gdy liczba wyników maleje podczas pracy, wracamy na istniejącą stronę.
      const lastPage = Math.max(1, Math.ceil(list.total / PAGE_SIZE));
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

  const filter = (patch: Partial<QueueQuery>) => setQuery((current) => ({ ...current, ...patch, page: 1 }));
  const currentPage = query.page ?? 1;
  const pages = Math.max(1, Math.ceil((page?.total ?? 0) / PAGE_SIZE));

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight"><ListTodoIcon />Kolejka zadań</h1>
        <p className="mt-1 text-sm text-muted-foreground">Bieżąca praca i historia wszystkich zadań AI. Stan pochodzi z bazy.</p>
      </div>
      <Button variant="outline" size="sm" disabled={refreshing} onClick={() => void load()}><RefreshCwIcon className={refreshing ? "animate-spin" : ""} />Odśwież</Button>
    </div>

    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
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
      <Table>
        <TableHeader><TableRow><TableHead>Temat / zadanie</TableHead><TableHead>Etap</TableHead><TableHead>Status</TableHead><TableHead>Postęp</TableHead><TableHead>Próby</TableHead><TableHead>Utworzono</TableHead><TableHead><span className="sr-only">Szczegóły</span></TableHead></TableRow></TableHeader>
        <TableBody>
          {!page && <TableRow><TableCell colSpan={7}>Ładowanie zadań…</TableCell></TableRow>}
          {page?.items.length === 0 && <TableRow><TableCell colSpan={7} className="py-12 text-center text-muted-foreground">Brak zadań pasujących do filtrów.</TableCell></TableRow>}
          {page?.items.map((job) => <TableRow key={job.id}>
            <TableCell className="max-w-80 whitespace-normal">
              <Link href={`/candidates/${job.candidate_id}`} className="line-clamp-2 font-medium hover:underline">{job.candidate_title ?? `Temat #${job.candidate_id}`}</Link>
              <p className="mt-1 font-mono text-xs text-muted-foreground">{job.id.slice(0, 8)}…</p>
              {job.error_code && job.status !== "succeeded" && <p className="mt-1 text-xs text-destructive">{job.error_code}</p>}
            </TableCell>
            <TableCell>{KIND_LABELS[job.kind]}</TableCell>
            <TableCell><span className={`rounded-full px-2 py-1 text-xs font-medium ring-1 ${STATUS_STYLES[job.status]}`}>{STATUS_LABELS[job.status]}</span></TableCell>
            <TableCell>{stageLabel(job.stage)}{job.status === "retrying" && <p className="text-xs text-muted-foreground">Najwcześniej {formatDate(job.available_at)}</p>}</TableCell>
            <TableCell className="font-mono">{job.attempt_count}/{job.max_attempts}</TableCell>
            <TableCell className="text-xs text-muted-foreground">{formatDate(job.created_at)}</TableCell>
            <TableCell><Button size="sm" variant="ghost" aria-label={`Szczegóły zadania ${job.id}`} onClick={() => setSelected(job)}>Szczegóły</Button></TableCell>
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
        {selected && <JobDetails key={selected.id} initial={selected} onRetried={(job) => { setSelected(job); void load(); }} />}
      </DialogContent>
    </Dialog>
  </div>;
}

function CountCard({ label, value, selected, onClick }: { label: string; value?: number; selected: boolean; onClick: () => void }) {
  return <button onClick={onClick} aria-pressed={selected} aria-label={`Filtr: ${label}`} className={`rounded-xl border bg-card p-4 text-left transition-colors hover:bg-muted/40 ${selected ? "border-primary ring-1 ring-primary" : ""}`}>
    <p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold tabular-nums">{value ?? "—"}</p>
  </button>;
}
