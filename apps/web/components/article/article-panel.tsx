"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangleIcon, CheckIcon, PencilIcon, RefreshCwIcon, SendIcon, SparklesIcon, XIcon } from "lucide-react";
import { toast } from "sonner";

import { WorkflowSection } from "@/components/workflow-section";
import { UsageSummary } from "@/components/usage-summary";
import { articleState } from "@/lib/workflow";
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

import { ArticleEditor } from "./article-editor";
import { FactUsage } from "./fact-usage";
import { GenerateArticleDialog } from "./generate-article-dialog";
import { Markdown } from "./markdown";

const STATUS_STYLES: Record<ArticleStatus, string> = {
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

export function ArticlePanel({ candidateId, candidateCategory, research }: ArticlePanelProps) {
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [versions, setVersions] = useState<ArticleSummary[]>([]);
  const [article, setArticle] = useState<Article | null>(null);
  const [dialog, setDialog] = useState<"generate" | "regenerate" | null>(null);
  const [generating, setGenerating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadVersions = useCallback(
    async (selectId?: number) => {
      try {
        const list = await api.listArticles(candidateId);
        setVersions(list);
        const target = selectId ?? list.find((v) => v.is_current)?.id ?? list[0]?.id;
        setArticle(target ? await api.getArticle(target) : null);
        setLoadError(null);
        setLoaded(true);
      } catch (error) {
        setLoadError(errorText(error));
        toast.error("Could not load articles", { description: errorText(error) });
      }
    },
    [candidateId],
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching on mount
    void loadVersions();
  }, [loadVersions]);

  const researchReady = research?.status === "completed";

  async function generate(options: GenerateArticleRequest) {
    setGenerating(true);
    setGenerationError(null);
    try {
      const created =
        dialog === "regenerate" && article
          ? await api.regenerateArticle(article.id, options)
          : await api.generateArticle(candidateId, options);
      toast.success(`Draft v${created.version} generated`, {
        description: `${created.word_count} words · ${created.facts_used_count}/${created.facts_available_count} facts`,
      });
      setDialog(null);
      setEditing(false);
      await loadVersions(created.id);
    } catch (error) {
      setGenerationError(errorText(error));
      toast.error("Generation failed", { description: errorText(error) });
    } finally {
      setGenerating(false);
    }
  }

  async function save(data: ArticleUpdate) {
    if (!article) return;
    if (Object.keys(data).length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      setArticle(await api.updateArticle(article.id, data));
      setEditing(false);
      toast.success("Draft saved");
      await loadVersions(article.id);
    } catch (error) {
      toast.error("Could not save", { description: errorText(error) });
    } finally {
      setSaving(false);
    }
  }

  async function setStatus(status: ArticleStatus) {
    if (!article) return;
    try {
      setArticle(await api.updateArticleStatus(article.id, status));
      toast.success(`Marked as ${status}`);
      await loadVersions(article.id);
    } catch (error) {
      toast.error("Could not change status", { description: errorText(error) });
    }
  }

  return (
    <WorkflowSection number={4} title="Generowanie artykułu" description="Brief i treść opracowane na podstawie ukończonego researchu." paid
      status={loadError ? "Błąd odczytu" : generationError ? "Ostatnie uruchomienie: błąd" : articleState(Boolean(article), generating, Boolean(researchReady), loaded)}
      actions={<Button variant={article ? "outline" : "default"} size="sm" onClick={() => setDialog(article ? "regenerate" : "generate")} disabled={!researchReady || !loaded || generating}>
        {article ? <RefreshCwIcon /> : <SparklesIcon />}{article ? "Nowa wersja · płatne" : "Generuj artykuł · płatne"}
      </Button>}
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
        {article && <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/20 p-3">          {article && (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium ring-1", STATUS_STYLES[article.status])}>
              {{draft: "Szkic", review: "W weryfikacji", approved: "Zatwierdzony", rejected: "Odrzucony"}[article.status]}
            </span>
          )}
          {versions.length > 1 && article && (
            <FilterSelect
              label="Version"
              allowAll={false}
              value={String(article.id)}
              options={versions.map((v) => ({
                value: String(v.id),
                label: `Version ${v.version}${v.is_current ? " (current)" : ""}${v.is_edited ? " · edited" : ""}`,
              }))}
              onChange={(value) => value && void loadVersions(Number(value))}
            />
          )}

          {article && !editing && (
            <>
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                <PencilIcon />
                Edytuj
              </Button>
              {article.status === "draft" && (
                <Button size="sm" onClick={() => setStatus("review")}>
                  <SendIcon />
                  Przekaż do weryfikacji
                </Button>
              )}
              {article.status === "review" && (
                <>
                  <Button size="sm" onClick={() => setStatus("approved")}>
                    <CheckIcon />
                    Zatwierdź
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setStatus("rejected")}>
                    <XIcon />
                    Odrzuć
                  </Button>
                </>
              )}
              {(article.status === "approved" || article.status === "rejected") && (
                <Button size="sm" variant="ghost" onClick={() => setStatus("draft")}>
                  Przywróć szkic
                </Button>
              )}
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

        {article && editing && (
          <ArticleEditor article={article} saving={saving} onSave={save} onCancel={() => setEditing(false)} />
        )}

        {article && !editing && <ArticleBody article={article} />}
      </div>

      <GenerateArticleDialog
        open={dialog !== null}
        onOpenChange={(open) => !open && setDialog(null)}
        title={dialog === "regenerate" ? `Generuj nową wersję na podstawie v${article?.version}` : "Generuj artykuł"}
        defaults={dialog === "regenerate" && article ? article.generation_options : {}}
        defaultType={candidateCategory ?? "news"}
        suggestedAngle={research?.suggested_angle ?? null}
        busy={generating}
        onSubmit={generate}
      />
    </WorkflowSection>
  );
}

function ArticleBody({ article }: { article: Article }) {
  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <article className="min-w-0">
        <h2 className="text-3xl font-semibold tracking-tight text-balance">{article.title}</h2>
        <p className="mt-4 text-lg leading-8 font-medium text-foreground/90">{article.lead}</p>
        <div className="mt-2 text-[15px]">
          <Markdown>{article.content}</Markdown>
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
            <Stat label="Type" value={article.article_type} />
            <Stat label="Created" value={formatDate(article.created_at)} />
            <Stat label="Edited manually" value={article.is_edited ? "yes" : "no"} />
          </dl>
        </section>

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
