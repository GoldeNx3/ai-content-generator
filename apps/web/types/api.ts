export type CandidateStatus = "pending" | "approved" | "ignored";

export type CandidateCategory =
  | "news"
  | "guide"
  | "comparison"
  | "pricing"
  | "release"
  | "tool"
  | "other";

export const CANDIDATE_STATUSES: CandidateStatus[] = ["pending", "approved", "ignored"];

export const CANDIDATE_CATEGORIES: CandidateCategory[] = [
  "news",
  "guide",
  "comparison",
  "pricing",
  "release",
  "tool",
  "other",
];

export interface Source {
  id: number;
  name: string;
  type: "rss";
  url: string;
  active: boolean;
  last_fetched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Candidate {
  id: number;
  source_id: number;
  source_name: string;
  external_url: string;
  title: string;
  summary: string | null;
  original_published_at: string | null;
  status: CandidateStatus;
  relevance_score: number | null;
  freshness_score: number | null;
  search_potential_score: number | null;
  commercial_potential_score: number | null;
  total_score: number | null;
  category: CandidateCategory | null;
  llm_reason: string | null;
  classified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidatePage {
  items: Candidate[];
  total: number;
  page: number;
  page_size: number;
}

export type CandidateSort = "total_score" | "created_at" | "original_published_at";

export interface CandidateQuery {
  status?: CandidateStatus;
  category?: CandidateCategory;
  source_id?: number;
  min_score?: number;
  max_score?: number;
  sort?: CandidateSort;
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface FetchResult {
  sources_processed: number;
  items_found: number;
  new_candidates: number;
  duplicates: number;
  skipped_old: number;
  errors: number;
}

export interface ClassifyBatchResult {
  processed: number;
  classified: number;
  errors: number;
}

export interface DashboardStats {
  candidates_today: number;
  new_today: number;
  approved: number;
  ignored: number;
  average_score: number | null;
}

export type ResearchStatus = "pending" | "running" | "completed" | "failed";
export type FactImportance = "critical" | "important" | "supporting";
export type ResearchSourceType =
  | "official"
  | "documentation"
  | "github"
  | "news"
  | "blog"
  | "community"
  | "other";

export interface ResearchSource {
  id: number;
  url: string;
  origin: "original" | "search" | "manual";
  title: string | null;
  publisher: string | null;
  source_type: ResearchSourceType;
  source_score: number;
  published_at: string | null;
  extracted_content: string | null;
  fetch_status: "pending" | "success" | "failed";
  http_status: number | null;
  error: string | null;
  created_at: string;
}

export interface ResearchFact {
  id: number;
  claim: string;
  importance: FactImportance;
  confidence: number;
  source_ids: number[];
}

export interface ResearchUncertainty {
  claim: string;
  reason: string;
}

export interface ResearchConflict {
  topic: string;
  sources: { url: string; claim: string }[];
}

export interface Research {
  id: number;
  candidate_id: number;
  status: ResearchStatus;
  summary: string | null;
  why_it_matters: string | null;
  suggested_angle: string | null;
  search_queries: string[];
  uncertainties: ResearchUncertainty[];
  conflicts: ResearchConflict[];
  error: string | null;
  llm_model: string | null;
  llm_input_tokens: number;
  llm_output_tokens: number;
  estimated_cost_usd: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  sources: ResearchSource[];
  facts: ResearchFact[];
}

export type ArticleStatus = "draft" | "review" | "approved" | "rejected";
export type ArticleLength = "auto" | "short" | "standard" | "long";

export interface GenerateArticleRequest {
  article_type?: CandidateCategory | null;
  length?: ArticleLength;
  angle?: string | null;
  instructions?: string | null;
}

export interface ArticleSectionMeta {
  heading: string | null;
  content: string;
  used_fact_ids: number[];
  source_ids: number[];
  is_conclusion?: boolean;
}

export interface SnapshotFact {
  id: number;
  claim: string;
  importance: FactImportance;
  confidence: number;
  source_ids: number[];
}

export interface SnapshotSource {
  id: number;
  url: string;
  title: string | null;
  publisher: string | null;
  source_type: ResearchSourceType;
  source_score: number;
}

export interface ArticleSummary {
  id: number;
  candidate_id: number;
  version: number;
  is_current: boolean;
  status: ArticleStatus;
  title: string;
  article_type: CandidateCategory;
  word_count: number;
  is_edited: boolean;
  estimated_cost_usd: string | null;
  llm_model: string | null;
  created_at: string;
  updated_at: string;
}

export interface Article extends ArticleSummary {
  research_id: number | null;
  slug: string;
  lead: string;
  content: string;
  generated_content: string;
  meta_title: string;
  meta_description: string;
  angle: string | null;
  brief: {
    primary_angle: string;
    target_audience: string;
    key_points: string[];
    required_facts: number[];
    optional_facts: number[];
    uncertainties_to_avoid: string[];
    conflicts_to_mention: string[];
    desired_length_words: number;
  };
  sections: ArticleSectionMeta[];
  lead_fact_ids: number[];
  generation_options: GenerateArticleRequest;
  research_snapshot: { facts: SnapshotFact[]; sources: SnapshotSource[] };
  validation_warnings: string[];
  sections_count: number;
  facts_used_count: number;
  facts_available_count: number;
  source_count: number;
  llm_input_tokens: number;
  llm_output_tokens: number;
  brief_llm_model: string | null;
  brief_input_tokens: number;
  brief_output_tokens: number;
  brief_cost_usd: string | null;
  writer_input_tokens: number;
  writer_output_tokens: number;
  writer_cost_usd: string | null;
}

export type ArticleUpdate = Partial<Pick<Article, "title" | "lead" | "content" | "meta_title" | "meta_description">>;
