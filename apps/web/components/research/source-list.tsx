"use client";

import { useState } from "react";
import { ChevronDownIcon, ChevronRightIcon, ExternalLinkIcon } from "lucide-react";

import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ResearchSource } from "@/types/api";

import { hostname, sourceLabel } from "./research-utils";

const FETCH_STYLES: Record<ResearchSource["fetch_status"], string> = {
  success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
  pending: "bg-zinc-100 text-zinc-600 ring-zinc-200",
};

function scoreClass(score: number): string {
  if (score >= 90) return "text-emerald-700";
  if (score >= 65) return "text-amber-700";
  return "text-zinc-500";
}

export function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (sources.length === 0) {
    return <p className="text-sm text-muted-foreground">Brak źródeł.</p>;
  }
  return (
    <ul className="divide-y rounded-lg border bg-background">
      {sources.map((source) => (
        <SourceItem key={source.id} source={source} />
      ))}
    </ul>
  );
}

function SourceItem({ source }: { source: ResearchSource }) {
  const [open, setOpen] = useState(false);
  const canExpand = Boolean(source.extracted_content);

  return (
    <li id={`research-source-${source.id}`} className="scroll-mt-36 p-4">
      <div className="flex items-start gap-3">
        <span
          className={cn("w-9 shrink-0 pt-0.5 text-right font-mono text-sm font-semibold", scoreClass(source.source_score))}
          title="Ocena wiarygodności źródła"
        >
          [{source.id}]
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-medium">{sourceLabel(source)}</span>
            <span className="rounded bg-slate-100 px-2 py-1 text-[11px] text-slate-700">
              {({official:"Oficjalne źródło",documentation:"Dokumentacja",github:"GitHub",news:"Wiadomości",blog:"Blog",community:"Społeczność",other:"Inne"})[source.source_type]}
            </span>
            <span className="text-xs text-muted-foreground">{source.origin === "original" ? "Materiał oryginalny" : source.origin === "manual" ? "Dodane ręcznie" : source.origin === "sibling" ? "Ten sam temat z innego RSS" : "Dodatkowe źródło"}</span>
            <span
              className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium ring-1", FETCH_STYLES[source.fetch_status])}
              title={source.error ?? undefined}
            >
              {source.fetch_status === "success" ? "Pobrano" : source.fetch_status === "failed" ? "Błąd pobrania" : "Oczekuje"}

            </span>
          </div>
          {source.title && <p className="text-sm">{source.title}</p>}
          <div className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
            <span>{source.published_at ? formatDate(source.published_at) : "Data nieznana"}</span>
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex max-w-full items-center gap-1 truncate font-mono hover:underline"
            >
              {hostname(source.url)}
              <ExternalLinkIcon className="size-3 shrink-0" />
            </a>
          </div>
          {source.extracted_content && <p className="line-clamp-3 text-sm leading-6 text-slate-600">{source.extracted_content.slice(0,240)}{source.extracted_content.length>240 ? "…" : ""}</p>}
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-9 items-center gap-1 text-xs font-medium text-sky-800 hover:underline">Otwórz źródło <ExternalLinkIcon className="size-3" /></a>
          <p className="text-xs text-muted-foreground">Wiarygodność: {source.source_score}/100</p>
          {source.error && <p className="text-xs text-rose-700">{source.error}</p>}
          {canExpand && (
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              className="inline-flex items-center gap-1 text-xs font-medium text-foreground/80 hover:text-foreground"
              aria-expanded={open}
            >
              {open ? <ChevronDownIcon className="size-3.5" /> : <ChevronRightIcon className="size-3.5" />}
              Pełna pobrana treść ({source.extracted_content?.length.toLocaleString("pl-PL")} znaków)
            </button>
          )}
          {open && (
            <pre className="mt-2 max-h-96 overflow-auto rounded-md bg-zinc-50 p-3 font-sans text-xs leading-relaxed whitespace-pre-wrap">
              {source.extracted_content}
            </pre>
          )}
        </div>
      </div>
    </li>
  );
}
