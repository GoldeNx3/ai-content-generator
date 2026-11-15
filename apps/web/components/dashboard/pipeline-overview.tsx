"use client";

import { useEffect, useState } from "react";
import {
  ChevronDownIcon, MicroscopeIcon, PenLineIcon, RssIcon, SendIcon, ShieldCheckIcon, SparklesIcon, WandSparklesIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

type Cost = "free" | "paid" | "decision";

const STAGES: { icon: typeof RssIcon; title: string; text: string; cost: Cost; here?: boolean }[] = [
  { icon: RssIcon, title: "Pobranie RSS", text: "Nowe tematy z aktywnych źródeł, z wykrywaniem duplikatów.", cost: "free", here: true },
  { icon: SparklesIcon, title: "Ocena AI", text: "Wynik 0–100 i kategoria. Pomaga wybrać, nie blokuje dalszych kroków.", cost: "paid", here: true },
  { icon: MicroscopeIcon, title: "Research", text: "Źródła, fakty z podstawą i ważnością, niepewności i konflikty.", cost: "paid" },
  { icon: PenLineIcon, title: "Artykuł", text: "Brief i treść. Każda generacja to nowa wersja.", cost: "paid" },
  { icon: ShieldCheckIcon, title: "QA", text: "Sprawdza fakty, styl, strukturę i SEO względem researchu.", cost: "paid" },
  { icon: WandSparklesIcon, title: "Auto Fix i zatwierdzenie", text: "Poprawka tworzy nową wersję do ponownego QA. Zatwierdzasz ręcznie.", cost: "decision" },
  { icon: SendIcon, title: "WordPress", text: "Publikacja zatwierdzonej wersji – domyślnie jako szkic.", cost: "decision" },
];

const COST: Record<Cost, { label: string; className: string }> = {
  free: { label: "Bez kosztu AI", className: "bg-emerald-50 text-emerald-800 ring-emerald-200" },
  paid: { label: "Płatne · AI", className: "bg-amber-50 text-amber-900 ring-amber-200" },
  decision: { label: "Twoja decyzja", className: "bg-sky-50 text-sky-800 ring-sky-200" },
};

const STORAGE_KEY = "content-engine:pipeline-overview-open";

export function PipelineOverview() {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- restore per-viewer preference after hydration
      if (localStorage.getItem(STORAGE_KEY) === "0") setOpen(false);
    } catch { /* storage unavailable */ }
  }, []);

  function toggle() {
    const next = !open;
    setOpen(next);
    try { localStorage.setItem(STORAGE_KEY, next ? "1" : "0"); } catch { /* storage unavailable */ }
  }

  return (
    <section aria-labelledby="pipeline-heading" className="rounded-xl bg-card shadow-xs ring-1 ring-foreground/8">
      <button type="button" onClick={toggle} aria-expanded={open} aria-controls="pipeline-stages"
        className="flex w-full items-center justify-between gap-3 rounded-xl px-4 py-3 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:px-5">
        <span className="min-w-0">
          <span id="pipeline-heading" className="block font-semibold">Jak temat staje się artykułem</span>
          <span className="block text-sm text-muted-foreground">7 etapów. Pierwsze dwa uruchamiasz tutaj, resztę w szczegółach tematu. Etapy nie startują same po sobie.</span>
        </span>
        <ChevronDownIcon className={cn("size-5 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden="true" />
      </button>
      {open && (
        <div id="pipeline-stages" className="border-t px-4 pb-4 pt-4 sm:px-5">
          <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-7 lg:gap-0">
            {STAGES.map(({ icon: Icon, title, text, cost, here }, index) => (
              <li key={title} className="relative flex gap-3 lg:flex-col lg:gap-2 lg:px-2">
                {index < STAGES.length - 1 && <span aria-hidden="true" className="absolute left-[calc(50%+1.5rem)] right-[calc(-50%+1.5rem)] top-5 hidden h-px bg-gradient-to-r from-emerald-300 to-zinc-200 lg:block" />}
                <span className={cn("relative z-10 flex size-10 shrink-0 items-center justify-center rounded-full ring-1 lg:mx-auto",
                  here ? "bg-emerald-600 text-white ring-emerald-700 shadow-sm shadow-emerald-600/30" : "bg-white text-zinc-600 ring-zinc-200")}>
                  <Icon className="size-[18px]" aria-hidden="true" />
                </span>
                <span className="min-w-0 space-y-1 lg:text-center">
                  <span className="block text-sm font-semibold"><span className="mr-1 text-muted-foreground tabular-nums">{index + 1}.</span>{title}</span>
                  <span className="block text-xs leading-relaxed text-muted-foreground">{text}</span>
                  <span className="flex flex-wrap gap-1 pt-1 lg:justify-center">
                    <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium ring-1", COST[cost].className)}>{COST[cost].label}</span>
                  </span>
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs text-muted-foreground">Płatne kroki liczą się do miesięcznego budżetu AI. Zadania wykonuje worker w tle – możesz zamknąć przeglądarkę.</p>
        </div>
      )}
    </section>
  );
}
