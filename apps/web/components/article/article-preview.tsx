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
  const seo = article.seo_preview && Object.keys(article.seo_preview).length ? article.seo_preview : article.seo_data;
  const rows: [string, string | undefined][] = [
    ["Meta title", `${article.meta_title} (${article.meta_title.length} znaków)`],
    ["Meta description", `${article.meta_description} (${article.meta_description.length} znaków)`],
    ["Slug", `/${article.slug}`],
  ];
  if (seo) rows.push(
    ["Zajawka (excerpt)", seo.excerpt], ["Główna fraza kluczowa", seo.focus_keyword],
    ["Dodatkowe frazy", seo.secondary_keywords?.join(", ")], ["Tagi", seo.tags?.join(", ")],
    ["Kategoria", seo.category], ["Typ danych strukturalnych", seo.schema_type],
    ["Tytuł w social media (OG)", seo.og_title || article.meta_title], ["Opis w social media (OG)", seo.og_description || article.meta_description],
    ["Tytuł na X/Twitterze", seo.twitter_title || article.meta_title], ["Opis na X/Twitterze", seo.twitter_description || article.meta_description],
    ["Indeksowanie", `${seo.robots_index === false ? "noindex" : "index"}, ${seo.robots_follow === false ? "nofollow" : "follow"}`],
  );
  return <section className="space-y-4 text-sm" aria-label="Dane SEO artykułu">
    <div className="rounded-xl bg-background p-5 ring-1 ring-foreground/8">
      <p className="text-xs text-muted-foreground">Podgląd w wynikach wyszukiwania</p>
      <p className="mt-3 break-all text-xs text-emerald-800 dark:text-emerald-400">/{article.slug}</p>
      <p className="mt-1 text-lg leading-snug text-sky-800 dark:text-sky-400">{article.meta_title}</p>
      <p className="mt-1 leading-6 text-muted-foreground">{article.meta_description}</p>
    </div>
    <dl className="divide-y rounded-xl bg-muted/40 px-4">
      {rows.map(([label, value]) => <div key={label} className="grid gap-1 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
        <dt className="font-medium text-muted-foreground">{label}</dt><dd className="break-words">{value || "—"}</dd>
      </div>)}
    </dl>
    <p className="text-xs text-muted-foreground">{article.seo_origin === "publication_profile" ? "Ta starsza wersja korzysta z wcześniej przygotowanego profilu SEO. Nowe generacje zapisują SEO razem z artykułem. " : ""}Adres kanoniczny ustali WordPress po wysłaniu wpisu.</p>
  </section>;
}
