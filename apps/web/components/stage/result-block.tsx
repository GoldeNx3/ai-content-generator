"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDownIcon, ChevronsDownUpIcon, ChevronsUpDownIcon, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Wspólny układ wyniku etapu: spis bloków na górze, a pod nim zwijane bloki z nagłówkiem,
 * jednym zdaniem „co to jest” i treścią. Każdy etap używa tego samego wzorca.
 */

const SET_EVENT = "result-block:set";
type SetDetail = { open: boolean; id?: string; scope?: Element | null };

// Bloki do otwarcia przy najbliższym zamontowaniu (np. wynik akcji pojawia się dopiero po przełączeniu wersji).
const pendingOpen = new Set<string>();

/**
 * Otwiera albo zamyka blok o danym id. `remember` utrzymuje otwarcie także dla bloku, który zamontuje się
 * dopiero za chwilę (np. wynik Auto Fix po przełączeniu na nową wersję).
 */
export function setResultBlock(id: string, open = true, remember = true) {
  if (open && remember) pendingOpen.add(id); else pendingOpen.delete(id);
  window.dispatchEvent(new CustomEvent<SetDetail>(SET_EVENT, { detail: { id, open } }));
}

function openAndScroll(id: string) {
  setResultBlock(id, true, false);
  requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

export type OutlineTone = "neutral" | "success" | "attention" | "danger";

const OUTLINE_TONES: Record<OutlineTone, string> = {
  neutral: "text-foreground",
  success: "text-emerald-700 dark:text-emerald-400",
  attention: "text-amber-700 dark:text-amber-400",
  danger: "text-rose-700 dark:text-rose-400",
};

export interface OutlineItem {
  target: string;
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: OutlineTone;
  icon: LucideIcon;
}

const TEXT_BUTTON = "inline-flex min-h-8 items-center gap-1.5 rounded-md px-2 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring";

/** Spis zawartości wyniku: kafel otwiera swój blok i przewija do niego; obok rozwijanie/zwijanie wszystkich bloków etapu. */
export function ResultOutline({ items, label = "Zawartość wyniku", meta }: { items: OutlineItem[]; label?: string; meta?: React.ReactNode }) {
  const ref = useRef<HTMLElement>(null);
  const setAll = (open: boolean) => window.dispatchEvent(new CustomEvent<SetDetail>(SET_EVENT, { detail: { open, scope: ref.current?.closest("[data-stage-result]") } }));
  return (
    <nav ref={ref} aria-label={label} className="space-y-2">
      <ul className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {items.map(({ target, label: itemLabel, value, hint, tone = "neutral", icon: Icon }) => (
          <li key={target} className="min-w-0">
            <button type="button" onClick={() => openAndScroll(target)}
              className="group flex h-full w-full min-w-0 flex-col gap-1 rounded-xl bg-muted/50 p-3 text-left ring-1 ring-transparent transition-colors hover:bg-muted hover:ring-foreground/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
              <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Icon className="size-3.5 shrink-0" aria-hidden="true" />{itemLabel}
              </span>
              <span className={cn("text-xl font-semibold tabular-nums leading-tight", OUTLINE_TONES[tone])}>{value}</span>
              {hint && <span className="truncate text-xs text-muted-foreground">{hint}</span>}
            </button>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-xs text-muted-foreground">{meta}</p>
        <div className="flex flex-wrap gap-1">
        <button type="button" onClick={() => setAll(true)} className={TEXT_BUTTON}><ChevronsUpDownIcon className="size-3.5" aria-hidden="true" />Rozwiń wszystkie sekcje</button>
        <button type="button" onClick={() => setAll(false)} className={TEXT_BUTTON}><ChevronsDownUpIcon className="size-3.5" aria-hidden="true" />Zwiń wszystkie</button>
        </div>
      </div>
    </nav>
  );
}

/**
 * Zwijany blok wyniku: nagłówek (ikona, tytuł, licznik, jedno zdanie) jest przyciskiem.
 * Zwinięta treść zostaje w DOM (atrybut hidden), więc odnośniki #id do jej elementów działają —
 * wejście na taki odnośnik otwiera blok.
 */
export function ResultBlock({ id, icon: Icon, title, count, description, actions, children, className, defaultOpen = false }: {
  id: string; icon: LucideIcon; title: string; count?: number; description: React.ReactNode;
  actions?: React.ReactNode; children: React.ReactNode; className?: string; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(() => pendingOpen.delete(id) || defaultOpen);
  const sectionRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const uid = useId();
  const titleId = `${id}-title`;
  const descriptionId = `${uid}-description`;
  const contentId = `${uid}-content`;

  useEffect(() => {
    const onSet = (event: Event) => {
      const { open: next, id: target, scope } = (event as CustomEvent<SetDetail>).detail;
      if (target ? target === id : Boolean(scope && sectionRef.current && scope.contains(sectionRef.current))) setOpen(next);
    };
    const onHash = () => {
      const hash = decodeURIComponent(window.location.hash.slice(1));
      const target = hash ? document.getElementById(hash) : null;
      if (target && contentRef.current?.contains(target)) {
        setOpen(true);
        requestAnimationFrame(() => target.scrollIntoView({ block: "start" }));
      }
    };
    window.addEventListener(SET_EVENT, onSet);
    window.addEventListener("hashchange", onHash);
    return () => { window.removeEventListener(SET_EVENT, onSet); window.removeEventListener("hashchange", onHash); };
  }, [id]);

  return (
    <section ref={sectionRef} id={id} aria-labelledby={titleId} data-open={open}
      className={cn("scroll-mt-60 border-t pt-5 first:border-t-0 first:pt-0", className)}>
      <h4>
        <button type="button" aria-expanded={open} aria-controls={contentId} aria-labelledby={titleId} aria-describedby={descriptionId}
          onClick={() => setOpen((value) => !value)}
          className="group -mx-2 flex w-[calc(100%+1rem)] items-start gap-3 rounded-xl p-2 text-left transition-colors hover:bg-muted/60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
          <span className={cn("hidden size-9 shrink-0 items-center justify-center rounded-lg ring-1 transition-colors sm:flex",
            open ? "bg-emerald-50 text-emerald-700 ring-emerald-100 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-900" : "bg-muted text-muted-foreground ring-transparent")} aria-hidden="true">
            <Icon className="size-4.5" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-baseline gap-2">
              <span id={titleId} className="text-base font-semibold">{title}</span>
              {count !== undefined && <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium tabular-nums text-muted-foreground group-hover:bg-background">{count}</span>}
            </span>
            <span id={descriptionId} className="mt-0.5 block max-w-prose text-sm font-normal leading-6 text-muted-foreground">{description}</span>
          </span>
          <span className="flex shrink-0 items-center gap-1.5 self-center text-xs font-medium text-muted-foreground group-hover:text-foreground" aria-hidden="true">
            <span className="hidden sm:inline">{open ? "Zwiń" : "Rozwiń"}</span>
            <span className={cn("flex size-7 items-center justify-center rounded-full ring-1 transition-colors",
              open ? "bg-emerald-600 text-white ring-emerald-600" : "bg-background ring-foreground/15")}>
              <ChevronDownIcon className={cn("size-4 transition-transform duration-200 motion-reduce:transition-none", open && "rotate-180")} />
            </span>
          </span>
        </button>
      </h4>
      <div ref={contentRef} id={contentId} hidden={!open} className="space-y-4 pt-4">
        {actions && <div className="flex flex-wrap justify-end gap-2">{actions}</div>}
        {children}
      </div>
    </section>
  );
}

/** Pozioma skala 0–100 z wartością liczbową; kolor zależy od progu. */
export function Meter({ value, label, suffix = "%", className }: { value: number; label: string; suffix?: string; className?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped >= 85 ? "bg-emerald-600" : clamped >= 65 ? "bg-amber-500" : "bg-rose-500";
  return (
    <span className={cn("inline-flex items-center gap-2", className)} title={`${label}: ${clamped}${suffix}`}>
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="h-1.5 w-14 overflow-hidden rounded-full bg-muted" aria-hidden="true">
        <span className={cn("block h-full rounded-full", color)} style={{ width: `${clamped}%` }} />
      </span>
      <span className="text-xs font-semibold tabular-nums">{clamped}{suffix}</span>
    </span>
  );
}
