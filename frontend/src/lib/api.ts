import { DEFAULT_MODEL_ID } from "@/types";
import { readServerEvents } from "./sse";
import type { AnalysisProgress } from "./analysis-progress";
import { API_ENDPOINTS, joinApiUrl } from "./constants";
import { getChatApiSessionId, isValidChatApiSessionId } from "./chat-session";
import type {
  AskQuestionRequest,
  AskQuestionResponse,
  UploadResponse,
  StatusResponse,
  APIError,
  RuntimeSummary,
  FetchedPaper,
  PaperSearchResponse,
  IngestPapersResponse,
  AnalyzeGapsResponse,
  ChatFollowupResponse,
} from "@/types";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || message;
  }
}

function withSessionHeaders(init?: RequestInit): RequestInit {
  const sid = getChatApiSessionId();
  if (!isValidChatApiSessionId(sid)) {
    throw new ApiError(
      "Chat session id is missing or invalid. Use a modern browser with Web Crypto enabled.",
      400,
      "missing_session_id",
    );
  }
  const merged: Record<string, string> = { "X-Chat-Session-Id": sid };
  const inHeaders = init?.headers;
  if (inHeaders instanceof Headers) {
    inHeaders.forEach((v, k) => {
      if (k.toLowerCase() !== "x-chat-session-id") merged[k] = v;
    });
  } else if (inHeaders && typeof inHeaders === "object") {
    for (const [k, v] of Object.entries(inHeaders as Record<string, string>)) {
      if (k.toLowerCase() !== "x-chat-session-id" && v !== undefined) {
        merged[k] = String(v);
      }
    }
  }
  return { ...init, headers: merged };
}

async function fetchWithErrorHandling<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  try {
    const response = await fetch(url, withSessionHeaders({ ...options, signal: options?.signal ?? AbortSignal.timeout(180000) }));

    if (!response.ok) {
      const errorData: APIError = await response.json().catch(() => ({
        detail: `HTTP error ${response.status}`,
      }));
      const detail = typeof errorData.detail === "string" ? errorData.detail
        : Array.isArray(errorData.detail) ? (errorData.detail as { msg?: string }[]).map(item => item.msg || "Invalid input").join("; ").slice(0, 500)
        : `HTTP error ${response.status}`;
      throw new ApiError(detail, response.status, detail);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      "Network error. Please check if the backend server is running.",
      0,
      "Connection failed",
    );
  }
}

export interface StreamCallbacks {
  onToken: (text: string) => void;
  onDone: (meta: {
    answer?: string;
    model_used?: string;
    processing_time?: number;
    sources?: string[];
  }) => void;
  onError: (message: string) => void;
  onStatus?: (stage: string, message: string) => void;
}

export function streamQuestion(
  request: AskQuestionRequest,
  callbacks: StreamCallbacks,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(
        joinApiUrl(API_ENDPOINTS.ASK_STREAM),
        withSessionHeaders({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
          signal: controller.signal,
        }),
      );

      if (!response.ok || !response.body) {
        const err = await response.json().catch(() => ({ detail: "Stream failed" }));
        callbacks.onError(err.detail ?? "Stream failed");
        return;
      }

      for await (const { event, data } of readServerEvents(response.body)) {
        if (event === "token") callbacks.onToken(data.content ?? "");
        if (event === "status") callbacks.onStatus?.(data.stage, data.message);
        if (event === "done") { callbacks.onDone(data); return; }
        if (event === "error") { callbacks.onError(data.message ?? "Unknown error"); return; }
      }
      callbacks.onError("The response stream was interrupted. Please retry.");
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError((err as Error).message ?? "Stream failed");
      }
    }
  })();

  return controller;
}

export const api = {
  async runAnalysis(
    input: { topic: string; provider: string; model: string; paperIds: string[]; files: File[] },
    onProgress: (progress: Partial<AnalysisProgress>) => void,
    signal: AbortSignal,
  ): Promise<{ report: string; progress: Partial<AnalysisProgress> }> {
    const form = new FormData();
    form.set("topic", input.topic);
    form.set("provider", input.provider);
    form.set("model_name", input.model);
    form.set("paper_ids", JSON.stringify(input.paperIds));
    input.files.forEach((file) => form.append("files", file));
    const response = await fetch(joinApiUrl("/api/analyze/stream"), withSessionHeaders({ method: "POST", body: form, signal }));
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(typeof error.detail === "string" ? error.detail : "Unable to start analysis. Check your sources and retry.", response.status);
    }
    if (!response.body) throw new Error("The server did not provide a progress stream.");
    for await (const { event, data } of readServerEvents(response.body)) {
      if (event === "progress" || event === "heartbeat") onProgress(data);
      if (event === "error") throw new Error(data.message || "Analysis failed. Please retry.");
      if (event === "done") {
        if (typeof data.report !== "string" || !data.report.trim()) throw new Error("The analysis finished without a report.");
        return { report: data.report, progress: data };
      }
    }
    throw new Error("The analysis connection was interrupted. Please retry.");
  },
  async checkHealth(): Promise<StatusResponse> {
    return fetchWithErrorHandling<StatusResponse>(
      joinApiUrl(API_ENDPOINTS.HEALTH),
    );
  },

  async getStatus(): Promise<StatusResponse> {
    return fetchWithErrorHandling<StatusResponse>(
      joinApiUrl(API_ENDPOINTS.STATUS),
    );
  },

  async uploadPDFs(files: File[]): Promise<UploadResponse> {
    const formData = new FormData();
    files.forEach((f) => {
      formData.append("files", f);
    });

    return fetchWithErrorHandling<UploadResponse>(
      joinApiUrl(API_ENDPOINTS.UPLOAD),
      {
        method: "POST",
        body: formData,
      },
    );
  },

  async uploadPDF(file: File): Promise<UploadResponse> {
    return this.uploadPDFs([file]);
  },

  async askQuestion(
    question: string,
    model?: string,
    includeSources: boolean = true,
    hybridMode: boolean = false,
  ): Promise<AskQuestionResponse> {
    const requestBody: AskQuestionRequest = {
      question,
      include_sources: includeSources,
      hybrid_mode: hybridMode,
      knowledge_mode: hybridMode ? "hybrid" : "strict",
    };
    if (model) requestBody.model = model;

    return fetchWithErrorHandling<AskQuestionResponse>(
      joinApiUrl(API_ENDPOINTS.ASK),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      },
    );
  },

  async searchPapers(query: string, limitPerSource: number = 4): Promise<PaperSearchResponse> {
    return fetchWithErrorHandling<PaperSearchResponse>(
      joinApiUrl(API_ENDPOINTS.PAPER_SEARCH),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit_per_source: limitPerSource }),
      },
    );
  },

  async ingestPapers(fetchedPapers: FetchedPaper[]): Promise<IngestPapersResponse> {
    return fetchWithErrorHandling<IngestPapersResponse>(
      joinApiUrl(API_ENDPOINTS.PAPER_INGEST),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fetched_papers: fetchedPapers.map(({ id }) => ({ id })) }),
      },
    );
  },

  async analyzeGaps(
    topic: string,
    provider: string = "gemini",
    modelName: string = DEFAULT_MODEL_ID,
    apiKey?: string,
  ): Promise<AnalyzeGapsResponse> {
    return fetchWithErrorHandling<AnalyzeGapsResponse>(
      joinApiUrl(API_ENDPOINTS.ANALYZE_GAPS),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic,
          provider,
          model_name: modelName,
          api_key: apiKey,
        }),
      },
    );
  },

  async clearFollowup(): Promise<void> {
    await fetchWithErrorHandling(joinApiUrl(API_ENDPOINTS.CHAT_FOLLOWUP), { method: "DELETE" });
  },

  async chatFollowup(
    question: string,
    provider: string = "gemini",
    modelName: string = DEFAULT_MODEL_ID,
    apiKey?: string,
  ): Promise<ChatFollowupResponse> {
    return fetchWithErrorHandling<ChatFollowupResponse>(
      joinApiUrl(API_ENDPOINTS.CHAT_FOLLOWUP),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          provider,
          model_name: modelName,
          api_key: apiKey,
        }),
      },
    );
  },
};

export async function fetchRuntimeSummary(
  options?: { signal?: AbortSignal },
): Promise<RuntimeSummary> {
  const response = await fetch(joinApiUrl(API_ENDPOINTS.RUNTIME_SUMMARY), {
    signal: options?.signal,
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new ApiError(text || `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<RuntimeSummary>;
}

export default api;
