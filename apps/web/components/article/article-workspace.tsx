"use client";

import { useEffect, useState } from "react";
import { AlertTriangleIcon, ClipboardListIcon, CopyIcon, FileCode2Icon, FileTextIcon, HistoryIcon, LinkIcon, ListChecksIcon, PencilIcon, SearchIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ResultBlock, ResultOutline } from "@/components/stage/result-block";
import { ARTICLE_STATUS_LABELS } from "@/lib/article-status";
import { articleFormatLabel, legacyArticleFormat } from "@/lib/article-options";
import { plural } from "@/lib/pagination";
import { cn } from "@/lib/utils";
import type { Article, ArticleSummary, ArticleUpdate } from "@/types/api";

import { ArticleEditor } from "./article-editor";
import { FactUsage } from "./fact-usage";
import { ArticlePreview, SEOPreview } from "./article-preview";

const ORIGIN: Record<string, string> = { generated: "Wygenerowana", regenerated: "Ponowna generacja", auto_fix: "Auto Fix", manual_edit: "Ręczna edycja", legacy: "Wersja archiwalna" };
const LENGTH: Record<string, string> = { auto: "automatyczna", short: "krótki", standard: "standardowy", long: "długi" };

export function ArticleWorkspace({ article, versions, selecting, editingArticle, saving, editingBlocked, onSelect, onEdit, onSave, onCancel, extra }: {
  article: Article; versions: ArticleSummary[]; selecting: boolean; editingArticle: Article | null; saving: boolean; editingBlocked: boolean;
  onSelect: (id: number) => Promise<void>; onEdit: () => void; onSave: (data: ArticleUpdate) => Promise<void>; onCancel: () => void;
  extra?: React.ReactNode;
}) {
  const [textState, setTextState] = useState<{ articleId: number; view: "preview" | "markdown" }>({ articleId: article.id, view: "preview" });
  const view = textState.articleId === article.id ? textState.view : "preview";
  const setView = (next: "preview" | "markdown") => setTextState({ articleId: article.id, view: next });
  const editing = Boolean(editingArticle);
  useEffect(() => {
    const show = () => setTextState({ articleId: article.id, view: "preview" });
    window.addEventListener(`article-${article.id}-reveal`, show);
    window.addEventListener("article-workspace-read", show);
    return () => { window.removeEventListener(`article-${article.id}-reveal`, show); window.removeEventListener("article-workspace-read", show); };
  }, [article.id]);

  async function copy() {
    try { await navigator.clipboard.writeText(`# ${article.title}\n\n${article.lead}\n\n${article.content}`); toast.success("Skopiowano tekst wybranej wersji"); }
    catch { toast.error("Nie udało się skopiować tekstu. Zaznacz go w podglądzie."); }
  }

  const minutes = Math.max(1, Math.ceil(article.word_count / 200));
  const usedFacts = article.facts_used_count;
  const availableFacts = article.facts_available_count;
  const warnings = article.validation_warnings.length;

  return (
    <section tabIndex={-1} id="article-workspace" aria-labelledby="article-workspace-title" aria-busy={selecting} className="min-w-0 scroll-mt-56 space-y-7">
      <header className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 id="article-workspace-title" className="text-base font-semibold">Wybrany artykuł</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">Tekst, brief i SEO wersji {article.version} — wersję zmienisz w pasku nad etapem.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" disabled={selecting || editing} onClick={() => void copy()}><CopyIcon />Kopiuj Markdown</Button>
            <Button variant="outline" size="sm" disabled={selecting || editing || editingBlocked} title={editingBlocked ? "Poczekaj na zakończenie zadania przed edycją." : undefined} onClick={onEdit}><PencilIcon />Edytuj tekst</Button>
          </div>
        </div>
        <p role="status" aria-live="polite" className="sr-only">{editingArticle ? `Edytujesz wersję ${editingArticle.version}. Formularz pozostaje przypięty do tej wersji, również podczas pracy w tle.` : selecting ? "Wczytywanie wybranej wersji…" : `Wyświetlana wersja ${article.version}${article.is_current ? " · najnowsza" : " · historyczna"}. Zmiana wersji zmienia również cel QA i Auto Fix.`}</p>
      </header>

      {editingArticle ? (
        <div className="space-y-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            <h4 id="article-editor-heading" tabIndex={-1} className="font-semibold outline-none">Edytujesz wersję {editingArticle.version}</h4>
            <p>Zapis utworzy nową wersję wymagającą nowego QA. Oryginalny tekst i jego raport pozostaną w historii.</p>
          </div>
          <ArticleEditor key={editingArticle.id} article={editingArticle} saving={saving} onSave={onSave} onCancel={onCancel} />
        </div>
      ) : <>
        <ResultOutline label="Zawartość wybranej wersji" items={[
          { target: "article-text", label: "Tekst", value: article.word_count.toLocaleString("pl-PL"), hint: `słów · ok. ${minutes} min czytania`, icon: FileTextIcon },
          { target: "article-facts", label: "Fakty w tekście", value: `${usedFacts}/${availableFacts}`, hint: availableFacts - usedFacts > 0 ? `${availableFacts - usedFacts} niewykorzystane` : "wszystkie wykorzystane", icon: ListChecksIcon, tone: usedFacts ? "success" : "attention" },
          { target: warnings ? "article-warnings" : "article-brief", label: "Ostrzeżenia", value: warnings, hint: warnings ? "sprawdź przed QA" : "brak uwag generatora", icon: AlertTriangleIcon, tone: warnings ? "attention" : "neutral" },
          { target: "article-history", label: "Wersje", value: versions.length, hint: `wybrana: wersja ${article.version}`, icon: HistoryIcon },
        ]} />

        {warnings > 0 && (
          <div id="article-warnings" role="note" className="scroll-mt-60 flex gap-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-950 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-100 dark:ring-amber-900">
            <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden="true" />
            <div><p className="font-medium">Ostrzeżenia generowania ({warnings})</p>
              <p className="text-amber-900/80 dark:text-amber-200/80">Generator zauważył możliwe problemy. QA sprawdzi je szczegółowo.</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">{article.validation_warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
            </div>
          </div>
        )}

        <ResultBlock id="article-text" icon={FileTextIcon} title="Tekst artykułu"
          description="Tak tekst wygląda dla czytelnika. Wersję Markdown możesz skopiować albo wkleić do innego edytora."
          actions={<div role="group" aria-label="Widok tekstu" className="inline-flex rounded-lg bg-muted p-0.5">
            {([["preview", "Podgląd", FileTextIcon], ["markdown", "Markdown", FileCode2Icon]] as const).map(([value, label, Icon]) => (
              <button key={value} type="button" aria-pressed={view === value} onClick={() => setView(value)}
                className={cn("inline-flex min-h-8 items-center gap-1.5 rounded-md px-3 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-ring", view === value ? "bg-background text-foreground shadow-xs" : "text-muted-foreground hover:text-foreground")}>
                <Icon className="size-3.5" aria-hidden="true" />{label}
              </button>
            ))}
          </div>}>
          <div className="rounded-xl bg-background p-5 ring-1 ring-foreground/8 sm:p-8">
            {view === "preview" ? <ArticlePreview article={article} /> :
              <pre className="overflow-auto whitespace-pre-wrap break-words text-sm leading-7">{`# ${article.title}\n\n${article.lead}\n\n${article.content}`}</pre>}
          </div>
        </ResultBlock>

        <ResultBlock id="article-brief" icon={ClipboardListIcon} title="Brief i plan tekstu"
          description="Założenia, które AI przygotowało przed pisaniem: kąt, odbiorcy i plan sekcji z przypisanymi faktami.">
          <Brief article={article} />
        </ResultBlock>

        <ResultBlock id="article-facts" icon={LinkIcon} title="Fakty z researchu w tekście" count={usedFacts}
          description="Które fakty z bazy researchu stoją za każdą częścią tekstu. Fragment bez faktów warto sprawdzić szczególnie uważnie.">
          <FactUsage article={article} />
        </ResultBlock>

        <ResultBlock id="article-seo" icon={SearchIcon} title="SEO"
          description="Tytuł i opis w wynikach wyszukiwania oraz dane, które trafią do wtyczki SEO w WordPressie.">
          <SEOPreview article={article} />
        </ResultBlock>

        <ResultBlock id="article-history" icon={HistoryIcon} title="Historia wersji" count={versions.length}
          description="Każda generacja, edycja i Auto Fix tworzą nową wersję. Starsze wersje i ich raporty QA zostają bez zmian.">
          <div className="overflow-x-auto rounded-xl ring-1 ring-foreground/8">
            <table className="w-full text-left text-sm"><caption className="sr-only">Wersje artykułu, źródło zmiany, QA i status</caption>
              <thead className="bg-muted/50"><tr className="text-xs text-muted-foreground">{["Wersja", "Pochodzenie", "QA", "Status"].map((h) => <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
              <tbody>{versions.map((v) => <tr key={v.id} className={cn("border-t", v.id === article.id && "bg-emerald-50/50 dark:bg-emerald-950/30")}>
                <td className="px-3 py-1.5"><button disabled={selecting} aria-current={v.id === article.id ? "true" : undefined} className="min-h-9 rounded px-1 font-medium underline-offset-4 hover:underline focus-visible:outline-2" onClick={() => void onSelect(v.id)}>Wersja {v.version}{v.id === article.id ? " · wybrana" : ""}{v.is_current ? " · najnowsza" : ""}</button></td>
                <td className="px-3 py-1.5">{ORIGIN[v.created_by] ?? v.created_by}</td>
                <td className="px-3 py-1.5 tabular-nums">{v.qa_score != null ? `${v.qa_score}/100` : <span className="text-muted-foreground">QA wymagane</span>}</td>
                <td className="px-3 py-1.5">{ARTICLE_STATUS_LABELS[v.status]}</td>
              </tr>)}</tbody>
            </table>
          </div>
        </ResultBlock>
        {extra}
      </>}
    </section>
  );
}

function Brief({ article }: { article: Article }) {
  const brief = article.brief;
  const options = article.generation_options ?? {};
  const plan = Array.isArray(brief?.section_plan) ? brief.section_plan : [];
  const keyPoints = Array.isArray(brief?.key_points) ? brief.key_points : [];
  const settings: [string, string][] = [
    ["Format", articleFormatLabel(article.article_format ?? legacyArticleFormat(article.article_type))],
    ["Długość", `${LENGTH[options.length ?? "auto"] ?? options.length}${brief?.desired_length_words ? ` · cel ok. ${brief.desired_length_words} słów` : ""}`],
  ];
  if (options.refresh) settings.push(["Tryb", "aktualizacja istniejącego wpisu"]);
  const rows: [string, React.ReactNode][] = [
    ["Kąt", brief?.primary_angle || article.angle || "—"],
    ["Odbiorcy", brief?.target_audience || "—"],
    ...settings,
  ];
  if (options.instructions) rows.push(["Twoje instrukcje", options.instructions]);
  return (
    <div className="space-y-4">
      <dl className="divide-y rounded-xl bg-muted/40 px-4">
        {rows.map(([label, value]) => (
          <div key={label} className="grid gap-1 py-3 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
            <dt className="text-sm font-medium text-muted-foreground">{label}</dt><dd className="text-sm leading-6">{value}</dd>
          </div>
        ))}
      </dl>
      {keyPoints.length > 0 && <div className="space-y-2">
        <h5 className="text-sm font-semibold">Najważniejsze punkty</h5>
        <ul className="list-disc space-y-1 pl-5 text-sm leading-6">{keyPoints.map((point, index) => <li key={index}>{point}</li>)}</ul>
      </div>}
      {plan.length > 0 && <div className="space-y-2">
        <h5 className="text-sm font-semibold">Plan sekcji</h5>
        <ol className="divide-y overflow-hidden rounded-xl ring-1 ring-foreground/8">
          {plan.map((item, index) => (
            <li key={index} className="flex gap-3 bg-background px-4 py-3 text-sm">
              <span className="w-5 shrink-0 text-right font-semibold tabular-nums text-muted-foreground">{index + 1}.</span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{item.heading}</p>
                {item.purpose && <p className="mt-0.5 text-muted-foreground">{item.purpose}</p>}
              </div>
              <span className="shrink-0 text-right text-xs text-muted-foreground">
                {item.target_words ? <span className="block tabular-nums">~{item.target_words} słów</span> : null}
                {item.fact_ids?.length ? <span className="block tabular-nums">{item.fact_ids.length} {plural(item.fact_ids.length, "fakt", "fakty", "faktów")}</span> : null}
              </span>
            </li>
          ))}
        </ol>
      </div>}
    </div>
  );
}
