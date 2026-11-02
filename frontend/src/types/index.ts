import modelCatalog from "@/lib/model-catalog.json";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface ChatEntry {
  id?: string;
  question: string;
  answer: string;
  timestamp?: Date;
  sources?: string[];
  modelUsed?: string;
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
}

export interface PDFDocument {
  id: string;
  fileName: string;
  fileSize: number;
  uploadedAt: Date;
  chunksCreated?: number;
}

export interface PDFUploadState {
  isUploading: boolean;
  isLoaded: boolean;
  document: PDFDocument | null;
  error: string | null;
}

export interface DocumentFileMeta {
  file_name: string;
  page_count: number;
  chunks_created: number;
}

export interface AskQuestionRequest {
  question: string;
  model?: string;
  include_sources?: boolean;
  hybrid_mode?: boolean;
  knowledge_mode?: string;
}

export interface AskQuestionResponse {
  answer: string;
  sources?: string[];
  model_used?: string;
  processing_time?: number;
}

export interface UploadResponse {
  message: string;
  chunks_created: number;
  file_name?: string;
  files?: DocumentFileMeta[];
  total_files?: number;
}

export interface StatusResponse {
  status: string;
  message: string;
  pdf_loaded?: boolean;
  server_boot_id?: string;
}

export interface RuntimeProviderRow {
  id: string;
  display_name: string;
  llm_ready: boolean;
  embedding_ready: boolean;
  status: string;
}

export interface RuntimeSummary {
  embedding_model?: string;
  embedding_chunk_tokens?: number;
  embedding_overlap_tokens?: number;
  embedding_mode?: string;
  status: string;
  providers: number;
  working: number;
  app_version: string;
  default_model: string;
  providers_detail: RuntimeProviderRow[];
  pipeline_agents?: number;
  embedding_chain_steps?: number;
  llm_providers_ready?: number;
  rate_limit_upload_per_minute?: number;
  rate_limit_ask_per_minute?: number;
  max_vector_sessions?: number;
  faiss_session_max_age_days?: number;
  total_pdf_uploads?: number;
  total_chat_completions?: number;
}

export interface APIError {
  detail: string;
  status_code?: number;
}

export interface FetchedPaper {
  id: string;
  source_api: string;
  title: string;
  authors: string;
  year: string;
  abstract: string;
  url: string;
  pdf_url?: string;
  is_open_access: boolean;
  citations?: number;
}

export interface PaperSearchResponse {
  source_status?: { source: string; status: "ok" | "timeout" | "unavailable"; count?: number }[];
  query: string;
  total_found: number;
  papers: FetchedPaper[];
}

export interface IngestPapersRequest {
  fetched_papers: FetchedPaper[];
}

export interface IngestPapersResponse {
  status: string;
  indexed_papers_count: number;
  chunks_created: number;
}

export interface AnalyzeGapsRequest {
  topic: string;
  provider?: string;
  model_name?: string;
  api_key?: string;
}

export interface AnalyzeGapsResponse {
  topic: string;
  report: string;
}

export interface ChatFollowupRequest {
  question: string;
  provider?: string;
  model_name?: string;
  api_key?: string;
}

export interface ChatFollowupResponse {
  question: string;
  answer: string;
}

export type AIProvider =
  | "gemini"
  | "groq"
  | "sambanova"
  | "openrouter";

export interface AIModel {
  id: string;
  name: string;
  provider: AIProvider;
  description?: string;
  maxTokens?: number;
  isDefault?: boolean;
  isAvailable?: boolean;
  apiKeyEnv?: string;
  accessTier?: string;
}

export const DEFAULT_MODEL_ID = modelCatalog.default_model;

export const AI_MODELS: AIModel[] = modelCatalog.providers.flatMap((provider) =>
  provider.models.map((model) => ({
    id: model.id, name: model.name, provider: provider.name as AIProvider,
    isDefault: model.id === modelCatalog.default_model && provider.name === modelCatalog.default_provider,
    // Offline catalog is descriptive, not evidence of credentials or current quota.
    isAvailable: false, accessTier: provider.access_tier,
    description: `${model.preview ? "Preview · " : ""}${provider.access_tier === "free" ? "Free tier, subject to quotas" : provider.access_tier === "trial" ? "Trial credits; server opt-in required" : "Purchased credits; server opt-in required"}`,
    apiKeyEnv: provider.api_key_env,
  })),
);

export type ButtonVariant =
  | "default"
  | "destructive"
  | "outline"
  | "secondary"
  | "ghost"
  | "link";

export type ButtonSize = "default" | "sm" | "lg" | "icon";

export type BadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "warning";

export type AnimationDirection = "up" | "down" | "left" | "right" | "none";

export interface ScrollRevealProps {
  children: React.ReactNode;
  direction?: AnimationDirection;
  delay?: number;
  duration?: number;
  className?: string;
}

export interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

export interface HowItWorksStep {
  step: number;
  title: string;
  description: string;
  icon: React.ReactNode;
}

export interface TechStackItem {
  name: string;
  icon: React.ReactNode;
  category: "frontend" | "backend" | "ai" | "database";
  description?: string;
}
