"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangleIcon, FlaskConicalIcon, Loader2Icon, RefreshCwIcon, SplitIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Research, ResearchStatus } from "@/types/api";

import { FactList } from "./fact-list";
import { ManualSourceForm } from "./manual-source-form";
import { hostname } from "./research-utils";
import { SourceList } from "./source-list";

const POLL_INTERVAL_MS = 2000;

const STATUS_STYLES: Record<ResearchStatus, string> = {
  pending: "bg-zinc-100 text-zinc-600 ring-zinc-200",
  running: "bg-sky-50 text-sky-800 ring-sky-200",
  completed: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
};

interface ResearchPanelProps {
  candidateId: number;
  onResearchChange?: (research: Research | null) => void;
}

export function ResearchPanel({ candidateId, onResearchChange }: ResearchPanelProps) {
  const [research, setResearch] = useState<Research | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [starting, setStarting] = useState(false);

  const load = useCallback(async () => {
    try {
      setResearch(await api.getResearch(candidateId));
    } catch (error) {
      toast.error("Could not load research", { description: errorText(error) });
    } finally {
      setLoaded(true);
    }
  }, [candidateId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void load();
  }, [load]);

  useEffect(() => {
    onResearchChange?.(research);
  }, [research, onResearchChange]);

  const running = research?.status === "running";
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [running, load]);

  async function trigger(kind: "start" | "retry") {
    setStarting(true);
    try {
      setResearch(kind === "start" ? await api.startResearch(candidateId) : await api.retryResearch(candidateId));
    } catch (error) {
      toast.error("Could not start research", { description: errorText(error) });
    } finally {
      setStarting(false);
    }
  }

  const busy = starting || running;
  const hasReport = research?.status === "completed";

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <CardTitle className="text-xs font-semibold tracking-[0.2em] uppercase">Research report</CardTitle>
          {research && (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium ring-1", STATUS_STYLES[research.status])}>
              {research.status}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {research && research.sources.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => trigger("retry")} disabled={busy}>
              <RefreshCwIcon />
              Re-run analysis
            </Button>
          )}
          <Button size="sm" onClick={() => trigger("start")} disabled={busy}>
            {busy ? <Loader2Icon className="animate-spin" /> : <FlaskConicalIcon />}
            {research ? "Start new research" : "Start Research"}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-8">
        {!loaded && <p className="text-sm text-muted-foreground">Loading…</p>}

        {loaded && !research && (
          <p className="text-sm text-muted-foreground">
            No research yet. “Start Research” fetches the original article, looks for additional sources and asks the
            LLM to build a fact base with sources, uncertainties and conflicts.
          </p>
        )}

        {running && (
          <div className="flex items-center gap-3 rounded-lg bg-sky-50 px-4 py-3 text-sm text-sky-900">
            <Loader2Icon className="size-4 animate-spin" />
            <span>
              Fetching sources and analysing… <Elapsed since={research.started_at} />{" "}
              {research.sources.length > 0 && `· ${research.sources.length} source(s) so far`}
              <span className="block text-xs text-sky-800/80">
                Usually 20–90 s; larger models can take a few minutes.
              </span>
            </span>
          </div>
        )}

        {research?.status === "failed" && (
          <div className="flex gap-3 rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-900">
            <AlertTriangleIcon className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium">Research failed</p>
              <p>{research.error}</p>
              <p className="mt-1 text-rose-800/80">Fetched sources were kept. Add a source manually or re-run.</p>
            </div>
          </div>
        )}

        {hasReport && research && (
          <>
            <div className="grid gap-6 md:grid-cols-3">
              <ReportText title="Summary" text={research.summary} />
              <ReportText title="Why it matters" text={research.why_it_matters} />
              <ReportText title="Suggested angle" text={research.suggested_angle} />
            </div>

            <section className="space-y-3">
              <h3 className="font-semibold">
                Verified facts <span className="font-normal text-muted-foreground">({research.facts.length})</span>
              </h3>
              <FactList facts={research.facts} sources={research.sources} />
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-3">
                <h3 className="font-semibold">
                  Uncertainties{" "}
                  <span className="font-normal text-muted-foreground">({research.uncertainties.length})</span>
                </h3>
                {research.uncertainties.length === 0 ? (
                  <p className="text-sm text-muted-foreground">None reported.</p>
                ) : (
                  <ul className="space-y-2">
                    {research.uncertainties.map((item, index) => (
                      <li key={index} className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 text-sm">
                        <p>{item.claim}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{item.reason}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="space-y-3">
                <h3 className="font-semibold">
                  Conflicts <span className="font-normal text-muted-foreground">({research.conflicts.length})</span>
                </h3>
                {research.conflicts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No conflicts between sources.</p>
                ) : (
                  <ul className="space-y-2">
                    {research.conflicts.map((conflict, index) => (
                      <li key={index} className="rounded-lg border border-rose-200 bg-rose-50/40 p-3 text-sm">
                        <p className="flex items-center gap-1.5 font-medium">
                          <SplitIcon className="size-3.5" />
                          {conflict.topic}
                        </p>
                        <ul className="mt-2 space-y-1">
                          {conflict.sources.map((item, itemIndex) => (
                            <li key={itemIndex} className="text-xs">
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium hover:underline"
                              >
                                {hostname(item.url)}
                              </a>
                              : {item.claim}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </>
        )}

        {research && (
          <section className="space-y-3">
            <h3 className="font-semibold">
              Sources <span className="font-normal text-muted-foreground">({research.sources.length})</span>
            </h3>
            <SourceList sources={research.sources} />
            <ManualSourceForm candidateId={candidateId} disabled={busy} onAdded={load} />
            {research.search_queries.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Search queries: {research.search_queries.map((query) => `“${query}”`).join(", ")}
              </p>
            )}
          </section>
        )}

        {research && (research.llm_model || research.completed_at) && (
          <p className="border-t pt-3 text-xs text-muted-foreground">
            {research.llm_model && (
              <>
                {research.llm_model} · {research.llm_input_tokens.toLocaleString("en")} in /{" "}
                {research.llm_output_tokens.toLocaleString("en")} out tokens
                {research.estimated_cost_usd !== null && ` · ~$${Number(research.estimated_cost_usd).toFixed(4)}`}
                {" · "}
              </>
            )}
            {research.completed_at && `finished ${formatDate(research.completed_at)}`}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Elapsed({ since }: { since: string | null }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (!since) return null;
  const seconds = Math.max(0, Math.round((now - new Date(since).getTime()) / 1000));
  return <span className="font-mono tabular-nums">{seconds} s</span>;
}

function ReportText({ title, text }: { title: string; text: string | null }) {
  return (
    <section className="space-y-1.5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-foreground/90">{text ?? "—"}</p>
    </section>
  );
}
