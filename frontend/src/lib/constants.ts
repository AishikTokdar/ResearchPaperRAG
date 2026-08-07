export { API_BASE_URL, joinApiUrl } from "./env";

export const API_ENDPOINTS = {
  HEALTH: "/",
  STATUS: "/status",
  UPLOAD: "/upload",
  ASK: "/ask",
  ASK_STREAM: "/ask/stream",
  MODELS: "/models",
  RUNTIME_SUMMARY: "/runtime-summary",
  PAPER_SEARCH: "/api/papers/search",
  PAPER_INGEST: "/api/papers/ingest",
  ANALYZE_GAPS: "/api/analyze/gaps",
  CHAT_FOLLOWUP: "/api/chat/followup",
} as const;

export const APP_CONFIG = {
  name: "ResearchPaperRAG",
  description:
    "Chat with your research papers using AI-powered Retrieval Augmented Generation",
  author: "Aishik Tokdar",
  version: "1.0.0",
  github: "https://github.com/AishikTokdar",
} as const;

export const ANIMATION_DURATION = {
  fast: 0.2,
  normal: 0.4,
  slow: 0.6,
  verySlow: 0.8,
} as const;

export const ANIMATION_DELAY = {
  none: 0,
  short: 0.1,
  medium: 0.2,
  long: 0.3,
} as const;

export const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
} as const;

export const MAX_FILE_SIZE = 50 * 1024 * 1024;

export const SUPPORTED_FILE_TYPES = {
  pdf: ["application/pdf", ".pdf"],
} as const;

export const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/chat", label: "Start Chat" },
] as const;

export const SOCIAL_LINKS = {
  github: "https://github.com/AishikTokdar",
  repository: "https://github.com/AishikTokdar/ResearchPaperRAG",
  linkedin: "https://www.linkedin.com/in/aishiktokdar/",
} as const;

export const FEATURES = [
  {
    title: "6 Free Academic Search APIs",
    description:
      "Simultaneous real-time paper retrieval across arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed (Healthcare), and DOAJ.",
  },
  {
    title: "Strict 3-Year Publication Window",
    description:
      "Automatically filters search results to recent publications from the last 3 years (2024–2026) for cutting-edge literature discovery.",
  },
  {
    title: "Max 5-Paper Deep Synthesis",
    description:
      "Select up to 5 research papers (or attach custom PDFs) for focused, high-precision cross-document RAG analysis.",
  },
  {
    title: "8-Layer LLM Research Analysis",
    description:
      "Synthesizes Literature Summary, Trend Detection, Common Methods, Limitations, Contradictions, Research Gaps, Future Directions, and Novel Paper Suggestions.",
  },
  {
    title: "Grounded Interactive Chat",
    description:
      "Ask follow-up questions strictly grounded in the ingested literature with exact source paper and section citations.",
  },
  {
    title: "Multi-Format Export (.pdf, .md, .txt)",
    description:
      "Export structured gap reports instantly into clean PDF print documents, raw Markdown, or plain text files.",
  },
  {
    title: "6 Free AI Cloud Providers",
    description:
      "Powered by free AI cloud providers: Groq LPU, Google Gemini, OpenRouter, Cerebras, SambaNova, and Hugging Face.",
  },
  {
    title: "Chroma & FAISS Vector Indexing",
    description:
      "Automated PDF text layer extraction, sentence-transformer embeddings, and local vector database indexing.",
  },
  {
    title: "New-Tab Paper Access",
    description:
      "Direct external links for every fetched research result to open original publisher PDFs and DOIs in a new browser tab.",
  },
] as const;

export const HOW_IT_WORKS_STEPS = [
  {
    step: 1,
    title: "Query Academic Literature",
    description:
      "Enter any research topic or question. The platform searches 6 free academic sources and filters papers from 2024–2026.",
  },
  {
    step: 2,
    title: "Select Papers & Build Knowledge Base",
    description:
      "Select up to 5 top research papers or upload your own custom PDFs to form the active multi-document knowledge base.",
  },
  {
    step: 3,
    title: "Automated RAG Vector Processing",
    description:
      "Documents are validated, chunked, vectorized using MiniLM embeddings, and indexed into local vector databases.",
  },
  {
    step: 4,
    title: "Synthesize 8-Layer Report & Chat",
    description:
      "The LLM generates a structured 8-layer gap report with citations, ready for grounded follow-up chat and export.",
  },
] as const;

export const TECH_STACK = [
  { name: "React", category: "frontend" },
  { name: "TypeScript", category: "frontend" },
  { name: "Tailwind CSS", category: "frontend" },
  { name: "Framer Motion", category: "frontend" },
  { name: "FastAPI", category: "backend" },
  { name: "LangChain", category: "ai" },
  { name: "FAISS", category: "database" },
  { name: "OpenRouter", category: "ai" },
] as const;
