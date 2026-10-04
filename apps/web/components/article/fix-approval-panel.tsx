"use client";

import { useDemoMode } from "@/components/demo-mode";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/components/filter-select";
import { ArticlePreview } from "./article-preview";
import { ScoreBar } from "@/components/score-badge";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { JobStatus } from "@/components/job-status";
import { api, errorText } from "@/lib/api";
import { ARTICLE_STATUS_LABELS } from "@/lib/article-status";
import type { Article, ArticleSummary, ArticleFix, ArticleQA, Job } from "@/types/api";
import type { useCandidateJobs } from "@/hooks/use-candidate-jobs";

type Jobs = ReturnType<typeof useCandidateJobs>;
export function FixApprovalPanel({article, versions, qa, fixes, jobs, error, editing, selectingVersion, onRefresh, onSelectVersion, onEdit, onAutoFix, autoFixDisabledReason, fixSubmitting, fixableCount}: {
  onAutoFix: () => Promise<void>; autoFixDisabledReason: string | null; fixSubmitting: boolean; fixableCount: number;
  versions: ArticleSummary[]; article: Article; qa: ArticleQA | null; fixes: ArticleFix[]; jobs: Jobs; error: string | null;
  selectingVersion: boolean; editing: boolean; onRefresh: () => Promise<void>; onSelectVersion: (id: number) => Promise<void>; onEdit: () => void;
}) {
  const demo = useDemoMode();
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const fix = fixes[0];
  const qaCurrent = qa?.status === "completed" && !qa.is_stale;
  const busy = selectingVersion || editing || approving || Boolean(jobs.active);
  async function decide(reject = false) {
    setApproving(true);
    try {
      if (reject) await api.rejectVersion(article.id, reason || undefined);
      else await api.approveVersion(article.id);
      await onRefresh(); setRejecting(false);
      toast.success(reject ? "Wersja odrzucona" : "Wersja zatwierdzona");
    } catch (failure) { toast.error("Nie udało się zapisać decyzji", {description: errorText(failure)}); }
    finally { setApproving(false); }
  }
  return <WorkflowSection number={6} title="Poprawki i zatwierdzenie" paid
    tone={jobs.active ? "running" : undefined}
    status={ARTICLE_STATUS_LABELS[article.status] ?? "Szkic"}
    description={`Poprawki i decyzja redakcyjna dotyczą wersji ${article.version}.`}
    actionTitle="Decyzja redakcyjna" actionDescription={article.status === "approved" ? "Ta wersja została zatwierdzona. Decyzja jest zapisana w historii." : "Zatwierdź konkretną wersję po zaliczonym QA lub popraw pozostałe problemy."}
    actionDetails={<p className="text-sm text-slate-600">Wersja {article.version} · {ARTICLE_STATUS_LABELS[article.status]}</p>}
    actions={<>
      {article.status === "ready_for_approval" && <>
        <Button disabled={busy || !qaCurrent || !qa.qa_passed} onClick={() => void decide()}>Zatwierdź wersję</Button>
        <Button variant="outline" disabled={busy} onClick={() => setRejecting(true)}>Odrzuć wersję</Button>
      </>}
      {(autoFixDisabledReason === null || fixSubmitting || jobs.active?.kind === "auto_fix_article") && <Button variant={article.status === "ready_for_approval" ? "outline" : "default"} disabled={busy || autoFixDisabledReason !== null} title="Auto Fix tworzy nową wersję i uruchamia jej QA." onClick={() => void onAutoFix()}>{fixSubmitting || jobs.active?.kind === "auto_fix_article" ? "Fixing…" : `Auto Fix · ${demo ? "demo · bezpłatne" : "płatne"}`}</Button>}
      <Button variant="outline" disabled={busy} onClick={onEdit}>Edytuj tekst</Button>
      {rejecting && <div className="space-y-2"><label className="block text-sm">Powód odrzucenia (opcjonalny)<textarea className="mt-1 block w-full rounded-lg border p-2" value={reason} maxLength={2000} onChange={(event) => setReason(event.target.value)} /></label>
      <div className="flex gap-2"><Button variant="destructive" disabled={busy} onClick={() => void decide(true)}>Potwierdź odrzucenie</Button><Button variant="ghost" onClick={() => setRejecting(false)}>Anuluj</Button></div></div>}
    </>}
    headerDetails={<div className="space-y-2"><FilterSelect label="Wersja do zatwierdzenia" allowAll={false} value={String(article.id)} disabled={busy} options={versions.map(v=>({value:String(v.id),label:`Wersja ${v.version}${v.is_current ? " · najnowsza" : ""}`}))} onChange={value=>value&&void onSelectVersion(Number(value))} /><p className="font-medium">{article.title}</p><p className="text-sm text-muted-foreground">
      {autoFixDisabledReason ?? `Problemy do poprawy: ${fixableCount}. Auto Fix utworzy nową wersję na podstawie v${article.version} i uruchomi jej QA.`}
    </p><a href="#article-workspace" onClick={() => window.dispatchEvent(new Event(`article-${article.id}-reveal`))} className="inline-flex min-h-9 items-center rounded px-2 text-sm font-medium underline underline-offset-4 focus-visible:outline-2">Czytaj wybrany tekst</a></div>}
    activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job: Job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label:"Auto Fix",configured:"auto_fix",model:fix?.llm_model,
      input:fix?.llm_input_tokens,output:fix?.llm_output_tokens,cost:fix?.estimated_cost_usd}]}
      note={`Jedno kliknięcie wykonuje jedną poprawkę oraz ${demo ? "bezpłatne demo" : "płatne"} QA nowej wersji. Zatwierdzenie nie publikuje artykułu.`} />}>

    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {fixes.map((item) => <section key={item.id} data-fix-report={item.id} className="space-y-3 rounded-lg border p-4 text-sm">
      <p className="font-semibold">Auto Fix · próba {item.iteration} · {item.status === "completed" ? "Zakończono" : item.status === "failed" ? "Błąd" : "Fixing…"}</p>
      {item.result_article_version_id && <div className="flex flex-wrap items-center gap-3">
        <p>Nowa wersja utworzona: v{versions.find((version) => version.id === item.result_article_version_id)?.version ?? "—"}</p>
        <Button disabled={busy} variant="outline" size="sm" onClick={() => void onSelectVersion(item.result_article_version_id!)}>Otwórz nową wersję</Button>
      </div>}
      <p>Poprawiono: {item.issues_fixed} · pominięto: {item.issues_skipped}</p>
      <p>{item.summary}</p>
      {item.warnings.map((warning) => <p key={warning} className="text-amber-800">{warning}</p>)}
      <div className="space-y-2">{item.issues.map((issue) => <p key={issue.id}>Issue #{issue.qa_issue_id} · {issue.status}: {issue.reason}</p>)}</div>
      {item.changes.length > 0 && <details open><summary className="cursor-pointer font-medium">Zmienione fragmenty · Before / After</summary>
        <div className="mt-3 space-y-3">{item.changes.map((change, index) => <div key={index} className="space-y-2 rounded-lg bg-muted/20 p-3">
          <p className="font-medium">{change.field}</p><div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-rose-100 bg-rose-50/40 p-3"><p className="text-xs font-medium text-rose-800">Przed poprawką</p><p className="whitespace-pre-wrap break-words">{change.before}</p></div>
            <div className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-3"><p className="text-xs font-medium text-emerald-800">Po poprawce</p><p className="whitespace-pre-wrap break-words">{change.after || "Usunięto fragment"}</p></div>
          </div></div>)}</div></details>}
    </section>)}
    {qaCurrent && <p className={`rounded-lg border p-4 text-sm ${qa.qa_passed ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>Wynik QA: {qa.overall_score}/100 · krytyczne: {qa.critical_issue_count} · niepoparte twierdzenia: {qa.unsupported_claims_count} · ostrzeżenia: {qa.warning_count}</p>}
    {!qaCurrent && <p className="text-sm text-muted-foreground">{qa?.status === "pending" || qa?.status === "running" ? "QA nowej wersji w kolejce / w toku…" : "Zatwierdzenie wymaga nowego, zaliczonego QA."}</p>}
    {article.status === "approved" && <p className="text-sm text-emerald-800">Zatwierdzono tę wersję{article.approved_at ? ` · ${new Date(article.approved_at).toLocaleString("pl-PL")}` : ""}.</p>}
    {qaCurrent && <section className="space-y-4" aria-label="Końcowy raport QA"><h3 className="text-base font-semibold">Końcowe QA · {qa.overall_score}/100</h3><div className="grid gap-3 sm:grid-cols-2">{[["Fakty",qa.factual_score],["Źródła",qa.source_score],["Styl",qa.style_score],["Struktura",qa.structure_score],["SEO",qa.seo_score]].map(([label,value])=><ScoreBar key={String(label)} label={String(label)} value={Number(value)} />)}</div></section>}
    <section className="space-y-6 border-t pt-6"><h3 className="text-base font-semibold">Podgląd finalnego artykułu · wersja {article.version}</h3><ArticlePreview article={article} anchorPrefix={`final-article-${article.id}`} /></section>

  </WorkflowSection>;
}
