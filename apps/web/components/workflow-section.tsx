"use client";

import { useEffect } from "react";
import { CheckCircle2Icon, CircleIcon, CircleAlertIcon, Loader2Icon } from "lucide-react";
import { useDemoMode } from "@/components/demo-mode";
import { useRegisterStage } from "@/components/pipeline-state";
import { cn } from "@/lib/utils";

const STAGE_HELP: Record<number, { purpose: string; requirements: string; next: string }> = {
  1: { purpose: "Zachowuje temat i oryginalny materiał pobrany z RSS.", requirements: "Temat musi pochodzić z aktywnego źródła RSS. W demo dostarcza go seeder.", next: "Sprawdź materiał, zdecyduj czy go opracować i przejdź do oceny lub Research. Zatwierdzenie tematu nie zatwierdza artykułu." },
  2: { purpose: "Ocenia trafność, aktualność oraz potencjał tematu. Zapisuje punktację, kategorię i uzasadnienie.", requirements: "Wymaga zapisanego tematu i braku aktywnej oceny. Ponowne uruchomienie zastępuje punktację.", next: "Wykorzystaj ocenę do decyzji redakcyjnej. Research można uruchomić także bez punktacji." },
  3: { purpose: "Zbiera źródła, fakty, niepewności i konflikty. Tworzy bazę dowodów dla tekstu.", requirements: "Wymaga zapisanego tematu i wolnej kolejki tego etapu. Nowy Research zastępuje raport; ponowna analiza korzysta z zachowanych źródeł.", next: "Sprawdź dowody. Ukończony Research z faktami pozwala przygotować brief i wygenerować artykuł." },
  4: { purpose: "Przygotowuje brief i pisze artykuł na podstawie Research oraz wybranych ustawień.", requirements: "Wymaga ukończonego Research z faktami i braku aktywnej generacji.", next: "Przeczytaj tekst w podglądzie i uruchom QA wybranej wersji. Każda generacja tworzy nową wersję; wcześniejsze pozostają w historii." },
  5: { purpose: "Sprawdza fakty, źródła, styl, strukturę i SEO konkretnej wersji. Korzysta wyłącznie z zapisanych dowodów, bez nowego researchu.", requirements: "Wymaga wygenerowanej wersji, zakończonej edycji i braku aktywnego QA dla tego tekstu.", next: "QA passed wymaga progu raportu, 0 krytycznych problemów i 0 niepopartych twierdzeń. Problemy przejrzyj w poprawkach; QA samo nie zmienia tekstu." },
  6: { purpose: "Auto Fix wykonuje precyzyjne poprawki i zapisuje nową wersję. Approval zapisuje decyzję człowieka o konkretnej wersji.", requirements: "Auto Fix wymaga aktualnego, ukończonego QA, problemów auto-fixable, wolnej kolejki i pozostałej iteracji. Approval wymaga aktualnego QA passed.", next: "Nowa wersja automatycznie trafia do QA. Jedno kliknięcie to jedna iteracja. Nierozwiązane problemy sprawdź ręcznie; zatwierdzenie niczego nie publikuje." },
};

type Tone = "neutral" | "success" | "attention" | "error" | "running";
const TONES: Record<Tone, { header: string; badge: string; border: string }> = {
  neutral: { header: "bg-slate-50/80", badge: "bg-slate-100 text-slate-700", border: "border-slate-200" },
  success: { header: "bg-emerald-50/60", badge: "bg-emerald-100 text-emerald-900", border: "border-emerald-200" },
  attention: { header: "bg-amber-50/70", badge: "bg-amber-100 text-amber-900", border: "border-amber-200" },
  error: { header: "bg-rose-50/70", badge: "bg-rose-100 text-rose-900", border: "border-rose-200" },
  running: { header: "bg-sky-50/70", badge: "bg-sky-100 text-sky-900", border: "border-sky-200" },
};

export function WorkflowSection({ number, title, description, headerDetails, status, paid, actions, summary, children, revealEvent, activity, tone, actionTitle, actionDescription, actionDetails, resultTitle, timestamp }: {
  number: number; title: string; description: string; status: string; paid: boolean;
  actions?: React.ReactNode; summary: React.ReactNode; children: React.ReactNode;
  actionTitle?: string; actionDescription?: string; actionDetails?: React.ReactNode; resultTitle?: string; timestamp?: string | null;
  headerDetails?: React.ReactNode; activity?: React.ReactNode; tone?: Tone;
  // Retained for compatibility with existing callers; stage results stay expanded.
  initiallyCollapsed?: boolean;
  revealEvent?: string;
}) {
  const demo = useDemoMode();
  paid = paid && !demo;
  useEffect(() => {
    if (!revealEvent) return;
    const reveal = () => document.getElementById(`workflow-step-${number}`)?.scrollIntoView({ block: "start" });
    window.addEventListener(revealEvent, reveal);
    return () => window.removeEventListener(revealEvent, reveal);
  }, [number, revealEvent]);
  const completed = status === "Zakończony" || status === "Zakończono";
  const error = status.toLowerCase().includes("błąd");
  const running = ["W toku", "Uruchamianie…", "W kolejce"].includes(status);
  const needsAttention = /wymaga|weryfikacji|odrzucon|zmian/i.test(status);
  const success = completed || /zatwierdzon|gotowy do zatwierdzenia/i.test(status);
  const stateTone = tone ?? (error ? "error" : running ? "running" : needsAttention ? "attention" : success ? "success" : "neutral");
  useRegisterStage(number, stateTone, status);
  const colors = TONES[stateTone];
  const help = STAGE_HELP[number];
  const Icon = completed ? CheckCircle2Icon : error ? CircleAlertIcon : running ? Loader2Icon : CircleIcon;
  return (
    <section tabIndex={-1} id={`workflow-step-${number}`} data-workflow-step={number} aria-labelledby={`workflow-${number}`} data-stage-tone={stateTone} className="scroll-mt-36 min-w-0">
      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_390px]">
        <div className={cn("min-w-0 overflow-hidden rounded-2xl border bg-card shadow-sm", colors.border)}>
          <header className={cn("flex items-start justify-between gap-4 border-b p-6", colors.header, colors.border)}>
            <div className="flex min-w-0 items-start gap-4">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-full border bg-white/80 text-lg font-semibold text-emerald-800">{number}</span>
              <div className="min-w-0"><h2 id={`workflow-${number}`} className="text-xl font-semibold tracking-tight">{title}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p></div>
            </div>
            <span role="status" aria-live="polite" className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium", colors.badge)}>
              <Icon className={cn("size-4", running && "animate-spin")} />{completed ? "Zakończono" : status}
            </span>
          </header>
          <div className="space-y-8 p-6">
            {headerDetails && <div data-stage-context className="space-y-4"><h3 className="text-base font-semibold">Wybrany materiał</h3>{headerDetails}</div>}
            <div data-stage-result className="space-y-5"><h3 className="text-base font-semibold">{resultTitle ?? "Wynik etapu"}</h3>{children}</div>
            <div data-stage-activity className="space-y-4 border-t pt-6"><h3 className="text-base font-semibold">Przebieg zadania</h3>
              {activity ?? <ol className="border-l border-slate-200 pl-5 text-sm"><li className="relative"><span className={cn("absolute -left-[26px] top-1.5 size-3 rounded-full ring-4 ring-white", success ? "bg-emerald-600" : "bg-slate-300")} /><p className="font-medium">{success ? "Wynik etapu zapisany" : "Oczekuje na uruchomienie"}</p><p className="mt-1 text-xs text-muted-foreground">{timestamp ? new Date(timestamp).toLocaleString("pl-PL") : status}</p></li></ol>}
            </div>
          </div>
        </div>
        <aside aria-label={`Panel akcji: ${title}`} className="min-w-0 space-y-4 xl:sticky xl:top-40">
          <div data-stage-actions className="space-y-4 rounded-2xl border bg-card p-6 shadow-sm">
            <h3 className="text-base font-semibold">{actionTitle ?? title}</h3>
            <p className="text-sm leading-6 text-muted-foreground">{actionDescription ?? help?.next}</p>
            {actionDetails}
            <div className="stage-action-buttons space-y-2">{actions}</div>
            <span data-cost={paid ? "paid" : "free"} className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">{paid ? "Płatne · AI" : "Bez kosztu AI"}</span>
          </div>
          {help && <details data-stage-guide className="rounded-2xl border bg-card p-6 shadow-sm"><summary className="cursor-pointer text-base font-semibold focus-visible:outline-2 focus-visible:outline-offset-4">Jak działa ten etap?</summary><dl className="mt-5 space-y-5">
            {[["Cel etapu",help.purpose],["Warunki uruchomienia",help.requirements],["Co dalej",help.next]].map(([label,text]) => <div key={label}><dt className="text-xs font-semibold text-sky-900">{label}</dt><dd className="mt-2 text-sm leading-6 text-slate-600">{text}</dd></div>)}
          </dl></details>}
          <footer className="rounded-2xl border bg-card p-6 shadow-sm">{summary}</footer>
        </aside>
      </div>
    </section>
  );
}

export { WorkflowSection as PipelineStageLayout };
