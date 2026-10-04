"use client";

import type { Article } from "@/types/api";
import { Markdown } from "./markdown";

export function ArticlePreview({ article, anchorPrefix }: { article: Article; anchorPrefix?: string }) {
  return <article className="mx-auto min-w-0 max-w-prose">
    <h2 className="text-3xl font-semibold tracking-tight text-balance">{article.title}</h2>
    <p className="mt-5 text-lg font-medium leading-8 text-slate-700">{article.lead}</p>
    <div className="mt-5 text-[15px]"><Markdown anchorPrefix={anchorPrefix ?? `article-${article.id}`}>{article.content}</Markdown></div>
  </article>;
}

export function SEOPreview({ article }: { article: Article }) {
  return <section className="space-y-5 text-sm" aria-label="Dane SEO artykułu">
    <div className="rounded-xl border p-5"><p className="text-xs text-muted-foreground">Podgląd wyniku wyszukiwania</p><p className="mt-3 break-all text-xs text-emerald-800">/{article.slug}</p><p className="mt-2 text-xl text-sky-800">{article.meta_title}</p><p className="mt-2 leading-6 text-slate-600">{article.meta_description}</p></div>
    <dl className="space-y-4"><div><dt className="font-medium">Meta title · {article.meta_title.length} znaków</dt><dd className="mt-1 text-slate-600">{article.meta_title}</dd></div><div><dt className="font-medium">Meta description · {article.meta_description.length} znaków</dt><dd className="mt-1 text-slate-600">{article.meta_description}</dd></div><div><dt className="font-medium">Slug</dt><dd className="mt-1 break-all font-mono text-slate-600">{article.slug}</dd></div></dl>
  </section>;
}
