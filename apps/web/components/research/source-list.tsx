"use client";

import { useState } from "react";
import { ChevronDownIcon, CircleAlertIcon, ExternalLinkIcon, Loader2Icon } from "lucide-react";

import { Meter } from "@/components/stage/result-block";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ResearchSource } from "@/types/api";

import { hostname, sourceLabel } from "./research-utils";

const TYPE_LABEL: Record<ResearchSource["source_type"], string> = {
  official: "Oficjalne źródło", documentation: "Dokumentacja", github: "GitHub", news: "Wiadomości", blog: "Blog", community: "Społeczność", other: "Inne",
};

const ORIGIN_LABEL: Record<ResearchSource["origin"], string> = {
  original: "Materiał oryginalny", search: "Znalezione w wyszukiwaniu", manual: "Dodane ręcznie", sibling: "Ten sam temat z innego RSS",
};

export function SourceList({ sources }: { sources: ResearchSource[] }) {
  if (sources.length === 0) {
    return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Brak źródeł. Uruchom research albo dodaj link poniżej.</p>;
  }
  return (
    <ol className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">
      {sources.map((source) => <SourceItem key={source.id} source={source} />)}
    </ol>
  );
}

function SourceItem({ source }: { source: ResearchSource }) {
  const [open, setOpen] = useState(false);
  const failed = source.fetch_status === "failed";
  const pending = source.fetch_status === "pending";
  const title = source.title || hostname(source.url);
  const publisher = sourceLabel(source);
  const type = TYPE_LABEL[source.source_type];

  return (
    <li id={`research-source-${source.id}`} className="scroll-mt-60 bg-background p-4 target:bg-emerald-50/60 dark:target:bg-emerald-950/40">
      <div className="flex gap-3">
        <span className="flex h-6 min-w-8 shrink-0 items-center justify-center rounded-md bg-muted px-1.5 text-xs font-semibold tabular-nums text-muted-foreground" aria-label={`Źródło ${source.id}`}>[{source.id}]</span>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
            <a href={source.url} target="_blank" rel="noopener noreferrer" className="group min-w-0 flex-1 basis-60 text-sm font-medium leading-6 hover:underline">
              {title}<ExternalLinkIcon className="ml-1 inline size-3.5 align-[-2px] text-muted-foreground group-hover:text-foreground" aria-hidden="true" />
              <span className="sr-only"> (otwiera się w nowej karcie)</span>
            </a>
            <Meter value={source.source_score} label="Wiarygodność" suffix="/100" />
          </div>
          <p className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            {publisher !== title && <span className="font-medium text-foreground/80">{publisher}</span>}
            {type !== publisher && <span>{type}</span>}
            <span>{ORIGIN_LABEL[source.origin]}</span>
            <span>{source.published_at ? `Opublikowano ${formatDate(source.published_at)}` : "Data publikacji nieznana"}</span>
          </p>
          {(failed || pending) && (
            <p className={cn("flex items-start gap-1.5 text-xs", failed ? "text-rose-700 dark:text-rose-400" : "text-muted-foreground")}>
              {failed ? <CircleAlertIcon className="mt-px size-3.5 shrink-0" aria-hidden="true" /> : <Loader2Icon className="mt-px size-3.5 shrink-0" aria-hidden="true" />}
              {failed ? `Nie udało się pobrać treści${source.error ? `: ${source.error}` : ""}. AI nie korzystało z tego źródła.` : "Treść czeka na pobranie."}
            </p>
          )}
          {source.extracted_content && (
            <div>
              <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}
                className="inline-flex min-h-8 items-center gap-1 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring">
                <ChevronDownIcon className={cn("size-3.5 transition-transform", !open && "-rotate-90")} aria-hidden="true" />
                Pobrana treść ({source.extracted_content.length.toLocaleString("pl-PL")} znaków)
              </button>
              {open && (
                <pre className="mt-1 max-h-80 overflow-auto rounded-lg bg-muted/50 p-3 font-sans text-xs leading-relaxed whitespace-pre-wrap">{source.extracted_content}</pre>
              )}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}
