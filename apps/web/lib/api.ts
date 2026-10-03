import type {
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
    });
  } catch {
    throw new ApiError(`Cannot reach API at ${API_URL}`, 0);
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return detail
          .map((item: { msg?: string }) => item.msg ?? JSON.stringify(item))
          .join("; ");
      }
    }
  } catch {
    // non-JSON error body
  }
  return `Request failed with status ${response.status}`;
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

export const api = {
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
  classifyCandidate: (id: number) => post<Candidate>(`/candidates/${id}/classify`),
  classifyPending: () => post<ClassifyBatchResult>("/candidates/classify-pending"),
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
  startResearch: (candidateId: number) => post<Research>(`/candidates/${candidateId}/research`),
  retryResearch: (candidateId: number) => post<Research>(`/candidates/${candidateId}/research/retry`),
  addResearchSource: (candidateId: number, url: string) =>
    post<ResearchSource>(`/candidates/${candidateId}/research/sources`, { url }),

  generateArticle: (candidateId: number, options: GenerateArticleRequest) =>
    post<Article>(`/candidates/${candidateId}/article`, options),
  listArticles: (candidateId: number) => request<ArticleSummary[]>(`/candidates/${candidateId}/articles`),
  getArticle: (id: number) => request<Article>(`/articles/${id}`),
  regenerateArticle: (id: number, options: GenerateArticleRequest) =>
    post<Article>(`/articles/${id}/regenerate`, options),
  updateArticle: (id: number, data: ArticleUpdate) => patch<Article>(`/articles/${id}`, data),
  updateArticleStatus: (id: number, status: ArticleStatus) =>
    patch<Article>(`/articles/${id}/status`, { status }),
};

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}
