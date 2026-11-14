import { CheckIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import type { FactImportance, ResearchFact, ResearchSource } from "@/types/api";

import { citationLabel } from "./research-utils";

const IMPORTANCE_STYLES: Record<FactImportance, string> = {
  critical: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  important: "bg-amber-50 text-amber-800 ring-amber-200",
  supporting: "bg-zinc-100 text-zinc-600 ring-zinc-200",
};

const GROUPS: { importance: FactImportance; title: string }[] = [
  { importance: "critical", title: "Kluczowe fakty" },
  { importance: "important", title: "Ważne fakty" },
  { importance: "supporting", title: "Fakty uzupełniające" },
];

interface FactListProps {
  facts: ResearchFact[];
  sources: ResearchSource[];
}

export function FactList({ facts, sources }: FactListProps) {
  const sourcesById = new Map(sources.map((source) => [source.id, source]));

  if (facts.length === 0) {
    return <p className="text-sm text-muted-foreground">Brak zweryfikowanych faktów.</p>;
  }

  return (
    <div className="space-y-6">
      {GROUPS.map(({ importance, title }) => {
        const group = facts.filter((fact) => fact.importance === importance);
        if (group.length === 0) return null;
        return (
          <section key={importance} className="space-y-3">
            <h4 className="text-sm font-semibold">
              {title} <span className="font-normal text-muted-foreground">({group.length})</span>
            </h4>
            <ul className="space-y-3">
              {group.map((fact) => (
                <li key={fact.id} className="rounded-lg border bg-background p-3">
                  <div className="mb-1.5 flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold tabular-nums">{fact.confidence}%</span>
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ring-1",
                        IMPORTANCE_STYLES[fact.importance],
                      )}
                    >
                      {({critical:"Kluczowy",important:"Ważny",supporting:"Uzupełniający"})[fact.importance]}
                    </span>
                    {fact.basis === "vendor_claim" && <span className="text-xs text-amber-800">deklaracja producenta</span>}
                    {fact.basis === "secondary" && <span className="text-xs text-muted-foreground">z drugiej ręki</span>}
                  </div>
                  <p className="text-sm leading-relaxed">{fact.claim}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                    <span>Źródła:</span>
                    {fact.source_ids.map((id) => {
                      const source = sourcesById.get(id);
                      if (!source) return null;
                      return (
                        <a
                          key={id}
                          href={`#research-source-${source.id}`}
                          className="inline-flex items-center gap-1 text-emerald-700 hover:underline"
                          title={source.url}
                        >
                          <CheckIcon className="size-3" />
                          [{source.id}] {citationLabel(source)}
                        </a>
                      );
                    })}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
