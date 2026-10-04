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
  const seo = article.seo_data;
  return <section className="space-y-5 text-sm" aria-label="Dane SEO artykułu">
    <p className="text-muted-foreground">Dane SEO wygenerowane w kroku 4 razem z tą wersją artykułu. Canonical zostanie ustalony po wysłaniu do WordPressa.</p>
    <div className="rounded-xl border p-5"><p className="text-xs text-muted-foreground">Podgląd wyniku wyszukiwania</p><p className="mt-3 break-all text-xs text-emerald-800">/{article.slug}</p><p className="mt-2 text-xl text-sky-800">{article.meta_title}</p><p className="mt-2 leading-6 text-slate-600">{article.meta_description}</p></div>
    <dl className="space-y-4"><div><dt className="font-medium">Meta title · {article.meta_title.length} znaków</dt><dd className="mt-1 text-slate-600">{article.meta_title}</dd></div><div><dt className="font-medium">Meta description · {article.meta_description.length} znaków</dt><dd className="mt-1 text-slate-600">{article.meta_description}</dd></div><div><dt className="font-medium">Slug</dt><dd className="mt-1 break-all font-mono text-slate-600">{article.slug}</dd></div></dl>
    {seo && <dl className="space-y-4">{[
      ["Excerpt", seo.excerpt], ["Focus keyword", seo.focus_keyword],
      ["Secondary keywords", seo.secondary_keywords?.join(", ")], ["Tags", seo.tags?.join(", ")],
      ["Category", seo.category], ["Schema", seo.schema_type],
      ["OG title", seo.og_title || article.meta_title], ["OG description", seo.og_description || article.meta_description],
      ["Twitter/X title", seo.twitter_title || article.meta_title], ["Twitter/X description", seo.twitter_description || article.meta_description],
      ["Robots", `${seo.robots_index === false ? "noindex" : "index"}, ${seo.robots_follow === false ? "nofollow" : "follow"}`],
    ].map(([label,value]) => <div key={label}><dt className="font-medium">{label}</dt><dd className="mt-1 break-words text-slate-600">{value || "—"}</dd></div>)}</dl>}
  </section>;
}
