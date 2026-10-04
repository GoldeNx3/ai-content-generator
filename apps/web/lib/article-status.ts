import type { ArticleStatus } from "@/types/api";
export const ARTICLE_STATUS_LABELS: Record<ArticleStatus, string> = {
  draft: "Szkic · QA wymagane", review: "W weryfikacji", approved: "Zatwierdzony", rejected: "Odrzucony",
  needs_changes: "Wymaga zmian", ready_for_approval: "Gotowy do zatwierdzenia",
  manual_review_required: "Wymaga ręcznej weryfikacji", superseded: "Zastąpiony",
};
