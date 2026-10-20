"use client";

import { useEffect, useState } from "react";
import { GaugeIcon, Loader2Icon } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, errorText } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Usage } from "@/types/api";

const usd = (value: string | null) => (value === null ? "bez limitu" : `$${Number(value).toFixed(2)}`);

export function UsageCard() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.usage().then(setUsage, (err) => setError(errorText(err)));
  }, []);

  const spent = Number(usage?.spent_usd ?? 0);
  const budget = usage?.budget_usd === null || usage?.budget_usd === undefined ? null : Number(usage.budget_usd);
  const percent = budget ? Math.min(100, Math.round((spent / budget) * 100)) : 0;
  const month = usage ? new Intl.DateTimeFormat("pl-PL", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(usage.period_start)) : "";

  return (
    <Card>
      <CardHeader>
        <CardTitle><h2 className="flex items-center gap-2 text-lg font-semibold"><GaugeIcon className="size-5" />Zużycie AI</h2></CardTitle>
        <CardDescription>Koszt płatnych kroków (ocena, research, pisanie, QA, poprawki) w tym workspace{month ? ` · ${month}` : ""}.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
        {!usage && !error && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Wczytywanie…</p>}
        {usage && <>
          <p className="text-2xl font-semibold tabular-nums">{usd(usage.spent_usd)} <span className="text-base font-normal text-muted-foreground">z {usd(usage.budget_usd)}</span></p>
          {budget !== null && (
            <div role="progressbar" aria-label="Wykorzystanie budżetu AI" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}
              className="h-2 overflow-hidden rounded-full bg-muted">
              <div className={cn("h-full rounded-full", usage.exceeded ? "bg-rose-600" : percent >= 80 ? "bg-amber-500" : "bg-emerald-600")} style={{ width: `${percent}%` }} />
            </div>
          )}
          {usage.exceeded
            ? <p role="status" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">Budżet wyczerpany: nowe płatne kroki są zablokowane do 1. dnia następnego miesiąca. Publikacja w WordPressie działa bez zmian.</p>
            : budget !== null && <p className="text-sm text-muted-foreground">Pozostało {usd(usage.remaining_usd)}. Zlecone zadanie może przekroczyć limit o swój koszt.</p>}
          {usage.unknown_cost_calls > 0 && <p className="text-xs text-muted-foreground">{usage.unknown_cost_calls} przerwanych wywołań bez znanego kosztu nie wliczono.</p>}
        </>}
      </CardContent>
    </Card>
  );
}
