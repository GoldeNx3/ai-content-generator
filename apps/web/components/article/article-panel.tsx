"use client";

import { useDemoMode } from "@/components/demo-mode";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangleIcon, PencilIcon, RefreshCwIcon, SparklesIcon } from "lucide-react";
import { toast } from "sonner";

import { useCandidateJobs } from "@/hooks/use-candidate-jobs";
import { JobStatus, jobStatusLabel } from "@/components/job-status";
import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { ARTICLE_STATUS_LABELS } from "@/lib/article-status";
import { articleState } from "@/lib/workflow";
import { articleFormatLabel, legacyArticleFormat } from "@/lib/article-options";
import { FilterSelect } from "@/components/filter-select";
import { Button } from "@/components/ui/button";
import { api, errorText } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  Article,
  ArticleStatus,
  ArticleSummary,
  ArticleUpdate,
  CandidateCategory,
  GenerateArticleRequest,
  Research,
} from "@/types/api";

import { QAPanel } from "./qa-panel";
import { ArticleEditor } from "./article-editor";
import { FactUsage } from "./fact-usage";
import { GenerateArticleDialog } from "./generate-article-dialog";
import { Markdown } from "./markdown";

const STATUS_STYLES: Record<ArticleStatus, string> = {
  needs_changes: "bg-amber-50 text-amber-900 ring-amber-200",
  ready_for_approval: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  manual_review_required: "bg-orange-50 text-orange-900 ring-orange-200",
  superseded: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  draft: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  review: "bg-sky-50 text-sky-800 ring-sky-200",
  approved: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  rejected: "bg-rose-50 text-rose-800 ring-rose-200",
};

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
        toast.error("Could not load articles", { description: errorText(error) });
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
      toast.error("Generation failed", { description: errorText(error) });
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
      toast.success("Draft saved");
      await loadVersions(updated.id);
    } catch (error) {
      toast.error("Could not save", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
    <WorkflowSection revealEvent={`article-${article?.id}-reveal`} number={4} title="Generowanie artykułu" description="Brief i treść opracowane na podstawie ukończonego researchu." paid
      initiallyCollapsed={loaded ? versions.length > 0 : undefined}
      status={jobs.latest ? jobStatusLabel[jobs.latest.status] : loadError ? "Błąd odczytu" : generationError ? "Ostatnie uruchomienie: błąd" : articleState(Boolean(article), generating, Boolean(researchReady), loaded)}
      actions={<Button variant={generationHasRun ? "outline" : "default"} size="sm" onClick={() => setDialog(article ? "regenerate" : "generate")} disabled={!researchReady || !loaded || generationBusy}>
        {generationHasRun ? <RefreshCwIcon /> : <SparklesIcon />}{generationHasRun ? `Nowa wersja · ${demo ? "demo · bezpłatne" : "płatne"}` : `Generuj artykuł · ${demo ? "demo · bezpłatne" : "płatne"}`}
      </Button>}
      summary={<UsageSummary rows={[
        {label: "Brief", configured: "brief", model: article?.brief_llm_model, input: article?.brief_llm_model ? article.brief_input_tokens : null, output: article?.brief_llm_model ? article.brief_output_tokens : null, cost: article?.brief_cost_usd},
        {label: "Pisanie artykułu", configured: "writer", model: article?.llm_model, input: article?.llm_model ? article.writer_input_tokens : null, output: article?.llm_model ? article.writer_output_tokens : null, cost: article?.writer_cost_usd}
      ]} total={article?.estimated_cost_usd} note="Każda generacja tworzy nową, płatną wersję. Poprzednie wersje pozostają dostępne. Edycja i zmiana statusu nie wywołują AI." />}>
      <div className="space-y-6">
        <JobStatus jobs={jobs.history} active={jobs.active} error={jobs.error} onRetry={(job) => jobs.enqueue(() => api.retryJob(job.id))} />
        <div className="space-y-1 text-sm text-muted-foreground">          {loadError && <p className="text-destructive">{loadError}</p>}
          {generationError && <p className="text-destructive">{generationError} — możesz ponowić generowanie; kolejne wywołanie może naliczyć koszt.</p>}
          {article && <p>Wersja {article.version} · {formatDate(article.created_at)} · {article.word_count} słów</p>}
          {article && <p className="mt-2">Kolejny krok: sprawdź treść i przekaż do weryfikacji.</p>}
</div>
        {article && <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/20 p-3">          {article && (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium ring-1", STATUS_STYLES[article.status])}>
              {ARTICLE_STATUS_LABELS[article.status]}
            </span>
          )}
          {versions.length > 1 && article && (
            <FilterSelect
              label="Version"
              disabled={editing || selectingVersion}
              allowAll={false}
              value={String(article.id)}
              options={versions.map((v) => ({
                value: String(v.id),
                label: `Version ${v.version}${v.is_current ? " (current)" : ""}${v.is_edited ? " · edited" : ""}`,
              }))}
              onChange={(value) => value && void selectVersion(Number(value))}
            />
          )}

          {article && !editing && (
            <>
              <Button variant="outline" size="sm" onClick={() => { setEditingArticle(article); setEditing(true); }}>
                <PencilIcon />
                Edytuj
              </Button>
            </>
          )}
</div>}
        {!researchReady && (
          <p className="text-sm text-muted-foreground">Najpierw ukończ research, aby odblokować generowanie artykułu.</p>
        )}

        {researchReady && !article && (
          <p className="text-sm text-muted-foreground">
            Brak artykułu. Generowanie przygotuje brief i treść na podstawie faktów z researchu.
          </p>
        )}

        {editingArticle && editing && (
          <ArticleEditor key={editingArticle.id} article={editingArticle} saving={saving} onSave={save} onCancel={() => setEditing(false)} />
        )}

        {article && !editing && <ArticleBody article={article} />}
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
    {versions.length > 0 && <div className="overflow-x-auto rounded-xl border bg-card p-4 text-sm">
      <h3 className="mb-3 font-semibold">Historia wersji</h3>
      <table className="w-full text-left"><thead><tr className="text-xs text-muted-foreground"><th className="p-2">Wersja</th><th className="p-2">Pochodzenie</th><th className="p-2">QA</th><th className="p-2">Status</th></tr></thead>
      <tbody>{versions.map((version) => <tr key={version.id} className="border-t"><td className="p-2"><button disabled={editing || selectingVersion} className="underline" onClick={() => void selectVersion(version.id)}>v{version.version}{version.is_current ? " · current" : ""}</button></td>
        <td className="p-2">{version.created_by ?? "generated"}</td><td className="p-2">{version.qa_score != null ? `${version.qa_score}/100` : version.qa_status === "required" ? "Wymagane" : version.qa_status ?? "—"}</td><td className="p-2">{ARTICLE_STATUS_LABELS[version.status]}</td></tr>)}</tbody></table>
    </div>}
    {article && <QAPanel key={article.id} article={article} versions={versions} onSelectVersion={selectVersion}
      onVersionCreated={async (id, sourceId) => { if (!editing) await loadVersions(id, sourceId); }}
      onEdit={() => { setEditingArticle(article); setEditing(true); window.dispatchEvent(new Event(`article-${article.id}-reveal`)); }}
      selectingVersion={selectingVersion} candidateId={candidateId} editing={editing} onArticleChange={async () => {
      const refreshed = await api.getArticle(article.id);
      // A completed QA read must not select an older version after the user/Write selected another.
      setArticle((current) => current?.id === refreshed.id ? refreshed : current);
      setVersions((current) => current.map((version) => version.id === refreshed.id ? {...version, ...refreshed} : version));
    }} />}
    </>
  );
}

function ArticleBody({ article }: { article: Article }) {
  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <article className="min-w-0">
        <h2 className="text-3xl font-semibold tracking-tight text-balance">{article.title}</h2>
        <p className="mt-4 text-lg leading-8 font-medium text-foreground/90">{article.lead}</p>
        <div className="mt-2 text-[15px]">
          <Markdown anchorPrefix={`article-${article.id}`}>{article.content}</Markdown>
        </div>
      </article>

      <aside className="space-y-6 text-sm">
        {article.validation_warnings.length > 0 && (
          <section className="space-y-2 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
            <p className="flex items-center gap-1.5 font-medium text-amber-900">
              <AlertTriangleIcon className="size-4" />
              Review warnings
            </p>
            <ul className="list-disc space-y-1 pl-5 text-xs text-amber-900">
              {article.validation_warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-2">
          <h3 className="font-semibold">Stats</h3>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <Stat label="Words" value={article.word_count.toLocaleString("en")} />
            <Stat label="Sections" value={article.sections_count} />
            <Stat label="Research facts used" value={`${article.facts_used_count} / ${article.facts_available_count}`} />
            <Stat label="Sources referenced" value={article.source_count} />
            <Stat label="Format" value={articleFormatLabel(article.article_format ?? legacyArticleFormat(article.article_type))} />
            <Stat label="Created" value={formatDate(article.created_at)} />
            <Stat label="Edited manually" value={article.is_edited ? "yes" : "no"} />
          </dl>
        </section>

        {article.angle && <section className="space-y-2">
          <h3 className="font-semibold">Kąt artykułu</h3>
          <p className="text-xs">{article.angle}</p>
        </section>}

        <section className="space-y-2">
          <h3 className="font-semibold">SEO</h3>
          <div className="space-y-2 text-xs">
            <div>
              <p className="text-muted-foreground">Meta title ({article.meta_title.length})</p>
              <p className="font-medium">{article.meta_title}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Meta description ({article.meta_description.length})</p>
              <p>{article.meta_description}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Slug</p>
              <p className="font-mono">{article.slug}</p>
            </div>
          </div>
        </section>

        <section className="space-y-2">
          <h3 className="font-semibold">Facts & sources used</h3>
          <FactUsage article={article} />
        </section>
      </aside>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-medium tabular-nums">{value}</dd>
    </>
  );
}
