"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRightIcon, CircleAlertIcon, GaugeIcon, LibraryIcon, ListChecksIcon, PenLineIcon, RefreshCwIcon, SearchIcon, ShieldAlertIcon, ShieldCheckIcon, type LucideIcon } from "lucide-react";
import { ResultBlock, ResultOutline, setResultBlock } from "@/components/stage/result-block";
import { toast } from "sonner";
import { navigateStage } from "@/components/pipeline-state";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { ScoreBar } from "@/components/score-badge";
import { Button } from "@/components/ui/button";
import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { api, errorText } from "@/lib/api";
import { qaState } from "@/lib/workflow";
import type { Article, ArticleSummary, ArticleFix, ArticleQA, ArticleQAIssue, QAIssueType } from "@/types/api";
import { FixApprovalPanel } from "./fix-approval-panel";
import { sectionAnchor } from "./markdown";

const ISSUE_LABELS: Record<QAIssueType, string> = {
  unsupported_claim: "Niepoparte twierdzenie", contradiction: "Sprzeczność z researchem",
  incorrect_number: "Nieprawidłowa liczba", incorrect_date: "Nieprawidłowa data",
  unsupported_quote: "Niepotwierdzony cytat", unsupported_name: "Niepotwierdzona nazwa lub osoba",
  source_mismatch: "Nieprawidłowe referencje", missing_uncertainty: "Pominięta niepewność",
  ignored_conflict: "Pominięty konflikt źródeł", title_mismatch: "Mylący tytuł",
  repetition: "Powtórzenie", too_close_to_source: "Zbyt blisko tekstu źródła", unverified_number: "Liczba bez potwierdzenia w źródłach", style_issue: "Problem stylistyczny", structure_issue: "Problem struktury",
  seo_issue: "Problem SEO", overclaim: "Zbyt mocne twierdzenie", other: "Inny problem",
};
const AUTO_FIX_TYPES = ["unsupported_claim", "title_mismatch", "repetition", "style_issue", "structure_issue", "seo_issue", "overclaim", "too_close_to_source", "unverified_number", "incorrect_number", "incorrect_date"];
const SEVERITY_LABELS = { info: "Informacja", warning: "Ostrzeżenie", high: "Wysoki", critical: "Krytyczny" };
const SEVERITY_STYLES = {
  info: "bg-sky-50 text-sky-800", warning: "bg-amber-50 text-amber-900",
  high: "bg-orange-50 text-orange-900", critical: "bg-rose-50 text-rose-800",
};

export function QAPanel({ article, versions, onSelectVersion, selectingVersion, candidateId, editing, onArticleChange, onVersionCreated, onEdit }: {
  article: Article; candidateId: number; editing: boolean; onArticleChange: () => Promise<void>;
  onVersionCreated: (id: number, sourceId: number) => Promise<void>; onEdit: () => void;
  versions: ArticleSummary[]; onSelectVersion: (id: number) => Promise<void>; selectingVersion: boolean;
}) {
  const demo = useDemoMode();
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const [report, setReport] = useState<ArticleQA | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const load = useCallback(async () => {
    try {
      const result = await api.getQA(article.id);
      if (!mounted.current) return false;
      setReport(result); setLoaded(true); setError(null); return true;
    }
    catch (failure) { if (mounted.current) setError(errorText(failure)); return false; }
  }, [article.id]);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- reload persisted report after an article edit
  useEffect(() => { void load(); }, [load, article.updated_at]);
  const refresh = async () => { const ok = await load(); if (ok && mounted.current) await onArticleChange(); return ok; };
  const jobs = useCandidateJobs(candidateId, "qa_article", refresh, article.id);
  const [fixes, setFixes] = useState<ArticleFix[]>([]);
  const [fixError, setFixError] = useState<string | null>(null);
  const [fixSubmitting, setFixSubmitting] = useState(false);
  const activeFixSeen = useRef(false);
  const loadFixes = async () => {
    try {
      const list = await api.listFixes(article.id);
      if (!mounted.current) return false;
      setFixes(list); setFixError(null);
      const latest = list[0];
      if (latest && ["pending", "running"].includes(latest.status)) activeFixSeen.current = true;
      if (latest?.status === "completed" && activeFixSeen.current) {
        activeFixSeen.current = false;
        if (latest.result_article_version_id) {
          toast.success("Nowa wersja utworzona. Uruchom jej QA, gdy zechcesz ją sprawdzić.");
          setResultBlock("auto-fix-report");
          await onVersionCreated(latest.result_article_version_id, article.id);
        }
      }
      return true;
    } catch (failure) { if (mounted.current) setFixError(errorText(failure)); return false; }
  };
  const fixJobs = useCandidateJobs(candidateId, "auto_fix_article", loadFixes, article.id);
  async function runFix() {
    setFixSubmitting(true); activeFixSeen.current = true;
    try { await fixJobs.enqueue(() => api.autoFix(article.id)); toast.success("Auto Fix zapisany w kolejce"); navigateStage(6); }
    catch (failure) { toast.error("Nie udało się uruchomić Auto Fix", {description: errorText(failure)}); }
    finally { if (mounted.current) setFixSubmitting(false); }
  }
  const fixable = report?.issues.filter((issue) => issue.auto_fixable && AUTO_FIX_TYPES.includes(issue.type)).length ?? 0;
  const busy = submitting || Boolean(jobs.active) || !jobs.loaded || !loaded || editing || selectingVersion;
  const autoFixDisabledReason = editing ? "Zapisz lub anuluj edycję przed uruchomieniem Auto Fix." :
    selectingVersion ? "Poczekaj na wczytanie wybranej wersji." :
    fixSubmitting || fixJobs.active || jobs.active || submitting ? "Dla tego tematu trwa zadanie. Poczekaj na jego zakończenie." :
    !loaded || !jobs.loaded || !fixJobs.loaded ? "Sprawdzanie raportu QA i kolejki…" :
    error || jobs.error || fixJobs.error ? "Nie udało się sprawdzić QA lub kolejki. Poczekaj na odświeżenie." :
    !report || report.status !== "completed" ? "Najpierw uruchom i zakończ QA dla tej wersji." :
    report.is_stale ? "Raport QA jest nieaktualny. Uruchom QA ponownie." :
    article.auto_fix_iterations_remaining === 0 ? "Limit Auto Fix został wykorzystany. Wymagana ręczna weryfikacja." :
    !fixable ? "QA nie wskazuje problemów możliwych do automatycznej poprawy." : null;
  const targetStatus = !loaded ? "Sprawdzanie historii QA…" : error ? "Nie udało się odczytać historii QA" :
    !report ? "QA jeszcze nie uruchomiono" : report.is_stale ? "QA nieaktualne · tekst zmieniony" :
    report.status === "completed" ? `QA wykonane · ${report.overall_score}/100${report.qa_passed ? " · QA zaliczone" : " · Wymaga weryfikacji"}` :
    report.status === "pending" ? "QA w kolejce" : report.status === "running" ? "QA w toku" : "QA nieudane";
  const status = error ? "Błąd odczytu" : report?.is_stale ? "Wymaga ponownej oceny" :
    jobs.latest && jobs.latest.status !== "succeeded" ? jobStatusLabel[jobs.latest.status] : qaState(report, loaded);
  async function run() {
    setSubmitting(true);
    try {
      await jobs.enqueue(() => api.runQA(article.id));
      toast.success("QA zapisane w kolejce");
    } catch (failure) { toast.error("Nie udało się uruchomić QA", {description: errorText(failure)}); }
    finally { setSubmitting(false); }
  }
  return <><WorkflowSection progressJob={jobs.ownActive} number={5} title="Kontrola jakości (QA)" paid status={status} resultTitle="Raport QA"
    tone={(status === "Zakończony" || status === "Zakończono") && report?.status === "completed" && !report.is_stale ? report.qa_passed ? "success" : "attention" : undefined}
    description="Kontrola faktów i jakości wybranej wersji na podstawie zapisanych dowodów."
    headerDetails={<div data-qa-target={article.id} className="space-y-1.5 rounded-xl bg-muted/40 p-4">
      <p className="text-xs font-medium text-muted-foreground">Artykuł wybrany do QA · Wersja {article.version}</p>
      <p className="break-words text-sm font-semibold">{article.title}</p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <p data-qa-target-status className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${report?.status === "completed" && !report.is_stale ? report.qa_passed ? "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-1 ring-amber-200" : "bg-background text-muted-foreground ring-1 ring-foreground/10"}`}>{targetStatus}</p>
        <a href="#article-workspace" onClick={() => window.dispatchEvent(new Event(`article-${article.id}-reveal`))} className="inline-flex min-h-8 items-center rounded text-sm font-medium underline underline-offset-4 focus-visible:outline-2">Czytaj wybrany tekst</a>
      </div>
      <p className="text-xs text-muted-foreground">Inną wersję wybierzesz w pasku nad etapem.</p>
    </div>}
    initiallyCollapsed={loaded ? report?.status === "completed" && !report.is_stale : undefined}
    actionTitle="QA wybranej wersji" actionDescription="QA ocenia tekst i wskazuje problemy. Poprawki i decyzja redakcyjna są w etapie „Poprawki i zatwierdzenie”."
    blocker={editing ? "Zapisz lub anuluj edycję przed uruchomieniem QA." : undefined}
    primary={<Button variant={report?.status === "completed" && !report.is_stale ? "outline" : "default"} disabled={busy} onClick={() => void run()}>
      {report ? <RefreshCwIcon /> : <ShieldCheckIcon />}{report ? `Uruchom QA ponownie · ${demo ? "demo · bezpłatne" : "płatne"}` : `Uruchom QA · ${demo ? "demo · bezpłatne" : "płatne"}`}
    </Button>}
    navigation={<>
      <Button variant={report?.status === "completed" && !report.is_stale ? "default" : "outline"} onClick={() => navigateStage(6)}>Przejdź do poprawek i zatwierdzenia<ArrowRightIcon /></Button>
      <p className="action-hint">Samo przejście nie uruchamia poprawek ani nie zatwierdza tekstu.</p>
    </>}

    activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active}
      error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label: "QA / Fact Checker", configured: "qa", model: report?.llm_model,
      input: report?.llm_input_tokens, output: report?.llm_output_tokens, cost: report?.estimated_cost_usd}]}
      note="QA korzysta wyłącznie z zapisanych materiałów tej wersji. Nie poprawia ani nie publikuje artykułu." />}>

    <div className="space-y-6">
      {error && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {report?.is_stale && <p role="status" className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">Treść zmieniła się od tej oceny. Raport dotyczy poprzedniej treści; uruchom QA ponownie.</p>}
      {article.auto_fix_iterations_remaining === 0 && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200">Limit Auto Fix został wykorzystany. Wymagana ręczna weryfikacja.</p>}
      {!report && loaded && <QAEmpty />}
      {report && report.status !== "completed" && <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">{report.status === "failed" ? "Ostatnie QA zakończyło się błędem. Ponów zadanie w panelu „Przebieg zadania” albo uruchom QA ponownie." : "QA sprawdza tekst w tle. Raport pojawi się tutaj po zakończeniu."}</p>}
      {report?.status === "completed" && <QualityReport key={report.id} report={report} article={article} fixable={fixable} />}
    </div>
  </WorkflowSection>
    <FixApprovalPanel selectingVersion={selectingVersion} versions={versions} article={article} qa={report} fixes={fixes} jobs={fixJobs} error={fixError} editing={editing}
      actionsLoading={!loaded || !jobs.loaded || !fixJobs.loaded || Boolean(jobs.active)}
      onAutoFix={runFix} autoFixDisabledReason={autoFixDisabledReason} fixSubmitting={fixSubmitting} fixableCount={fixable}
      onRefresh={onArticleChange} onSelectVersion={onSelectVersion} onEdit={onEdit} />
  </>;
}

const QA_AREAS: [LucideIcon, string, string][] = [
  [ListChecksIcon, "Fakty", "liczby, daty, cytaty i twierdzenia względem researchu"],
  [LibraryIcon, "Źródła", "czy odwołania pasują do zapisanych źródeł"],
  [PenLineIcon, "Styl i struktura", "powtórzenia, przesada, układ sekcji"],
  [SearchIcon, "SEO", "tytuł, opis i nagłówki"],
];

function QAEmpty() {
  return <div className="rounded-xl border border-dashed p-5">
    <p className="font-medium">QA jeszcze nie uruchomiono dla tej wersji</p>
    <p className="mt-1 text-sm leading-6 text-muted-foreground">QA porówna tekst z zapisanym researchem i briefem — bez internetu i bez nowego researchu. Sprawdzi:</p>
    <ul className="mt-3 grid gap-2 text-sm sm:grid-cols-2">{QA_AREAS.map(([Icon, title, text]) =>
      <li key={title} className="flex gap-2"><Icon className="mt-0.5 size-4 shrink-0 text-emerald-700" aria-hidden="true" /><span><span className="font-medium">{title}</span> <span className="text-muted-foreground">— {text}</span></span></li>)}</ul>
  </div>;
}

const SEVERITY_ORDER = { critical: 0, high: 1, warning: 2, info: 3 } as const;

function QualityReport({report, article, fixable}: {report: ArticleQA; article: Article; fixable: number}) {
  const scores = [["Fakty", report.factual_score, "40%"], ["Źródła", report.source_score, "20%"], ["Styl", report.style_score, "15%"],
    ["Struktura", report.structure_score, "15%"], ["SEO", report.seo_score, "10%"]] as const;
  const claims = report.supported_claims_count + report.unsupported_claims_count;
  const passed = report.qa_passed && !report.is_stale;
  const isAuto = (issue: ArticleQAIssue) => !report.is_stale && issue.auto_fixable && AUTO_FIX_TYPES.includes(issue.type);
  const sorted = [...report.issues].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  const groups = [
    { title: "Do poprawy automatycznej", description: "Auto Fix w etapie 6 może je poprawić bez dodawania nowych faktów.", items: sorted.filter(isAuto) },
    { title: "Do ręcznej weryfikacji", description: "Wymagają decyzji redakcji — popraw tekst ręcznie albo świadomie zostaw.", items: sorted.filter((issue) => !isAuto(issue)) },
  ];
  return <div className="space-y-6" data-qa-report={report.id}>
    <ResultOutline label="Zawartość raportu QA" meta={`Problemy: ${report.issues.length} · automatycznie: ${fixable} · ręcznie: ${report.issues.length - fixable}`} items={[
      { target: "qa-score", label: "Wynik", value: `${report.overall_score}/100`, hint: report.is_stale ? "nieaktualny" : passed ? "QA zaliczone" : `próg ${report.pass_score}`, icon: GaugeIcon, tone: report.is_stale ? "neutral" : passed ? "success" : "attention" },
      { target: "qa-issues", label: "Problemy", value: report.issues.length, hint: `${fixable} do Auto Fix`, icon: CircleAlertIcon, tone: report.issues.length ? "attention" : "success" },
      { target: "qa-score", label: "Poparte twierdzenia", value: `${report.supported_claims_count}/${claims}`, hint: report.unsupported_claims_count ? `${report.unsupported_claims_count} niepoparte` : "wszystkie poparte", icon: ListChecksIcon, tone: report.unsupported_claims_count ? "danger" : "success" },
      { target: "qa-issues", label: "Krytyczne", value: report.critical_issue_count, hint: report.critical_issue_count ? "blokują zatwierdzenie" : "brak", icon: ShieldAlertIcon, tone: report.critical_issue_count ? "danger" : "neutral" },
    ]} />

    <ResultBlock id="qa-score" icon={GaugeIcon} title="Raport jakości"
      description="Ogólna ocena i wyniki w pięciu obszarach. Wynik to średnia ważona; wagi podane przy każdym obszarze.">
      <div className="grid gap-5 rounded-xl bg-muted/40 p-5 md:grid-cols-[12rem_minmax(0,1fr)]">
        <div className="space-y-2">
          <p className="text-5xl font-semibold tabular-nums">{report.overall_score}<span className="text-base font-normal text-muted-foreground"> / 100</span></p>
          <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ring-1 ${report.is_stale ? "bg-muted text-muted-foreground ring-foreground/10" : passed ? "bg-emerald-50 text-emerald-800 ring-emerald-200" : "bg-amber-50 text-amber-900 ring-amber-200"}`}>
            {report.is_stale ? "Ocena nieaktualna" : passed ? "QA zaliczone" : "Wymaga weryfikacji"}</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">{scores.map(([label, value, weight]) => <ScoreBar key={label} label={`${label} · waga ${weight}`} value={value} />)}</div>
      </div>
      {report.summary && <p className="max-w-prose text-sm leading-6">{report.summary}</p>}
      <dl className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        {([["Poparte twierdzenia", report.supported_claims_count, "neutral"], ["Niepoparte twierdzenia", report.unsupported_claims_count, "attention"],
          ["Ostrzeżenia", report.warning_count, "attention"], ["Krytyczne problemy", report.critical_issue_count, "danger"]] as const).map(([label, value, tone]) =>
          <div key={label} className={`rounded-lg p-3 ring-1 ${value > 0 && tone === "danger" ? "bg-rose-50 text-rose-900 ring-rose-200" : value > 0 && tone === "attention" ? "bg-amber-50 text-amber-900 ring-amber-200" : "bg-background ring-foreground/8"}`}>
            <dt className="text-xs">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd></div>)}
      </dl>
      <p className="text-xs leading-5 text-muted-foreground">QA jest zaliczone, gdy wynik wynosi co najmniej {report.pass_score}/100 i nie ma problemów krytycznych ani niepopartych twierdzeń. Problem krytyczny ogranicza wynik do 60, niepoparte twierdzenie o wysokiej wadze — do 75.</p>
    </ResultBlock>

    <ResultBlock id="qa-issues" icon={CircleAlertIcon} title="Problemy" count={report.issues.length}
      description="Co QA znalazło w tekście, z cytatem, powodem i sugestią. Poprawki uruchamiasz w etapie 6 — QA niczego nie zmienia.">
      {report.issues.length === 0 ? <p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">Nie wykryto problemów.</p> :
        groups.filter((group) => group.items.length).map((group) => <section key={group.title} aria-label={group.title} className="space-y-2">
          <h5 className="flex flex-wrap items-baseline gap-x-2 text-sm"><span className="font-semibold">{group.title} <span className="font-normal tabular-nums text-muted-foreground">({group.items.length})</span></span><span className="text-xs text-muted-foreground">{group.description}</span></h5>
          <ol className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">{group.items.map((issue) => <IssueCard key={issue.id} issue={issue} article={article} stale={report.is_stale} />)}</ol>
        </section>)}
    </ResultBlock>
  </div>;
}

const SEVERITY_MARKER = { info: "bg-sky-400", warning: "bg-amber-500", high: "bg-orange-500", critical: "bg-rose-600" };

function IssueCard({issue, article, stale}: {issue: ArticleQAIssue; article: Article; stale: boolean}) {
  const prefix = `article-${article.id}`;
  const anchor = issue.section_heading && sectionAnchor(prefix, issue.section_heading);
  const headings = [...article.content.matchAll(/^#{2,3}\s+(.+)$/gm)].map((match) => sectionAnchor(prefix, match[1]));
  const canJump = !stale && anchor && headings.filter((id) => id === anchor).length === 1;
  return <li className="relative space-y-2 bg-background py-3 pr-4 pl-5 text-sm">
    <span className={`absolute inset-y-0 left-0 w-1 ${SEVERITY_MARKER[issue.severity]}`} aria-hidden="true" />
    <div className="flex flex-wrap items-center gap-2">
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${SEVERITY_STYLES[issue.severity]}`}>{SEVERITY_LABELS[issue.severity]}</span>
      <h6 className="font-semibold">{ISSUE_LABELS[issue.type]}</h6>
    </div>
    {issue.excerpt && <blockquote className="break-words rounded-md bg-muted/50 px-3 py-2 italic">„{issue.excerpt}”</blockquote>}
    <dl className="grid gap-1 sm:grid-cols-[6rem_minmax(0,1fr)] sm:gap-x-3">
      <dt className="font-medium text-muted-foreground">Powód</dt><dd>{issue.reason}</dd>
      <dt className="font-medium text-muted-foreground">Sugestia</dt><dd>{issue.suggestion}</dd>
    </dl>
    {(issue.section_heading || issue.fact_ids.length > 0 || issue.source_ids.length > 0) && <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
      {issue.section_heading && <span>Sekcja: {issue.section_heading}</span>}
      {canJump && <button className="inline-flex min-h-8 items-center font-medium text-emerald-700 underline underline-offset-4" onClick={() => jumpToSection(prefix, anchor)}>Zobacz w artykule</button>}
      {(issue.fact_ids.length > 0 || issue.source_ids.length > 0) && <span>Fakty: {issue.fact_ids.map((id) => `#${id}`).join(", ") || "—"} · źródła: {issue.source_ids.map((id) => `[${id}]`).join(", ") || "—"}</span>}
    </div>}
  </li>;
}

function jumpToSection(prefix: string, anchor: string) {
  window.location.hash = anchor;
  window.dispatchEvent(new Event("article-workspace-read"));
  window.dispatchEvent(new Event(`${prefix}-reveal`));
  requestAnimationFrame(() => document.getElementById(anchor)?.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}));
}
