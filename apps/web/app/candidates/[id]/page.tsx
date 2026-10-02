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

import { ArticlePanel } from "@/components/article/article-panel";
import { ResearchPanel } from "@/components/research/research-panel";
import { ScoreBadge, ScoreBar } from "@/components/score-badge";
import { CategoryBadge, StatusBadge } from "@/components/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, errorText } from "@/lib/api";
import { formatDate, SCORE_LEVEL_LABEL, scoreLevel } from "@/lib/format";
import type { Candidate, CandidateStatus, Research } from "@/types/api";

type Busy = CandidateStatus | "classify" | null;

export default function CandidatePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [error, setError] = useState<string | null>(null);
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
    try {
      setCandidate(await fn());
      toast.success(message);
    } catch (actionError) {
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

      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setStatus("approved")} disabled={busy !== null || candidate.status === "approved"}>
          {busy === "approved" ? <Loader2Icon className="animate-spin" /> : <CheckIcon />}
          Approve
        </Button>
        <Button
          variant="outline"
          onClick={() => setStatus("ignored")}
          disabled={busy !== null || candidate.status === "ignored"}
        >
          {busy === "ignored" ? <Loader2Icon className="animate-spin" /> : <XIcon />}
          Ignore
        </Button>
        {candidate.status !== "pending" && (
          <Button variant="ghost" onClick={() => setStatus("pending")} disabled={busy !== null}>
            <RotateCcwIcon />
            Back to pending
          </Button>
        )}
        <Button
          variant="outline"
          onClick={() => run("classify", () => api.classifyCandidate(id), "Classified")}
          disabled={busy !== null}
        >
          {busy === "classify" ? <Loader2Icon className="animate-spin" /> : <SparklesIcon />}
          {classified ? "Reclassify" : "Classify"}
        </Button>
        <a
          href={candidate.external_url}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonVariants({ variant: "ghost" })}
        >
          <ExternalLinkIcon />
          Open original
        </a>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="leading-relaxed whitespace-pre-line">
              {candidate.summary ?? <span className="text-muted-foreground">No summary in feed.</span>}
            </p>
            <a
              href={candidate.external_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block truncate font-mono text-xs text-muted-foreground hover:underline"
            >
              {candidate.external_url}
            </a>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>LLM assessment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {classified ? (
              <>
                <ScoreBar label="Relevance (40%)" value={candidate.relevance_score} />
                <ScoreBar label="Freshness (20%)" value={candidate.freshness_score} />
                <ScoreBar label="Search potential (25%)" value={candidate.search_potential_score} />
                <ScoreBar label="Commercial potential (15%)" value={candidate.commercial_potential_score} />
                <div className="flex items-baseline justify-between border-t pt-3">
                  <span className="text-sm font-medium">Total score</span>
                  <span className="font-mono text-lg font-semibold tabular-nums">
                    {candidate.total_score}{" "}
                    <span className="font-sans text-xs font-normal text-muted-foreground">
                      {SCORE_LEVEL_LABEL[scoreLevel(candidate.total_score ?? 0)]}
                    </span>
                  </span>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Reason</p>
                  <p className="text-sm leading-relaxed text-muted-foreground">{candidate.llm_reason}</p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Classified {formatDate(candidate.classified_at)}
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Not classified yet. Click “Classify” to score this topic.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <ResearchPanel candidateId={id} onResearchChange={setResearch} />

      <ArticlePanel candidateId={id} candidateCategory={candidate.category} research={research} />
    </div>
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
