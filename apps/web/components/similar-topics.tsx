"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import type { Candidate, SimilarTopic } from "@/types/api";

export function SimilarTopics({ candidateId, disabled, onJoined }: { candidateId: number; disabled: boolean; onJoined: (candidate: Candidate) => void }) {
  const [topics, setTopics] = useState<SimilarTopic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    api.similarTopics(candidateId).then((items) => { if (active) setTopics(items); }, (err) => { if (active) setError(errorText(err)); });
    return () => { active = false; };
  }, [candidateId]);

  async function join(primaryId: number) {
    setBusy(true);
    setError(null);
    try {
      onJoined(await api.joinTopicGroup(candidateId, primaryId));
    } catch (failure) {
      setError(errorText(failure));
    } finally {
      setBusy(false);
    }
  }

  if (!error && (topics === null || topics.length === 0)) return null;
  return (
    <section role="region" aria-label="Podobne tematy" className="mb-4 max-w-3xl space-y-2 rounded-xl border p-4 text-sm">
      <p className="font-medium">Podobne tematy</p>
      <p className="text-xs text-muted-foreground">Jeśli to ten sam news, połącz tematy: ten temat przejmie ocenę i zniknie z listy jako duplikat. Bezpłatne.</p>
      {error && <p role="alert" className="text-rose-800">{error}</p>}
      <ul className="space-y-2">{(topics ?? []).map((topic) => <li key={topic.id} className="flex flex-wrap items-center justify-between gap-2">
        <span><Link href={`/candidates/${topic.id}`} className="underline underline-offset-4">{topic.title}</Link>
          <span className="text-muted-foreground"> · {topic.source_name} · podobieństwo {topic.similarity.toFixed(2)}</span></span>
        <Button size="sm" variant="outline" disabled={disabled || busy} onClick={() => void join(topic.id)}>To ten sam temat · bezpłatne</Button>
      </li>)}</ul>
    </section>
  );
}
