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
        <h1 className="text-2xl font-semibold tracking-tight">Sources</h1>
        <p className="text-sm text-muted-foreground">Pobieranie RSS / Atom nie wywołuje AI. Ocena, research i generowanie są uruchamiane osobno.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add RSS source</CardTitle>
        </CardHeader>
        <CardContent>
          <SourceForm onCreated={load} />
        </CardContent>
      </Card>

      {fetchSummary && <div className="rounded-lg border bg-card px-4 py-3 text-sm" role="status">Ostatnie pobieranie: {fetchSummary}</div>}

      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      )}

      <div className="overflow-x-auto rounded-xl bg-card ring-1 ring-foreground/10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="pl-4">Name</TableHead>
              <TableHead>URL</TableHead>
              <TableHead>Active</TableHead>
              <TableHead>Last fetched</TableHead>
              <TableHead className="pr-4 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sources?.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-12 text-center text-muted-foreground">
                  No sources yet. Add one above or run <code>make seed</code>.
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
                    className="block truncate font-mono text-xs text-muted-foreground hover:underline"
                  >
                    {source.url}
                  </a>
                </TableCell>
                <TableCell>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={source.active}
                    aria-label={source.active ? "Disable source" : "Enable source"}
                    disabled={busy !== null}
                    onClick={() => run(source, "toggle")}
                    className={cn(
                      "relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50",
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
                  {source.last_fetched_at ? timeAgo(source.last_fetched_at) : "never"}
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
                          onClick={() => run(source, "delete")}
                        >
                          Delete with candidates
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(null)}>
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        aria-label="Delete source"
                        title="Delete"
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
