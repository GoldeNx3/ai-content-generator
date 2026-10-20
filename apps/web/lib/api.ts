import type {
  Credentials,
  Me,
  WordPressState, WordPressProfile,
  ArticleFix,
  ArticleQA,
  QueueQuery,
  JobStats,
  Job,
  JobPage,
  JobAttempt,
  ModelPricing,
  Article,
  ArticleStatus,
  ArticleSummary,
  ArticleUpdate,
  Candidate,
  CandidatePage,
  CandidateQuery,
  CandidateStatus,
  ClassifyBatchResult,
  DashboardStats,
  FetchResult,
  GenerateArticleRequest,
  Research,
  ResearchSource,
  Source,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: { code?: string; job_id?: string },
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api${path}`, {
      ...init,
      // Content-Type only with a body: a JSON header on GET forces a CORS preflight on every poll.
      headers: init.body ? { "Content-Type": "application/json", ...init.headers } : init.headers,
      cache: "no-store",
      // Ciasteczko sesji (HttpOnly) ustawia API; bez tego przeglądarka nie wyśle go cross-origin.
      credentials: "include",
    });
  } catch {
    throw new ApiError(`Cannot reach API at ${API_URL}`, 0);
  }

  // Wygasła/unieważniona sesja: wracamy na logowanie z powrotem na bieżącą stronę.
  // /auth/* obsługuje 401 samodzielnie (np. błędne hasło).
  if (response.status === 401 && !path.startsWith("/auth/") && typeof window !== "undefined") {
    redirectToLogin();
  }
  if (!response.ok) {
    const parsed = await errorMessage(response);
    throw new ApiError(parsed.message, response.status, parsed.detail);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function redirectToLogin() {
  const next = window.location.pathname + window.location.search + window.location.hash;
  // Celowo pełne przeładowanie: zrzuca stan klienta (polling, cache) po zmianie sesji.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

const AUTH_MESSAGES: Record<string, string> = {
  invalid_credentials: "Nieprawidłowy email lub hasło.",
  email_taken: "Konto z tym adresem już istnieje.",
  too_many_attempts: "Zbyt wiele nieudanych logowań. Spróbuj ponownie za kilkanaście minut.",
  too_many_registrations: "Z tego adresu IP założono już limit kont na tę godzinę. Spróbuj później.",
  registration_disabled: "Rejestracja jest wyłączona.",
  origin_not_allowed: "Żądanie z niedozwolonej domeny.",
  not_authenticated: "Sesja wygasła. Zaloguj się ponownie.",
};

async function errorMessage(response: Response): Promise<{ message: string; detail?: { code?: string; job_id?: string } }> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return { message: detail };
      if (detail && typeof detail === "object" && "code" in detail) {
        const conflict = detail as { code: string; job_id?: string };
        const message = conflict.code === "candidate_busy" ? "Dla tego tematu trwa już inne zadanie." : AUTH_MESSAGES[conflict.code] ?? conflict.code;
        return { message, detail: conflict };
      }
      if (Array.isArray(detail)) {
        return { message: detail
          .map((item: { msg?: string }) => item.msg ?? JSON.stringify(item))
          .join("; ") };
      }
    }
  } catch {
    // non-JSON error body
  }
  return { message: `Request failed with status ${response.status}` };
}

function toQueryString(query: CandidateQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

const patch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });

// Po błędzie sieci ponowienie używa tego samego klucza: serwer zwróci istniejące zadanie.
// Klucz jest usuwany dopiero po jednoznacznej odpowiedzi serwera.
const pendingKeys = new Map<string, string>();
async function enqueue<T>(path: string, body?: unknown): Promise<T> {
  const action = JSON.stringify([path, body]);
  const storageKey = `content-engine:request:${action}`;
  const key = pendingKeys.get(action) ?? sessionStorage.getItem(storageKey) ?? crypto.randomUUID();
  pendingKeys.set(action, key);
  sessionStorage.setItem(storageKey, key);
  try {
    const result = await request<T>(path, { method: "POST", headers: { "Idempotency-Key": key },
      body: body === undefined ? undefined : JSON.stringify(body) });
    pendingKeys.delete(action);
    sessionStorage.removeItem(storageKey);
    return result;
  } catch (error) {
    if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
      pendingKeys.delete(action);
      sessionStorage.removeItem(storageKey);
      if (error.detail?.code === "job_already_active" && error.detail.job_id) {
        return request<T>(`/jobs/${error.detail.job_id}`);
      }
    }
    throw error;
  }
}

// Klucze idempotencji należą do sesji użytkownika; po wylogowaniu nie mogą przejść na kolejne konto.
function clearPendingRequests() {
  pendingKeys.clear();
  for (const key of Object.keys(sessionStorage)) {
    if (key.startsWith("content-engine:request:")) sessionStorage.removeItem(key);
  }
}

export const api = {
  me: () => request<Me>("/auth/me"),
  login: (body: Credentials) => post<Me>("/auth/login", body),
  register: (body: Credentials) => post<Me>("/auth/register", body),
  logout: async () => {
    try {
      await post<void>("/auth/logout");
    } finally {
      clearPendingRequests();
    }
  },
  getWordPress: (id:number) => request<WordPressState>(`/article-versions/${id}/wordpress`),
  prepareWordPress: (id:number) => enqueue<Job>(`/article-versions/${id}/wordpress/prepare`),
  setWordPressSettings: (id:number, data:Partial<WordPressProfile>) => patch<WordPressState>(`/article-versions/${id}/wordpress/settings`,data),
  publishWordPress: (id:number, body:{status:"draft"|"future"|"publish";scheduled_at?:string}) => enqueue<Job>(`/article-versions/${id}/wordpress`,body),
  syncWordPress: (id:number, body:{expected_wp_hash?:string}={}) => enqueue<Job>(`/article-versions/${id}/wordpress/sync`,body),
  testWordPress: () => post<{ok:boolean;user_id:number;capabilities:{seo_plugin:string;timezone:string}}>("/wordpress/test-connection"),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  listJobs: (candidateId: number) => request<JobPage>(`/candidates/${candidateId}/jobs`),
  queueStats: () => request<JobStats>("/jobs/stats"),
  queueJobs: (query: QueueQuery) => {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) if (value !== undefined) params.set(key, String(value));
    return request<JobPage>(`/jobs?${params}`);
  },
  activeJobs: () => request<JobPage>("/jobs?status=active&page_size=100"),
  jobAttempts: (id: string) => request<JobAttempt[]>(`/jobs/${id}/attempts`),
  retryJob: (id: string) => enqueue<Job>(`/jobs/${id}/retry`),
  pricing: () => request<ModelPricing>("/pricing"),
  stats: () => request<DashboardStats>("/stats"),

  listSources: () => request<Source[]>("/sources"),
  createSource: (data: { name: string; url: string }) => post<Source>("/sources", data),
  updateSource: (id: number, data: Partial<Pick<Source, "name" | "url" | "active">>) =>
    patch<Source>(`/sources/${id}`, data),
  deleteSource: (id: number) => request<void>(`/sources/${id}`, { method: "DELETE" }),
  fetchAllSources: () => post<FetchResult>("/sources/fetch"),
  fetchSource: (id: number) => post<FetchResult>(`/sources/${id}/fetch`),

  listCandidates: (query: CandidateQuery) =>
    request<CandidatePage>(`/candidates${toQueryString(query)}`),
  getCandidate: (id: number) => request<Candidate>(`/candidates/${id}`),
  classifyCandidate: (id: number) => enqueue<Job>(`/candidates/${id}/classify`),
  classifyPending: () => enqueue<ClassifyBatchResult>("/candidates/classify-pending"),
  updateCandidateStatus: (id: number, status: CandidateStatus) =>
    patch<Candidate>(`/candidates/${id}/status`, { status }),

  /** Returns null when the candidate has no research yet. */
  getResearch: async (candidateId: number): Promise<Research | null> => {
    try {
      return await request<Research>(`/candidates/${candidateId}/research`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },
  startResearch: (candidateId: number) => enqueue<Job>(`/candidates/${candidateId}/research`),
  retryResearch: (candidateId: number) => enqueue<Job>(`/candidates/${candidateId}/research/retry`),
  addResearchSource: (candidateId: number, url: string) =>
    post<ResearchSource>(`/candidates/${candidateId}/research/sources`, { url }),

  generateArticle: (candidateId: number, options: GenerateArticleRequest) =>
    enqueue<Job>(`/candidates/${candidateId}/article`, options),
  listArticles: (candidateId: number) => request<ArticleSummary[]>(`/candidates/${candidateId}/articles`),
  autoFix: (id: number, issueIds?: number[]) => enqueue<Job>(`/article-versions/${id}/auto-fix`, issueIds ? {issue_ids: issueIds} : {}),
  getFix: (id: number) => request<ArticleFix>(`/article-fixes/${id}`),
  listFixes: (id: number) => request<ArticleFix[]>(`/article-versions/${id}/fixes`),
  approveVersion: (id: number) => request<Article>(`/article-versions/${id}/approve`, {method: "POST"}),
  rejectVersion: (id: number, reason?: string) => request<Article>(`/article-versions/${id}/reject`, {method: "POST", body: JSON.stringify({reason})}),
  runQA: (id: number) => enqueue<Job>(`/articles/${id}/qa`),
  retryQA: (id: number) => enqueue<Job>(`/articles/${id}/qa/retry`),
  getQA: async (id: number): Promise<ArticleQA | null> => {
    try { return await request<ArticleQA>(`/articles/${id}/qa`); }
    catch (error) { if (error instanceof ApiError && error.status === 404) return null; throw error; }
  },
  getArticle: (id: number) => request<Article>(`/articles/${id}`),
  regenerateArticle: (id: number, options: GenerateArticleRequest) =>
    enqueue<Job>(`/articles/${id}/regenerate`, options),
  updateArticle: (id: number, data: ArticleUpdate) => patch<Article>(`/articles/${id}`, data),
  updateArticleStatus: (id: number, status: ArticleStatus) =>
    patch<Article>(`/articles/${id}/status`, { status }),
};

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}
