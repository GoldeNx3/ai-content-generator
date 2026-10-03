"use client";

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

import { WorkflowSection } from "@/components/workflow-section";
import { ModelPricingProvider, UsageSummary } from "@/components/usage-summary";
import { ArticlePanel } from "@/components/article/article-panel";
import { ResearchPanel } from "@/components/research/research-panel";
import { ScoreBadge, ScoreBar } from "@/components/score-badge";
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
    } catch (loadError) {
      setError(errorText(loadError));
    }
  }, [id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void load();
  }, [load]);

  async function run(kind: Exclude<Busy, null>, fn: () => Promise<Candidate>, message: string) {
    setBusy(kind);
    if (kind === "classify") setClassificationError(null);
    try {
      setCandidate(await fn());
      toast.success(message);
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
    return <p className="text-muted-foreground">Loading…</p>;
  }

  const classified = candidate.total_score !== null;

  return (
    <ModelPricingProvider>
    <div className="space-y-6">
      <BackLink />

      <div className="flex flex-wrap items-start gap-5">
        <ScoreBadge score={candidate.total_score} size="lg" />
        <div className="min-w-0 flex-1 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">{candidate.title}</h1>
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{candidate.source_name}</span>
            <span>·</span>
            <span>{formatDate(candidate.original_published_at)}</span>
            <StatusBadge status={candidate.status} />
            <CategoryBadge category={candidate.category} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
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
      </div>

      <WorkflowSection number={1} title="Pobranie tematu" description="Materiał źródłowy pobrany z RSS." paid={false} status="Zakończono"
        actions={<a
          href={candidate.external_url}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          <ExternalLinkIcon />
          Otwórz oryginał
        </a>}
        summary={<UsageSummary free note={`Pobrano: ${formatDate(candidate.created_at)} · źródło: ${candidate.source_name}`} />}>
        <p className="leading-relaxed whitespace-pre-line">{candidate.summary ?? <span className="text-muted-foreground">Brak podsumowania w źródle RSS.</span>}</p>
        <a href={candidate.external_url} target="_blank" rel="noopener noreferrer" className="block break-all text-xs text-muted-foreground hover:underline">{candidate.external_url}</a>
      </WorkflowSection>

      <WorkflowSection number={2} title="Ocena tematu przez AI" description="Punktacja i uzasadnienie pomagające wybrać temat do opracowania." paid
        status={busy === "classify" ? "W toku" : classificationError ? "Ostatnie uruchomienie: błąd" : classified ? "Zakończono" : "Do uruchomienia"}
        actions={<Button
          size="sm"
          variant="outline"
          onClick={() => run("classify", () => api.classifyCandidate(id), "Classified")}
          disabled={busy !== null}
        >
          {busy === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {classified ? "Oceń ponownie · płatne" : "Oceń temat · płatne"}
        </Button>}
        summary={<UsageSummary rows={[{label: "Ocena tematu", configured: "classifier", model: candidate.llm_model, input: candidate.llm_input_tokens, output: candidate.llm_output_tokens, cost: candidate.estimated_cost_usd}]} note={classified ? `Oceniono: ${formatDate(candidate.classified_at)}. Starsze oceny mogą nie mieć zapisanych danych o zużyciu.` : "Dane zużycia pojawią się po ocenie tematu."} />}>
        {classificationError && <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{classificationError}</p>}
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-4">            {classified ? (
              <>
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
          <div className="space-y-3 text-sm text-muted-foreground">
            <h3 className="font-medium text-foreground">Co robi ten etap?</h3>
            <p>AI ocenia temat pod kątem trafności, aktualności, wyszukiwań i potencjału komercyjnego. Research możesz uruchomić także bez oceny.</p>
            <p>Ponowna ocena zastępuje aktualną punktację i nalicza nowy koszt AI.</p>
          </div>
        </div>
      </WorkflowSection>

      <ResearchPanel candidateId={id} onResearchChange={setResearch} />

      <ArticlePanel candidateId={id} candidateCategory={candidate.category} research={research} />
    </div>
    </ModelPricingProvider>
  );
}

function BackLink() {
  return (
    <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm", className: "-ml-2" })}>
      <ArrowLeftIcon />
      Candidates
    </Link>
  );
}
