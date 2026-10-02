import { CheckIcon } from "lucide-react";

import type { Article, SnapshotSource } from "@/types/api";

function sourceName(source: SnapshotSource): string {
  if (source.publisher) return source.publisher;
  try {
    return new URL(source.url).hostname.replace(/^www\./, "");
  } catch {
    return source.url;
  }
}

/** Which research facts and sources back each part of the generated draft. */
export function FactUsage({ article }: { article: Article }) {
  const facts = new Map(article.research_snapshot.facts.map((fact) => [fact.id, fact]));
  const sources = new Map(article.research_snapshot.sources.map((source) => [source.id, source]));
  const parts = [
    { heading: "Lead", used_fact_ids: article.lead_fact_ids, source_ids: [] as number[] },
    ...article.sections.map((section) => ({
      heading: section.is_conclusion ? "Conclusion" : (section.heading ?? "Section"),
      used_fact_ids: section.used_fact_ids,
      source_ids: section.source_ids,
    })),
  ];
  const used = new Set(parts.flatMap((part) => part.used_fact_ids));
  const unused = article.research_snapshot.facts.filter((fact) => !used.has(fact.id));

  return (
    <div className="space-y-4">
      {parts.map((part, index) => (
        <div key={index} className="space-y-1.5">
          <p className="text-sm font-medium">{part.heading}</p>
          {part.used_fact_ids.length === 0 ? (
            <p className="text-xs text-amber-700">No research facts referenced.</p>
          ) : (
            <ul className="space-y-1">
              {part.used_fact_ids.map((id) => {
                const fact = facts.get(id);
                return (
                  <li key={id} className="flex gap-2 text-xs">
                    <span className="shrink-0 font-mono text-muted-foreground">#{id}</span>
                    <span>
                      {fact?.claim ?? "unknown fact"}{" "}
                      {fact && <span className="font-mono text-muted-foreground">({fact.confidence}%)</span>}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          {part.source_ids.length > 0 && (
            <div className="flex flex-wrap gap-x-3 text-xs">
              {part.source_ids.map((id) => {
                const source = sources.get(id);
                if (!source) return null;
                return (
                  <a
                    key={id}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-emerald-700 hover:underline"
                    title={source.title ?? source.url}
                  >
                    <CheckIcon className="size-3" />
                    {sourceName(source)}
                  </a>
                );
              })}
            </div>
          )}
        </div>
      ))}
      {unused.length > 0 && (
        <div className="space-y-1.5 border-t pt-3">
          <p className="text-sm font-medium text-muted-foreground">Unused research facts ({unused.length})</p>
          <ul className="space-y-1">
            {unused.map((fact) => (
              <li key={fact.id} className="flex gap-2 text-xs text-muted-foreground">
                <span className="shrink-0 font-mono">#{fact.id}</span>
                <span>{fact.claim}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
