"use client";

import { useCallback, useEffect, useState } from "react";
import { DownloadIcon, Loader2Icon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { SourceForm } from "@/components/source-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { cn } from "@/lib/utils";
import type { Source } from "@/types/api";

type BusyAction = { id: number; kind: "fetch" | "toggle" | "delete" } | null;

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [busy, setBusy] = useState<BusyAction>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [fetchSummary, setFetchSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  async function run(source: Source, kind: "fetch" | "toggle" | "delete") {
    setBusy({ id: source.id, kind });
    try {
      if (kind === "fetch") {
        const result = await api.fetchSource(source.id);
        setFetchSummary(`${source.name}: ${result.new_candidates} nowych tematów · ${result.duplicates} duplikatów · ${result.skipped_old} zbyt starych · ${result.errors} błędów`);
        if (result.errors) {
          toast.error(`Fetching ${source.name} failed`, { description: "Check API logs for details." });
        } else {
          toast.success(`${source.name}: ${result.new_candidates} new`, {
            description: `${result.items_found} found · ${result.duplicates} duplicates · ${result.skipped_old} too old`,
          });
        }
      } else if (kind === "toggle") {
        await api.updateSource(source.id, { active: !source.active });
      } else {
        await api.deleteSource(source.id);
        toast.success(`Deleted ${source.name}`);
        setConfirmDelete(null);
      }
      await load();
    } catch (actionError) {
      if (kind === "fetch") setFetchSummary(`${source.name}: błąd pobierania — ${errorText(actionError)}`);
      toast.error("Action failed", { description: errorText(actionError) });
    } finally {
      setBusy(null);
    }
  }

  const isBusy = (source: Source, kind: "fetch" | "toggle" | "delete") =>
    busy?.id === source.id && busy.kind === kind;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Źródła RSS</h1>
        <p className="text-sm text-muted-foreground">Pobieranie RSS / Atom nie wywołuje AI. Ocena, research i generowanie są uruchamiane osobno.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Dodaj źródło RSS</CardTitle>
        </CardHeader>
        <CardContent>
          <SourceForm onCreated={load} />
        </CardContent>
      </Card>

      {fetchSummary && <div className="rounded-lg border bg-card px-4 py-3 text-sm" role="status">Ostatnie pobieranie: {fetchSummary}</div>}

      {error && (
        <div role="alert" className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      <div className="min-w-0 overflow-x-auto rounded-xl bg-card ring-1 ring-foreground/10">
        <Table aria-label="Źródła RSS">
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="pl-4">Nazwa</TableHead>
              <TableHead scope="col">URL</TableHead>
              <TableHead scope="col">Aktywne</TableHead>
              <TableHead scope="col">Ostatnie pobranie</TableHead>
              <TableHead scope="col" className="pr-4 text-right">Akcje</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-12 text-center text-muted-foreground">
                  Brak źródeł. Dodaj adres RSS w formularzu powyżej.
                </TableCell>
              </TableRow>
            )}
            {sources?.map((source) => (
              <TableRow key={source.id} className={source.active ? "" : "opacity-60"}>
                <TableCell className="pl-4 font-medium">{source.name}</TableCell>
                <TableCell className="max-w-[24rem]">
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block truncate font-mono text-xs text-muted-foreground hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
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
                    disabled={busy !== null}
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
                <TableCell className="text-muted-foreground" title={formatDate(source.last_fetched_at)}>
                  {source.last_fetched_at ? timeAgo(source.last_fetched_at) : "Nigdy"}
                </TableCell>
                <TableCell className="pr-4">
                  <div className="flex justify-end gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy !== null}
                      onClick={() => run(source, "fetch")}
                    >
                      {isBusy(source, "fetch") ? <Loader2Icon className="animate-spin" /> : <DownloadIcon />}
                      Pobierz · bez kosztu AI
                    </Button>
                    {confirmDelete === source.id ? (
                      <>
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={busy !== null}
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
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label={`Usuń źródło: ${source.name}`}
                        title="Usuń źródło i jego tematy"
                        disabled={busy !== null}
                        onClick={() => setConfirmDelete(source.id)}
                      >
                        <Trash2Icon />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
