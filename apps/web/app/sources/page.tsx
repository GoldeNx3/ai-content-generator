"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  CirclePauseIcon, ClockIcon, DownloadIcon, FilterXIcon, Loader2Icon, RssIcon, SearchIcon, SignalIcon, Trash2Icon,
} from "lucide-react";
import { toast } from "sonner";

import { RunSummary } from "@/components/run-summary";
import { SourceForm } from "@/components/source-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { StatTile } from "@/components/ui/stat-tile";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, errorText } from "@/lib/api";
import { formatDate, timeAgo } from "@/lib/format";
import { plural } from "@/lib/pagination";
import { cn } from "@/lib/utils";
import type { Source } from "@/types/api";

type BusyAction = { id: number; kind: "fetch" | "toggle" | "delete" } | null;
type StatusFilter = "all" | "active" | "inactive";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const DAY = 24 * 3600 * 1000;

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Wszystkie" },
  { value: "active", label: "Aktywne" },
  { value: "inactive", label: "Wyłączone" },
];

function host(url: string) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

function freshness(source: Source): { label: string; dot: string } {
  if (!source.last_fetched_at) return { label: "Nigdy", dot: "bg-zinc-300" };
  const age = Date.now() - new Date(source.last_fetched_at).getTime();
  return { label: timeAgo(source.last_fetched_at), dot: age < DAY ? "bg-emerald-500" : age < 7 * DAY ? "bg-amber-400" : "bg-rose-400" };
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [fetchingAll, setFetchingAll] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [fetchSummary, setFetchSummary] = useState<{ text: string; failed: boolean } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const load = useCallback(async () => {
    try {
      setSources(await api.listSources());
      setError(null);
    } catch (loadError) {
      setError(errorText(loadError));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (sources ?? []).filter((source) =>
      (status === "all" || (status === "active") === source.active)
      && (!needle || source.name.toLowerCase().includes(needle) || source.url.toLowerCase().includes(needle)));
  }, [sources, search, status]);

  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pages);
  const visible = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const filtersActive = search.trim() !== "" || status !== "all";

  const activeCount = sources?.filter((source) => source.active).length;
  const lastFetch = sources?.reduce<string | null>((latest, source) =>
    source.last_fetched_at && (!latest || source.last_fetched_at > latest) ? source.last_fetched_at : latest, null);

  async function run(source: Source, kind: "fetch" | "toggle" | "delete") {
    setBusy({ id: source.id, kind });
    try {
      if (kind === "fetch") {
        const result = await api.fetchSource(source.id);
        setFetchSummary({
          text: `${source.name}: ${result.new_candidates} nowych tematów · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych · ${result.errors} błędów`,
          failed: result.errors > 0,
        });
        if (result.errors) {
          toast.error(`Nie udało się pobrać: ${source.name}`, { description: "Szczegóły w logach API." });
        } else {
          toast.success(`${source.name}: ${result.new_candidates} nowych tematów`, {
            description: `${result.items_found} znalezionych · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych`,
          });
        }
      } else if (kind === "toggle") {
        await api.updateSource(source.id, { active: !source.active });
        toast.success(source.active ? `Wyłączono: ${source.name}` : `Włączono: ${source.name}`);
      } else {
        await api.deleteSource(source.id);
        toast.success(`Usunięto źródło: ${source.name}`);
        setConfirmDelete(null);
      }
      await load();
    } catch (actionError) {
      if (kind === "fetch") setFetchSummary({ text: `${source.name}: błąd pobierania — ${errorText(actionError)}`, failed: true });
      toast.error("Akcja nie powiodła się", { description: errorText(actionError) });
    } finally {
      setBusy(null);
    }
  }

  async function fetchAll() {
    setFetchingAll(true);
    try {
      const result = await api.fetchAllSources();
      setFetchSummary({
        text: `Wszystkie aktywne: ${result.sources_processed} źródeł · ${result.new_candidates} nowych tematów · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych · ${result.errors} błędów`,
        failed: result.errors > 0,
      });
      toast.success(`Pobrano ${result.sources_processed} źródeł`, { description: `${result.new_candidates} nowych tematów` });
      await load();
    } catch (fetchError) {
      setFetchSummary({ text: `Błąd pobierania: ${errorText(fetchError)}`, failed: true });
      toast.error("Nie udało się pobrać RSS", { description: errorText(fetchError) });
    } finally {
      setFetchingAll(false);
    }
  }

  const locked = busy !== null || fetchingAll;
  const isBusy = (source: Source, kind: "fetch" | "toggle" | "delete") =>
    busy?.id === source.id && busy.kind === kind;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Źródła"
        title="Źródła RSS"
        description="Kanały RSS i Atom, z których powstają tematy. Pobieranie nie wywołuje AI – ocena, research i generowanie są uruchamiane osobno."
        actions={
          <Button size="lg" className="bg-emerald-700 text-white shadow-sm shadow-emerald-700/20 hover:bg-emerald-800" onClick={fetchAll} disabled={locked || !activeCount}>
            {fetchingAll ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />} Pobierz wszystkie aktywne
          </Button>
        }
        actionsNote={fetchingAll ? "Pobieranie w toku…" : "Bez kosztu AI. Nowe tematy trafią na listę tematów."}
      />

      <RunSummary
        title="Ostatnie pobieranie"
        lines={fetchSummary ? [fetchSummary] : []}
        onClear={() => setFetchSummary(null)}
      />

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Wszystkie źródła" value={sources?.length} hint="RSS i Atom" icon={RssIcon} tone="violet" />
        <StatTile label="Aktywne" value={activeCount} hint="Pobierane ręcznie i przez automatykę" icon={SignalIcon} tone="emerald" />
        <StatTile label="Wyłączone" value={sources && activeCount !== undefined ? sources.length - activeCount : undefined} hint="Pomijane przy pobieraniu" icon={CirclePauseIcon} tone="zinc" />
        <StatTile
          label="Ostatnie pobranie"
          value={sources === null ? undefined : lastFetch ? timeAgo(lastFetch) : "Nigdy"}
          hint={lastFetch ? formatDate(lastFetch) : "Żadne źródło nie było jeszcze pobierane"}
          icon={ClockIcon}
          tone="sky"
          valueClassName="whitespace-normal text-xl sm:text-2xl"
        />
      </dl>

      <section aria-labelledby="add-source-heading" className="rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/8 sm:p-5">
        <div className="mb-4 space-y-1">
          <h2 id="add-source-heading" className="text-lg font-semibold">Dodaj źródło RSS</h2>
          <p className="text-sm text-muted-foreground">Wklej adres kanału RSS lub Atom. Nowe źródło jest od razu aktywne.</p>
        </div>
        <SourceForm onCreated={load} />
      </section>

      <section aria-labelledby="sources-heading" className="overflow-hidden rounded-xl bg-card shadow-xs ring-1 ring-foreground/8">
        <div className="space-y-4 border-b p-4 sm:p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="sources-heading" className="text-lg font-semibold">Lista źródeł</h2>
            <span className="text-sm text-muted-foreground tabular-nums">
              {sources ? `${filtered.length} ${plural(filtered.length, "źródło", "źródła", "źródeł")}` : "Wczytywanie…"}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-0 flex-1 basis-full sm:max-w-sm sm:basis-auto">
              <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                type="search"
                aria-label="Szukaj źródła po nazwie lub adresie"
                placeholder="Szukaj po nazwie lub adresie…"
                value={search}
                onChange={(event) => { setSearch(event.target.value); setPage(1); }}
                className="pl-8"
              />
            </div>
            <div role="radiogroup" aria-label="Filtr statusu źródeł" className="inline-flex rounded-lg bg-muted p-0.5">
              {STATUS_FILTERS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={status === option.value}
                  onClick={() => { setStatus(option.value); setPage(1); }}
                  className={cn(
                    "min-h-8 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                    status === option.value ? "bg-card text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
            {filtersActive && (
              <Button variant="ghost" className="text-muted-foreground" onClick={() => { setSearch(""); setStatus("all"); setPage(1); }}>
                <FilterXIcon /> Wyczyść filtry
              </Button>
            )}
          </div>
        </div>

        {error && (
          <div role="alert" className="m-4 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
        )}

        {sources === null && !error && (
          <div className="space-y-2 p-5" aria-hidden="true">
            {[0, 1, 2].map((row) => <div key={row} className="h-12 animate-pulse rounded-lg bg-muted" />)}
          </div>
        )}

        {sources && (
          <div className="min-w-0 overflow-x-auto">
            <Table aria-label="Źródła RSS">
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 [&>th]:h-10 [&>th]:text-xs [&>th]:font-medium [&>th]:uppercase [&>th]:tracking-wider [&>th]:text-muted-foreground">
                  <TableHead scope="col" className="pl-4 sm:pl-5">Nazwa</TableHead>
                  <TableHead scope="col" className="hidden md:table-cell">URL</TableHead>
                  <TableHead scope="col">Aktywne</TableHead>
                  <TableHead scope="col" className="hidden sm:table-cell">Ostatnie pobranie</TableHead>
                  <TableHead scope="col" className="pr-4 text-right sm:pr-5">Akcje</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sources.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-16 text-center whitespace-normal">
                      <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground" aria-hidden="true"><RssIcon className="size-6" /></span>
                      <p className="text-muted-foreground">Brak źródeł. Dodaj adres RSS w formularzu powyżej.</p>
                    </TableCell>
                  </TableRow>
                )}
                {sources.length > 0 && filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="py-12 text-center text-muted-foreground whitespace-normal">
                      Żadne źródło nie pasuje do filtrów.
                    </TableCell>
                  </TableRow>
                )}
                {visible.map((source) => {
                  const fresh = freshness(source);
                  return (
                    <TableRow key={source.id} className={source.active ? "" : "opacity-60"}>
                      <TableCell className="py-3 pl-4 sm:pl-5">
                        <div className="flex min-w-0 items-center gap-3">
                          <span aria-hidden="true" className="hidden size-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br sm:flex from-zinc-100 to-zinc-200 text-sm font-semibold uppercase text-zinc-700 ring-1 ring-zinc-200">
                            {source.name.charAt(0)}
                          </span>
                          <span className="min-w-0 max-w-36 sm:max-w-xs">
                            <span className="block truncate font-medium">{source.name}</span>
                            <span className="block truncate text-xs text-muted-foreground">{host(source.url)}</span>
                            <span className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground sm:hidden">
                              <span className={cn("size-1.5 rounded-full", fresh.dot)} aria-hidden="true" />{fresh.label}
                            </span>
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="hidden max-w-[22rem] md:table-cell">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block truncate font-mono text-xs text-muted-foreground hover:text-emerald-800 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                        >
                          {source.url}
                        </a>
                      </TableCell>
                      <TableCell>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={source.active}
                          aria-label={`${source.active ? "Wyłącz" : "Włącz"} źródło: ${source.name}`}
                          disabled={locked}
                          onClick={() => run(source, "toggle")}
                          className={cn(
                            "relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring disabled:opacity-50",
                            source.active ? "bg-emerald-600" : "bg-zinc-300",
                          )}
                        >
                          <span
                            className={cn(
                              "inline-block size-4 rounded-full bg-white shadow transition-transform",
                              source.active ? "translate-x-4.5" : "translate-x-0.5",
                            )}
                          />
                        </button>
                      </TableCell>
                      <TableCell className="hidden text-muted-foreground sm:table-cell" title={formatDate(source.last_fetched_at)}>
                        <span className="flex items-center gap-2">
                          <span className={cn("size-2 rounded-full", fresh.dot)} aria-hidden="true" />{fresh.label}
                        </span>
                      </TableCell>
                      <TableCell className="pr-4 sm:pr-5">
                        <div className="flex justify-end gap-1">
                          {confirmDelete === source.id ? (
                            <>
                              <Button
                                size="sm"
                                variant="destructive"
                                disabled={locked}
                                aria-label={`Potwierdź usunięcie źródła ${source.name} i jego tematów`}
                                onClick={() => run(source, "delete")}
                              >
                                Usuń źródło i jego tematy
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(null)}>
                                Anuluj
                              </Button>
                            </>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={locked}
                                aria-label={`Pobierz teraz: ${source.name} · bez kosztu AI`}
                                title="Pobierz teraz · bez kosztu AI"
                                onClick={() => run(source, "fetch")}
                              >
                                {isBusy(source, "fetch") ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />}
                                <span className="hidden lg:inline">Pobierz</span>
                              </Button>
                              <Button
                                size="icon-sm"
                                variant="ghost"
                                className="text-muted-foreground hover:bg-rose-50 hover:text-rose-700"
                                aria-label={`Usuń źródło: ${source.name}`}
                                title="Usuń źródło i jego tematy"
                                disabled={locked}
                                onClick={() => setConfirmDelete(source.id)}
                              >
                                <Trash2Icon />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}

        {filtered.length > 0 && (
          <Pagination
            className="border-t px-4 py-3 sm:px-5"
            label="Paginacja listy źródeł"
            page={currentPage}
            pageSize={pageSize}
            total={filtered.length}
            summary={`${(currentPage - 1) * pageSize + 1}–${Math.min(filtered.length, currentPage * pageSize)} z ${filtered.length} ${plural(filtered.length, "źródła", "źródeł", "źródeł")}`}
            onPageChange={setPage}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
          />
        )}
      </section>

      <p className="text-xs text-muted-foreground">
        Automatyczne pobieranie co określony czas ustawisz w <Link href="/settings" className="font-medium text-emerald-800 underline-offset-4 hover:underline">Ustawienia → Automatyka</Link>.
      </p>
    </div>
  );
}
