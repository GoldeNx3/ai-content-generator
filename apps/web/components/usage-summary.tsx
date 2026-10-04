"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useDemoMode } from "@/components/demo-mode";
import { api } from "@/lib/api";
import { costLabel } from "@/lib/workflow";
import type { ModelPricing } from "@/types/api";

const PricingContext = createContext<ModelPricing | null>(null);
export function ModelPricingProvider({ children }: { children: React.ReactNode }) {
  const [pricing, setPricing] = useState<ModelPricing | null>(null);
  useEffect(() => { api.pricing().then(setPricing).catch(() => setPricing(null)); }, []);
  return <PricingContext.Provider value={pricing}>{children}</PricingContext.Provider>;
}

type UsageRow = { aggregated?: boolean; label: string; model?: string | null; configured?: keyof ModelPricing["models"]; input?: number | null; output?: number | null; cost?: string | null };
export function UsageSummary({ rows = [], free = false, note, total }: { rows?: UsageRow[]; free?: boolean; note?: string; total?: string | null }) {
  const demo = useDemoMode();
  free = free || demo;
  const pricing = useContext(PricingContext);
  return <div className="space-y-3 text-sm">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Podsumowanie uruchomienia</h3>
      {!free && <a href="https://developers.openai.com/api/docs/pricing" target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground underline underline-offset-4">Cennik OpenAI · USD / 1 mln tokenów</a>}
    </div>
    {free ? <dl className="grid gap-3 sm:grid-cols-3"><UsageItem label="Model" value="Nie używa AI" /><UsageItem label="Tokeny AI" value="0" /><UsageItem label="Koszt AI" value="$0.00" /></dl> : rows.map((row) => {
      const model = row.model || (row.configured && pricing?.models[row.configured]);
      const key = model && Object.keys(pricing?.rates ?? {}).sort((a, b) => b.length - a.length).find((key) => model === key || model.startsWith(`${key}-`));
      const rate = key ? pricing?.rates[key] : undefined;
      const input = row.input == null ? "Brak danych" : row.input.toLocaleString("pl-PL");
      const output = row.output == null ? "Brak danych" : row.output.toLocaleString("pl-PL");
      const isLong = !row.aggregated && rate?.long_context_threshold !== undefined && (row.input ?? 0) > rate.long_context_threshold;
      const inRate = isLong ? rate?.long_input ?? rate?.input : rate?.input;
      const outRate = isLong ? rate?.long_output ?? rate?.output : rate?.output;
      const aggregateTierUnknown = row.aggregated && rate?.long_context_threshold !== undefined && (row.input ?? 0) > rate.long_context_threshold;
      const recalculated = !aggregateTierUnknown && row.cost == null && row.model && row.input != null && row.output != null && inRate !== undefined && outRate !== undefined;
      const cost = recalculated ? String((row.input! * inRate! + row.output! * outRate!) / 1000000) : row.cost ?? null;
      return <div key={row.label} className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground">{row.label}</p>
        <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <UsageItem label="Model" value={model ? `${model}${row.model ? "" : " (konfiguracja)"}` : "Brak danych"} />
          <UsageItem label="Tokeny wejście / wyjście" value={`${input} / ${output}`} />
          <UsageItem label="Stawka wejście / wyjście" value={rate ? `$${inRate} / $${outRate}${isLong ? " · długi kontekst" : ""}` : "Brak stawki"} />
          <UsageItem label={recalculated ? "Szacunek wg aktualnej stawki" : "Zapisany szacowany koszt"} value={costLabel(cost)} />
        </dl>
        {row.aggregated && rate?.long_context_threshold !== undefined && <p className="text-xs text-muted-foreground">Powyżej {rate.long_context_threshold.toLocaleString("pl-PL")} tokenów wejścia w jednym wywołaniu: ${rate.long_input} / ${rate.long_output} za 1 mln tokenów wejścia / wyjścia. Zużycie researchu jest sumą wywołań.</p>}
        {rate?.cached_input !== undefined && <p className="text-xs text-muted-foreground">Stawka wejścia z cache: ${isLong ? rate.long_cached_input ?? rate.cached_input : rate.cached_input} / 1 mln tokenów.</p>}
      </div>;
    })}
    {total !== undefined && <p className="border-t pt-3 font-medium">Łączny zapisany koszt tej wersji: {costLabel(total)}</p>}
    {!free && <p className="text-xs text-muted-foreground">Stawki Standard aplikacji. Koszty są szacunkowe; nie uwzględniają rabatów cache ani dodatkowych opłat. </p>}
    {note && <p className="text-xs leading-relaxed text-muted-foreground">{note}</p>}
  </div>;
}
function UsageItem({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium tabular-nums">{value}</dd></div>;
}
