import { Meter } from "@/components/stage/result-block";
import { cn } from "@/lib/utils";
import type { FactImportance, ResearchFact, ResearchSource } from "@/types/api";

import { sourceLabel } from "./research-utils";

const GROUPS: { importance: FactImportance; title: string; description: string; marker: string }[] = [
  { importance: "critical", title: "Kluczowe", description: "Rdzeń artykułu — bez nich tekst traci sens.", marker: "bg-emerald-600" },
  { importance: "important", title: "Ważne", description: "Rozwijają temat i dają kontekst.", marker: "bg-amber-500" },
  { importance: "supporting", title: "Uzupełniające", description: "Szczegóły, które można pominąć przy krótszym tekście.", marker: "bg-zinc-300 dark:bg-zinc-600" },
];

const BASIS: Partial<Record<NonNullable<ResearchFact["basis"]>, { label: string; title: string; className: string }>> = {
  vendor_claim: { label: "deklaracja producenta", title: "Twierdzenie firmy o sobie — w artykule podawaj je jako deklarację, nie jako fakt.", className: "bg-amber-50 text-amber-900 ring-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-900" },
  secondary: { label: "z drugiej ręki", title: "Źródło relacjonuje informację z innego źródła.", className: "bg-zinc-100 text-zinc-700 ring-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700" },
};

export function FactList({ facts, sources }: { facts: ResearchFact[]; sources: ResearchSource[] }) {
  const sourcesById = new Map(sources.map((source) => [source.id, source]));

  if (facts.length === 0) {
    return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Research nie potwierdził żadnego faktu. Dodaj źródło albo wyszukaj źródła od nowa.</p>;
  }

  return (
    <div className="space-y-6">
      {GROUPS.map(({ importance, title, description, marker }) => {
        const group = facts.filter((fact) => fact.importance === importance);
        if (group.length === 0) return null;
        return (
          <section key={importance} aria-label={`${title} fakty`} className="space-y-2">
            <h5 className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className="inline-flex items-center gap-2 font-semibold"><span className={cn("size-2 rounded-full", marker)} aria-hidden="true" />{title} <span className="font-normal tabular-nums text-muted-foreground">({group.length})</span></span>
              <span className="text-xs text-muted-foreground">{description}</span>
            </h5>
            <ol className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">
              {group.map((fact) => {
                const basis = fact.basis ? BASIS[fact.basis] : undefined;
                const cited = fact.source_ids.map((id) => sourcesById.get(id)).filter((source): source is ResearchSource => Boolean(source));
                return (
                  <li key={fact.id} className="relative bg-background py-3 pr-4 pl-5">
                    <span className={cn("absolute inset-y-0 left-0 w-1", marker)} aria-hidden="true" />
                    <p className="text-sm leading-6">{fact.claim}</p>
                    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
                      <Meter value={fact.confidence} label="Pewność" />
                      {basis && <span title={basis.title} className={cn("rounded-full px-2 py-0.5 text-xs font-medium ring-1", basis.className)}>{basis.label}</span>}
                      <span className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        {cited.length === 0 ? "Brak przypisanego źródła" : <>Źródła:{cited.map((source) => (
                          <a key={source.id} href={`#research-source-${source.id}`} title={source.title ?? source.url}
                            className="inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 font-medium text-foreground/80 hover:bg-emerald-50 hover:text-emerald-800 dark:hover:bg-emerald-950 dark:hover:text-emerald-300">
                            <span className="tabular-nums text-muted-foreground">[{source.id}]</span>{sourceLabel(source)}
                          </a>
                        ))}</>}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        );
      })}
    </div>
  );
}
