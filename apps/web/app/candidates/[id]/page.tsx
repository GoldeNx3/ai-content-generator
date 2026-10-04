"use client";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeftIcon,
  CheckIcon,
  ExternalLinkIcon,
  Loader2Icon,
  RotateCcwIcon,
  SparklesIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";

import { DemoModeProvider, PipelineGuide } from "@/components/demo-mode";
import { navigateStage } from "@/components/pipeline-state";
import { CandidateScreen } from "@/components/nav";
import { WorkflowSection } from "@/components/workflow-section";
import { ModelPricingProvider, UsageSummary } from "@/components/usage-summary";
import { ArticlePanel } from "@/components/article/article-panel";
import { ResearchPanel } from "@/components/research/research-panel";
import { ScoreBar } from "@/components/score-badge";
import { CategoryBadge, StatusBadge } from "@/components/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate, SCORE_LEVEL_LABEL, scoreLevel } from "@/lib/format";
import type { Candidate, CandidateStatus, Research } from "@/types/api";

type Busy = CandidateStatus | "classify" | null;

export default function CandidatePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [classificationError, setClassificationError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const [research, setResearch] = useState<Research | null>(null);

  const load = useCallback(async () => {
    try {
      setCandidate(await api.getCandidate(id));
      setError(null);
      return true;
    } catch (loadError) {
      setError(errorText(loadError));
      return false;
    }
  }, [id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void load();
  }, [load]);

  const jobs = useCandidateJobs(id, "classify", load);

  async function classify() {
    setBusy("classify");
    setClassificationError(null);
    try { await jobs.enqueue(() => api.classifyCandidate(id)); toast.success("Ocena zapisana w kolejce"); }
    catch (failure) { setClassificationError(errorText(failure)); }
    finally { setBusy(null); }
  }

  async function run(kind: Exclude<Busy, null>, fn: () => Promise<Candidate>, message: string) {
    setBusy(kind);
    if (kind === "classify") setClassificationError(null);
    try {
      setCandidate(await fn());
      toast.success(message);
      if (kind === "approved") navigateStage(2);
    } catch (actionError) {
      if (kind === "classify") setClassificationError(errorText(actionError));
      toast.error("Action failed", { description: errorText(actionError) });
    } finally {
      setBusy(null);
    }
  }

  const setStatus = (status: CandidateStatus) =>
    run(status, () => api.updateCandidateStatus(id, status), `Marked as ${status}`);

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink />
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
      </div>
    );
  }
  if (!candidate) {
    return <p role="status" className="text-muted-foreground">Ładowanie tematu…</p>;
  }

  const classified = candidate.total_score !== null;
  const classificationHasRun = classified || jobs.history.length > 0;

  return (
    <DemoModeProvider value={Boolean(candidate.is_demo)}>
    <ModelPricingProvider>
    <div className="min-w-0 space-y-6">
      <BackLink />

      <div className="flex flex-wrap items-start gap-5">

        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Przestrzeń redakcyjna · temat #{id}</p>
          <h1 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{candidate.title}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{candidate.source_name}</span>
            <span>·</span>
            <span>{formatDate(candidate.original_published_at)}</span>
            <span className="text-xs">Stan tematu:</span><StatusBadge status={candidate.status} />
            {candidate.is_demo && <span className="rounded-full bg-sky-50 px-2 py-1 text-xs font-medium text-sky-800">Demo · bez kosztów AI</span>}
            <CategoryBadge category={candidate.category} />
          </div>
        </div>
      </div>

      <CandidateScreen>
      <WorkflowSection number={1} title="Pobranie tematu" description="Materiał źródłowy pobrany z RSS." paid={false} status="Zakończono" timestamp={candidate.created_at}
        actionTitle="Decyzja redakcyjna" actionDescription="Na podstawie wybranego materiału zdecyduj, czy chcesz kontynuować dalsze etapy."
        actions={      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-2 text-xs font-medium text-muted-foreground">Decyzja redakcyjna · bez kosztu AI</span>
        <Button onClick={() => setStatus("approved")} disabled={busy !== null || candidate.status === "approved"}>
          {busy === "approved" ? <Loader2Icon className="animate-spin" /> : <CheckIcon />}
          Zatwierdź temat
        </Button>
        <Button
          variant="outline"
          onClick={() => setStatus("ignored")}
          disabled={busy !== null || candidate.status === "ignored"}
        >
          {busy === "ignored" ? <Loader2Icon className="animate-spin" /> : <XIcon />}
          Pomiń temat
        </Button>
        {candidate.status !== "pending" && (
          <Button variant="ghost" onClick={() => setStatus("pending")} disabled={busy !== null}>
            <RotateCcwIcon />
            Przywróć do oczekujących
          </Button>
        )}
      </div>}
        resultTitle="Wybrany materiał"
        summary={<UsageSummary free note={`Pobrano: ${formatDate(candidate.created_at)} · źródło: ${candidate.source_name}`} />}>
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">{candidate.title}</h3>
          <p className="text-sm leading-7 whitespace-pre-line text-slate-700">{candidate.summary ?? "Brak podsumowania w źródle RSS."}</p>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground"><span className="rounded-md bg-slate-100 px-3 py-2">{candidate.source_name}</span><span className="rounded-md bg-slate-100 px-3 py-2">{formatDate(candidate.original_published_at ?? candidate.created_at)}</span><CategoryBadge category={candidate.category} /></div>
          <a href={candidate.external_url} target="_blank" rel="noopener noreferrer" className={buttonVariants({variant:"outline"})}><ExternalLinkIcon className="size-4" />Otwórz oryginał</a>
        </div>
        <PipelineGuide demo={Boolean(candidate.is_demo)} />
      </WorkflowSection>

      <WorkflowSection number={2} title="Ocena tematu przez AI" description="Punktacja i uzasadnienie pomagające wybrać temat do opracowania." paid
        initiallyCollapsed={classified}
        status={jobs.latest ? jobStatusLabel[jobs.latest.status] : busy === "classify" ? "W toku" : classificationError ? "Ostatnie uruchomienie: błąd" : classified ? "Zakończono" : "Do uruchomienia"}
        actionTitle="Decyzja" actionDescription={classified ? "Ocena jest gotowa. Przejdź do Research lub pomiń temat. Ponowna ocena używa AI." : "Uruchom ocenę tematu. Wynik pomoże zdecydować, czy warto wykonać Research."}
        actions={<>{classified && <Button onClick={() => navigateStage(3)}>Kontynuuj do Research</Button>}<Button
          size="sm"
          variant={classificationHasRun ? "outline" : "default"}
          onClick={() => void classify()}
          disabled={busy !== null || !jobs.loaded || Boolean(jobs.active)}
        >
          {busy === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {classificationHasRun ? "Oceń ponownie" : "Oceń temat"} · {candidate.is_demo ? "demo · bezpłatne" : "płatne"}
        </Button><Button variant="outline" onClick={() => setStatus("ignored")} disabled={busy !== null || candidate.status === "ignored"}>Pomiń temat</Button></>}
        activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[{label: "Ocena tematu", configured: "classifier", model: candidate.llm_model, input: candidate.llm_input_tokens, output: candidate.llm_output_tokens, cost: candidate.estimated_cost_usd}]} note={classified ? `Oceniono: ${formatDate(candidate.classified_at)}. Starsze oceny mogą nie mieć zapisanych danych o zużyciu.` : "Dane zużycia pojawią się po ocenie tematu."} />}>

        {classificationError && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{classificationError}</p>}
        <div className="max-w-3xl">
          <div className="space-y-4">            {classified ? (
              <>
                <div className="rounded-xl border border-emerald-100 bg-emerald-50/40 p-5"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Ocena tematu</p><p className="mt-3 text-4xl font-semibold tabular-nums">{candidate.total_score}<span className="text-lg font-normal text-muted-foreground"> / 100</span></p><p className="mt-2 text-sm text-slate-600">{SCORE_LEVEL_LABEL[scoreLevel(candidate.total_score ?? 0)]}</p></div>
                <ScoreBar label="Trafność (40%)" value={candidate.relevance_score} />
                <ScoreBar label="Aktualność (20%)" value={candidate.freshness_score} />
                <ScoreBar label="Potencjał wyszukiwań (25%)" value={candidate.search_potential_score} />
                <ScoreBar label="Potencjał komercyjny (15%)" value={candidate.commercial_potential_score} />
                <div className="flex items-baseline justify-between border-t pt-3">
                  <span className="text-sm font-medium">Wynik łączny</span>
                  <span className="font-mono text-lg font-semibold tabular-nums">
                    {candidate.total_score}{" "}
                    <span className="font-sans text-xs font-normal text-muted-foreground">
                      {SCORE_LEVEL_LABEL[scoreLevel(candidate.total_score ?? 0)]}
                    </span>
                  </span>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Uzasadnienie</p>
                  <p className="text-sm leading-relaxed text-muted-foreground">{candidate.llm_reason}</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Oceniono: {formatDate(candidate.classified_at)}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Temat nie został oceniony. Wybierz „Oceń temat · płatne”, aby uruchomić ocenę AI.
              </p>
            )}</div>

        </div>
      </WorkflowSection>

      <ResearchPanel candidateId={id} onResearchChange={setResearch} />

      <ArticlePanel candidateId={id} candidateCategory={candidate.category} research={research} />
      </CandidateScreen>
    </div>
    </ModelPricingProvider>
    </DemoModeProvider>
  );
}

function BackLink() {
  return (
    <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm", className: "-ml-2" })}>
      <ArrowLeftIcon />
      Wróć do tematów
    </Link>
  );
}
