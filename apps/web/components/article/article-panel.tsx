"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCwIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { articleState } from "@/lib/workflow";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type {
  Article,
  ArticleSummary,
  ArticleUpdate,
  CandidateCategory,
  GenerateArticleRequest,
  Research,
} from "@/types/api";

import { QAPanel } from "./qa-panel";
import { ArticleWorkspace } from "./article-workspace";
import { GenerateArticleDialog } from "./generate-article-dialog";

interface ArticlePanelProps {
  candidateId: number;
  candidateCategory: CandidateCategory | null;
  research: Research | null;
}

export function ArticlePanel({ candidateId, research }: ArticlePanelProps) {
  const demo = useDemoMode();
  const selectedId = useRef<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [versions, setVersions] = useState<ArticleSummary[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [dialog, setDialog] = useState<"generate" | "regenerate" | null>(null);
  const [generating, setGenerating] = useState(false);
  const [editing, setEditing] = useState(false);
  // Formularz i docelowy ID są zamrożone na czas edycji tej konkretnej wersji.
  const [editingArticle, setEditingArticle] = useState<Article | null>(null);
  const [saving, setSaving] = useState(false);
  const [selectingVersion, setSelectingVersion] = useState(false);

  const loadVersions = useCallback(
    async (selectId?: number, expectedId?: number) => {
      try {
        const list = await api.listArticles(candidateId);
        setVersions(list);
        const target = selectId ?? list.find((v) => v.is_current)?.id ?? list[0]?.id;
        const next = target ? await api.getArticle(target) : null;
        if (expectedId !== undefined && selectedId.current !== expectedId) return true;
        selectedId.current = next?.id ?? null;
        setArticle(next);
        setLoadError(null);
        setLoaded(true);
        return true;
      } catch (error) {
        setLoadError(errorText(error));
        toast.error("Nie udało się wczytać artykułów", { description: errorText(error) });
        return false;
      }
    },
    [candidateId],
  );

  async function selectVersion(id: number) {
    if (editing || selectingVersion) return;
    selectedId.current = id;
    setSelectingVersion(true);
    try { await loadVersions(id); }
    finally { setSelectingVersion(false); }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void loadVersions();
  }, [loadVersions]);

  const jobs = useCandidateJobs(candidateId, "write", loadVersions);
  const generationBusy = generating || Boolean(jobs.active) || !jobs.loaded;

  const researchReady = research?.status === "completed";
  const generationHasRun = versions.length > 0 || jobs.history.length > 0;

  async function generate(options: GenerateArticleRequest) {
    setGenerating(true);
    setGenerationError(null);
    try {
      await jobs.enqueue(() => dialog === "regenerate" && article
        ? api.regenerateArticle(article.id, options)
        : api.generateArticle(candidateId, options));
      toast.success("Generowanie zapisane w kolejce");
      setDialog(null);
      setEditing(false);
    } catch (error) {
      setGenerationError(errorText(error));
      toast.error("Nie udało się wygenerować tekstu", { description: errorText(error) });
    } finally {
      setGenerating(false);
    }
  }

  async function save(data: ArticleUpdate) {
    if (!editingArticle) return;
    const editedId = editingArticle.id;
    if (Object.keys(data).length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await api.updateArticle(editedId, data);
      setArticle(updated);
      setEditing(false);
      toast.success("Zapisano nową wersję · QA wymagane");
      await loadVersions(updated.id);
    } catch (error) {
      toast.error("Nie udało się zapisać wersji", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  function editArticle() {
    if (!article || selectingVersion || jobs.active) return;
    setEditingArticle(article); setEditing(true);
    requestAnimationFrame(() => {
      window.location.hash = "article-workspace";
      window.dispatchEvent(new Event("article-workspace-read"));
      document.getElementById("article-workspace")?.scrollIntoView({block:"start"});
      document.getElementById("article-editor-heading")?.focus({preventScroll:true});
    });
  }

  return (
    <>
    {article ? <ArticleWorkspace article={article} versions={versions} selecting={selectingVersion}
      editingArticle={editing ? editingArticle : null} saving={saving} editingBlocked={Boolean(jobs.active)} onSelect={selectVersion}
      onEdit={editArticle} onSave={save} onCancel={() => setEditing(false)} /> :
      <section tabIndex={-1} id="article-workspace" aria-labelledby="article-empty-title" aria-busy={!loaded && !loadError} className="scroll-mt-36 rounded-xl border bg-card p-5">
        <h2 id="article-empty-title" className="font-semibold">Wybrany artykuł</h2>
        <p role={loadError ? "alert" : undefined} className="mt-2 text-sm text-muted-foreground">{loadError ? loadError : !loaded ? "Wczytywanie artykułów…" : researchReady ? "Nie ma jeszcze tekstu. Wygeneruj pierwszą wersję na podstawie Research." : "Najpierw ukończ Research, a następnie wygeneruj artykuł. Tutaj zobaczysz wybraną wersję."}</p>
      </section>}
    <WorkflowSection revealEvent={`article-${article?.id}-reveal`} number={4} title="Generowanie artykułu" description="Brief i treść opracowane na podstawie ukończonego researchu." paid
      initiallyCollapsed={loaded ? versions.length > 0 : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : generationError ? "Ostatnie uruchomienie: błąd" : articleState(Boolean(article), generating, Boolean(researchReady), loaded)}
      actions={<Button variant={generationHasRun ? "outline" : "default"} size="sm" onClick={() => setDialog(article ? "regenerate" : "generate")} disabled={!researchReady || !loaded || generationBusy}>
        {generationHasRun ? <RefreshCwIcon /> : <SparklesIcon />}{generationHasRun ? `Nowa wersja · ${demo ? "demo · bezpłatne" : "płatne"}` : `Generuj artykuł · ${demo ? "demo · bezpłatne" : "płatne"}`}
      </Button>}
      activity={(jobs.history.length > 0 || jobs.active || jobs.error) ? <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} /> : undefined}
      summary={<UsageSummary rows={[
        {label: "Brief", configured: "brief", model: article?.brief_llm_model, input: article?.brief_llm_model ? article.brief_input_tokens : null, output: article?.brief_llm_model ? article.brief_output_tokens : null, cost: article?.brief_cost_usd},
        {label: "Pisanie artykułu", configured: "writer", model: article?.llm_model, input: article?.llm_model ? article.writer_input_tokens : null, output: article?.llm_model ? article.writer_output_tokens : null, cost: article?.writer_cost_usd}
      ]} total={article?.estimated_cost_usd} note="Każda generacja tworzy nową, płatną wersję. Poprzednie wersje pozostają dostępne. Edycja i zmiana statusu nie wywołują AI." />}>
      <div className="space-y-6">

        <div className="space-y-1 text-sm text-muted-foreground">          {loadError && <p className="text-destructive">{loadError}</p>}
          {generationError && <p className="text-destructive">{generationError} — możesz ponowić generowanie; kolejne wywołanie może naliczyć koszt.</p>}
          {article && <p>Wersja {article.version} · {formatDate(article.created_at)} · {article.word_count} słów</p>}
          {article && <p className="mt-2">Kolejny krok: sprawdź treść i przekaż do weryfikacji.</p>}
</div>
        {!researchReady && (
          <p className="text-sm text-muted-foreground">Najpierw ukończ research, aby odblokować generowanie artykułu.</p>
        )}

        {researchReady && !article && (
          <p className="text-sm text-muted-foreground">
            Brak artykułu. Generowanie przygotuje brief i treść na podstawie faktów z researchu.
          </p>
        )}

      </div>

      <GenerateArticleDialog
        open={dialog !== null}
        onOpenChange={(open) => !open && setDialog(null)}
        title={dialog === "regenerate" ? `Generuj nową wersję na podstawie v${article?.version}` : "Generuj artykuł"}
        defaults={dialog === "regenerate" && article ? article.generation_options : {}}
        suggestedAngle={research?.suggested_angle ?? null}
        busy={generationBusy}
        onSubmit={generate}
      />
    </WorkflowSection>
    {!article && <>
      <WorkflowSection number={5} title="QA / Fact Checker" paid status="Najpierw wygeneruj artykuł"
        description="Sprawdza konkretną wersję tekstu względem Research." initiallyCollapsed
        actions={<Button size="sm" disabled>Run QA</Button>} summary={<UsageSummary note="QA będzie dostępne po wygenerowaniu artykułu." />}>
        <p className="text-sm text-muted-foreground">Brak wersji do sprawdzenia. Ukończ Research i wygeneruj artykuł.</p>
      </WorkflowSection>
      <WorkflowSection number={6} title="Auto Fix + Approval" paid status="Najpierw wykonaj QA"
        description="Poprawki i zatwierdzanie zawsze dotyczą wybranej wersji artykułu." initiallyCollapsed
        actions={<Button size="sm" disabled>Auto Fix</Button>} summary={<UsageSummary note="Poprawki wymagają ukończonego QA; approval wymaga QA passed." />}>
        <p className="text-sm text-muted-foreground">Po QA zobaczysz dostępne poprawki. Zatwierdzanie będzie dostępne po spełnieniu wymagań jakości.</p>
      </WorkflowSection>
    </>}
    {article && <QAPanel key={article.id} article={article} versions={versions} onSelectVersion={selectVersion}
      onVersionCreated={async (id, sourceId) => { if (!editing) await loadVersions(id, sourceId); }}
      onEdit={editArticle}
      selectingVersion={selectingVersion} candidateId={candidateId} editing={editing} onArticleChange={async () => {
      const refreshed = await api.getArticle(article.id);
      // A completed QA read must not select an older version after the user/Write selected another.
      setArticle((current) => current?.id === refreshed.id ? refreshed : current);
      setVersions((current) => current.map((version) => version.id === refreshed.id ? {...version, ...refreshed} : version));
    }} />}
    </>
  );
}
