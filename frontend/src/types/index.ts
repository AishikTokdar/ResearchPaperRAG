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
  | "cerebras"
  | "sambanova"
  | "huggingface"
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
}

export const AI_MODELS: AIModel[] = [
  {
    id: "gemini-3.6-flash",
    name: "Gemini 3.6 Flash",
    provider: "gemini",
    description: "Free tier via Google AI Studio — ultra fast & accurate",
    isDefault: true,
  },
  {
    id: "gemini-3.5-flash-lite",
    name: "Gemini 3.5 Flash-Lite",
    provider: "gemini",
    description: "Free tier fast lightweight model",
  },
  {
    id: "llama-3.3-70b-versatile",
    name: "Llama 3.3 70B (Groq)",
    provider: "groq",
    description: "Free ultra-fast LPU inference on Groq Cloud",
  },
  {
    id: "llama-3.1-8b-instant",
    name: "Llama 3.1 8B (Groq)",
    provider: "groq",
    description: "Free instant LPU responses for general Q&A",
  },
  {
    id: "qwen/qwen3.6-27b",
    name: "Qwen 3.6 27B (Groq)",
    provider: "groq",
    description: "Free high reasoning model on Groq",
  },
  {
    id: "mixtral-8x7b-32768",
    name: "Mixtral 8x7B (Groq)",
    provider: "groq",
    description: "Free MoE model on Groq Cloud",
  },
  {
    id: "deepseek-r1-distill-llama-70b",
    name: "DeepSeek R1 70B (Groq)",
    provider: "groq",
    description: "Free reasoning model on Groq LPU",
  },
  {
    id: "openai/gpt-oss-120b",
    name: "GPT-OSS 120B (Groq)",
    provider: "groq",
    description: "Free LPU inference on Groq Cloud",
  },
  {
    id: "openai/gpt-oss-20b",
    name: "GPT-OSS 20B (Groq)",
    provider: "groq",
    description: "Free lightweight model on Groq",
  },
  {
    id: "llama3.3-70b",
    name: "Llama 3.3 70B (Cerebras)",
    provider: "cerebras",
    description: "Free ultra-high-speed Wafer-Scale Engine inference",
  },
  {
    id: "llama3.1-8b",
    name: "Llama 3.1 8B (Cerebras)",
    provider: "cerebras",
    description: "Free 2000+ tokens/sec Cerebras inference",
  },
  {
    id: "Meta-Llama-3.3-70B-Instruct",
    name: "Llama 3.3 70B (SambaNova)",
    provider: "sambanova",
    description: "Free SN40L chip high speed inference",
  },
  {
    id: "DeepSeek-R1-Distill-Llama-70B",
    name: "DeepSeek R1 70B (SambaNova)",
    provider: "sambanova",
    description: "Free SambaNova Cloud reasoning model",
  },
  {
    id: "Qwen2.5-72B-Instruct",
    name: "Qwen 2.5 72B (SambaNova)",
    provider: "sambanova",
    description: "Free SambaNova Cloud 72B model",
  },
  {
    id: "mistralai/Mistral-7B-Instruct-v0.3",
    name: "Mistral 7B (HuggingFace)",
    provider: "huggingface",
    description: "Free serverless inference on Hugging Face",
  },
  {
    id: "HuggingFaceH4/zephyr-7b-beta",
    name: "Zephyr 7B (HuggingFace)",
    provider: "huggingface",
    description: "Free serverless assistant model",
  },
  {
    id: "meta-llama/Meta-Llama-3-8B-Instruct",
    name: "Llama 3 8B (HuggingFace)",
    provider: "huggingface",
    description: "Free Hugging Face serverless router",
  },
  {
    id: "Qwen/Qwen2.5-Coder-32B-Instruct",
    name: "Qwen 2.5 Coder 32B (HuggingFace)",
    provider: "huggingface",
    description: "Free Hugging Face coding & document analysis",
  },
  {
    id: "openrouter/free",
    name: "Auto Free Router (OpenRouter)",
    provider: "openrouter",
    description: "Smart router automatically directing to available 100% free models",
  },
  {
    id: "meta-llama/llama-3.3-70b-instruct:free",
    name: "Llama 3.3 70B (OpenRouter Free)",
    provider: "openrouter",
    description: "100% free tier on OpenRouter",
  },
  {
    id: "google/gemini-2.0-flash-exp:free",
    name: "Gemini 2.0 Flash (OpenRouter Free)",
    provider: "openrouter",
    description: "100% free tier on OpenRouter",
  },
  {
    id: "deepseek/deepseek-r1:free",
    name: "DeepSeek R1 (OpenRouter Free)",
    provider: "openrouter",
    description: "100% free reasoning model on OpenRouter",
  },
  {
    id: "qwen/qwen-2.5-72b-instruct:free",
    name: "Qwen 2.5 72B (OpenRouter Free)",
    provider: "openrouter",
    description: "100% free high-capacity model",
  },
  {
    id: "qwen/qwen-2.5-coder-32b-instruct:free",
    name: "Qwen 2.5 Coder 32B (OpenRouter Free)",
    provider: "openrouter",
    description: "100% free coding & analysis model",
  },
];

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
