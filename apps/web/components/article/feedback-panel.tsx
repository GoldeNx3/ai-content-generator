"use client";

import { useCallback, useState } from "react";
import { GraduationCapIcon, Loader2Icon } from "lucide-react";

import { useDemoMode } from "@/components/demo-mode";
import { Button } from "@/components/ui/button";
import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { api, errorText } from "@/lib/api";
import { isActiveJob } from "@/lib/jobs";
import type { ArticleSummary, EditorialSuggestion } from "@/types/api";

const KIND_LABEL: Record<EditorialSuggestion["kind"], string> = { style_rule: "Zasada stylu", banned_phrase: "Zakazany zwrot" };

export function FeedbackPanel({ candidateId, versions }: { candidateId: number; versions: ArticleSummary[] }) {
  const demo = useDemoMode();
  const [suggestions, setSuggestions] = useState<EditorialSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const load = useCallback(async () => {
    try {
      setSuggestions(await api.suggestions(candidateId));
      return true;
    } catch (failure) {
      setError(errorText(failure));
      return false;
    }
  }, [candidateId]);
  const jobs = useCandidateJobs(candidateId, "learn_feedback", load);

  const eligible = versions.some((version) => version.is_edited || Boolean(version.rejection_reason));
  const running = Boolean(jobs.ownActive);
  const failed = jobs.latest?.status === "failed" ? jobs.latest.error_message : null;

  async function request() {
    setError(null);
    try {
      await jobs.enqueue(() => api.requestFeedback(candidateId));
    } catch (failure) {
      setError(errorText(failure));
    }
  }

  async function decide(suggestion: EditorialSuggestion, accept: boolean) {
    setPending(suggestion.id);
    setError(null);
    try {
      const updated = accept ? await api.acceptSuggestion(suggestion.id) : await api.dismissSuggestion(suggestion.id);
      setSuggestions((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setPending(null);
    }
  }

  return (
    <section role="region" aria-label="Wnioski z Twoich poprawek" className="space-y-3 rounded-xl border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="flex items-center gap-2 font-semibold"><GraduationCapIcon className="size-4" />Wnioski z Twoich poprawek</h3>
          <p className="text-sm text-muted-foreground">AI porówna swój tekst z Twoją poprawioną wersją i powodami odrzuceń, i zaproponuje zasady stylu do profilu redakcji. Nic nie trafi do profilu bez Twojej zgody.</p>
        </div>
        <Button size="sm" variant="outline" disabled={!eligible || running || !jobs.loaded || Boolean(jobs.active && !jobs.ownActive)} onClick={() => void request()}>
          {running ? <Loader2Icon className="animate-spin" /> : null}Zaproponuj reguły · {demo ? "demo · bezpłatne" : "płatne"}
        </Button>
      </div>
      {!eligible && <p className="text-xs text-muted-foreground">Dostępne po ręcznej poprawce wersji albo odrzuceniu jej z podanym powodem.</p>}
      {running && <p role="status" className="text-sm text-muted-foreground">Analiza poprawek w toku{jobs.ownActive && isActiveJob(jobs.ownActive) ? "…" : ""}</p>}
      {failed && <p role="alert" className="text-sm text-rose-800">{failed}</p>}
      {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
      {suggestions.length > 0 && <ul className="space-y-2">
        {suggestions.map((suggestion) => <li key={suggestion.id} className="space-y-2 rounded-lg border p-3 text-sm">
          <p><span className="mr-2 rounded bg-muted px-2 py-0.5 text-xs">{KIND_LABEL[suggestion.kind]}</span>{suggestion.text}</p>
          <p className="text-xs text-muted-foreground">{suggestion.why}</p>
          {suggestion.status === "pending" ? <div className="flex gap-2">
            <Button size="sm" disabled={pending !== null} onClick={() => void decide(suggestion, true)}>Dodaj do profilu · bezpłatne</Button>
            <Button size="sm" variant="ghost" disabled={pending !== null} onClick={() => void decide(suggestion, false)}>Pomiń</Button>
          </div> : <p className="text-xs font-medium">{suggestion.status === "accepted" ? "Dodano do profilu" : "Pominięto"}</p>}
        </li>)}
      </ul>}
    </section>
  );
}
