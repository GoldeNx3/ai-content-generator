import { CircleAlertIcon, ExternalLinkIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Article, SnapshotSource } from "@/types/api";

function sourceName(source: SnapshotSource): string {
  if (source.publisher) return source.publisher;
  try {
    return new URL(source.url).hostname.replace(/^www\./, "");
  } catch {
    return source.url;
  }
}

/** Które fakty i źródła z researchu stoją za każdą częścią wygenerowanego tekstu. */
export function FactUsage({ article }: { article: Article }) {
  const facts = new Map(article.research_snapshot.facts.map((fact) => [fact.id, fact]));
  const sources = new Map(article.research_snapshot.sources.map((source) => [source.id, source]));
  const sectionCount = article.sections.filter((section) => !section.is_conclusion).length;
  const parts = [
    { heading: "Lead", kind: "Wstęp", used_fact_ids: article.lead_fact_ids, source_ids: [] as number[] },
    ...article.sections.map((section, position) => {
      const sectionIndex = article.sections.slice(0, position + 1).filter((item) => !item.is_conclusion).length;
      return {
        heading: section.is_conclusion ? (section.heading ?? "Podsumowanie") : (section.heading ?? `Sekcja ${sectionIndex}`),
        kind: section.is_conclusion ? "Zakończenie" : `Sekcja ${sectionIndex} z ${sectionCount}`,
        used_fact_ids: section.used_fact_ids,
        source_ids: section.source_ids,
      };
    }),
  ];
  const used = new Set(parts.flatMap((part) => part.used_fact_ids));
  const unused = article.research_snapshot.facts.filter((fact) => !used.has(fact.id));

  if (article.sections.length === 0 && article.lead_fact_ids.length === 0) {
    return <p className="rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">Ta wersja nie ma zapisanych powiązań z faktami (np. powstała przed tą funkcją albo została edytowana ręcznie).</p>;
  }

  return (
    <div className="space-y-4">
      <ol className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">
        {parts.map((part, index) => {
          const empty = part.used_fact_ids.length === 0;
          return (
            <li key={index} className="space-y-2 bg-background px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className="text-sm font-medium">{part.heading}</p>
                <span className="text-xs text-muted-foreground">{part.kind}</span>
              </div>
              {empty ? (
                <p className={cn("flex items-center gap-1.5 text-xs", part.kind === "Zakończenie" ? "text-muted-foreground" : "text-amber-700 dark:text-amber-400")}>
                  <CircleAlertIcon className="size-3.5" aria-hidden="true" />Brak odwołań do faktów z researchu.
                </p>
              ) : (
                <ul className="space-y-1">
                  {part.used_fact_ids.map((id) => {
                    const fact = facts.get(id);
                    return (
                      <li key={id} className="flex gap-2 text-sm leading-6">
                        <span className="shrink-0 tabular-nums text-xs leading-6 text-muted-foreground">#{id}</span>
                        <span className="min-w-0">{fact?.claim ?? "Fakt usunięty z researchu"}{fact && <span className="ml-1.5 text-xs tabular-nums text-muted-foreground">pewność {fact.confidence}%</span>}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
              {part.source_ids.length > 0 && (
                <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                  Źródła:
                  {part.source_ids.map((id) => {
                    const source = sources.get(id);
                    if (!source) return null;
                    return (
                      <a key={id} href={source.url} target="_blank" rel="noopener noreferrer" title={source.title ?? source.url}
                        className="inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5 font-medium text-foreground/80 hover:bg-emerald-50 hover:text-emerald-800">
                        {sourceName(source)}<ExternalLinkIcon className="size-3" aria-hidden="true" />
                      </a>
                    );
                  })}
                </p>
              )}
            </li>
          );
        })}
      </ol>
      {unused.length > 0 && (
        <details className="rounded-xl bg-muted/40 px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium">Niewykorzystane fakty ({unused.length})</summary>
          <p className="mt-1 text-xs text-muted-foreground">Są w researchu, ale nie trafiły do tej wersji. To nie błąd — przy krótszym tekście część faktów zostaje pominięta.</p>
          <ul className="mt-2 space-y-1">
            {unused.map((fact) => (
              <li key={fact.id} className="flex gap-2 text-muted-foreground">
                <span className="shrink-0 text-xs leading-6 tabular-nums">#{fact.id}</span><span>{fact.claim}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
