"use client";

import { useEffect, useState } from "react";
import { Loader2Icon, ReceiptIcon } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, errorText } from "@/lib/api";
import { KIND_LABELS, stageLabel } from "@/lib/jobs";
import type { CostReport, Job } from "@/types/api";

const usd = (value: string) => `≈ $${Number(value).toFixed(4)}`;
const currentMonth = () => new Date().toISOString().slice(0, 7);
const unknownCalls = (count: number) => count === 1 ? "1 przerwane wywołanie bez znanego kosztu"
  : `${count} przerwanych wywołań bez znanego kosztu`;

export function CostReportCard() {
  const [month, setMonth] = useState(currentMonth);
  const [report, setReport] = useState<CostReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!/^\d{4}-\d{2}$/.test(month)) return;
    let active = true;
    api.costReport(month).then(
      (data) => { if (active) { setReport(data); setError(null); } },
      (err) => { if (active) setError(errorText(err)); },
    );
    return () => { active = false; };
  }, [month]);

  return (
    <Card role="region" aria-label="Koszty AI według kroków">
      <CardHeader>
        <CardTitle><h2 className="flex items-center gap-2 text-lg font-semibold"><ReceiptIcon className="size-5" />Koszty według kroków</h2></CardTitle>
        <CardDescription>Na co poszedł budżet: płatne kroki, etapy wywołań (w tym wyszukiwanie Tavily) i średni koszt tematu doprowadzonego do artykułu. Raport jest bezpłatny.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <label className="flex max-w-48 flex-col gap-1 text-sm">Miesiąc
          <Input type="month" value={month} onChange={(event) => setMonth(event.target.value)} />
        </label>
        {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
        {!report && !error && <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2Icon className="size-4 animate-spin" />Wczytywanie…</p>}
        {report && <>
          <p className="text-2xl font-semibold tabular-nums">{usd(report.total_usd)}</p>
          <p className="text-sm text-muted-foreground">{report.articles.average_usd === null
            ? "W tym miesiącu żaden opłacony temat nie ma jeszcze artykułu."
            : `${usd(report.articles.average_usd)} na temat z artykułem (${report.articles.topics})`}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <CostTable title="Kroki" rows={report.by_kind.map((row) => ({ label: KIND_LABELS[row.kind as Job["kind"]] ?? row.kind, detail: `${row.jobs} zad.`, cost: row.cost_usd }))} />
            <CostTable title="Etapy wywołań" rows={report.by_stage.map((row) => ({ label: stageLabel(row.stage), detail: `${row.calls} wyw.`, cost: row.cost_usd }))} />
          </div>
          {report.unknown_cost_calls > 0 && <p className="text-xs text-muted-foreground">{unknownCalls(report.unknown_cost_calls)}</p>}
        </>}
      </CardContent>
    </Card>
  );
}

function CostTable({ title, rows }: { title: string; rows: { label: string; detail: string; cost: string }[] }) {
  return <div className="space-y-2">
    <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</h3>
    {rows.length === 0 ? <p className="text-sm text-muted-foreground">Brak płatnych wywołań.</p> : <ul className="space-y-1 text-sm">
      {rows.map((row) => <li key={row.label} className="flex justify-between gap-3"><span>{row.label}</span><span className="tabular-nums text-muted-foreground">{row.detail} · {usd(row.cost)}</span></li>)}
    </ul>}
  </div>;
}
