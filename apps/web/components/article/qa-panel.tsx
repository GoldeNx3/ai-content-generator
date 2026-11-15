"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRightIcon, ShieldCheckIcon, RefreshCwIcon } from "lucide-react";
import { toast } from "sonner";
import { navigateStage } from "@/components/pipeline-state";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { ScoreBar } from "@/components/score-badge";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/components/filter-select";
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
  return <><WorkflowSection progressJob={jobs.ownActive} number={5} title="Kontrola jakości (QA)" paid status={status}
    tone={(status === "Zakończony" || status === "Zakończono") && report?.status === "completed" && !report.is_stale ? report.qa_passed ? "success" : "attention" : undefined}
    description="Kontrola faktów i jakości wybranej wersji na podstawie zapisanych dowodów."
    headerDetails={<div data-qa-target={article.id} className="space-y-2">
      <FilterSelect label="Wersja artykułu do QA" allowAll={false} value={String(article.id)}
        disabled={editing || selectingVersion || submitting}
        options={versions.map((version) => ({value: String(version.id),
          label: `Wersja ${version.version}${version.is_current ? " · aktualna" : ""}${version.qa_passed ? " · QA zaliczone" : ""}`}))}
        onChange={(value) => value && void onSelectVersion(Number(value))} />
      <p className="text-xs font-medium text-muted-foreground">Artykuł wybrany do QA · Wersja {article.version}</p>
      <p className="break-words text-sm font-semibold">{article.title}</p>
      <p data-qa-target-status className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${report?.status === "completed" && !report.is_stale ? "bg-emerald-50 text-emerald-800" : "bg-muted text-muted-foreground"}`}>{targetStatus}</p>
      <p className="text-xs text-muted-foreground">QA sprawdzi wybraną wersję. Wybór jest wspólny z podglądem artykułu.</p>
      <a href="#article-workspace" onClick={() => window.dispatchEvent(new Event(`article-${article.id}-reveal`))} className="inline-flex min-h-9 items-center rounded px-2 text-sm font-medium underline underline-offset-4 focus-visible:outline-2">Czytaj wybrany tekst</a>
    </div>}
    initiallyCollapsed={loaded ? report?.status === "completed" && !report.is_stale : undefined}
    actionTitle="QA wybranej wersji" actionDescription="QA ocenia tekst i wskazuje problemy. Poprawki i decyzja redakcyjna są w etapie „Poprawki i zatwierdzenie”."
    actionDetails={<p className="text-sm text-slate-600">Wersja {article.version}{report?.status === "completed" && !report.is_stale ? ` · ${report.overall_score}/100 · ${report.qa_passed ? "zaliczone" : "wymaga weryfikacji"}` : ""}</p>}
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

    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {!report && loaded && <p className="text-sm text-muted-foreground">Uruchom QA, aby sprawdzić fakty i jakość artykułu. Ocena wykona się w tle.</p>}
    {report?.is_stale && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Treść zmieniła się od tej oceny. Raport dotyczy poprzedniej treści; uruchom QA ponownie.</p>}
    {report?.status === "completed" && <p className="text-sm">Problemy: {report.issues.length} · automatycznie: {fixable} · ręcznie: {report.issues.length - fixable}</p>}
    {article.auto_fix_iterations_remaining === 0 && <p className="text-sm text-amber-800">Limit Auto Fix został wykorzystany. Wymagana ręczna weryfikacja.</p>}
    {report?.status === "completed" && <QualityReport report={report} article={article} />}
  </WorkflowSection>
    <FixApprovalPanel selectingVersion={selectingVersion} versions={versions} article={article} qa={report} fixes={fixes} jobs={fixJobs} error={fixError} editing={editing}
      actionsLoading={!loaded || !jobs.loaded || !fixJobs.loaded || Boolean(jobs.active)}
      onAutoFix={runFix} autoFixDisabledReason={autoFixDisabledReason} fixSubmitting={fixSubmitting} fixableCount={fixable}
      onRefresh={onArticleChange} onSelectVersion={onSelectVersion} onEdit={onEdit} />
  </>;
}

function QualityReport({report, article}: {report: ArticleQA; article: Article}) {
  const scores = [["Fakty", report.factual_score], ["Źródła", report.source_score], ["Styl", report.style_score],
    ["Struktura", report.structure_score], ["SEO", report.seo_score]] as const;
  return <div className="space-y-6" data-qa-report={report.id}>
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div><h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Raport jakości</h3>
        <p className="mt-2 text-5xl font-semibold tabular-nums">{report.overall_score}<span className="text-base text-muted-foreground"> / 100</span></p></div>
      <span className={`rounded-full px-3 py-1 text-sm font-medium ${report.qa_passed ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}>
        {report.is_stale ? "Ocena nieaktualna" : report.qa_passed ? "QA zaliczone" : "Wymaga weryfikacji"}</span>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">{scores.map(([label, value]) => <ScoreBar key={label} label={label} value={value} />)}</div>
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {[["Poparte twierdzenia", report.supported_claims_count], ["Niepoparte twierdzenia", report.unsupported_claims_count],
        ["Ostrzeżenia", report.warning_count], ["Krytyczne problemy", report.critical_issue_count]].map(([label, value]) =>
        <div key={label} className={`rounded-lg border p-3 ${Number(value) > 0 && label === "Krytyczne problemy" ? "border-rose-200 bg-rose-50 text-rose-900" : Number(value) > 0 && (label === "Niepoparte twierdzenia" || label === "Ostrzeżenia") ? "border-amber-200 bg-amber-50 text-amber-900" : "border-slate-200 bg-white text-slate-700"}`}><dt className="text-xs">{label}</dt><dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd></div>)}
    </dl>
    <p className="text-sm leading-relaxed">{report.summary}</p>
    <p className="text-xs text-muted-foreground">Próg QA zaliczone: {report.pass_score}/100, bez krytycznych problemów i niepopartych twierdzeń.</p>
    <div className="space-y-3">{report.issues.map((issue) => <IssueCard key={issue.id} issue={issue} article={article} stale={report.is_stale} />)}</div>
    {report.issues.length === 0 && <p className="text-sm text-emerald-800">Nie wykryto problemów.</p>}
  </div>;
}

function IssueCard({issue, article, stale}: {issue: ArticleQAIssue; article: Article; stale: boolean}) {
  const prefix = `article-${article.id}`;
  const anchor = issue.section_heading && sectionAnchor(prefix, issue.section_heading);
  const headings = [...article.content.matchAll(/^#{2,3}\s+(.+)$/gm)].map((match) => sectionAnchor(prefix, match[1]));
  const canJump = !stale && anchor && headings.filter((id) => id === anchor).length === 1;
  return <section className="space-y-3 rounded-xl p-4 ring-1 ring-foreground/10">
    <div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${SEVERITY_STYLES[issue.severity]}`}>{SEVERITY_LABELS[issue.severity]}</span>
      <h4 className="text-sm font-semibold">{ISSUE_LABELS[issue.type]}</h4><span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{!stale && issue.auto_fixable && AUTO_FIX_TYPES.includes(issue.type) ? "Możliwy Auto Fix" : "Ręczna weryfikacja"}</span></div>
    {issue.excerpt && <blockquote className="break-words border-l-2 pl-3 text-sm italic">„{issue.excerpt}”</blockquote>}
    <div className="space-y-2 text-sm"><p><span className="font-medium">Powód: </span>{issue.reason}</p>
      <p><span className="font-medium">Sugestia: </span>{issue.suggestion}</p></div>
    {issue.section_heading && <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
      <span>Sekcja: {issue.section_heading}</span>{canJump && <button className="text-emerald-700 underline" onClick={() => jumpToSection(prefix, anchor)}>Zobacz w artykule</button>}
    </div>}
    {(issue.fact_ids.length > 0 || issue.source_ids.length > 0) && <p className="text-xs text-muted-foreground">Powiązane fakty: {issue.fact_ids.join(", ") || "—"} · źródła: {issue.source_ids.join(", ") || "—"}</p>}
  </section>;
}


function jumpToSection(prefix: string, anchor: string) {
  window.location.hash = anchor;
  window.dispatchEvent(new Event("article-workspace-read"));
  window.dispatchEvent(new Event(`${prefix}-reveal`));
  requestAnimationFrame(() => document.getElementById(anchor)?.scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}));
}
