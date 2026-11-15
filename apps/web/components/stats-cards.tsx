import { CircleCheckIcon, DownloadIcon, EyeOffIcon, GaugeIcon, InboxIcon } from "lucide-react";

import { StatTile } from "@/components/ui/stat-tile";
import { scoreLevel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DashboardStats } from "@/types/api";

const BAR: Record<ReturnType<typeof scoreLevel>, string> = {
  "very-high": "bg-emerald-600",
  high: "bg-emerald-400",
  medium: "bg-amber-400",
  low: "bg-zinc-400",
};

export function StatsCards({ stats }: { stats: DashboardStats | null }) {
  const count = (value: number | null | undefined) => (stats === null ? undefined : typeof value === "number" ? value : "—");
  const average = typeof stats?.average_score === "number" ? Math.round(stats.average_score) : null;
  return (
    <dl className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      <StatTile label="Nowe dziś" value={count(stats?.new_today)} hint="Pobrane dziś, czekają na decyzję" icon={InboxIcon} tone="sky" />
      <StatTile label="Pobrane dziś" value={count(stats?.candidates_today)} hint="Od północy UTC" icon={DownloadIcon} tone="violet" />
      <StatTile label="Zatwierdzone" value={count(stats?.approved)} hint="Łącznie" icon={CircleCheckIcon} tone="emerald" />
      <StatTile label="Pominięte" value={count(stats?.ignored)} hint="Łącznie" icon={EyeOffIcon} tone="zinc" />
      <StatTile
        className="col-span-2 md:col-span-1"
        label="Średni wynik"
        value={stats === null ? undefined : average ?? "—"}
        suffix={average !== null ? "/100" : undefined}
        hint="Z ocenionych tematów"
        icon={GaugeIcon}
        tone="amber"
        footer={average === null ? undefined : (
          <span className="block h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
            <span className={cn("block h-full rounded-full", BAR[scoreLevel(average)])} style={{ width: `${average}%` }} />
          </span>
        )}
      />
    </dl>
  );
}
