"use client";

import { useEffect, useState } from "react";
import { CopyIcon, PencilIcon, FileTextIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/components/filter-select";
import { ARTICLE_STATUS_LABELS } from "@/lib/article-status";
import { articleFormatLabel, legacyArticleFormat } from "@/lib/article-options";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Article, ArticleSummary, ArticleUpdate } from "@/types/api";
import { ArticleEditor } from "./article-editor";
import { FactUsage } from "./fact-usage";
import { ArticlePreview, SEOPreview } from "./article-preview";

const ORIGIN: Record<string,string> = {generated:"Wygenerowana",regenerated:"Ponowna generacja",auto_fix:"Auto Fix",manual_edit:"Ręczna edycja",legacy:"Wersja archiwalna"};

export function ArticleWorkspace({article, versions, selecting, editingArticle, saving, editingBlocked, onSelect, onEdit, onSave, onCancel}: {
  article: Article; versions: ArticleSummary[]; selecting: boolean; editingArticle: Article | null; saving: boolean; editingBlocked: boolean;
  onSelect: (id:number)=>Promise<void>; onEdit:()=>void; onSave:(data:ArticleUpdate)=>Promise<void>; onCancel:()=>void;
}) {
  const [viewState,setViewState]=useState<{articleId:number;view:"text"|"history"|"content"|"seo"}>({articleId:article.id,view:"text"});
  const view=viewState.articleId===article.id?viewState.view:"text";
  const setView=(next:"text"|"history"|"content"|"seo")=>setViewState({articleId:article.id,view:next});
  const editing=Boolean(editingArticle);
  useEffect(()=>{
    const show=()=>setViewState({articleId:article.id,view:"text"});
    window.addEventListener(`article-${article.id}-reveal`,show);
    window.addEventListener("article-workspace-read",show);
    return()=>{window.removeEventListener(`article-${article.id}-reveal`,show);window.removeEventListener("article-workspace-read",show);};
  },[article.id]);
  async function copy(){
    try { await navigator.clipboard.writeText(`# ${article.title}\n\n${article.lead}\n\n${article.content}`);toast.success("Skopiowano tekst wybranej wersji"); }
    catch { toast.error("Nie udało się skopiować tekstu. Zaznacz go w podglądzie."); }
  }
  return <section tabIndex={-1} id="article-workspace" aria-labelledby="article-workspace-title" aria-busy={selecting} className="min-w-0 scroll-mt-36">
    <header className="space-y-4 border-b pb-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h2 id="article-workspace-title" className="text-lg font-semibold">Wybrany artykuł</h2>
          </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={selecting||editing} onClick={()=>void copy()}><CopyIcon />Kopiuj Markdown</Button>
          <Button variant="outline" size="sm" disabled={selecting||editing||editingBlocked} title={editingBlocked?"Poczekaj na zakończenie zadania przed edycją.":undefined} onClick={onEdit}><PencilIcon />Edytuj tekst</Button>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <FilterSelect label="Wersja wybranego artykułu" allowAll={false} value={String(article.id)} disabled={selecting||editing}
          options={versions.map(v=>({value:String(v.id),label:`Wersja ${v.version}${v.is_current?" · najnowsza":""}${v.status==="approved"?" · zatwierdzona":""}`}))}
          onChange={value=>value&&void onSelect(Number(value))} />
        <span className={cn("rounded-full px-3 py-1 text-xs font-medium",article.status==="approved"||article.status==="ready_for_approval"?"bg-emerald-50 text-emerald-800":"bg-muted text-foreground")}>{ARTICLE_STATUS_LABELS[article.status]}</span>
        <span className="text-sm text-muted-foreground">{article.word_count} słów · około {Math.max(1,Math.ceil(article.word_count/200))} min czytania · {ORIGIN[article.created_by]??article.created_by}</span>
        
      </div>
      <p role="status" aria-live="polite" className="sr-only">{editingArticle?`Edytujesz wersję ${editingArticle.version}. Formularz pozostaje przypięty do tej wersji, również podczas pracy w tle.`:selecting?"Wczytywanie wybranej wersji…":`Wyświetlana wersja ${article.version}${article.is_current?" · najnowsza":" · historyczna"}. Zmiana wersji zmienia również cel QA i Auto Fix.`}</p>
      {!editing&&<div aria-label="Widok artykułu" className="flex flex-wrap gap-2">
        <Button size="sm" variant={view==="text"?"secondary":"ghost"} aria-pressed={view==="text"} onClick={()=>setView("text")}><FileTextIcon />Podgląd</Button>
        <Button size="sm" variant={view==="content"?"secondary":"ghost"} aria-pressed={view==="content"} onClick={()=>setView("content")}>Treść</Button>
        <Button size="sm" variant={view==="seo"?"secondary":"ghost"} aria-pressed={view==="seo"} onClick={()=>setView("seo")}>SEO</Button>
        <Button size="sm" variant={view==="history"?"secondary":"ghost"} aria-pressed={view==="history"} onClick={()=>setView("history")}>Historia wersji ({versions.length})</Button>

      </div>}
    </header>
    <div className="pt-6">
      {editingArticle?<div className="space-y-4"><div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
        <h3 id="article-editor-heading" tabIndex={-1} className="font-semibold outline-none">Edytujesz wersję {editingArticle.version}</h3>
        <p>Zapis utworzy nową wersję wymagającą nowego QA. Oryginalny tekst i jego raport pozostaną w historii.</p></div>
        <ArticleEditor key={editingArticle.id} article={editingArticle} saving={saving} onSave={onSave} onCancel={onCancel}/></div>:
        view==="text"?<ArticleBody article={article}/>:view==="seo"?<SEOPreview article={article}/>:view==="content"?<pre className="overflow-auto whitespace-pre-wrap break-words rounded-xl bg-slate-50 p-5 text-sm leading-7">{`# ${article.title}\n\n${article.lead}\n\n${article.content}`}</pre>:<div className="space-y-3">
          <h3 className="font-semibold">Historia wersji</h3>
          <p className="text-sm text-muted-foreground">Wybierz wersję, aby przeczytać jej tekst i zobaczyć przypisane raporty.</p>
          <div className="overflow-x-auto"><table className="w-full text-left text-sm"><caption className="sr-only">Wersje artykułu, źródło zmiany, QA i status</caption>
            <thead><tr className="text-xs text-muted-foreground">{["Wersja","Pochodzenie","QA","Status"].map(h=><th key={h} scope="col" className="p-3">{h}</th>)}</tr></thead>
            <tbody>{versions.map(v=><tr key={v.id} className={cn("border-t",v.id===article.id&&"bg-muted/40")}>
              <td className="p-3"><button disabled={selecting} aria-current={v.id===article.id?"true":undefined} className="min-h-9 rounded px-2 font-medium underline underline-offset-4 focus-visible:outline-2" onClick={()=>void onSelect(v.id)}>Wersja {v.version}{v.id===article.id?" · wybrana":""}{v.is_current?" · najnowsza":""}</button></td>
              <td className="p-3">{ORIGIN[v.created_by]??v.created_by}</td><td className="p-3">{v.qa_score!=null?`${v.qa_score}/100`:"QA wymagane"}</td><td className="p-3">{ARTICLE_STATUS_LABELS[v.status]}</td>
            </tr>)}</tbody></table></div></div>}
    </div>
  </section>;
}

function ArticleBody({ article }: { article: Article }) {
  return (
    <div className="space-y-8">
      <ArticlePreview article={article} />

      <details className="min-w-0 rounded-lg border bg-muted/10 p-4 text-sm"><summary className="cursor-pointer font-semibold">Brief, SEO i dowody</summary><aside className="mt-5 space-y-6">
        {article.validation_warnings.length > 0 && (
          <section className="space-y-2 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
            <p className="flex items-center gap-1.5 font-medium text-amber-900">
              
              Ostrzeżenia generowania
            </p>
            <ul className="list-disc space-y-1 pl-5 text-xs text-amber-900">
              {article.validation_warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="space-y-2">
          <h3 className="font-semibold">Informacje o wersji</h3>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <Stat label="Słowa" value={article.word_count.toLocaleString("pl-PL")} />
            <Stat label="Sekcje" value={article.sections_count} />
            <Stat label="Wykorzystane fakty" value={`${article.facts_used_count} / ${article.facts_available_count}`} />
            <Stat label="Źródła" value={article.source_count} />
            <Stat label="Format" value={articleFormatLabel(article.article_format ?? legacyArticleFormat(article.article_type))} />
            <Stat label="Utworzono" value={formatDate(article.created_at)} />
            <Stat label="Ręczna edycja" value={article.is_edited ? "tak" : "nie"} />
          </dl>
        </section>

        {article.brief && <section className="space-y-2">
          <h3 className="font-semibold">Brief i plan tekstu</h3>
          {typeof article.brief.primary_angle === "string" && <p className="text-xs">{article.brief.primary_angle}</p>}
          {typeof article.brief.target_audience === "string" && <p className="text-xs text-muted-foreground">Odbiorcy: {article.brief.target_audience}</p>}
          {Array.isArray(article.brief.section_plan) && article.brief.section_plan.length > 0 && <ol className="list-decimal space-y-1 pl-5 text-xs">
            {article.brief.section_plan.map((item:{heading:string;purpose?:string},index:number)=><li key={index}><span className="font-medium">{item.heading}</span>{item.purpose&&<p className="text-muted-foreground">{item.purpose}</p>}</li>)}
          </ol>}
        </section>}

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
          <h3 className="font-semibold">Wykorzystane fakty i źródła</h3>
          <FactUsage article={article} />
        </section>
      </aside></details>
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
