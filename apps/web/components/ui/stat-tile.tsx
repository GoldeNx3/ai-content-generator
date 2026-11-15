import type { LucideIcon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type StatTone = "sky" | "violet" | "emerald" | "zinc" | "amber" | "rose";

export const STAT_TONES: Record<StatTone, string> = {
  sky: "bg-sky-50 text-sky-700 ring-sky-200",
  violet: "bg-violet-50 text-violet-700 ring-violet-200",
  emerald: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  zinc: "bg-zinc-100 text-zinc-600 ring-zinc-200",
  amber: "bg-amber-50 text-amber-700 ring-amber-200",
  rose: "bg-rose-50 text-rose-700 ring-rose-200",
};

/** Kafel KPI. Renderuje parę dt/dd – umieść go w `<dl>`. `value === undefined` pokazuje szkielet ładowania. */
export function StatTile({ label, value, suffix, hint, icon: Icon, tone = "zinc", footer, className, valueClassName }: {
  label: string;
  value: React.ReactNode | undefined;
  suffix?: string;
  hint?: React.ReactNode;
  icon: LucideIcon;
  tone?: StatTone;
  /** Zastępuje podpowiedź, np. paskiem postępu. */
  footer?: React.ReactNode;
  className?: string;
  /** Np. mniejsza czcionka dla wartości tekstowych („20 minut temu”). */
  valueClassName?: string;
}) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-3 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/8", className)}>
      <div className="flex items-center justify-between gap-2">
        <dt className="text-sm font-medium text-muted-foreground">{label}</dt>
        <span className={cn("flex size-8 items-center justify-center rounded-lg ring-1", STAT_TONES[tone])} aria-hidden="true"><Icon className="size-4" /></span>
      </div>
      <dd className="space-y-2">
        {value === undefined
          ? <Skeleton className="h-8 w-16" />
          : <span className={cn("block truncate text-3xl font-semibold tracking-tight tabular-nums", valueClassName)}>{value}{suffix && <span className="text-base font-normal text-muted-foreground">{suffix}</span>}</span>}
        {footer ?? (hint && <span className="block text-xs text-muted-foreground">{hint}</span>)}
      </dd>
    </div>
  );
}
