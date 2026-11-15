"use client";

import Link from "next/link";
import { ActivityIcon, ArrowRightIcon, BotIcon, CirclePauseIcon, WalletIcon } from "lucide-react";

import { formatDate, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { AutomationSettings, Usage } from "@/types/api";

const usd = (value: string) => `$${Number(value).toFixed(2)}`;

function intervalLabel(minutes: number) {
  if (minutes < 60) return `co ${minutes} min`;
  if (minutes === 1440) return "raz na dobę";
  return `co ${minutes / 60} h`;
}

function Tile({ icon: Icon, label, href, linkLabel, tone = "neutral", children }: {
  icon: typeof ActivityIcon; label: string; href: string; linkLabel: string;
  tone?: "neutral" | "warning" | "danger"; children: React.ReactNode;
}) {
  return (
    <section aria-label={label} className={cn(
      "flex min-w-0 flex-col gap-3 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/8",
      tone === "warning" && "ring-amber-300 bg-amber-50/60",
      tone === "danger" && "ring-rose-300 bg-rose-50/60",
    )}>
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <Icon className="size-4" aria-hidden="true" />{label}
        </span>
        <Link href={href} className="inline-flex items-center gap-1 rounded-sm text-xs font-medium text-emerald-800 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          {linkLabel}<ArrowRightIcon className="size-3" aria-hidden="true" />
        </Link>
      </div>
      <div className="min-w-0 text-sm">{children}</div>
    </section>
  );
}

export function StatusStrip({ activeCount, queueError, usage, automation }: {
  activeCount: number; queueError: string | null; usage: Usage | null; automation: AutomationSettings | null;
}) {
  const hasUsage = typeof usage?.spent_usd === "string";
  const budget = hasUsage && usage!.budget_usd != null ? Number(usage!.budget_usd) : null;
  const spent = hasUsage ? Number(usage!.spent_usd) : 0;
  const percent = budget ? Math.min(100, Math.round((spent / budget) * 100)) : 0;
  const hasAutomation = typeof automation?.auto_fetch_enabled === "boolean";
  const paused = hasAutomation && automation!.paused_at !== null;
  const autoOn = hasAutomation && (automation!.auto_fetch_enabled || automation!.auto_classify_enabled);

  return (
    <div className="space-y-3">
      {paused && (
        <div role="status" className="flex flex-wrap items-center gap-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-950 ring-1 ring-amber-300">
          <CirclePauseIcon className="size-5 shrink-0" aria-hidden="true" />
          <p className="min-w-0 flex-1"><strong>Workspace wstrzymany</strong> od {formatDate(automation!.paused_at)}. Nowe zadania AI i automatyka nie ruszą do wznowienia.</p>
          <Link href="/queue" className="font-medium underline underline-offset-4">Wznów w kolejce</Link>
        </div>
      )}
      <div className="grid gap-3 md:grid-cols-3">
        <Tile icon={ActivityIcon} label="Kolejka" href="/queue" linkLabel="Otwórz kolejkę zadań" tone={queueError ? "danger" : "neutral"}>
          <p className="flex items-center gap-2" role="status">
            <span className="relative flex size-2.5" aria-hidden="true">
              {activeCount > 0 && <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
              <span className={cn("relative inline-flex size-2.5 rounded-full", activeCount > 0 ? "bg-emerald-500" : "bg-zinc-300")} />
            </span>
            <span className="text-lg font-semibold tabular-nums">Aktywne zadania: {activeCount}</span>
          </p>
          {queueError
            ? <p className="mt-1 text-rose-800">Błąd odczytu kolejki: {queueError}</p>
            : <p className="mt-1 text-muted-foreground">Worker działa również po zamknięciu przeglądarki.</p>}
        </Tile>

        <Tile icon={WalletIcon} label="Budżet AI" href="/settings" linkLabel="Szczegóły" tone={hasUsage && usage!.exceeded ? "danger" : percent >= 80 ? "warning" : "neutral"}>
          {hasUsage ? <>
            <p className="text-lg font-semibold tabular-nums">{usd(usage!.spent_usd)} <span className="text-sm font-normal text-muted-foreground">z {budget === null ? "bez limitu" : usd(usage!.budget_usd!)} w tym miesiącu</span></p>
            {budget !== null && (
              <div role="progressbar" aria-label="Wykorzystanie budżetu AI" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                <div className={cn("h-full rounded-full transition-[width]", usage!.exceeded ? "bg-rose-600" : percent >= 80 ? "bg-amber-500" : "bg-emerald-600")} style={{ width: `${percent}%` }} />
              </div>
            )}
            <p className={cn("mt-2", usage!.exceeded ? "font-medium text-rose-800" : "text-muted-foreground")}>
              {usage!.exceeded ? "Limit wyczerpany – nowe płatne zadania są blokowane." : budget === null ? "Brak miesięcznego limitu kosztów." : `Pozostało ${usd(usage!.remaining_usd ?? "0")}.`}
            </p>
          </> : <p className="text-muted-foreground">Brak danych o zużyciu.</p>}
        </Tile>

        <Tile icon={BotIcon} label="Automatyka" href="/settings" linkLabel="Ustaw" tone="neutral">
          {hasAutomation ? <>
            <p className="flex items-center gap-2 text-lg font-semibold">
              <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium ring-1", autoOn && !paused && automation!.automation_enabled_globally ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-zinc-100 text-zinc-600 ring-zinc-200")}>
                {autoOn ? (paused ? "Wstrzymana" : "Włączona") : "Wyłączona"}
              </span>
              {autoOn && <span className="text-sm font-normal text-muted-foreground">{intervalLabel(automation!.auto_fetch_interval_minutes)}</span>}
            </p>
            <p className="mt-2 text-muted-foreground">
              {!automation!.automation_enabled_globally
                ? "Automatyka wyłączona przez administratora instancji."
                : !autoOn
                  ? "Pobieranie RSS i ocena działają tylko na żądanie."
                  : automation!.next_auto_run_at && !paused
                    ? `Następne uruchomienie ${timeAgo(automation!.next_auto_run_at)}.`
                    : automation!.last_auto_run_at ? `Ostatnio ${timeAgo(automation!.last_auto_run_at)}.` : "Czeka na pierwsze uruchomienie."}
            </p>
          </> : <p className="text-muted-foreground">Brak danych o automatyce.</p>}
        </Tile>
      </div>
    </div>
  );
}
