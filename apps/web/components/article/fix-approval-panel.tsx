"use client";

import { useDemoMode } from "@/components/demo-mode";
import { useEffect, useState } from "react";
import { ArrowLeftIcon, ArrowRightIcon, CheckCircle2Icon, CircleDashedIcon, FileTextIcon, GaugeIcon, ListChecksIcon, StampIcon, WandSparklesIcon } from "lucide-react";
import { ResultBlock, ResultOutline, setResultBlock } from "@/components/stage/result-block";
import { toast } from "sonner";
import { navigateStage } from "@/components/pipeline-state";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ArticlePreview } from "./article-preview";
import { ScoreBar } from "@/components/score-badge";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { api, errorText } from "@/lib/api";
import { ARTICLE_STATUS_LABELS } from "@/lib/article-status";
import { formatDate } from "@/lib/format";
import type { Article, ArticleSummary, ArticleFix, ArticleQA, Job } from "@/types/api";
import type { useCandidateJobs } from "@/hooks/use-candidate-jobs";

type Jobs = ReturnType<typeof useCandidateJobs>;
const FIX_STATUS = {
  fixed: { label: "Poprawiono", className: "bg-emerald-50 text-emerald-800" },
  skipped: { label: "Pominięto", className: "bg-zinc-100 text-zinc-700" },
  failed: { label: "Błąd", className: "bg-rose-50 text-rose-800" },
} as const;
const FIELD_LABELS: Record<string, string> = { content: "Treść", title: "Tytuł", lead: "Lead", meta_title: "Meta title", meta_description: "Meta description" };
export function FixApprovalPanel({article, versions, qa, fixes, jobs, error, editing, selectingVersion, onRefresh, onSelectVersion, onEdit, onAutoFix, autoFixDisabledReason, fixSubmitting, fixableCount, actionsLoading}: {
  actionsLoading: boolean;
  onAutoFix: () => Promise<void>; autoFixDisabledReason: string | null; fixSubmitting: boolean; fixableCount: number;
  versions: ArticleSummary[]; article: Article; qa: ArticleQA | null; fixes: ArticleFix[]; jobs: Jobs; error: string | null;
  selectingVersion: boolean; editing: boolean; onRefresh: () => Promise<void>; onSelectVersion: (id: number) => Promise<void>; onEdit: () => void;
}) {
  const demo = useDemoMode();
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const fix = fixes[0];
  const fixRunning = Boolean(jobs.ownActive) || fix?.status === "pending" || fix?.status === "running";
  useEffect(() => { if (fixRunning) setResultBlock("auto-fix-report", true, false); }, [fixRunning, fixes.length]);
  const qaCurrent = qa?.status === "completed" && !qa.is_stale;
  const busy = actionsLoading || selectingVersion || editing || approving || fixSubmitting || Boolean(jobs.active);
  const approvalReason = article.status === "approved" ? "Ta wersja jest już zatwierdzona." :
    article.status !== "ready_for_approval" || !qaCurrent || !qa?.qa_passed ? "Zatwierdzenie wymaga aktualnego, zaliczonego QA dla tej wersji." : null;
  const readiness: [string, boolean, string][] = [
    ["Aktualne QA tej wersji", qaCurrent, qa?.is_stale ? "Tekst zmienił się po QA — uruchom QA ponownie." : qaCurrent ? `Ocena z ${formatDate(qa.updated_at)}.` : "Uruchom QA w etapie 5."],
    ["Wynik co najmniej " + (qa?.pass_score ?? 85) + "/100", Boolean(qaCurrent && (qa.overall_score ?? 0) >= qa.pass_score), qaCurrent ? `Obecny wynik: ${qa.overall_score}/100.` : "Brak wyniku."],
    ["Brak problemów krytycznych", Boolean(qaCurrent && qa.critical_issue_count === 0), qaCurrent ? `Krytyczne: ${qa.critical_issue_count}.` : "Brak wyniku."],
    ["Brak niepopartych twierdzeń", Boolean(qaCurrent && qa.unsupported_claims_count === 0), qaCurrent ? `Niepoparte: ${qa.unsupported_claims_count}, ostrzeżenia: ${qa.warning_count}.` : "Brak wyniku."],
    ["Decyzja redakcji", article.status === "approved", article.status === "approved" ? "Wersja zatwierdzona." : "Zatwierdź albo odrzuć wersję w panelu po prawej."],
  ];
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
  return <WorkflowSection progressJob={jobs.ownActive} number={6} title="Poprawki i zatwierdzenie" paid resultTitle="Stan wersji"
    tone={jobs.ownActive ? "running" : article.status === "approved" ? "success" :
      article.status === "rejected" ? "error" :
      ["ready_for_approval", "needs_changes", "manual_review_required"].includes(article.status) ? "attention" : "neutral"}
    status={jobs.ownActive ? jobStatusLabel[jobs.ownActive.status] : article.status === "ready_for_approval" ? "Oczekuje na Twoją decyzję" : ARTICLE_STATUS_LABELS[article.status] ?? "Szkic"}
    description={`Poprawki i decyzja redakcyjna dotyczą wersji ${article.version}.`}
    actionTitle="Poprawki i decyzja" actionDescription={article.status === "approved" ? "Ta wersja jest zatwierdzona. Kolejna poprawka utworzy nową wersję wymagającą osobnego QA i zatwierdzenia." : "Najpierw zastosuj potrzebne poprawki albo zatwierdź tekst w obecnej postaci. Poprawki nie wymagają wcześniejszego zatwierdzenia."}
    primaryTitle="Poprawki tekstu"
    primary={<>
      <Button variant={autoFixDisabledReason === null ? "default" : "outline"} disabled={busy || autoFixDisabledReason !== null} onClick={() => void onAutoFix()}>{fixSubmitting || Boolean(jobs.ownActive) ? "Poprawianie…" : `Popraw automatycznie · ${demo ? "demo · bezpłatne" : "płatne"}`}</Button>
      <p className="action-hint">{autoFixDisabledReason ?? `${fixableCount} ${fixableCount === 1 ? "problem" : "problemów"} do poprawy. Tworzy nową wersję; jej QA uruchamiasz osobno.`}</p>
      <Button variant="outline" disabled={busy} onClick={onEdit}>Edytuj tekst</Button>
      <Button variant="outline" disabled={selectingVersion || editing || fixSubmitting || Boolean(jobs.ownActive)} onClick={() => navigateStage(5)}><ArrowLeftIcon />Przejdź do QA wybranej wersji</Button>
      <p className="action-hint">Po poprawce uruchom QA nowej wersji — bez niego nie da się jej zatwierdzić.</p>
    </>}
    secondaryTitle={`Decyzja dla wersji ${article.version}`}
    secondary={<>
      <Button variant={article.status === "approved" || autoFixDisabledReason === null ? "outline" : "default"} disabled={busy || approvalReason !== null} onClick={() => void decide()}>{article.status === "approved" ? "Wersja zatwierdzona" : "Zatwierdź wersję"}</Button>
      <p className="action-hint">{approvalReason ?? "Zatwierdza obecny tekst bez poprawek. Nie uruchamia agenta ani publikacji."}</p>
      <Button variant="outline" disabled={busy || article.status !== "ready_for_approval"} onClick={() => setRejecting(true)}>Odrzuć wersję</Button>
      {rejecting && <div className="space-y-2 rounded-lg bg-rose-50/60 p-3 ring-1 ring-rose-200"><label className="block text-sm">Powód odrzucenia (opcjonalny)<Textarea className="mt-2" value={reason} maxLength={2000} onChange={(event) => setReason(event.target.value)} /></label>
        <div className="grid gap-2"><Button variant="destructive" disabled={busy} onClick={() => void decide(true)}>Potwierdź odrzucenie</Button><Button variant="ghost" onClick={() => setRejecting(false)}>Anuluj</Button></div></div>}
    </>}
    navigation={<>
      <Button variant={article.status === "approved" ? "default" : "outline"} onClick={() => navigateStage(8)}>Przejdź do publikacji<ArrowRightIcon /></Button>
      {article.status !== "approved" && <p className="action-hint">Wysłać do WordPressa można dopiero zatwierdzoną wersję.</p>}
    </>}
    activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job: Job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label:"Auto Fix",configured:"auto_fix",model:fix?.llm_model,
      input:fix?.llm_input_tokens,output:fix?.llm_output_tokens,cost:fix?.estimated_cost_usd}]}
      note="Jedno kliknięcie wykonuje jedną poprawkę. QA nowej wersji uruchamiasz osobno. Zatwierdzenie nie publikuje artykułu." />}>

    <div className="space-y-6">
      {error && <p role="alert" className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</p>}
      {article.status === "approved" && <p role="status" className="flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-sm font-medium text-emerald-900 ring-1 ring-emerald-200"><CheckCircle2Icon className="size-4 shrink-0" aria-hidden="true" />Zatwierdzono tę wersję{article.approved_at ? ` · ${new Date(article.approved_at).toLocaleString("pl-PL")}` : ""}. Możesz ją wysłać do WordPressa.</p>}
      {article.status === "rejected" && <p role="status" className="rounded-xl bg-rose-50 p-4 text-sm text-rose-900 ring-1 ring-rose-200"><span className="font-medium">Wersja odrzucona.</span>{article.rejection_reason ? ` Powód: ${article.rejection_reason}` : ""}</p>}
      <ResultOutline label="Stan wybranej wersji" meta={approvalReason ?? "Wersja spełnia warunki zatwierdzenia."} items={[
        { target: "approval-readiness", label: "Decyzja", value: article.status === "approved" ? "Zatwierdzona" : article.status === "rejected" ? "Odrzucona" : article.status === "ready_for_approval" ? "Czeka" : "Jeszcze nie", hint: article.status === "ready_for_approval" ? "na Twoją decyzję" : "możliwa po zaliczonym QA", icon: StampIcon, tone: article.status === "approved" ? "success" : article.status === "rejected" ? "danger" : article.status === "ready_for_approval" ? "attention" : "neutral" },
        { target: "approval-readiness", label: "QA tej wersji", value: qaCurrent ? `${qa.overall_score}/100` : "—", hint: qaCurrent ? qa.qa_passed ? "zaliczone" : "niezaliczone" : qa?.is_stale ? "nieaktualne" : "brak QA", icon: GaugeIcon, tone: qaCurrent ? qa.qa_passed ? "success" : "attention" : "neutral" },
        { target: fixes.length ? "auto-fix-report" : "approval-readiness", label: "Auto Fix", value: fixes.length, hint: `${article.auto_fix_iterations_remaining} ${article.auto_fix_iterations_remaining === 1 ? "próba" : "prób"} do wykorzystania`, icon: WandSparklesIcon, tone: article.auto_fix_iterations_remaining === 0 ? "attention" : "neutral" },
        { target: "final-preview", label: "Tekst", value: article.word_count.toLocaleString("pl-PL"), hint: "słów w tej wersji", icon: FileTextIcon },
      ]} />

      {fixes.length > 0 && <ResultBlock id="auto-fix-report" icon={WandSparklesIcon} title="Wynik Auto Fix" count={fixes.length}
        description="Co poprawił Auto Fix: każda próba pokazuje poprawione i pominięte problemy oraz zmiany przed i po. Poprawka zawsze tworzy nową wersję.">
        <ol className="space-y-3">{fixes.map((item) => <li key={item.id} data-fix-report={item.id} className="space-y-3 rounded-xl p-4 text-sm ring-1 ring-foreground/8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="font-semibold">Auto Fix · próba {item.iteration} · {item.status === "completed" ? "Zakończono" : item.status === "failed" ? "Błąd" : "Poprawianie…"}</p>
            <p className="text-muted-foreground">Poprawiono: {item.issues_fixed} · pominięto: {item.issues_skipped}</p>
          </div>
          {item.summary && <p className="leading-6">{item.summary}</p>}
          {item.result_article_version_id && <div className="flex flex-wrap items-center gap-3 rounded-lg bg-emerald-50/60 px-3 py-2 ring-1 ring-emerald-100">
            <p>Nowa wersja utworzona: v{versions.find((version) => version.id === item.result_article_version_id)?.version ?? "—"}{item.result_article_version_id === article.id ? " · obecnie wybrana" : ""}</p>
            {item.result_article_version_id !== article.id && <Button disabled={busy} variant="outline" size="sm" onClick={() => void onSelectVersion(item.result_article_version_id!)}>Otwórz nową wersję</Button>}
          </div>}
          {item.warnings.map((warning) => <p key={warning} className="text-amber-800">{warning}</p>)}
          {item.issues.length > 0 && <ul className="space-y-1.5">{item.issues.map((issue) => <li key={issue.id} className="flex gap-2"><span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${FIX_STATUS[issue.status].className}`}>{FIX_STATUS[issue.status].label}</span><span>Problem #{issue.qa_issue_id}: {issue.reason}</span></li>)}</ul>}
          {item.changes.length > 0 && <details open className="rounded-lg bg-muted/40 p-3"><summary className="cursor-pointer font-medium">Zmienione fragmenty · Before / After</summary>
            <div className="mt-3 space-y-3">{item.changes.map((change, index) => <div key={index} className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">{FIELD_LABELS[change.field] ?? change.field}</p><div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg bg-rose-50/60 p-3 ring-1 ring-rose-100"><p className="text-xs font-medium text-rose-800">Przed poprawką</p><p className="mt-1 whitespace-pre-wrap break-words">{change.before}</p></div>
                <div className="rounded-lg bg-emerald-50/60 p-3 ring-1 ring-emerald-100"><p className="text-xs font-medium text-emerald-800">Po poprawce</p><p className="mt-1 whitespace-pre-wrap break-words">{change.after || "Usunięto fragment"}</p></div>
              </div></div>)}</div></details>}
        </li>)}</ol>
      </ResultBlock>}

      <ResultBlock id="approval-readiness" icon={ListChecksIcon} title="Gotowość do zatwierdzenia"
        description="Warunki, które musi spełnić ta wersja, zanim ją zatwierdzisz. Zatwierdzenie dotyczy tylko tej wersji i niczego nie publikuje.">
        <ul className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">
          {readiness.map(([label, ok, detail]) => <li key={label} className="flex items-start gap-3 bg-background px-4 py-3 text-sm">
            {ok ? <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-emerald-600" aria-label="spełnione" /> : <CircleDashedIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-label="niespełnione" />}
            <span className="min-w-0 flex-1"><span className="font-medium">{label}</span><span className="block text-xs text-muted-foreground">{detail}</span></span>
          </li>)}
        </ul>
        {!qaCurrent && <p className="text-sm text-muted-foreground">{qa?.status === "pending" || qa?.status === "running" ? "QA nowej wersji w kolejce / w toku…" : "Zatwierdzenie wymaga nowego, zaliczonego QA."}</p>}
        {qaCurrent && <section className="grid gap-3 rounded-xl bg-muted/40 p-4 sm:grid-cols-2" aria-label="Końcowy raport QA">{[["Fakty",qa.factual_score],["Źródła",qa.source_score],["Styl",qa.style_score],["Struktura",qa.structure_score],["SEO",qa.seo_score]].map(([label,value])=><ScoreBar key={String(label)} label={String(label)} value={Number(value)} />)}</section>}
      </ResultBlock>

      <ResultBlock id="final-preview" icon={FileTextIcon} title="Podgląd finalnego artykułu"
        description={`Tekst wersji ${article.version} — dokładnie ten, który zatwierdzasz i wyślesz do WordPressa.`}>
        <div className="rounded-xl bg-background p-5 ring-1 ring-foreground/8 sm:p-8"><ArticlePreview article={article} anchorPrefix={`final-article-${article.id}`} /></div>
      </ResultBlock>
    </div>
  </WorkflowSection>;
}
