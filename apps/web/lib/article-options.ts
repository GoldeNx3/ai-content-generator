import type { ArticleFormat, GenerateArticleRequest } from "@/types/api";

export const FORMAT_OPTIONS = [
  { value: "auto", label: "Automatyczny — na podstawie researchu", description: "Brief dobierze formę do materiału, niezależnie od kategorii RSS." },
  { value: "news", label: "Krótka wiadomość", description: "Jedno wydarzenie i kilka istotnych informacji." },
  { value: "explainer", label: "Omówienie", description: "Wyjaśnienie produktu, zmiany lub technologii." },
  { value: "case_study", label: "Studium przypadku", description: "Rzeczywisty problem, decyzje, przeszkody i rezultat." },
  { value: "guide", label: "Poradnik", description: "Instrukcje do wykonania. Research musi zawierać rzeczywiste kroki." },
  { value: "comparison", label: "Porównanie", description: "Różnice między rozwiązaniami. Research musi zawierać porównywalne dane." },
] satisfies { value: ArticleFormat | "auto"; label: string; description: string }[];

export function legacyArticleFormat(category: string): ArticleFormat {
  if (category === "news" || category === "guide" || category === "comparison") return category;
  return "explainer";
}

export function articleFormatLabel(format: string): string {
  return FORMAT_OPTIONS.find((option) => option.value === format)?.label ?? format;
}

export function generationDefaults(defaults: GenerateArticleRequest): GenerateArticleRequest {
  return {
    ...defaults,
    article_format: defaults.article_format ?? (defaults.article_type ? legacyArticleFormat(defaults.article_type) : "auto"),
    length: defaults.length === "standard" ? "auto" : defaults.length ?? "auto",
  };
}
