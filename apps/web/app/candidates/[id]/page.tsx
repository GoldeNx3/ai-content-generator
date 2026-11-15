"use client";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  CheckIcon,
  ExternalLinkIcon,
  Loader2Icon,
  RotateCcwIcon,
  SparklesIcon,
  XIcon,
} from "lucide-react";
import { toast } from "sonner";

import { DemoModeProvider, DemoNotice } from "@/components/demo-mode";
import { navigateStage } from "@/components/pipeline-state";
import { CandidateScreen } from "@/components/nav";
import { WorkflowSection } from "@/components/workflow-section";
import { ModelPricingProvider, UsageSummary } from "@/components/usage-summary";
import { ArticlePanel } from "@/components/article/article-panel";
import { ResearchPanel } from "@/components/research/research-panel";
import { ScoreBadge, ScoreBar } from "@/components/score-badge";
import { CategoryBadge, StatusBadge } from "@/components/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate, SCORE_LEVEL_LABEL, scoreLevel } from "@/lib/format";
import { classificationUsageRow } from "@/lib/workflow";
import { SimilarTopics } from "@/components/similar-topics";
import type { Candidate, CandidateStatus, Research } from "@/types/api";
import { EditorTake } from "@/components/editor-take";

type Busy = CandidateStatus | "classify" | null;

export default function CandidatePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [classificationError, setClassificationError] = useState<string | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  async function ungroup() {
    setGroupError(null);
    try {
      setCandidate(await api.leaveTopicGroup(id));
    } catch (failure) {
      setGroupError(errorText(failure));
    }
  }
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

  async function classify(force = false) {
    setBusy("classify");
    setClassificationError(null);
    try { await jobs.enqueue(() => api.classifyCandidate(id, force)); toast.success("Ocena zapisana w kolejce"); }
    catch (failure) { setClassificationError(errorText(failure)); }
    finally { setBusy(null); }
  }

  async function run(kind: Exclude<Busy, null>, fn: () => Promise<Candidate>, message: string) {
    setBusy(kind);
    if (kind === "classify") setClassificationError(null);
    try {
      setCandidate(await fn());
      toast.success(message);
    } catch (actionError) {
      if (kind === "classify") setClassificationError(errorText(actionError));
      toast.error("Nie udało się zapisać decyzji", { description: errorText(actionError) });
    } finally {
      setBusy(null);
    }
  }

  const setStatus = (status: CandidateStatus) =>
    run(status, () => api.updateCandidateStatus(id, status), ({ approved: "Temat zatwierdzony", ignored: "Temat pominięty", pending: "Temat przywrócony do oczekujących", classified: "Temat oceniony" }[status] ?? "Status tematu zapisany"));

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

      <header className="flex flex-wrap items-start gap-5 rounded-2xl bg-card p-5 shadow-xs ring-1 ring-foreground/8 sm:p-6">
        <ScoreBadge score={candidate.total_score} size="lg" />
        <div className="min-w-0 flex-1 basis-72 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Temat #{id}</p>
          <h1 className="text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{candidate.title}</h1>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{candidate.source_name}</span>
            <span aria-hidden="true">·</span>
            <span title={formatDate(candidate.original_published_at)}>{formatDate(candidate.original_published_at ?? candidate.created_at)}</span>
            <span aria-hidden="true">·</span>
            <span className="inline-flex items-center gap-1.5"><span className="text-xs">Stan tematu:</span><StatusBadge status={candidate.status} /></span>
            <CategoryBadge category={candidate.category} />
            {candidate.is_demo && <span className="rounded-full bg-sky-50 px-2 py-0.5 text-xs font-medium text-sky-800 ring-1 ring-sky-200">Demo · bez kosztów AI</span>}
          </div>
        </div>
        <a href={candidate.external_url} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "outline", className: "shrink-0" })}>
          <ExternalLinkIcon className="size-4" />Źródło<span className="sr-only"> (otwiera się w nowej karcie)</span>
        </a>
      </header>

      <CandidateScreen>
      <WorkflowSection number={1} title="Pobranie tematu" description="Materiał źródłowy pobrany z RSS." paid={false} status="Zakończono" timestamp={candidate.created_at}
        actionTitle="Decyzja redakcyjna" actionDescription="Zdecyduj, czy chcesz opracować ten temat. Decyzja porządkuje listę tematów i niczego nie uruchamia."
        actionDetails={<p className="inline-flex items-center gap-2 text-sm">Obecny stan: <StatusBadge status={candidate.status} /></p>}
        primary={<Button variant={candidate.status === "approved" ? "outline" : "default"} onClick={() => setStatus("approved")} disabled={busy !== null || candidate.status === "approved"}>
          {busy === "approved" ? <Loader2Icon className="animate-spin" /> : <CheckIcon />}
          {candidate.status === "approved" ? "Temat zatwierdzony" : "Zatwierdź temat"}
        </Button>}
        secondary={<>
          <Button variant="outline" onClick={() => setStatus("ignored")} disabled={busy !== null || candidate.status === "ignored"}>
            {busy === "ignored" ? <Loader2Icon className="animate-spin" /> : <XIcon />}
            Pomiń temat
          </Button>
          <Button variant="ghost" onClick={() => setStatus("pending")} disabled={busy !== null || candidate.status === "pending"}>
            <RotateCcwIcon />
            Przywróć do oczekujących
          </Button>
        </>}
        navigation={<>
          <Button variant={candidate.status === "approved" ? "default" : "outline"} onClick={() => navigateStage(2)}>Przejdź do oceny tematu<ArrowRightIcon /></Button>
          <p className="action-hint">Ocena jest opcjonalna — w razie potrzeby przejdź od razu do researchu w nawigacji etapów.</p>
        </>}
        resultTitle="Wybrany materiał"
        summary={<UsageSummary free note={`Pobrano: ${formatDate(candidate.created_at)} · źródło: ${candidate.source_name}`} />}>
        <div className="space-y-4">
          <h4 className="text-lg font-semibold">{candidate.title}</h4>
          <p className="max-w-3xl text-sm leading-7 whitespace-pre-line text-slate-700">{candidate.summary ?? "Brak podsumowania w źródle RSS."}</p>
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-lg bg-muted/50 p-3"><dt className="text-xs text-muted-foreground">Źródło</dt><dd className="mt-1 font-medium">{candidate.source_name}</dd></div>
            <div className="rounded-lg bg-muted/50 p-3"><dt className="text-xs text-muted-foreground">Publikacja w źródle</dt><dd className="mt-1 font-medium">{formatDate(candidate.original_published_at)}</dd></div>
            <div className="rounded-lg bg-muted/50 p-3"><dt className="text-xs text-muted-foreground">Pobrano do systemu</dt><dd className="mt-1 font-medium">{formatDate(candidate.created_at)}</dd></div>
          </dl>
          <a href={candidate.external_url} target="_blank" rel="noopener noreferrer" className={buttonVariants({variant:"outline"})}><ExternalLinkIcon className="size-4" />Otwórz oryginał</a>
        </div>
        {candidate.is_demo && <DemoNotice />}
      </WorkflowSection>

      <WorkflowSection progressJob={jobs.ownActive} number={2} title="Ocena tematu przez AI" description="Punktacja i uzasadnienie pomagające wybrać temat do opracowania." paid
        initiallyCollapsed={classified}
        status={jobs.latest ? jobStatusLabel[jobs.latest.status] : busy === "classify" ? "W toku" : classificationError ? "Ostatnie uruchomienie: błąd" : classified ? "Zakończono" : "Do uruchomienia"}
        actionTitle="Ocena AI" actionDescription={classified ? "Ocena jest gotowa. Ponowna ocena zastąpi punktację i ponownie użyje AI." : "Uruchom ocenę, aby zobaczyć punktację i uzasadnienie. Ocena jest opcjonalna — research możesz uruchomić bez niej."}
        actionDetails={classified ? <p className="text-sm"><span className="font-semibold tabular-nums">{candidate.total_score}/100</span> · {SCORE_LEVEL_LABEL[scoreLevel(candidate.total_score ?? 0)]}</p> : undefined}
        blocker={jobs.active && !jobs.ownActive ? "Dla tego tematu trwa inne zadanie. Ocena będzie dostępna po jego zakończeniu." : undefined}
        primary={<Button
          variant={classificationHasRun ? "outline" : "default"}
          onClick={() => void classify()}
          disabled={busy !== null || !jobs.loaded || Boolean(jobs.active)}
        >
          {busy === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {classificationHasRun ? "Oceń ponownie" : "Oceń temat"} · {candidate.is_demo ? "demo · bezpłatne" : "płatne"}
        </Button>}
        navigation={<Button variant={classified ? "default" : "outline"} onClick={() => navigateStage(3)}>Przejdź do researchu<ArrowRightIcon /></Button>}
        activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[classificationUsageRow(candidate)]} note={classified ? `Oceniono: ${formatDate(candidate.classified_at)}. Starsze oceny mogą nie mieć zapisanych danych o zużyciu.` : "Dane zużycia pojawią się po ocenie tematu."} />}>

        {classificationError && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{classificationError}</p>}
        {candidate.topic_group && <div className="mb-4 max-w-3xl space-y-2 rounded-xl border border-sky-200 bg-sky-50/50 p-4 text-sm" role="note">
          <p className="font-medium">{candidate.topic_group_id ? "Ten sam temat co inne wpisy z RSS" : "Ten temat podały też inne kanały RSS"}</p>
          <ul className="space-y-1">{candidate.topic_group.members.map((member) => <li key={member.id}>
            <Link href={`/candidates/${member.id}`} className="underline underline-offset-4">{member.title}</Link>
            <span className="text-muted-foreground"> · {member.source_name}{member.id === candidate.topic_group?.primary_id ? " · główny temat" : ""}</span>
          </li>)}</ul>
          <p className="text-xs text-muted-foreground">Research głównego tematu użyje tych artykułów jako dodatkowych źródeł.</p>
          {candidate.topic_group_id && <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={busy !== null || Boolean(jobs.active)} onClick={() => void classify(true)}>Oceń mimo to osobno · {candidate.is_demo ? "demo · bezpłatne" : "płatne"}</Button>
            <Button size="sm" variant="ghost" disabled={busy !== null || Boolean(jobs.active)} onClick={() => void ungroup()}>Odłącz od grupy · bezpłatne</Button>
          </div>}
          {groupError && <p role="alert" className="text-rose-800">{groupError}</p>}
        </div>}
        {classified && !candidate.topic_group && <SimilarTopics candidateId={candidate.id} disabled={busy !== null || Boolean(jobs.active)} onJoined={setCandidate} />}
        {candidate.covered_by && <div className="mb-4 max-w-3xl space-y-1 rounded-xl border border-amber-200 bg-amber-50/50 p-4 text-sm" role="note">
          <p className="font-medium">{candidate.covered_by.url ? "Ten temat jest już na blogu" : "Podobny artykuł już powstał w tym systemie"}</p>
          <p>{candidate.covered_by.url ? <a href={candidate.covered_by.url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4">{candidate.covered_by.title}</a> : candidate.covered_by.title}
            <span className="text-muted-foreground"> · podobieństwo {candidate.covered_by.similarity.toFixed(2)}</span></p>
          {candidate.covered_by.post_id ? <p className="text-xs text-muted-foreground">W kroku 4 możesz napisać aktualizację tego wpisu zamiast nowego tekstu.</p> : null}
        </div>}
        <div className="max-w-3xl">
          <div className="space-y-4">{classified ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-emerald-50/50 p-5 ring-1 ring-emerald-100"><div><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Wynik łączny</p><p className="mt-2 text-4xl font-semibold tabular-nums">{candidate.total_score}<span className="text-lg font-normal text-muted-foreground"> / 100</span></p></div><span className="rounded-full bg-white px-3 py-1 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">{SCORE_LEVEL_LABEL[scoreLevel(candidate.total_score ?? 0)]}</span></div>
                <p className="text-xs text-muted-foreground">Wynik to średnia ważona czterech ocen poniżej (wagi w nawiasach).</p>
                <ScoreBar label="Trafność (40%)" value={candidate.relevance_score} />
                <ScoreBar label="Aktualność (20%)" value={candidate.freshness_score} />
                <ScoreBar label="Potencjał wyszukiwań (25%)" value={candidate.search_potential_score} />
                <ScoreBar label="Potencjał komercyjny (15%)" value={candidate.commercial_potential_score} />
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
                Temat nie został jeszcze oceniony. Uruchom ocenę w panelu akcji.
              </p>
            )}</div>

        </div>
      </WorkflowSection>

      <ResearchPanel candidateId={id} onResearchChange={setResearch} />

      <ArticlePanel candidateId={id} candidateCategory={candidate.category} research={research} coveredBy={candidate.covered_by ?? null}
        editorTake={<EditorTake candidate={candidate} onSaved={setCandidate} />} />
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
