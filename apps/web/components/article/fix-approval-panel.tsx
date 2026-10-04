"use client";

import { useDemoMode } from "@/components/demo-mode";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
  return <WorkflowSection number={6} title="Auto Fix + Approval" paid
    status={ARTICLE_STATUS_LABELS[article.status] ?? "Szkic"}
    description={`Poprawki i decyzja redakcyjna dotyczą wersji ${article.version}.`}
    actions={<Button size="sm" disabled={busy || autoFixDisabledReason !== null} title={autoFixDisabledReason ?? undefined}
      onClick={() => void onAutoFix()}>{fixSubmitting || jobs.active?.kind === "auto_fix_article" ? "Fixing…" : `Auto Fix · ${demo ? "demo · bezpłatne" : "płatne"}`}</Button>}
    headerDetails={<p className="text-sm text-muted-foreground">
      {autoFixDisabledReason ?? `Problemy do poprawy: ${fixableCount}. Auto Fix utworzy nową wersję na podstawie v${article.version} i uruchomi jej QA.`}
    </p>}
    summary={<UsageSummary rows={[{label:"Auto Fix",configured:"auto_fix",model:fix?.llm_model,
      input:fix?.llm_input_tokens,output:fix?.llm_output_tokens,cost:fix?.estimated_cost_usd}]}
      note={`Jedno kliknięcie wykonuje jedną poprawkę oraz ${demo ? "bezpłatne demo" : "płatne"} QA nowej wersji. Zatwierdzenie nie publikuje artykułu.`} />}>
    {(jobs.history.length > 0 || jobs.active || jobs.error) && <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job: Job) => jobs.enqueue(() => api.retryJob(job.id))} />}
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {fixes.map((item) => <section key={item.id} data-fix-report={item.id} className="space-y-3 rounded-lg border p-4 text-sm">
      <p className="font-semibold">Auto Fix · próba {item.iteration} · {item.status === "completed" ? "Zakończono" : item.status === "failed" ? "Błąd" : "Fixing…"}</p>
      {item.result_article_version_id && <div className="flex flex-wrap items-center gap-3">
        <p>Nowa wersja utworzona: v{versions.find((version) => version.id === item.result_article_version_id)?.version ?? "—"}</p>
        <Button disabled={busy} variant="outline" size="sm" onClick={() => void onSelectVersion(item.result_article_version_id!)}>Otwórz nową wersję</Button>
      </div>}
      <p>{item.issues_fixed} fixed · {item.issues_skipped} skipped</p>
      <p>{item.summary}</p>
      {item.warnings.map((warning) => <p key={warning} className="text-amber-800">{warning}</p>)}
      <div className="space-y-2">{item.issues.map((issue) => <p key={issue.id}>Issue #{issue.qa_issue_id} · {issue.status}: {issue.reason}</p>)}</div>
      {item.changes.length > 0 && <details><summary className="cursor-pointer font-medium">Zmienione fragmenty · Before / After</summary>
        <div className="mt-3 space-y-3">{item.changes.map((change, index) => <div key={index} className="space-y-2 rounded-lg bg-muted/20 p-3">
          <p className="font-medium">{change.field}</p><div className="grid gap-3 md:grid-cols-2">
            <div><p className="text-xs text-muted-foreground">Before</p><p className="whitespace-pre-wrap break-words">{change.before}</p></div>
            <div><p className="text-xs text-muted-foreground">After</p><p className="whitespace-pre-wrap break-words">{change.after || "Usunięto fragment"}</p></div>
          </div></div>)}</div></details>}
    </section>)}
    {qaCurrent && <p className="rounded-lg border bg-muted/20 p-3 text-sm">QA Score: {qa.overall_score}/100 · {qa.critical_issue_count} critical · {qa.unsupported_claims_count} unsupported claims · {qa.warning_count} warnings</p>}
    {!qaCurrent && <p className="text-sm text-muted-foreground">{qa?.status === "pending" || qa?.status === "running" ? "QA nowej wersji w kolejce / w toku…" : "Zatwierdzenie wymaga nowego, zaliczonego QA."}</p>}
    {article.status === "ready_for_approval" && <div className="flex flex-wrap gap-2">
      <Button disabled={busy || !qaCurrent || !qa.qa_passed} onClick={() => void decide()}>Approve</Button>
      <Button variant="outline" disabled={busy} onClick={() => setRejecting(true)}>Reject</Button>
      <Button variant="outline" disabled={busy} onClick={onEdit}>Edit manually</Button>
    </div>}
    {article.status === "manual_review_required" && <div className="space-y-2 text-sm"><p>Wymagana ręczna weryfikacja. Kolejny Auto Fix nie zostanie uruchomiony automatycznie.</p><Button variant="outline" disabled={busy} onClick={onEdit}>Edit manually</Button></div>}
    {article.status === "approved" && <p className="text-sm text-emerald-800">Zatwierdzono tę wersję{article.approved_at ? ` · ${new Date(article.approved_at).toLocaleString("pl-PL")}` : ""}.</p>}
    {rejecting && <div className="space-y-2"><label className="block text-sm">Powód odrzucenia (opcjonalny)<textarea className="mt-1 block w-full rounded-lg border p-2" value={reason} maxLength={2000} onChange={(event) => setReason(event.target.value)} /></label>
      <div className="flex gap-2"><Button disabled={busy} onClick={() => void decide(true)}>Potwierdź odrzucenie</Button><Button variant="ghost" onClick={() => setRejecting(false)}>Anuluj</Button></div></div>}
  </WorkflowSection>;
}
