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
    const response = await fetch(url, withSessionHeaders(options));

    if (!response.ok) {
      const errorData: APIError = await response.json().catch(() => ({
        detail: `HTTP error ${response.status}`,
      }));
      throw new ApiError(errorData.detail, response.status, errorData.detail);
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

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventName = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventName = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            try {
              const data = JSON.parse(raw);
              switch (eventName) {
                case "token":
                  callbacks.onToken(data.content ?? "");
                  break;
                case "done":
                  callbacks.onDone(data);
                  break;
                case "error":
                  callbacks.onError(data.message ?? "Unknown error");
                  break;
                case "status":
                  callbacks.onStatus?.(data.stage, data.message);
                  break;
              }
            } catch {
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        callbacks.onError((err as Error).message ?? "Stream failed");
      }
    }
  })();

  return controller;
}

export const api = {
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
    hybridMode: boolean = true,
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
        body: JSON.stringify({ fetched_papers: fetchedPapers }),
      },
    );
  },

  async analyzeGaps(
    topic: string,
    provider: string = "ollama",
    modelName: string = "mistral",
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

  async chatFollowup(
    question: string,
    provider: string = "ollama",
    modelName: string = "mistral",
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
