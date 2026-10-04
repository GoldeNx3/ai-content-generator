"use client";

import { useEffect, useId, useState } from "react";
import { CheckCircle2Icon, ChevronDownIcon, ChevronUpIcon, CircleIcon, CircleAlertIcon, Loader2Icon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useDemoMode } from "@/components/demo-mode";
import { cn } from "@/lib/utils";

export function WorkflowSection({ number, title, description, headerDetails, status, paid, actions, summary, children, initiallyCollapsed, revealEvent }: {
  number: number; title: string; description: string; status: string; paid: boolean;
  actions?: React.ReactNode; summary: React.ReactNode; children: React.ReactNode;
  headerDetails?: React.ReactNode;
  // Undefined until the first successful result read. Later polling must not change expansion.
  initiallyCollapsed?: boolean;
  revealEvent?: string;
}) {
  const demo = useDemoMode();
  paid = paid && !demo;
  const contentId = useId();
  const [expanded, setExpanded] = useState<boolean | null>(null);
  if (expanded === null && initiallyCollapsed !== undefined) {
    setExpanded(!initiallyCollapsed);
  }
  useEffect(() => {
    if (!revealEvent) return;
    const reveal = () => setExpanded(true);
    window.addEventListener(revealEvent, reveal);
    return () => window.removeEventListener(revealEvent, reveal);
  }, [revealEvent]);
  const isExpanded = expanded ?? true;
  const completed = status === "Zakończony" || status === "Zakończono";
  const error = status.toLowerCase().includes("błąd");
  const running = ["W toku", "Uruchamianie…", "W kolejce"].includes(status);
  const Icon = completed ? CheckCircle2Icon : error ? CircleAlertIcon : running ? Loader2Icon : CircleIcon;
  return (
    <section data-workflow-step={number} aria-labelledby={`workflow-${number}`} className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <header className="grid gap-4 border-b bg-muted/20 p-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div className="flex items-start gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border bg-background text-sm font-semibold text-muted-foreground">{number}</span>
          <div className="min-w-0 space-y-2">
            <h2 id={`workflow-${number}`} className="text-base font-semibold tracking-tight">{title}</h2>
            <p className="text-sm text-muted-foreground">{description}</p>
            {headerDetails}
            <div className="flex flex-wrap items-center gap-2">
              <span role="status" aria-live="polite" className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium", completed ? "bg-emerald-50 text-emerald-800" : error ? "bg-rose-50 text-rose-800" : running ? "bg-sky-50 text-sky-800" : "bg-muted text-muted-foreground")}>
                <Icon className={cn("size-3.5", running && "animate-spin")} />{completed ? "Zakończono" : status}
              </span>
              <span data-cost={paid ? "paid" : "free"} className={cn("rounded-full px-2.5 py-1 text-xs font-medium", paid ? "bg-amber-50 text-amber-900" : "bg-muted text-muted-foreground")}>{paid ? "Płatne · AI" : "Bez kosztu AI"}</span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          {actions}
          <Button variant="ghost" size="sm" aria-expanded={isExpanded} aria-controls={contentId}
            onClick={() => setExpanded(!isExpanded)}>
            {isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
            {isExpanded ? "Zwiń" : "Rozwiń"}
          </Button>
        </div>
      </header>
      <div id={contentId} hidden={!isExpanded}>
        <div className="space-y-6 p-5">{children}</div>
        <footer className="border-t bg-muted/20 p-5">{summary}</footer>
      </div>
    </section>
  );
}
