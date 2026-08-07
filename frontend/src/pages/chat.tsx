import * as React from "react";
import {
  Search,
  Upload,
  BookOpen,
  FileText,
  CheckSquare,
  Square,
  Send,
  MessageSquare,
  Bot,
  User,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Sliders,
  Layers,
  Filter,
  Check,
  Circle,
  CheckCircle2,
} from "lucide-react";
import { PageWrapper, SectionWrapper } from "@/components/layout/page-wrapper";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { AI_MODELS, type AIModel, type FetchedPaper } from "@/types";
import { toast } from "sonner";
import { ReportRenderer } from "@/components/chat/report-renderer";
import { ModelSelector } from "@/components/chat/model-selector";

interface ChatMessageItem {
  id: string;
  sender: "user" | "assistant";
  text: string;
}

const MAX_SELECTED_PAPERS = 5;
const CURRENT_YEAR = 2026;
const MIN_YEAR = CURRENT_YEAR - 2;

const PIPELINE_STEPS = [
  {
    title: "Ingest & validate PDF",
    detail: "Verify MIME, format, cumulative size (<= 50MB)",
  },
  {
    title: "Extract text layer",
    detail: "Pull text layer from document pages",
  },
  {
    title: "Semantic chunking",
    detail: "Split into overlapping segments",
  },
  {
    title: "Embedding pass",
    detail: "Vectorize chunks for similarity search",
  },
  {
    title: "Vector index",
    detail: "Update FAISS / Chroma store for retrieval",
  },
  {
    title: "Session metadata",
    detail: "Wire document id and counters",
  },
  {
    title: "Handoff to synthesis",
    detail: "RAG pipeline ready for multi-paper gap analysis",
  },
];

function getSourceBadgeStyle(sourceApi: string): string {
  const s = sourceApi.toLowerCase();
  if (s.includes("arxiv")) {
    return "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20";
  } else if (s.includes("crossref")) {
    return "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20";
  } else if (s.includes("semantic")) {
    return "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20";
  } else if (s.includes("openalex")) {
    return "bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-500/20";
  } else if (s.includes("pubmed")) {
    return "bg-teal-500/10 text-teal-700 dark:text-teal-400 border-teal-500/20";
  } else if (s.includes("doaj")) {
    return "bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20";
  }
  return "bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-300 dark:border-zinc-700";
}

export function ChatPage() {
  const [topicQuery, setTopicQuery] = React.useState(
    "Retrieval-Augmented Generation for educational chatbots"
  );
  const [paperLimit, setPaperLimit] = React.useState(3);
  const [isSearching, setIsSearching] = React.useState(false);
  const [fetchedPapers, setFetchedPapers] = React.useState<FetchedPaper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = React.useState<Set<string>>(new Set());

  const [uploadedFiles, setUploadedFiles] = React.useState<File[]>([]);

  const [activeTab, setActiveTab] = React.useState<"search" | "upload">("search");
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [activeStepIndex, setActiveStepIndex] = React.useState<number>(-1);
  const [report, setReport] = React.useState<string | null>(null);

  const [chatMessages, setChatMessages] = React.useState<ChatMessageItem[]>([]);
  const [chatInput, setChatInput] = React.useState("");
  const [isAsking, setIsAsking] = React.useState(false);

  const defaultModel = AI_MODELS.find((m) => m.isDefault) ?? AI_MODELS[0];
  const [selectedModelObj, setSelectedModelObj] = React.useState<AIModel>(defaultModel);
  const [activeModelObj, setActiveModelObj] = React.useState<AIModel>(defaultModel);

  const [expandedPaperId, setExpandedPaperId] = React.useState<string | null>(null);

  const handleSaveModel = () => {
    setActiveModelObj(selectedModelObj);
    toast.success(`Active AI Model Saved: ${selectedModelObj.name} (${selectedModelObj.provider.toUpperCase()})`);
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!topicQuery.trim()) {
      toast.error("Please enter a research topic or question.");
      return;
    }

    setIsSearching(true);
    try {
      const res = await api.searchPapers(topicQuery.trim(), paperLimit);
      const recentPapers = res.papers.filter((p) => {
        try {
          const y = intVal(p.year);
          return y >= MIN_YEAR && y <= CURRENT_YEAR;
        } catch {
          return true;
        }
      });

      setFetchedPapers(recentPapers);
      const initialSelected = new Set(recentPapers.slice(0, MAX_SELECTED_PAPERS).map((p) => p.id));
      setSelectedPaperIds(initialSelected);

      if (recentPapers.length > 0) {
        toast.success(`Retrieved ${recentPapers.length} papers from last 3 years (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ).`);
      } else {
        toast.warning("No recent papers found matching the topic from 2024 to 2026.");
      }
    } catch (err) {
      toast.error((err as Error).message || "Failed to fetch research papers.");
    } finally {
      setIsSearching(false);
    }
  };

  const togglePaperSelection = (id: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= MAX_SELECTED_PAPERS) {
          toast.error(`Maximum of ${MAX_SELECTED_PAPERS} research papers can be selected for analysis.`);
          return prev;
        }
        next.add(id);
      }
      return next;
    });
  };

  const selectTopFive = () => {
    const topFive = fetchedPapers.slice(0, MAX_SELECTED_PAPERS).map((p) => p.id);
    setSelectedPaperIds(new Set(topFive));
  };

  const deselectAll = () => {
    setSelectedPaperIds(new Set());
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files).filter((f) => f.name.endsWith(".pdf"));
    if (files.length > 0) {
      setUploadedFiles((prev) => [...prev, ...files].slice(0, MAX_SELECTED_PAPERS));
      toast.success(`Attached ${files.length} custom PDF document(s).`);
    }
  };

  const selectedFetchedPapers = fetchedPapers.filter((p) => selectedPaperIds.has(p.id));
  const totalActivePapers = selectedFetchedPapers.length + uploadedFiles.length;

  const handleRunAnalysis = async () => {
    if (totalActivePapers === 0) {
      toast.error("Please select at least one paper before running analysis.");
      return;
    }
    if (totalActivePapers > MAX_SELECTED_PAPERS) {
      toast.error(`Please select a maximum of ${MAX_SELECTED_PAPERS} papers.`);
      return;
    }

    setIsAnalyzing(true);
    setActiveStepIndex(0);

    try {
      if (uploadedFiles.length > 0) {
        await api.uploadPDFs(uploadedFiles);
      }
      setActiveStepIndex(1);
      await new Promise((r) => setTimeout(r, 400));

      setActiveStepIndex(2);
      await new Promise((r) => setTimeout(r, 400));

      setActiveStepIndex(3);
      if (selectedFetchedPapers.length > 0) {
        await api.ingestPapers(selectedFetchedPapers.slice(0, MAX_SELECTED_PAPERS));
      }
      
      setActiveStepIndex(4);
      await new Promise((r) => setTimeout(r, 300));

      setActiveStepIndex(5);
      await new Promise((r) => setTimeout(r, 300));

      setActiveStepIndex(6);
      const res = await api.analyzeGaps(
        topicQuery || "Research Paper Analysis",
        activeModelObj.provider,
        activeModelObj.id
      );

      setActiveStepIndex(7);
      setReport(res.report);
      toast.success("Research paper analysis and gap report generated.");
    } catch (err) {
      toast.error((err as Error).message || "Failed to generate research report.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isAsking) return;

    const q = chatInput.trim();
    setChatInput("");

    const userMsg: ChatMessageItem = { id: String(Date.now()), sender: "user", text: q };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsAsking(true);

    try {
      const res = await api.chatFollowup(q, activeModelObj.provider, activeModelObj.id);
      const assistantMsg: ChatMessageItem = {
        id: String(Date.now() + 1),
        sender: "assistant",
        text: res.answer,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      toast.error((err as Error).message || "Chat query failed.");
    } finally {
      setIsAsking(false);
    }
  };

  const handleClearSession = () => {
    setFetchedPapers([]);
    setSelectedPaperIds(new Set());
    setUploadedFiles([]);
    setReport(null);
    setChatMessages([]);
    setActiveStepIndex(-1);
    toast.info("Session reset.");
  };

  return (
    <PageWrapper showBackground showFooter className="w-full min-h-screen">
      <SectionWrapper className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            <Filter className="w-3.5 h-3.5" /> Multi-Source Academic Retrieval & Gap Analysis
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
            Research Gap Analyzer
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto text-sm sm:text-base">
            Search 6 free academic sources (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ), filter recent 3-year publications, select up to 5 papers, and synthesize structured 8-layer research insights.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-white dark:bg-zinc-900/90 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm flex-1 min-w-0">
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5 shrink-0">
              <Sliders className="w-4 h-4 text-indigo-500" /> Select AI Model:
            </span>
            
            <div className="w-full sm:w-72 md:w-80">
              <ModelSelector
                value={selectedModelObj.id}
                onChange={(m) => setSelectedModelObj(m)}
              />
            </div>

            <Button
              type="button"
              size="sm"
              onClick={handleSaveModel}
              className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-xs text-xs px-4"
            >
              <Check className="w-3.5 h-3.5 stroke-[2.5]" /> Save Model
            </Button>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 text-xs font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              <span>Active Model: <strong className="font-semibold text-zinc-900 dark:text-zinc-100">{activeModelObj.name}</strong> ({activeModelObj.provider.toUpperCase()})</span>
            </div>
          </div>

          <Button variant="outline" size="sm" onClick={handleClearSession} className="gap-1.5 text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 border-zinc-300 dark:border-zinc-700 shrink-0">
            <RotateCcw className="w-3.5 h-3.5" /> Clear Session
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5 space-y-6">
            <div className="flex rounded-xl bg-zinc-100 dark:bg-zinc-900 p-1 border border-zinc-200 dark:border-zinc-800">
              <button
                type="button"
                onClick={() => setActiveTab("search")}
                className={`flex-1 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                  activeTab === "search"
                    ? "bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm"
                    : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
                }`}
              >
                <Search className="w-4 h-4" /> Academic Search
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("upload")}
                className={`flex-1 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                  activeTab === "upload"
                    ? "bg-white dark:bg-zinc-800 text-indigo-600 dark:text-indigo-400 shadow-sm"
                    : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
                }`}
              >
                <Upload className="w-4 h-4" /> Upload PDFs
              </button>
            </div>

            {activeTab === "search" && (
              <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-semibold text-zinc-500">
                    <span>Search Sources (6 Free APIs):</span>
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-mono text-[10px] font-semibold border border-indigo-500/20">
                      Last 3 Years (2024-2026)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 text-[11px] font-medium">
                    <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">arXiv</span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">Crossref</span>
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">Semantic Scholar</span>
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">OpenAlex</span>
                    <span className="px-2 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">PubMed</span>
                    <span className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20">DOAJ</span>
                  </div>
                </div>

                <form onSubmit={handleSearch} className="space-y-3">
                  <div className="relative">
                    <input
                      type="text"
                      value={topicQuery}
                      onChange={(e) => setTopicQuery(e.target.value)}
                      placeholder="Enter research topic or question..."
                      className="w-full bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <span>Results limit per API:</span>
                    <select
                      value={paperLimit}
                      onChange={(e) => setPaperLimit(Number(e.target.value))}
                      className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500"
                    >
                      <option value={2}>2 papers per API</option>
                      <option value={3}>3 papers per API</option>
                      <option value={4}>4 papers per API</option>
                    </select>
                  </div>

                  <Button type="submit" disabled={isSearching} className="w-full gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm">
                    {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    {isSearching ? "Fetching Recent Papers..." : "Search Research Papers"}
                  </Button>
                </form>

                {fetchedPapers.length > 0 && (
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      <span>Fetched Papers ({fetchedPapers.length})</span>
                      <div className="flex items-center gap-2">
                        <button type="button" onClick={selectTopFive} className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline">
                          Select Top 5
                        </button>
                        <span>|</span>
                        <button type="button" onClick={deselectAll} className="text-zinc-400 hover:underline">
                          Deselect All
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                      {fetchedPapers.map((paper) => {
                        const isSelected = selectedPaperIds.has(paper.id);
                        const isExpanded = expandedPaperId === paper.id;
                        return (
                          <div
                            key={paper.id}
                            className={`p-3 rounded-xl border transition-all text-xs space-y-1.5 ${
                              isSelected
                                ? "bg-indigo-50/50 dark:bg-indigo-950/20 border-indigo-500/40 shadow-sm"
                                : "bg-zinc-50 dark:bg-zinc-950/50 border-zinc-200 dark:border-zinc-800"
                            }`}
                          >
                            <div className="flex items-start gap-2.5">
                              <button
                                type="button"
                                onClick={() => togglePaperSelection(paper.id)}
                                className="mt-0.5 hover:scale-105 transition-transform"
                              >
                                {isSelected ? (
                                  <CheckSquare className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                                ) : (
                                  <Square className="w-4 h-4 text-zinc-400" />
                                )}
                              </button>
                              <div className="flex-1 min-w-0">
                                <a
                                  href={paper.url || paper.pdf_url || "#"}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="font-semibold text-zinc-900 dark:text-zinc-100 hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline leading-snug flex items-center gap-1 group"
                                >
                                  {paper.title} ({paper.year})
                                  <ExternalLink className="w-3 h-3 text-zinc-400 group-hover:text-indigo-500 shrink-0 inline" />
                                </a>
                                <p className="text-zinc-500 dark:text-zinc-400 text-[11px] truncate mt-0.5">
                                  Authors: {paper.authors}
                                </p>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${getSourceBadgeStyle(paper.source_api)}`}>
                                    {paper.source_api}
                                  </span>
                                  <span className="px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 text-[10px]">
                                    {paper.year}
                                  </span>
                                  {paper.is_open_access && (
                                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                                      Open Access
                                    </span>
                                  )}
                                </div>
                              </div>
                              <button
                                type="button"
                                onClick={() => setExpandedPaperId(isExpanded ? null : paper.id)}
                                className="p-1 text-zinc-400 hover:text-zinc-200"
                              >
                                {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                              </button>
                            </div>

                            {isExpanded && (
                              <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-300 leading-relaxed text-[11px]">
                                <strong>Abstract:</strong> {paper.abstract}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "upload" && (
              <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Upload Custom Research Papers (PDF)
                </label>
                <div className="border-2 border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl p-6 text-center hover:border-indigo-500/50 transition-colors cursor-pointer relative bg-zinc-50 dark:bg-zinc-950/50">
                  <input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleFileChange}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                  />
                  <Upload className="w-8 h-8 mx-auto text-indigo-500/70 mb-2" />
                  <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                    Click or drag & drop PDF papers
                  </p>
                  <p className="text-xs text-zinc-400 mt-1">Maximum 5 documents for analysis</p>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold text-zinc-500">Attached PDFs ({uploadedFiles.length})</p>
                    <div className="space-y-1">
                      {uploadedFiles.map((file, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs">
                          <span className="truncate text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5 text-indigo-400" /> {file.name}
                          </span>
                          <span className="text-zinc-400 text-[10px]">{round(file.size / 1024, 1)} KB</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="p-5 rounded-2xl bg-zinc-900 text-zinc-100 border border-zinc-800 space-y-4 font-sans">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100">
                    <BookOpen className="w-4 h-4 text-indigo-400" /> Active Knowledge Base
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    Selected papers ({totalActivePapers} / {MAX_SELECTED_PAPERS} max)
                  </p>
                </div>
                <span className="text-xl font-bold text-indigo-400">{totalActivePapers} / {MAX_SELECTED_PAPERS}</span>
              </div>

              <Button
                onClick={handleRunAnalysis}
                disabled={isAnalyzing || totalActivePapers === 0 || totalActivePapers > MAX_SELECTED_PAPERS}
                className="w-full py-5 text-sm font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md gap-2"
              >
                {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                {isAnalyzing ? "Analyzing Papers..." : "Run Multi-Paper Gap Analysis"}
              </Button>

              <div className="pt-3 border-t border-zinc-800 space-y-2.5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                  Pipeline Processing Steps
                </p>
                {PIPELINE_STEPS.map((step, i) => {
                  const isCompleted = activeStepIndex > i || report !== null;
                  const isCurrent = activeStepIndex === i && isAnalyzing;

                  return (
                    <div key={i} className="flex items-start gap-2.5 text-xs">
                      <div className="mt-0.5 shrink-0">
                        {isCompleted ? (
                          <Check className="w-4 h-4 text-emerald-400 stroke-[2.5]" />
                        ) : isCurrent ? (
                          <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                        ) : (
                          <Circle className="w-3.5 h-3.5 text-zinc-600" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className={`font-semibold font-mono leading-tight ${isCompleted ? "text-zinc-100" : isCurrent ? "text-indigo-300" : "text-zinc-500"}`}>
                          {step.title}
                        </div>
                        <div className="text-[11px] text-zinc-400 font-mono leading-tight mt-0.5 truncate">
                          {step.detail}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

          <div className="lg:col-span-7 space-y-6">
            <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4 min-h-[400px]">
              {report ? (
                <ReportRenderer report={report} topic={topicQuery} />
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-center text-zinc-400 space-y-3">
                  <BookOpen className="w-10 h-10 stroke-1 text-indigo-500 opacity-40" />
                  <p className="text-sm font-medium">No analysis generated yet.</p>
                  <p className="text-xs text-zinc-500 max-w-md">
                    Search academic sources, select up to 5 research papers from the last 3 years, and click &ldquo;Run Multi-Paper Gap Analysis&rdquo;.
                  </p>
                </div>
              )}
            </div>

            <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-indigo-500" /> Grounded Interactive Follow-up Chat
              </h3>
              <p className="text-xs text-zinc-500">
                Ask follow-up questions regarding common methods, contradictions, or research gaps. Answers cite exact papers and sections.
              </p>

              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-6 text-xs text-zinc-400 italic">
                    Example: &ldquo;Which contradiction between paper 1 and paper 2 requires further dataset benchmarking?&rdquo;
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex gap-3 text-xs sm:text-sm ${
                        msg.sender === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {msg.sender === "assistant" && (
                        <div className="w-7 h-7 rounded-lg bg-indigo-950 text-indigo-300 border border-indigo-800 flex items-center justify-center shrink-0">
                          <Bot className="w-4 h-4 text-indigo-400" />
                        </div>
                      )}
                      <div
                        className={`p-3.5 rounded-2xl max-w-[85%] leading-relaxed ${
                          msg.sender === "user"
                            ? "bg-indigo-600 text-white rounded-br-none"
                            : "bg-zinc-100 dark:bg-zinc-800/90 text-zinc-800 dark:text-zinc-200 rounded-bl-none border border-zinc-200 dark:border-zinc-700"
                        }`}
                      >
                        {msg.text}
                      </div>
                      {msg.sender === "user" && (
                        <div className="w-7 h-7 rounded-lg bg-zinc-700 text-zinc-200 flex items-center justify-center shrink-0">
                          <User className="w-4 h-4" />
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              <form onSubmit={handleSendChat} className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask a follow-up question..."
                  className="flex-1 bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
                <Button type="submit" disabled={isAsking || !chatInput.trim()} className="gap-1 bg-indigo-600 hover:bg-indigo-700 text-white">
                  {isAsking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
              </form>
            </div>
          </div>
        </div>
      </SectionWrapper>
    </PageWrapper>
  );
}

function intVal(val: any): number {
  try {
    const parsed = parseInt(String(val).trim().slice(0, 4), 10);
    return isNaN(parsed) ? CURRENT_YEAR : parsed;
  } catch {
    return CURRENT_YEAR;
  }
}

function round(num: number, decimals: number) {
  return Number(Math.round(Number(num + "e" + decimals)) + "e-" + decimals);
}

export default ChatPage;
