import * as React from "react";
import { useReducedMotion } from "framer-motion";
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
  Check,
  Trash2,
  X,
} from "lucide-react";
import { PageWrapper, SectionWrapper } from "@/components/layout/page-wrapper";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { resetChatApiSessionId } from "@/lib/chat-session";
import { MAX_FILE_SIZE } from "@/lib/constants";
import { AI_MODELS, type AIModel, type FetchedPaper } from "@/types";
import { toast } from "sonner";
import { ReportRenderer, FormattedBlock } from "@/components/chat/report-renderer";
import { AnalysisProgressPanel, ReportGenerationPreview } from "@/components/chat/analysis-progress-panel";
import { INITIAL_ANALYSIS_PROGRESS, mergeAnalysisProgress, type AnalysisProgress, type AnalysisStatus } from "@/lib/analysis-progress";
import { ModelSelector } from "@/components/chat/model-selector";

interface ChatMessageItem {
  id: string;
  sender: "user" | "assistant";
  text: string;
}

const MAX_SELECTED_PAPERS = 5;
const CURRENT_YEAR = new Date().getFullYear();
const MIN_YEAR = CURRENT_YEAR - 2;


export function ChatPage() {
  const reducedMotion = useReducedMotion();
  const [searchError, setSearchError] = React.useState<string | null>(null);
  const [searchNotice, setSearchNotice] = React.useState<string | null>(null);
  const [hasSearched, setHasSearched] = React.useState(false);
  const [topicQuery, setTopicQuery] = React.useState(
    "Retrieval-Augmented Generation for educational chatbots"
  );
  const [paperLimit, setPaperLimit] = React.useState(3);
  const [isSearching, setIsSearching] = React.useState(false);
  const [fetchedPapers, setFetchedPapers] = React.useState<FetchedPaper[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = React.useState<Set<string>>(new Set());

  const [uploadedFiles, setUploadedFiles] = React.useState<File[]>([]);
  const uploadedFilesRef = React.useRef(uploadedFiles);
  uploadedFilesRef.current = uploadedFiles;
  const searchController = React.useRef<AbortController | null>(null);
  const followupController = React.useRef<AbortController | null>(null);

  const [activeTab, setActiveTab] = React.useState<"search" | "upload">("search");
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [analysisProgress, setAnalysisProgress] = React.useState<AnalysisProgress>(INITIAL_ANALYSIS_PROGRESS);
  const [analysisStatus, setAnalysisStatus] = React.useState<AnalysisStatus>("idle");
  const [analysisError, setAnalysisError] = React.useState<string | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = React.useState<number | null>(null);
  const [analysisFinishedAt, setAnalysisFinishedAt] = React.useState<number | null>(null);
  const [estimatedDuration, setEstimatedDuration] = React.useState(90);
  const [clock, setClock] = React.useState(Date.now());
  const analysisController = React.useRef<AbortController | null>(null);
  React.useEffect(() => () => {
    analysisController.current?.abort();
    searchController.current?.abort();
    followupController.current?.abort();
  }, []);
  React.useEffect(() => {
    if (!isAnalyzing) return;
    const interval = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [isAnalyzing]);
  const [report, setReport] = React.useState<string | null>(null);
  const [reportTopic, setReportTopic] = React.useState("");

  const [chatMessages, setChatMessages] = React.useState<ChatMessageItem[]>([]);
  const [chatInput, setChatInput] = React.useState("");
  const [isAsking, setIsAsking] = React.useState(false);
  const chatEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "nearest" });
  }, [chatMessages, isAsking, reducedMotion]);

  const defaultModel = AI_MODELS.find((m) => m.isDefault) ?? AI_MODELS[0];
  const [selectedModelObj, setSelectedModelObj] = React.useState<AIModel>(defaultModel);
  const [activeModelObj, setActiveModelObj] = React.useState<AIModel>(defaultModel);

  const [expandedPaperId, setExpandedPaperId] = React.useState<string | null>(null);

  const handleSaveModel = () => {
    if (selectedModelObj.id === activeModelObj.id) return;
    setActiveModelObj(selectedModelObj);
    setReport(null);
    setChatMessages([]);
    setAnalysisStatus("idle");
    setAnalysisProgress(INITIAL_ANALYSIS_PROGRESS);
    setAnalysisError(null);
    toast.success(`Active AI Model Saved: ${selectedModelObj.name} (${selectedModelObj.provider.toUpperCase()}). Pipeline and chat reset for new model.`);
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (searchController.current) return;
    if (!topicQuery.trim()) {
      toast.error("Please enter a research topic or question.");
      return;
    }

    setSearchError(null);
    setSearchNotice(null);
    setIsSearching(true);
    const controller = new AbortController();
    searchController.current = controller;
    try {
      const res = await api.searchPapers(topicQuery.trim(), paperLimit, controller.signal);
      if (controller.signal.aborted) return;
      const recentPapers = res.papers.filter((p) => {
        try {
          const y = intVal(p.year);
          return y >= MIN_YEAR && y <= CURRENT_YEAR;
        } catch {
          return true;
        }
      });

      const unavailable = res.source_status?.filter((source) => source.status !== "ok").map((source) => source.source) ?? [];
      setSearchNotice(
        recentPapers.length < 3 && unavailable.length > 0
          ? `Some sources could not be reached: ${unavailable.join(", ")}. You can use these results or try searching again.`
          : null
      );
      setHasSearched(true);
      setFetchedPapers(recentPapers);
      const initialSelected = new Set(recentPapers.slice(0, Math.max(0, MAX_SELECTED_PAPERS - uploadedFilesRef.current.length)).map((p) => p.id));
      setSelectedPaperIds(initialSelected);

      if (recentPapers.length > 0) {
        toast.success(`Found ${recentPapers.length} papers matching your topic.`);
      } else {
        toast.warning(`No papers found matching your topic from ${MIN_YEAR} to ${CURRENT_YEAR}.`);
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = (err as Error).message || "Failed to fetch research papers.";
      setSearchError(message);
      toast.error(message);
    } finally {
      searchController.current = null;
      setIsSearching(false);
    }
  };

  const togglePaperSelection = (id: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size + uploadedFiles.length >= MAX_SELECTED_PAPERS) {
          toast.error(`Maximum of ${MAX_SELECTED_PAPERS} research papers can be selected for analysis.`);
          return prev;
        }
        next.add(id);
      }
      return next;
    });
  };

  const selectTopFive = () => {
    const topFive = fetchedPapers.slice(0, Math.max(0, MAX_SELECTED_PAPERS - uploadedFiles.length)).map((p) => p.id);
    setSelectedPaperIds(new Set(topFive));
  };

  const deselectAll = () => {
    setSelectedPaperIds(new Set());
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);
    if (files.some((file) => !file.name.toLowerCase().endsWith(".pdf"))) {
      toast.error("Please choose PDF files only.");
      e.target.value = "";
      return;
    }
    const combined = [...uploadedFiles, ...files];
    if (combined.length + selectedPaperIds.size > MAX_SELECTED_PAPERS) {
      toast.error(`Choose at most ${MAX_SELECTED_PAPERS} papers and PDFs combined.`);
    } else if (combined.reduce((size, file) => size + file.size, 0) > MAX_FILE_SIZE) {
      toast.error("Combined PDFs must be no larger than 50 MB.");
    } else if (files.length) {
      setUploadedFiles(combined);
      toast.success(`Attached ${files.length} custom PDF document(s).`);
    }
    e.target.value = "";
  };

  const handleRemoveFile = (index: number) => {
    setUploadedFiles((prev) => {
      const removed = prev[index];
      const next = prev.filter((_, i) => i !== index);
      toast.info(`Removed ${removed?.name || "document"}.`);
      return next;
    });
  };

  const handleClearUploadedFiles = () => {
    setUploadedFiles([]);
    toast.info("Cleared all uploaded PDFs.");
  };

  const selectedFetchedPapers = fetchedPapers.filter((p) => selectedPaperIds.has(p.id));
  const totalActivePapers = selectedFetchedPapers.length + uploadedFiles.length;

  const handleRunAnalysis = async () => {
    if (analysisController.current || isSearching || isAsking) return;
    if (totalActivePapers === 0) {
      toast.error("Please select at least one paper before running analysis.");
      return;
    }
    if (totalActivePapers > MAX_SELECTED_PAPERS) {
      toast.error(`Please select a maximum of ${MAX_SELECTED_PAPERS} papers.`);
      return;
    }

    setReport(null);
    setChatMessages([]);
    setChatInput("");
    setIsAnalyzing(true);
    const controller = new AbortController();
    analysisController.current = controller;
    const started = Date.now();
    const analysisTopic = topicQuery.trim() || "Research Paper Analysis";
    setAnalysisStartedAt(started);
    setAnalysisFinishedAt(null);
    setClock(started);
    setEstimatedDuration(45 + totalActivePapers * 12 + uploadedFiles.reduce((bytes, file) => bytes + file.size, 0) / 1048576);
    setAnalysisStatus("running");
    setAnalysisError(null);
    setAnalysisProgress(INITIAL_ANALYSIS_PROGRESS);
    try {
      const result = await api.runAnalysis({
        topic: analysisTopic,
        provider: activeModelObj.provider,
        model: activeModelObj.id,
        paperIds: selectedFetchedPapers.map(({ id }) => id),
        files: uploadedFiles,
      }, (update) => {
        if (!controller.signal.aborted) setAnalysisProgress((current) => mergeAnalysisProgress(current, update));
      }, controller.signal);
      if (controller.signal.aborted) return;
      setAnalysisProgress((current) => ({ ...mergeAnalysisProgress(current, result.progress), stage: "complete", percent: 100 }));
      setAnalysisStatus("complete");
      setReport(result.report);
      setReportTopic(analysisTopic);
      toast.success(result.progress.limited ? "Report ready with limited source evidence." : "Research paper analysis and gap report generated.");
    } catch (err) {
      const message = controller.signal.aborted ? "Analysis stopped. You can run it again when ready." : (err as Error).message || "Failed to generate research report.";
      setAnalysisStatus("error");
      setAnalysisError(message);
      if (!controller.signal.aborted) toast.error(message);
    } finally {
      setAnalysisFinishedAt(Date.now());
      setIsAnalyzing(false);
      analysisController.current = null;
    }
  };

  const handleSendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || followupController.current || isAsking || isAnalyzing || !report) return;
    const controller = new AbortController();
    followupController.current = controller;

    const q = chatInput.trim();
    setChatInput("");

    const userMsg: ChatMessageItem = { id: String(Date.now()), sender: "user", text: q };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsAsking(true);

    try {
      const res = await api.chatFollowup(q, activeModelObj.provider, activeModelObj.id, undefined, controller.signal);
      if (controller.signal.aborted) return;
      const assistantMsg: ChatMessageItem = {
        id: String(Date.now() + 1),
        sender: "assistant",
        text: res.answer,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      if (controller.signal.aborted) return;
      setChatInput(q);
      setChatMessages((previous) => previous.filter((message) => message.id !== userMsg.id));
      toast.error((err as Error).message || "Chat query failed.");
    } finally {
      followupController.current = null;
      setIsAsking(false);
    }
  };

  const handleClearSession = () => {
    resetChatApiSessionId();
    setSearchNotice(null);
    setFetchedPapers([]);
    setSelectedPaperIds(new Set());
    setUploadedFiles([]);
    setReport(null);
    setChatMessages([]);
    setAnalysisStatus("idle");
    setAnalysisProgress(INITIAL_ANALYSIS_PROGRESS);
    setAnalysisError(null);
    setSearchError(null);
    setHasSearched(false);
    toast.info("Session reset.");
  };

  return (
    <PageWrapper showBackground showFooter className="w-full min-h-screen">
      <SectionWrapper className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="workspace-heading flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div className="max-w-2xl space-y-3">
            <p className="section-kicker">Research workspace</p>
            <h1 className="plain-heading text-3xl font-semibold tracking-tight sm:text-4xl">Research Gap Analyzer</h1>
            <p className="max-w-xl text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">Choose your sources, read the analysis, and follow the questions it raises.</p>
          </div>
          <nav aria-label="Workspace sections" className="workspace-jumps">
            <a href="#sources" aria-current={!report && !isAnalyzing ? "step" : undefined}>Sources</a>
            <a href="#report" aria-current={isAnalyzing || report ? "step" : undefined}>Report</a>
            <a href="#follow-up">Follow-up</a>
          </nav>
        </div>

        <div className="workspace-toolbar p-3 sm:p-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm flex-1 min-w-0">
            <span className="font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5 shrink-0">
              <Sliders className="w-4 h-4 text-indigo-500" /> Analysis model
            </span>
            
            <div className="w-full min-w-0 sm:w-72 md:w-80">
              <ModelSelector
                disabled={isAnalyzing || isAsking}
                value={selectedModelObj.id}
                onChange={(m) => setSelectedModelObj(m)}
              />
            </div>

            <Button
              type="button"
              size="sm"
              disabled={isAnalyzing || isAsking || selectedModelObj.id === activeModelObj.id}
              onClick={handleSaveModel}
              variant="outline" className="gap-1.5 px-4"
            >
              <Check className="w-3.5 h-3.5 stroke-[2.5]" /> Save Model
            </Button>

            <p className="text-xs text-[var(--text-muted)]">In use: <strong className="font-medium text-[var(--text-main)]">{activeModelObj.name}</strong>{selectedModelObj.id !== activeModelObj.id && <span className="ml-2">Save to apply your selection.</span>}</p>
          </div>

          <Button variant="outline" size="sm" disabled={isAnalyzing || isAsking || isSearching} onClick={handleClearSession} className="gap-1.5 text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 border-zinc-300 dark:border-zinc-700 shrink-0">
            <RotateCcw className="w-3.5 h-3.5" /> Clear Session
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
          <div id="sources" className="min-w-0 lg:col-span-5 xl:col-span-4 space-y-5">
            <fieldset hidden={isAnalyzing} disabled={isAnalyzing || isAsking} className="min-w-0 space-y-5 disabled:opacity-60">
            <div className="source-tabs" role="group" aria-label="Source input method">
              <button
                type="button"
                onClick={() => setActiveTab("search")}
                aria-pressed={activeTab === "search"}
                aria-controls="source-input-panel"
              >
                <Search className="w-4 h-4" /> Academic Search
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("upload")}
                aria-pressed={activeTab === "upload"}
                aria-controls="source-input-panel"
              >
                <Upload className="w-4 h-4" /> Upload PDFs
              </button>
            </div>

            {activeTab === "search" && (
              <div id="source-input-panel" className="workspace-panel p-5 space-y-4">
                <div><h2 className="text-base font-semibold">Find your sources</h2><p className="mt-1 text-xs leading-6 text-[var(--text-muted)]">Recent papers from {MIN_YEAR}–{CURRENT_YEAR} across six academic sources.</p></div>
                <form onSubmit={handleSearch} className="space-y-3">
                  <div className="relative space-y-2">
                    <label htmlFor="research-topic" className="workspace-label">Research topic or question</label>
                    <input
                      id="research-topic"
                      type="text"
                      aria-label="Research topic"
                      value={topicQuery}
                      onChange={(e) => setTopicQuery(e.target.value)}
                      maxLength={500}
                      placeholder="Enter research topic or question..."
                      className="w-full bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-zinc-500">
                    <label htmlFor="results-limit">Results per source</label>
                    <select
                      id="results-limit" aria-label="Results per academic source"
                      value={paperLimit}
                      onChange={(e) => setPaperLimit(Number(e.target.value))}
                      className="bg-zinc-100 dark:bg-zinc-800 border border-zinc-300 dark:border-zinc-700 rounded px-2 py-1 focus:ring-1 focus:ring-indigo-500"
                    >
                      <option value={2}>2 papers</option>
                      <option value={3}>3 papers</option>
                      <option value={4}>4 papers</option>
                    </select>
                  </div>

                  <Button type="submit" disabled={isSearching} className="w-full gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-sm">
                    {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    {isSearching ? "Fetching Recent Papers..." : "Search Research Papers"}
                  </Button>
                </form>

                <p className="text-xs leading-6 text-[var(--text-muted)]">arXiv · Crossref · Semantic Scholar · OpenAlex · PubMed · DOAJ</p>
                {isSearching && <p role="status" className="text-sm text-[var(--text-muted)]">Searching the academic sources. Results will appear here.</p>}
                {searchNotice && <p role="status" className="rounded-lg border border-border p-3 text-sm text-muted-foreground">{searchNotice}</p>}
                {searchError && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">{searchError} Your previous selections are still available. Try searching again.</p>}
                {hasSearched && !isSearching && !searchError && fetchedPapers.length === 0 && <p role="status" className="border-t border-[var(--border-color)] pt-4 text-sm text-[var(--text-muted)]">No recent papers matched this topic. Try a broader question or upload your PDFs.</p>}
                {fetchedPapers.length > 0 && (
                  <div className="space-y-3 pt-2">
                    <div className="flex items-center justify-between text-xs font-semibold text-zinc-600 dark:text-zinc-400">
                      <span>Fetched Papers ({fetchedPapers.length})</span>
                      <div className="flex items-center gap-2">
                        <button type="button" onClick={selectTopFive} className="min-h-8 text-indigo-600 dark:text-indigo-400 font-medium hover:underline">
                          Select Top 5
                        </button>
                        <span>|</span>
                        <button type="button" onClick={deselectAll} className="min-h-8 text-zinc-500 dark:text-zinc-400 hover:underline">
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
                                aria-label={`${isSelected ? "Deselect" : "Select"} ${paper.title}`}
                                aria-pressed={isSelected}
                                onClick={() => togglePaperSelection(paper.id)}
                                className="flex h-8 w-8 shrink-0 items-center justify-center rounded"
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
                                  className="min-h-6 text-sm font-semibold text-zinc-900 dark:text-zinc-100 hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline leading-snug flex items-center gap-1 group"
                                >
                                  {paper.title} ({paper.year})
                                  <ExternalLink className="w-3 h-3 text-zinc-400 group-hover:text-indigo-500 shrink-0 inline" />
                                </a>
                                <p className="text-zinc-500 dark:text-zinc-400 text-[11px] truncate mt-0.5">
                                  Authors: {paper.authors}
                                </p>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono border source-badge`}>
                                    {paper.source_api}
                                  </span>
                                  <span className="px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300 text-[10px]">
                                    {paper.year}
                                  </span>
                                  {paper.is_open_access && (
                                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                                      Open Access
                                    </span>
                                  )}
                                </div>
                              </div>
                              <button
                                type="button"
                                onClick={() => setExpandedPaperId(isExpanded ? null : paper.id)}
                                aria-label={`${isExpanded ? "Hide" : "Show"} abstract for ${paper.title}`}
                                aria-expanded={isExpanded}
                                className="flex h-8 w-8 shrink-0 items-center justify-center rounded text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
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
              <div id="source-input-panel" className="workspace-panel p-5 space-y-4">
                <label htmlFor="research-pdfs" className="workspace-label">
                  Upload Custom Research Papers (PDF)
                </label>
                <div className="border-2 border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl p-6 text-center hover:border-indigo-500/50 transition-colors cursor-pointer relative bg-zinc-50 dark:bg-zinc-950/50">
                  <input
                    id="research-pdfs"
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleFileChange}
                    className="absolute inset-0 opacity-0 cursor-pointer w-full h-full focus-visible:opacity-100"
                  />
                  <Upload className="w-8 h-8 mx-auto text-indigo-500/70 mb-2" />
                  <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                    Choose PDFs or drop them here
                  </p>
                  <p className="text-xs text-zinc-400 mt-1">Up to 5 papers · 50 MB total</p>
                </div>

                {uploadedFiles.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-zinc-500">Attached PDFs ({uploadedFiles.length})</p>
                      <button
                        type="button"
                        onClick={handleClearUploadedFiles}
                        className="min-h-8 px-1 text-[11px] text-red-500 hover:text-red-600 dark:hover:text-red-400 hover:underline flex items-center gap-1 font-medium"
                      >
                        <Trash2 className="w-3 h-3" /> Clear All
                      </button>
                    </div>
                    <div className="space-y-1">
                      {uploadedFiles.map((file, i) => (
                        <div key={i} className="flex items-center justify-between p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs gap-2">
                          <span className="truncate text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5 min-w-0">
                            <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                            <span className="truncate">{file.name}</span>
                          </span>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className="text-zinc-400 text-[10px]">{round(file.size / 1024, 1)} KB</span>
                            <button
                              type="button"
                              onClick={() => handleRemoveFile(i)}
                              className="flex h-8 w-8 items-center justify-center text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                              title="Remove PDF"
                              aria-label={`Remove ${file.name}`}
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            </fieldset>

            <div className="workspace-panel p-5 sm:p-6 text-zinc-900 dark:text-zinc-100 space-y-4 font-sans">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold flex items-center gap-2 text-zinc-900 dark:text-zinc-100">
                    <BookOpen className="w-4 h-4 text-indigo-600 dark:text-indigo-400" /> Selected sources
                  </h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                    Selected papers ({totalActivePapers} / {MAX_SELECTED_PAPERS} max)
                  </p>
                </div>
                <span className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{totalActivePapers} / {MAX_SELECTED_PAPERS}</span>
              </div>

              <Button
                onClick={handleRunAnalysis}
                disabled={isAnalyzing || isSearching || isAsking || totalActivePapers === 0 || totalActivePapers > MAX_SELECTED_PAPERS}
                className="w-full h-auto min-h-11 whitespace-normal py-3 text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md gap-2"
              >
                {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                {isAnalyzing ? "Analyzing Papers..." : "Run Multi-Paper Gap Analysis"}
              </Button>

              {isAnalyzing && <Button variant="outline" className="w-full" onClick={() => analysisController.current?.abort()}>Stop analysis</Button>}
              <AnalysisProgressPanel
                progress={analysisProgress} status={analysisStatus} error={analysisError}
                elapsed={analysisStartedAt ? Math.max(0, ((analysisFinishedAt ?? clock) - analysisStartedAt) / 1000) : 0}
                baseline={estimatedDuration}
              />
            </div>

          </div>

          <div className="workspace-report min-w-0 lg:col-span-7 xl:col-span-8 space-y-6">
            <div id="report" className="workspace-panel p-5 sm:p-8 space-y-4">
              {report ? (
                <ReportRenderer report={report} topic={reportTopic} />
              ) : analysisStatus === "running" || analysisStatus === "error" ? (
                <ReportGenerationPreview progress={analysisProgress} status={analysisStatus} error={analysisError} />
              ) : (
                <div className="workspace-empty py-3 sm:py-5">
                  <p className="section-kicker">Your reading desk</p><h2 className="editorial-title text-3xl sm:text-4xl">Start with the sources.</h2>
                  <p className="mt-5 max-w-lg text-sm leading-7 text-[var(--text-muted)]">Search for a topic or upload your PDFs. Choose up to five papers, then run the analysis to compare their findings.</p>
                  <div className="mt-8 grid gap-5 border-y border-[var(--border-color)] py-5 sm:grid-cols-2">
                    <div><h3 className="text-sm font-semibold">While the report is written</h3><p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">Follow the processing stages, sections being drafted, and estimated time remaining.</p></div>
                    <div><h3 className="text-sm font-semibold">When it is ready</h3><p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">Read all eight sections, check the citations, and export the report or ask a follow-up.</p></div>
                  </div>
                  <p className="mt-5 text-xs leading-6 text-[var(--text-muted)]">The quality of the report depends on the evidence available in your papers. Check the original sources as you review the findings.</p>
                </div>
              )}
            </div>

            <div id="follow-up" className="workspace-panel p-5 sm:p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-indigo-500" /> Follow-up questions
                </h2>
                {chatMessages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isAsking || isAnalyzing}
                    onClick={async () => {
                      if (followupController.current) return;
                      const controller = new AbortController();
                      followupController.current = controller;
                      setIsAsking(true);
                      try {
                        await api.clearFollowup(controller.signal);
                        if (controller.signal.aborted) return;
                        setChatMessages([]);
                        setChatInput("");
                        toast.info("Follow-up chat history cleared.");
                      } catch {
                        if (!controller.signal.aborted) toast.error("Chat history could not be cleared. Please retry.");
                      } finally {
                        followupController.current = null;
                        setIsAsking(false);
                      }
                    }}
                    className="h-7 px-2 text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 gap-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Clear Chat
                  </Button>
                )}
              </div>
              <p className="text-xs text-zinc-500">
                Ask about the methods, contradictions, or gaps in your sources. Review citations alongside the answers.
              </p>

              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {chatMessages.length === 0 && !isAsking ? (
                  <div className="text-center py-6 text-xs text-zinc-400 italic">
                    {report ? "Try asking: Which limitations are shared across these studies?" : "Generate a report to start asking questions about your sources."}
                  </div>
                ) : (
                  <>
                    {chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-3 text-xs sm:text-sm ${
                          msg.sender === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        {msg.sender === "assistant" && (
                          <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center shrink-0">
                            <Bot className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                          </div>
                        )}
                        <div
                          className={`p-3.5 rounded-2xl max-w-[85%] leading-relaxed ${
                            msg.sender === "user"
                              ? "bg-indigo-600 text-white rounded-br-none"
                              : "bg-zinc-100 dark:bg-zinc-800/90 text-zinc-800 dark:text-zinc-200 rounded-bl-none border border-zinc-200 dark:border-zinc-700"
                          }`}
                        >
                          {msg.sender === "user" ? (
                            msg.text
                          ) : (
                            <FormattedBlock text={msg.text} />
                          )}
                        </div>
                        {msg.sender === "user" && (
                          <div className="w-7 h-7 rounded-lg bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200 flex items-center justify-center shrink-0">
                            <User className="w-4 h-4" />
                          </div>
                        )}
                      </div>
                    ))}

                    {isAsking && (
                      <div className="flex gap-3 text-xs sm:text-sm justify-start">
                        <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center shrink-0">
                          <Bot className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                        </div>
                        <div className="px-4 py-3.5 rounded-2xl bg-zinc-100 dark:bg-zinc-800/90 rounded-bl-none border border-zinc-200 dark:border-zinc-700 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 animate-bounce motion-reduce:animate-none [animation-delay:-0.3s]" />
                          <span className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 animate-bounce motion-reduce:animate-none [animation-delay:-0.15s]" />
                          <span className="w-2 h-2 rounded-full bg-indigo-500 dark:bg-indigo-400 animate-bounce" />
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </>
                )}
              </div>

              <label htmlFor="follow-up-question" className="workspace-label">Your question</label>
              <form onSubmit={handleSendChat} className="flex gap-2">
                <input
                  type="text"
                  id="follow-up-question"
                  disabled={isAnalyzing || isAsking || !report}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  aria-label="Follow-up question"
                  maxLength={2000}
                  placeholder="Ask a follow-up question..."
                  className="flex-1 bg-zinc-50 dark:bg-zinc-950 border border-zinc-300 dark:border-zinc-700 rounded-xl px-4 py-2 text-sm text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
                <Button type="submit" aria-label="Send follow-up question" disabled={isAnalyzing || isAsking || !report || !chatInput.trim()} className="gap-1 bg-indigo-600 hover:bg-indigo-700 text-white">
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

function intVal(val: unknown): number {
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
