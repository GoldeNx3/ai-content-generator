"use client";

import type { Job } from "@/types/api";
import { AgentProgress } from "@/components/agent-progress";
import { useEffect } from "react";
import { CheckCircle2Icon, CircleHelpIcon, CircleIcon, CircleAlertIcon, InfoIcon, Loader2Icon, ReceiptIcon } from "lucide-react";
import { InfoDialog } from "@/components/ui/info-dialog";
import { useDemoMode } from "@/components/demo-mode";
import { useRegisterStage } from "@/components/pipeline-state";
import { cn } from "@/lib/utils";

const STAGE_HELP: Record<number, { purpose: string; requirements: string; next: string }> = {
  1: { purpose: "Zachowuje temat i oryginalny materiał pobrany z RSS.", requirements: "Temat pochodzi z aktywnego źródła RSS. W trybie demo dostarcza go seeder.", next: "Sprawdź materiał i zdecyduj, czy go opracować. Zatwierdzenie tematu nie zatwierdza artykułu i niczego nie uruchamia." },
  2: { purpose: "Ocenia trafność (40%), aktualność (20%), potencjał wyszukiwań (25%) i potencjał komercyjny (15%). Zapisuje punktację, kategorię i uzasadnienie.", requirements: "Wymaga zapisanego tematu i braku innego aktywnego zadania dla tego tematu. Ponowna ocena zastępuje punktację.", next: "Wykorzystaj ocenę do decyzji redakcyjnej. Research można uruchomić także bez punktacji." },
  3: { purpose: "Zbiera źródła, fakty, niepewności i sprzeczności. Tworzy bazę dowodów dla tekstu.", requirements: "Wymaga zapisanego tematu i braku innego aktywnego zadania. Wyszukanie od nowa zastępuje raport; analiza zapisanych źródeł je zachowuje.", next: "Sprawdź dowody. Ukończony research z faktami odblokowuje generowanie artykułu." },
  4: { purpose: "Przygotowuje brief i pisze artykuł na podstawie researchu oraz wybranych ustawień.", requirements: "Wymaga ukończonego researchu z faktami i braku aktywnej generacji.", next: "Przeczytaj tekst i uruchom QA wybranej wersji. Każda generacja tworzy nową wersję; poprzednie zostają w historii." },
  5: { purpose: "Sprawdza fakty, źródła, styl, strukturę i SEO konkretnej wersji. Korzysta wyłącznie z zapisanych dowodów, bez nowego researchu.", requirements: "Wymaga wygenerowanej wersji, zakończonej edycji i braku aktywnego QA.", next: "Zaliczenie wymaga progu z raportu, 0 krytycznych problemów i 0 niepopartych twierdzeń. QA nie zmienia tekstu — poprawki są w kolejnym etapie." },
  6: { purpose: "Auto Fix wprowadza precyzyjne poprawki i zapisuje nową wersję. Zatwierdzenie to decyzja człowieka o konkretnej wersji.", requirements: "Auto Fix wymaga aktualnego, ukończonego QA z problemami do automatycznej poprawy i wolnego limitu iteracji. Zatwierdzenie wymaga aktualnego, zaliczonego QA.", next: "Nowa wersja po poprawce wymaga osobnego QA. Jedno kliknięcie to jedna iteracja. Zatwierdzenie niczego nie publikuje." },
  8: { purpose: "Wysyła zatwierdzoną wersję do WordPressa jako szkic, zaplanowany albo opublikowany wpis, razem z danymi SEO.", requirements: "Wymaga zatwierdzonej wersji z aktualnym, zaliczonym QA, połączenia z WordPressem (Ustawienia → Integracje) i wtyczki Content Engine Bridge.", next: "Domyślnie powstaje szkic. Zmian wprowadzonych ręcznie w WordPressie system nie nadpisuje bez Twojego potwierdzenia." },
};

type Tone = "neutral" | "success" | "attention" | "error" | "running";
const TONES: Record<Tone, { badge: string; ring: string; number: string }> = {
  neutral: { badge: "bg-slate-100 text-slate-700", ring: "ring-foreground/8", number: "bg-slate-100 text-slate-700" },
  success: { badge: "bg-emerald-100 text-emerald-900", ring: "ring-emerald-200", number: "bg-emerald-600 text-white" },
  attention: { badge: "bg-amber-100 text-amber-900", ring: "ring-amber-200", number: "bg-amber-500 text-white" },
  error: { badge: "bg-rose-100 text-rose-900", ring: "ring-rose-200", number: "bg-rose-600 text-white" },
  running: { badge: "bg-sky-100 text-sky-900", ring: "ring-sky-200", number: "bg-sky-600 text-white" },
};

function ActionGroup({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      {title && <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>}
      <div className="stage-action-buttons">{children}</div>
    </div>
  );
}

export interface WorkflowSectionProps {
  number: number; title: string; description: string; status: string; paid: boolean;
  summary: React.ReactNode; children: React.ReactNode;
  /** Nagłówek i opis panelu akcji. */
  actionTitle?: string; actionDescription?: string;
  /** Krótkie liczby lub stan pod opisem (np. „12 źródeł · 30 faktów”). */
  actionDetails?: React.ReactNode;
  /** Dlaczego główna akcja jest niedostępna albo czego wymaga — wyróżniona informacja nad przyciskami. */
  blocker?: React.ReactNode;
  /** Główna akcja etapu (uruchomienie, decyzja). */
  primary?: React.ReactNode; primaryTitle?: string;
  /** Akcje dodatkowe tego samego etapu. */
  secondary?: React.ReactNode; secondaryTitle?: string;
  /** Narzędzia pomocnicze (diagnostyka, planowanie). */
  tools?: React.ReactNode; toolsTitle?: string;
  /** Przejście do następnego etapu — zawsze aktywne, na dole panelu. */
  navigation?: React.ReactNode; navigationTitle?: string;
  resultTitle?: string | null; timestamp?: string | null;
  progressJob?: Job;
  headerDetails?: React.ReactNode; activity?: React.ReactNode; tone?: Tone;
  // Pozostawione dla zgodności wywołań; wyniki etapów są zawsze rozwinięte.
  initiallyCollapsed?: boolean;
  revealEvent?: string;
}

export function WorkflowSection({ number, title, description, headerDetails, status, paid, summary, children, revealEvent, activity, tone,
  actionTitle, actionDescription, actionDetails, blocker, primary, primaryTitle, secondary, secondaryTitle, tools, toolsTitle, navigation, navigationTitle,
  resultTitle, timestamp, progressJob }: WorkflowSectionProps) {
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
  const card = "rounded-2xl bg-card shadow-xs ring-1";
  return (
    <section tabIndex={-1} id={`workflow-step-${number}`} data-workflow-step={number} aria-labelledby={`workflow-${number}`} data-stage-tone={stateTone} className="min-w-0 scroll-mt-56 space-y-5">
      <header className={cn("flex flex-wrap items-center justify-between gap-4 p-5", card, colors.ring)}>
        <div className="flex min-w-0 flex-1 basis-72 items-center gap-4">
          <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl text-base font-semibold tabular-nums", colors.number)} aria-hidden="true">{number === 8 ? 7 : number}</span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Etap {number === 8 ? 7 : number} z 7</p>
            <h2 id={`workflow-${number}`} className="text-xl font-semibold tracking-tight">{title}</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>
          </div>
        </div>
        <span role="status" aria-live="polite" className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium", colors.badge)}>
          <Icon className={cn("size-4", running && "animate-spin")} aria-hidden="true" />{completed ? "Zakończono" : status}
        </span>
      </header>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <aside aria-label={`Panel akcji: ${title}`} className="order-1 min-w-0 space-y-4 xl:sticky xl:top-56 xl:order-2">
          <div data-stage-actions className={cn("overflow-hidden ring-emerald-200", card)}>
            <div className="space-y-2 border-b p-5">
              <h3 className="text-base font-semibold">{actionTitle ?? title}</h3>
              <p className="text-sm leading-6 text-muted-foreground">{actionDescription ?? help?.next}</p>
              {actionDetails && <div className="pt-1">{actionDetails}</div>}
            </div>
            <div className="space-y-5 p-5">
              {blocker && <div className="flex gap-2 rounded-lg bg-amber-50 p-3 text-sm leading-6 text-amber-950 ring-1 ring-amber-200">
                <InfoIcon className="mt-1 size-4 shrink-0 text-amber-700" aria-hidden="true" /><div className="min-w-0">{blocker}</div>
              </div>}
              {primary && <ActionGroup title={primaryTitle}>{primary}</ActionGroup>}
              {secondary && <div className="border-t pt-5"><ActionGroup title={secondaryTitle}>{secondary}</ActionGroup></div>}
              {tools && <div className="border-t pt-5"><ActionGroup title={toolsTitle}>{tools}</ActionGroup></div>}
            </div>
            {navigation && <div className="border-t bg-muted/40 p-5"><ActionGroup title={navigationTitle ?? "Następny etap"}>{navigation}</ActionGroup></div>}
            <div className="space-y-2 border-t px-5 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span data-cost={paid ? "paid" : "free"} className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1", paid ? "bg-amber-50 text-amber-900 ring-amber-200" : "bg-emerald-50 text-emerald-800 ring-emerald-200")}>{paid ? "Płatne · AI" : "Bez kosztu AI"}</span>
                {demo && <span className="text-xs text-sky-800">Tryb demo · 0 kosztów</span>}
              </div>
              <div className="-mx-2 grid">
                {help && <InfoDialog data-stage-guide label="Jak działa ten etap?" title={`Jak działa etap: ${title}`} icon={CircleHelpIcon}>
                  <dl className="space-y-4">
                    {[["Cel etapu", help.purpose], ["Warunki uruchomienia", help.requirements], ["Co dalej", help.next]].map(([label, text]) => <div key={label}><dt className="text-xs font-semibold uppercase tracking-wider text-sky-900">{label}</dt><dd className="mt-1 text-sm leading-6 text-slate-700">{text}</dd></div>)}
                  </dl>
                </InfoDialog>}
                <footer><InfoDialog label="Koszt i szczegóły uruchomienia" title={`Koszt i szczegóły: ${title}`} icon={ReceiptIcon}>{summary}</InfoDialog></footer>
              </div>
            </div>
          </div>
        </aside>

        <div className={cn("order-2 min-w-0 overflow-hidden xl:order-1", card, colors.ring)}>
          <div className="space-y-8 p-5 sm:p-6">
            {headerDetails && <div data-stage-context className="space-y-4"><h3 className="text-base font-semibold">Wybrany materiał</h3>{headerDetails}</div>}
            <div data-stage-result className="space-y-5">{progressJob && <AgentProgress key={progressJob.id} job={progressJob} />}{resultTitle !== null && <h3 className="text-base font-semibold">{resultTitle ?? "Wynik etapu"}</h3>}{children}</div>
            <div data-stage-activity className="space-y-4 border-t pt-6"><h3 className="text-base font-semibold">Przebieg zadania</h3>
              {activity ?? <ol className="border-l border-slate-200 pl-5 text-sm"><li className="relative"><span className={cn("absolute -left-[26px] top-1.5 size-3 rounded-full ring-4 ring-white", success ? "bg-emerald-600" : "bg-slate-300")} /><p className="font-medium">{success ? "Wynik etapu zapisany" : "Oczekuje na uruchomienie"}</p><p className="mt-1 text-xs text-muted-foreground">{timestamp ? new Date(timestamp).toLocaleString("pl-PL") : status}</p></li></ol>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export { WorkflowSection as PipelineStageLayout };
