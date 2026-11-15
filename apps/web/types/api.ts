export type CandidateStatus = "pending" | "approved" | "ignored";
export type CandidateWorkflowStatus = CandidateStatus | "draft" | "published" | "scheduled";

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
  is_demo?: boolean;
  id: number;
  source_id: number;
  source_name: string;
  external_url: string;
  title: string;
  summary: string | null;
  original_published_at: string | null;
  status: CandidateStatus;
  workflow_status?: CandidateWorkflowStatus | null;
  relevance_score: number | null;
  freshness_score: number | null;
  search_potential_score: number | null;
  commercial_potential_score: number | null;
  total_score: number | null;
  category: CandidateCategory | null;
  llm_reason: string | null;
  llm_model?: string | null;
  llm_input_tokens?: number | null;
  llm_output_tokens?: number | null;
  estimated_cost_usd?: string | null;
  classified_at: string | null;
  created_at: string;
  updated_at: string;
  group_size?: number;
  topic_group_id?: number | null;
  duplicate_similarity?: number | null;
  editor_take?: string | null;
  covered_by?: CoveredBy | null;
  topic_group?: { primary_id: number; members: { id: number; title: string; external_url: string; source_name: string }[] } | null;
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
  workflow_status?: CandidateWorkflowStatus;
  category?: CandidateCategory;
  source_id?: number;
  min_score?: number;
  max_score?: number;
  sort?: CandidateSort;
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
  duplicates?: 1;
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
  job_ids: string[];
  enqueued: number;
  existing: number;
  skipped_busy: number;
  skipped_budget: number;
}

export interface EditorialSuggestion {
  id: number;
  candidate_id: number;
  kind: "style_rule" | "banned_phrase";
  text: string;
  why: string;
  status: "pending" | "accepted" | "dismissed";
  created_at: string;
}

export interface CostReport {
  month: string;
  total_usd: string;
  unknown_cost_calls: number;
  by_kind: { kind: string; jobs: number; cost_usd: string }[];
  by_stage: { stage: string; calls: number; cost_usd: string }[];
  articles: { topics: number; cost_usd: string; average_usd: string | null };
}

export interface Usage {
  period_start: string;
  spent_usd: string;
  budget_usd: string | null;
  remaining_usd: string | null;
  exceeded: boolean;
  unknown_cost_calls: number;
}

export interface EditorialProfile { audience: string; voice: string; topics_scope: string; banned_phrases: string[]; example_post: string; style_rules: string[] }

export const AUTOMATION_INTERVALS = [15, 30, 60, 120, 360, 720, 1440] as const;
export interface AutomationRunResult { new_candidates: number; enqueued: number; errors: number; budget_exceeded: boolean }
export interface AutomationSettings {
  auto_fetch_enabled: boolean;
  auto_fetch_interval_minutes: number;
  auto_classify_enabled: boolean;
  auto_classify_batch_limit: number;
  last_auto_run_at: string | null;
  last_auto_run_result: AutomationRunResult | null;
  next_auto_run_at: string | null;
  paused_at: string | null;
  automation_enabled_globally: boolean;
}
export type AutomationUpdate = Partial<Pick<AutomationSettings,
  "auto_fetch_enabled" | "auto_fetch_interval_minutes" | "auto_classify_enabled" | "auto_classify_batch_limit">>;

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
  origin: "original" | "search" | "manual" | "sibling";
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
  basis?: "verifiable" | "vendor_claim" | "secondary" | null;
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

export type ArticleStatus = "draft" | "review" | "approved" | "rejected" | "needs_changes" | "ready_for_approval" | "manual_review_required" | "superseded";
export type ArticleLength = "auto" | "short" | "standard" | "long";
export type ArticleFormat = "news" | "explainer" | "case_study" | "guide" | "comparison";

export interface GenerateArticleRequest {
  article_format?: ArticleFormat | "auto" | null;
  article_type?: CandidateCategory | null;
  length?: ArticleLength;
  angle?: string | null;
  instructions?: string | null;
  refresh?: boolean;
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

export interface CoveredBy {
  type: "post" | "article";
  title: string;
  url?: string | null;
  post_id?: number | null;
  article_id?: number;
  similarity: number;
}

export interface RefreshOf { post_id: number; url: string | null; title: string }

export interface ArticleSummary {
  refresh_of?: RefreshOf | null;
  id: number;
  candidate_id: number;
  version: number;
  is_current: boolean;
  status: ArticleStatus;
  title: string;
  article_type: CandidateCategory;
  article_format: ArticleFormat;
  word_count: number;
  parent_version_id: number | null;
  created_by: "generated" | "regenerated" | "auto_fix" | "manual_edit" | "legacy";
  creation_reason: string | null;
  content_hash: string;
  auto_fix_iterations_remaining: number;
  auto_fix_iteration: number;
  approved_at: string | null;
  approved_by: string | null;
  rejection_reason: string | null;
  qa_score: number | null;
  qa_status: string | null;
  qa_passed: boolean;
  is_edited: boolean;
  estimated_cost_usd: string | null;
  llm_model: string | null;
  created_at: string;
  updated_at: string;
}

export interface Article extends ArticleSummary {
  seo_data?: Partial<WordPressProfile>;
  seo_preview?: Partial<WordPressProfile>;
  seo_origin?: "article" | "publication_profile" | "fallback";
  research_id: number | null;
  slug: string;
  lead: string;
  content: string;
  generated_content: string;
  meta_title: string;
  meta_description: string;
  angle: string | null;
  brief: {
    article_format?: ArticleFormat;
    section_plan?: { heading: string; purpose: string; fact_ids: number[]; target_words: number; presentation?: string }[];
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

export interface ModelPricing {
  models: { classifier: string; research: string; brief: string; writer: string; qa: string; auto_fix: string; embedding: string };
  rates: Record<string, { input: number; output: number; cached_input?: number; long_context_threshold?: number; long_input?: number; long_output?: number; long_cached_input?: number }>;
  source_url: string;
  verified_at: string;
}

// Status zadania pochodzi z bazy. Zamknięcie przeglądarki nie zatrzymuje workera.
export type JobStatus = "queued" | "running" | "retrying" | "succeeded" | "failed" | "cancelled";
export interface Job {
  id: string;
  candidate_id: number;
  candidate_title?: string | null;
  kind: "classify" | "research" | "write" | "qa_article" | "auto_fix_article" | "prepare_wordpress" | "publish_wordpress" | "learn_feedback";
  article_id?: number | null;
  status: JobStatus;
  stage: string | null;
  attempt_count: number;
  max_attempts: number;
  available_at: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result_id: number | null;
  result_type: string | null;
  error_code: string | null;
  error_message: string | null;
  cancel_requested_at?: string | null;
}
export interface JobPage { items: Job[]; total: number; page: number; page_size: number }
export interface JobAttempt {
  number: number;
  started_at: string;
  finished_at: string | null;
  outcome: string;
  error_message: string | null;
  llm_calls: { stage: string; finished: boolean; estimated_cost_usd: string | null;
    usage?: { model?: string; input_tokens: number; output_tokens: number; recorded?: boolean; provider?: string; search_credits?: number } | null }[];
}

export interface QueueQuery {
  status?: JobStatus | "all" | "active";
  kind?: Job["kind"];
  candidate_id?: number;
  page?: number;
  page_size?: number;
}
export type JobStats = Record<JobStatus | "total", number>;


export type QAIssueType = "unsupported_claim" | "contradiction" | "incorrect_number" | "incorrect_date" |
  "unsupported_quote" | "unsupported_name" | "source_mismatch" | "missing_uncertainty" |
  "ignored_conflict" | "title_mismatch" | "repetition" | "style_issue" | "structure_issue" |
  "seo_issue" | "overclaim" | "too_close_to_source" | "other";
export interface ArticleQAIssue {
  id: number; article_qa_id: number; type: QAIssueType;
  severity: "info" | "warning" | "high" | "critical";
  excerpt: string; reason: string; suggestion: string; section_heading: string | null;
  fact_ids: number[]; source_ids: number[]; auto_fixable: boolean;
  created_at: string; updated_at: string;
}
export interface ArticleQA {
  id: number; article_id: number; article_version: number; job_id: string | null;
  status: "pending" | "running" | "completed" | "failed";
  overall_score: number | null; factual_score: number | null; source_score: number | null;
  style_score: number | null; structure_score: number | null; seo_score: number | null;
  supported_claims_count: number; unsupported_claims_count: number;
  critical_issue_count: number; warning_count: number;
  summary: string | null; llm_model: string | null; llm_input_tokens: number | null;
  llm_output_tokens: number | null; estimated_cost_usd: string | null;
  qa_passed: boolean; pass_score: number; is_stale: boolean;
  issues: ArticleQAIssue[]; created_at: string; updated_at: string;
}

export interface ArticleFix {
  id: number; source_article_version_id: number; result_article_version_id: number | null;
  qa_id: number; job_id: string | null; status: "pending" | "running" | "completed" | "failed";
  iteration: number; issues_requested: number; issues_fixed: number; issues_skipped: number;
  summary: string | null; change_ratio: string | null; warnings: string[];
  changes: {field: string; before: string; after: string; qa_issue_ids: number[]; fact_ids: number[]; source_ids: number[]}[];
  llm_model: string | null; llm_input_tokens: number | null; llm_output_tokens: number | null;
  estimated_cost_usd: string | null; created_at: string; updated_at: string;
  issues: {id: number; qa_issue_id: number; status: "fixed" | "skipped" | "failed"; reason: string; created_at: string}[];
}

export interface WordPressProfile {
  title: string; slug: string; seo_title: string; meta_description: string;
  excerpt: string; canonical_url: string | null; focus_keyword: string;
  secondary_keywords: string[]; og_title: string; og_description: string;
  twitter_title: string; twitter_description: string; robots_index: boolean; robots_follow: boolean;
  schema_type: string; category: string; tags: string[]; author_id: number | null;
  featured_image_url: string | null; featured_image_asset: string | null;
}
export interface WordPressPublication {
  id: number; article_version_id: number; wordpress_post_id: number | null;
  wordpress_url: string | null; status: string; wp_status: string | null;
  last_synced_at: string | null; scheduled_at: string | null; warnings: string[]; error_code: string | null;
}
export interface WordPressState {
  remote_status: string | null;
  publication: WordPressPublication | null; profile: WordPressProfile;
  checks: {name:string; status:string; value?:string|number}[];
  categories: string[]; qa_ok: boolean; newer_approved_version_id: number | null;
  conflict: {current_hash:string;post_id:number} | null; wordpress_admin_url: string | null;
  wordpress_connected: boolean;
}

export interface BlogMemory {
  count: number;
  synced_at: string | null;
}

export interface WordPressConnection {
  site_url: string;
  api_url: string | null;
  username: string;
  seo_plugin: "yoast" | "rankmath" | "none";
  default_status: "draft" | "future" | "publish";
  default_author_id: number | null;
  default_category_id: number | null;
  wp_user_id: number | null;
  wp_user_name: string | null;
  can_publish: boolean;
  last_checked_at: string | null;
  last_error: string | null;
}

export interface WordPressManualConnect {
  site_url: string;
  api_url?: string | null;
  username: string;
  app_password: string;
  confirm_site_change?: boolean;
}


export interface Credentials {
  email: string;
  password: string;
}

export interface Me {
  user: { id: number; email: string };
  workspace: { id: number; name: string };
}
