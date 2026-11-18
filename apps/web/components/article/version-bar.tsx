"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { ArrowRightIcon, CheckIcon, CircleAlertIcon, Layers3Icon } from "lucide-react";

import { FilterSelect } from "@/components/filter-select";
import { navigateStage } from "@/components/pipeline-state";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Article, ArticleSummary } from "@/types/api";

type StepState = "done" | "current" | "problem" | "todo";

export function versionOptionLabel(version: ArticleSummary): string {
  const qa = version.status === "approved" ? "zatwierdzona" : version.qa_passed ? `QA zaliczone (${version.qa_score})` : version.qa_score != null ? `QA ${version.qa_score} · niezaliczone` : "bez QA";
  return `Wersja ${version.version}${version.is_current ? " · najnowsza" : ""} · ${qa}`;
}

/** Co dalej z wybraną wersją: QA → zatwierdzenie → WordPress, z jednym przyciskiem do następnego kroku. */
function nextStep(article: Article): { steps: [string, StepState][]; title: string; text: string; action: string; stage: number; tone: "attention" | "success" | "danger" } {
  const approved = article.status === "approved";
  const qaDone = article.qa_passed;
  const qaFailed = !qaDone && article.qa_score != null;
  const steps: [string, StepState][] = [
    ["QA", qaDone ? "done" : qaFailed ? "problem" : "current"],
    ["Zatwierdzenie", approved ? "done" : qaDone ? "current" : "todo"],
    ["WordPress", approved ? "current" : "todo"],
  ];
  if (approved) return { steps, tone: "success", title: "Gotowa do publikacji", text: "Wersja jest zatwierdzona. Wyślij ją do WordPressa.", action: "Przejdź do publikacji", stage: 8 };
  if (article.status === "rejected") return { steps, tone: "danger", title: "Wersja odrzucona", text: "Popraw tekst albo wygeneruj nową wersję.", action: "Przejdź do poprawek", stage: 6 };
  if (qaDone) return { steps, tone: "success", title: "Czeka na zatwierdzenie", text: "QA zaliczone. Zatwierdź wersję, aby ją wysłać.", action: "Przejdź do zatwierdzenia", stage: 6 };
  if (qaFailed) return { steps, tone: "attention", title: "QA niezaliczone", text: "Popraw problemy — poprawka tworzy nową wersję do ponownego QA.", action: "Przejdź do poprawek", stage: 6 };
  return { steps, tone: "attention", title: "Ta wersja wymaga QA", text: "Uruchom QA, potem zatwierdź wersję i wyślij ją do WordPressa.", action: "Uruchom QA tej wersji", stage: 5 };
}

const STEP_STYLES: Record<StepState, string> = {
  done: "bg-emerald-100 text-emerald-800",
  current: "bg-foreground text-background",
  problem: "bg-amber-100 text-amber-900",
  todo: "bg-muted text-muted-foreground",
};

const TONE_STYLES = {
  attention: "bg-amber-50 text-amber-900 ring-amber-200",
  success: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  danger: "bg-rose-50 text-rose-800 ring-rose-200",
};

const subscribeHash = (notify: () => void) => { window.addEventListener("hashchange", notify); return () => window.removeEventListener("hashchange", notify); };

/**
 * Kompaktowy pasek wersji artykułu. Renderuje się w przyklejonej nawigacji etapów (slot w nav.tsx),
 * więc zostaje widoczny na każdym etapie 4–7 i przy przewijaniu.
 */
export function VersionBar(props: { article: Article; versions: ArticleSummary[]; selecting: boolean; editing: boolean; onSelect: (id: number) => Promise<void> }) {
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- slot lives in the stepper rendered by a parent
  useEffect(() => { setSlot(document.getElementById("pipeline-version-slot")); }, []);
  const bar = <VersionBarContent {...props} />;
  return slot ? createPortal(bar, slot) : bar;
}

function VersionBarContent({ article, versions, selecting, editing, onSelect }: {
  article: Article; versions: ArticleSummary[]; selecting: boolean; editing: boolean; onSelect: (id: number) => Promise<void>;
}) {
  const next = nextStep(article);
  const hash = useSyncExternalStore(subscribeHash, () => window.location.hash, () => "");
  const here = hash === `#workflow-step-${next.stage}`;
  const newest = versions.find((version) => version.is_current);
  const older = !article.is_current && newest && newest.id !== article.id;
  return (
    <section data-version-bar aria-label="Wybrana wersja artykułu"
      className={cn("mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl bg-card px-3 py-2 shadow-xs ring-1", next.tone === "success" ? "ring-emerald-200" : next.tone === "danger" ? "ring-rose-200" : "ring-amber-200")}>
      <Layers3Icon className="hidden size-4 shrink-0 text-muted-foreground sm:block" aria-hidden="true" />
      <FilterSelect inline label="Wersja artykułu" allowAll={false} value={String(article.id)} disabled={selecting || editing} className="h-9 min-w-0 w-64 max-w-full"
        options={versions.map((version) => ({ value: String(version.id), label: versionOptionLabel(version) }))}
        onChange={(value) => value && void onSelect(Number(value))} />

      {older && <button type="button" disabled={selecting || editing} onClick={() => void onSelect(newest.id)}
        className="inline-flex items-center gap-1 text-xs font-medium text-amber-800 underline underline-offset-4 disabled:opacity-50">
        <CircleAlertIcon className="size-3.5" aria-hidden="true" />Starsza wersja · przełącz na {newest.version}
      </button>}
      {editing && <span className="text-xs font-medium text-amber-800">Trwa edycja — zapisz albo anuluj, aby zmienić wersję.</span>}

      <ol aria-label={`Postęp wersji ${article.version}`} className="hidden items-center gap-1 text-xs sm:flex">
        {next.steps.map(([label, state], index) => (
          <li key={label} className="flex items-center gap-1">
            {index > 0 && <span aria-hidden="true" className="h-px w-2 bg-foreground/20" />}
            <span title={label} className={cn("inline-flex h-6 items-center gap-1 rounded-full px-2 font-medium", STEP_STYLES[state])}>
              {state === "done" ? <CheckIcon className="size-3" aria-hidden="true" /> : state === "problem" ? <CircleAlertIcon className="size-3" aria-hidden="true" /> : null}
              {label}<span className="sr-only">{state === "done" ? " — zrobione" : state === "problem" ? " — wymaga poprawek" : state === "current" ? " — następny krok" : " — później"}</span>
            </span>
          </li>
        ))}
      </ol>

      <p className="min-w-0 text-xs leading-5 sm:flex-1 sm:basis-56" title={next.text}>
        <span className={cn("mr-1.5 inline-flex rounded-full px-2 py-0.5 font-semibold ring-1", TONE_STYLES[next.tone])}>{next.title}.</span>
        <span className="hidden text-muted-foreground lg:inline">{next.text}</span>
      </p>

      {here ? <span className="hidden text-xs font-medium text-emerald-800 sm:inline">Jesteś w tym kroku — użyj panelu akcji.</span> :
        <Button size="sm" disabled={editing} className="bg-emerald-700 text-white hover:bg-emerald-800" onClick={() => navigateStage(next.stage)}>{next.action}<ArrowRightIcon /></Button>}
    </section>
  );
}
