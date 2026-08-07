import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  FileText,
  Trash2,
  Download,
  StopCircle,
  History,
  HardDrive,
  X,
  Sparkles,
  Brain,
  BookOpen,
  Key,
  Lightbulb,
  Zap,
  FileType,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PDFUpload } from "./pdf-upload";
import { ChatMessage, TypingIndicator } from "./chat-message";
import { ChatInput } from "./chat-input";
import { ModelSelector } from "./model-selector";
import { usePDFUpload } from "@/hooks/use-pdf-upload";
import { useChat } from "@/hooks/use-chat";
import { api } from "@/lib/api";
import { AI_MODELS, type AIModel, type ChatEntry } from "@/types";
import {
  loadPreference,
  savePreference,
  prefKeys,
  saveChatSession,
  loadChatSession,
  listChatSessions,
  deleteChatSession,
  clearAllSessions,
  type ChatSession,
} from "@/lib/storage";
import { getChatEntryReactKey } from "@/lib/chat-history";
import { ConfirmAlertDialog } from "@/components/ui/confirm-alert-dialog";
import { SESSION_INDEX_RETENTION_DAYS } from "@/lib/session-retention";

const DEFAULT_CHAT_MODEL_ID = "openai/gpt-oss-120b";

function exportAsTXT(chatHistory: ChatEntry[], activeSessionName?: string) {
  if (chatHistory.length === 0) return;
  const header = `==================================================\nResearchPaperRAG Conversation Export\nDocument: ${activeSessionName || "Indexed PDF"}\nExported Date: ${new Date().toLocaleString()}\n==================================================\n\n`;
  const body = chatHistory
    .map((e, idx) => {
      let text = `[Question ${idx + 1}]\n${e.question}\n\n[Answer]\n${e.answer}\n`;
      if (e.modelUsed) text += `Model Used: ${e.modelUsed}\n`;
      if (e.sources && e.sources.length) {
        text += `Citations:\n` + e.sources.map((s) => `  - ${s}`).join("\n") + "\n";
      }
      return text + "\n--------------------------------------------------\n";
    })
    .join("\n");

  const blob = new Blob([header + body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chat_export_${(activeSessionName || "document").replace(/[^a-z0-9]/gi, "_").toLowerCase()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function exportAsPDF(chatHistory: ChatEntry[], activeSessionName?: string) {
  if (chatHistory.length === 0) return;
  const printWindow = window.open("", "_blank");
  if (!printWindow) return;

  const escapeHtml = (str: string) =>
    str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");

  const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <title>ResearchPaperRAG Export - ${escapeHtml(activeSessionName || "Conversation")}</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          line-height: 1.6;
          color: #18181b;
          padding: 40px;
          max-width: 800px;
          margin: 0 auto;
          background: #ffffff;
        }
        .header {
          border-bottom: 2px solid #e4e4e7;
          padding-bottom: 16px;
          margin-bottom: 24px;
        }
        .header h1 {
          font-size: 22px;
          font-weight: 800;
          color: #09090b;
          margin: 0 0 6px 0;
          letter-spacing: -0.5px;
        }
        .meta {
          font-size: 12px;
          color: #71717a;
          line-height: 1.5;
        }
        .message-card {
          margin-bottom: 24px;
          border: 1px solid #e4e4e7;
          border-radius: 12px;
          overflow: hidden;
          page-break-inside: avoid;
        }
        .question-box {
          background: #f4f4f5;
          padding: 12px 16px;
          font-size: 14px;
          font-weight: 700;
          color: #18181b;
          border-bottom: 1px solid #e4e4e7;
        }
        .answer-box {
          padding: 16px;
          font-size: 13px;
          color: #27272a;
          white-space: pre-wrap;
        }
        .model-tag {
          margin-top: 12px;
          font-size: 11px;
          color: #71717a;
          font-weight: 600;
        }
        .citations-box {
          margin-top: 12px;
          padding: 12px;
          background: #fafafa;
          border-radius: 8px;
          border: 1px solid #f4f4f5;
          font-size: 11px;
        }
        .citations-title {
          font-weight: 700;
          color: #3f3f46;
          margin-bottom: 4px;
        }
        .citation-item {
          font-family: monospace;
          color: #52525b;
          margin-top: 2px;
        }
        @media print {
          body { padding: 20px; }
        }
      </style>
    </head>
    <body>
      <div class="header">
        <h1>ResearchPaperRAG Conversation Transcript</h1>
        <div class="meta">
          <strong>Document:</strong> ${escapeHtml(activeSessionName || "Indexed PDF")}<br/>
          <strong>Exported Date:</strong> ${new Date().toLocaleString()}<br/>
          <strong>Total Messages:</strong> ${chatHistory.length}
        </div>
      </div>
      ${chatHistory
        .map(
          (e, idx) => `
        <div class="message-card">
          <div class="question-box">Q${idx + 1}: ${escapeHtml(e.question)}</div>
          <div class="answer-box">
            ${escapeHtml(e.answer)}
            ${e.modelUsed ? `<div class="model-tag">Model: ${escapeHtml(e.modelUsed)}</div>` : ""}
            ${
              e.sources && e.sources.length
                ? `
              <div class="citations-box">
                <div class="citations-title">Document Citations:</div>
                ${e.sources.map((s) => `<div class="citation-item">• ${escapeHtml(s)}</div>`).join("")}
              </div>
            `
                : ""
            }
          </div>
        </div>
      `,
        )
        .join("")}
      <script>
        window.onload = function() {
          window.print();
        };
      </script>
    </body>
    </html>
  `;
  printWindow.document.write(htmlContent);
  printWindow.document.close();
}

export function ChatContainer() {
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const messagesScrollRef = React.useRef<HTMLDivElement>(null);

  const [selectedModel, setSelectedModel] = React.useState(() =>
    loadPreference<string>(prefKeys.SELECTED_MODEL, DEFAULT_CHAT_MODEL_ID),
  );
  const [_modelMeta, setModelMeta] = React.useState(() => {
    const id = loadPreference<string>(prefKeys.SELECTED_MODEL, DEFAULT_CHAT_MODEL_ID);
    const m = AI_MODELS.find((x) => x.id === id) ?? AI_MODELS[0];
    return { name: m.name, provider: m.provider };
  });
  const [includeSources, setIncludeSources] = React.useState(true);
  const [hybridMode, setHybridMode] = React.useState(true);
  const [useStreaming, setUseStreaming] = React.useState(() =>
    loadPreference<boolean>(prefKeys.STREAMING_ENABLED, true),
  );
  const [showBanner, setShowBanner] = React.useState(
    () => !loadPreference<boolean>(prefKeys.DISMISSED_LOCAL_BANNER, false),
  );
  const [showExportMenu, setShowExportMenu] = React.useState(false);

  const [sessions, setSessions] = React.useState<ChatSession[]>([]);
  const [showSessions, setShowSessions] = React.useState(false);
  const [clearAllOpen, setClearAllOpen] = React.useState(false);
  const [sessionToDelete, setSessionToDelete] = React.useState<string | null>(null);
  const [activeSessionName, setActiveSessionName] = React.useState<string | null>(null);

  const {
    isUploading,
    isLoaded,
    fileName,
    chunksCreated,
    files,
    totalFiles,
    error: uploadError,
    uploadPDFs,
    reset: resetUpload,
  } = usePDFUpload();

  const {
    chatHistory,
    isLoading,
    error: chatError,
    streamingAnswer,
    statusMessage,
    sendMessage,
    sendMessageStreaming,
    clearHistory,
    cancelStream,
    setChatHistory,
  } = useChat();

  React.useEffect(() => {
    savePreference(prefKeys.SELECTED_MODEL, selectedModel);
  }, [selectedModel]);
  React.useEffect(() => {
    savePreference(prefKeys.INCLUDE_SOURCES, includeSources);
  }, [includeSources]);
  React.useEffect(() => {
    savePreference(prefKeys.STREAMING_ENABLED, useStreaming);
  }, [useStreaming]);

  React.useEffect(() => {
    if (fileName) setActiveSessionName(fileName);
  }, [fileName]);

  React.useEffect(() => {
    const key = activeSessionName ?? fileName;
    if (key && chatHistory.length > 0) {
      saveChatSession(key, chatHistory);
    }
  }, [chatHistory, activeSessionName, fileName]);

  React.useEffect(() => {
    if (fileName && isLoaded && chatHistory.length === 0) {
      loadChatSession(fileName).then((saved) => {
        if (saved.length > 0) setChatHistory(saved);
      });
    }
  }, [fileName, isLoaded]);

  React.useEffect(() => {
    listChatSessions().then(setSessions);
  }, [chatHistory, fileName, showSessions]);

  // Detect server restart via server_boot_id and reset browser document history
  React.useEffect(() => {
    let isMounted = true;
    api
      .getStatus()
      .then((statusData) => {
        if (!isMounted) return;
        const currentBootId = statusData.server_boot_id;
        if (currentBootId) {
          const storedBootId = localStorage.getItem("doc_rag_server_boot_id");
          if (storedBootId && storedBootId !== currentBootId) {
            clearAllSessions().then(() => {
              setSessions([]);
              clearHistory();
              setActiveSessionName(null);
            });
          }
          localStorage.setItem("doc_rag_server_boot_id", currentBootId);
        }
      })
      .catch(() => {
        // Backend offline or unreachable
      });

    return () => {
      isMounted = false;
    };
  }, [clearHistory]);

  const scrollToBottom = React.useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  React.useEffect(() => {
    scrollToBottom();
  }, [chatHistory, streamingAnswer, scrollToBottom]);

  const handleSendMessage = React.useCallback(
    (content: string) => {
      if (useStreaming) {
        sendMessageStreaming(content, selectedModel, includeSources, hybridMode);
      } else {
        sendMessage(content, selectedModel, includeSources, hybridMode);
      }
    },
    [selectedModel, includeSources, hybridMode, useStreaming, sendMessageStreaming, sendMessage],
  );

  const handleRestoreSession = (s: ChatSession) => {
    setChatHistory(s.entries);
    setActiveSessionName(s.pdfName);
  };

  const handleDeleteSession = async (name: string) => {
    await deleteChatSession(name);
    const remaining = await listChatSessions();
    setSessions(remaining);
    if (activeSessionName === name) {
      clearHistory();
      setActiveSessionName(null);
    }
  };

  const handleClearAllConfirmed = async () => {
    await clearAllSessions();
    setSessions([]);
    clearHistory();
    setActiveSessionName(null);
  };

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6 space-y-6">
      {/* Top Session / Local Index Storage Info Banner */}
      {showBanner && (
        <GlassCard padding="sm" className="border-blue-500/30 bg-blue-500/10 dark:bg-blue-950/20">
          <div className="flex items-start justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
              <HardDrive className="w-4 h-4 shrink-0" />
              <span>
                <strong>Session Isolation:</strong> Each browser tab uses an isolated FAISS vector index. In-memory sessions stay active for {SESSION_INDEX_RETENTION_DAYS} days.
              </span>
            </div>
            <button
              onClick={() => {
                setShowBanner(false);
                savePreference(prefKeys.DISMISSED_LOCAL_BANNER, true);
              }}
              className="p-1 hover:bg-blue-500/20 rounded transition-colors text-blue-600 dark:text-blue-400"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </GlassCard>
      )}

      {/* Main Grid: Left Control Panel (4 cols) | Right Chat View (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Sidebar: PDF Upload & Model Controls */}
        <div className="lg:col-span-4 space-y-4">
          <GlassCard padding="default" className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <FileText className="w-4 h-4 text-zinc-500" />
                Document Upload
              </h2>
              {isLoaded && (
                <Badge variant="success">Active</Badge>
              )}
            </div>

            <PDFUpload
              onUpload={uploadPDFs}
              isUploading={isUploading}
              isLoaded={isLoaded}
              chunksCreated={chunksCreated ?? undefined}
              files={files}
              totalFiles={totalFiles}
              error={uploadError}
              onReset={() => {
                resetUpload();
                clearHistory();
                setActiveSessionName(null);
              }}
            />
          </GlassCard>

          {/* Knowledge Mode & Execution Controls */}
          <GlassCard padding="default" className="space-y-4">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Pipeline &amp; Brain Settings
            </h2>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1.5 block">
                  AI Model
                </label>
                <ModelSelector
                  value={selectedModel}
                  onChange={(m: AIModel) => {
                    setSelectedModel(m.id);
                    setModelMeta({ name: m.name, provider: m.provider });
                  }}
                />
              </div>

              {/* Knowledge Source Mode Toggle */}
              <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-medium text-zinc-700 dark:text-zinc-300 flex items-center justify-between">
                    <span className="flex items-center gap-1.5 font-semibold">
                      {hybridMode ? (
                        <Brain className="w-3.5 h-3.5 text-purple-500" />
                      ) : (
                        <BookOpen className="w-3.5 h-3.5 text-emerald-500" />
                      )}
                      Knowledge Source Mode
                    </span>
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold border transition-colors",
                        hybridMode
                          ? "bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-300/40 dark:border-purple-800/60"
                          : "bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300/40 dark:border-emerald-800/60",
                      )}
                    >
                      {hybridMode ? "Hybrid Brain" : "Strict to Source"}
                    </span>
                  </label>

                  <div className="grid grid-cols-2 gap-1.5 p-1 bg-zinc-100 dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
                    <button
                      type="button"
                      onClick={() => setHybridMode(true)}
                      className={cn(
                        "flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium transition-all cursor-pointer",
                        hybridMode
                          ? "bg-white dark:bg-zinc-800 text-purple-700 dark:text-purple-300 shadow-sm border border-purple-200 dark:border-purple-800/50 font-bold"
                          : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200",
                      )}
                    >
                      <Brain className="w-3 h-3 text-purple-500" />
                      <span>Hybrid Brain</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setHybridMode(false)}
                      className={cn(
                        "flex items-center justify-center gap-1 py-1.5 px-2 rounded-md text-[11px] font-medium transition-all cursor-pointer",
                        !hybridMode
                          ? "bg-white dark:bg-zinc-800 text-emerald-700 dark:text-emerald-300 shadow-sm border border-emerald-200 dark:border-emerald-800/50 font-bold"
                          : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-200",
                      )}
                    >
                      <BookOpen className="w-3 h-3 text-emerald-500" />
                      <span>Strict to Source</span>
                    </button>
                  </div>
                  <p className="text-[10px] text-zinc-500 dark:text-zinc-400 leading-tight">
                    {hybridMode
                      ? "Combines PDF citations with pretrained AI world knowledge."
                      : "Answers strictly using only the uploaded PDF document text."}
                  </p>
                </div>

                <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800 space-y-2">
                  <label className="flex items-center justify-between text-xs cursor-pointer">
                    <span className="text-zinc-600 dark:text-zinc-400">Stream Token Responses</span>
                    <input
                      type="checkbox"
                      checked={useStreaming}
                      onChange={(e) => setUseStreaming(e.target.checked)}
                      className="rounded border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-0"
                    />
                  </label>

                  <label className="flex items-center justify-between text-xs cursor-pointer">
                    <span className="text-zinc-600 dark:text-zinc-400">Include Citation Sources</span>
                    <input
                      type="checkbox"
                      checked={includeSources}
                      onChange={(e) => setIncludeSources(e.target.checked)}
                      className="rounded border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 focus:ring-0"
                    />
                  </label>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Saved Sessions Drawer Button */}
          {sessions.length > 0 && (
            <GlassCard padding="sm" className="flex items-center justify-between">
              <button
                onClick={() => setShowSessions((p) => !p)}
                className="flex items-center gap-2 text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors w-full justify-between"
              >
                <span className="flex items-center gap-2">
                  <History className="w-4 h-4 text-zinc-500" />
                  Saved Sessions ({sessions.length})
                </span>
                <Badge variant="outline" size="sm">{showSessions ? "Hide" : "Show"}</Badge>
              </button>
            </GlassCard>
          )}

          {/* Sessions List Dropdown */}
          <AnimatePresence>
            {showSessions && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                <GlassCard padding="sm" className="space-y-2">
                  <div className="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
                    <span className="text-xs font-semibold text-zinc-500">History</span>
                    <button
                      onClick={() => setClearAllOpen(true)}
                      className="text-xs text-red-500 hover:underline cursor-pointer"
                    >
                      Clear All
                    </button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {sessions.map((s) => (
                      <div
                        key={s.pdfName}
                        className={cn(
                          "flex items-center justify-between p-2 rounded-lg text-xs transition-colors cursor-pointer",
                          s.pdfName === (activeSessionName ?? fileName)
                            ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-medium"
                            : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
                        )}
                        onClick={() => handleRestoreSession(s)}
                      >
                        <span className="truncate flex-1">{s.pdfName}</span>
                        <div className="flex items-center gap-1.5 shrink-0 ml-2">
                          <span className="text-[10px] text-zinc-400">{s.entries.length} msgs</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSessionToDelete(s.pdfName);
                            }}
                            className="p-1 text-zinc-400 hover:text-red-500 rounded"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right Panel / Main Chat Stream */}
        <div className="lg:col-span-8 flex flex-col h-[75vh] min-h-[500px] rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden shadow-sm">
          {/* Chat Top Header Toolbar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-zinc-500" />
              <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                {activeSessionName ? activeSessionName : "Interactive Chat"}
              </span>
            </div>

            <div className="flex items-center gap-2">
              {isLoading && (
                <Button variant="ghost" size="sm" onClick={cancelStream} className="text-xs text-red-500">
                  <StopCircle className="w-3.5 h-3.5 mr-1" />
                  Stop
                </Button>
              )}
              {chatHistory.length > 0 && (
                <div className="relative">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowExportMenu((p) => !p)}
                    className="text-xs h-8 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5 mr-1 text-zinc-500" />
                    Export Chat
                  </Button>

                  {/* Export Dropdown Menu */}
                  {showExportMenu && (
                    <div className="absolute right-0 mt-1 w-44 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-lg p-1.5 z-50 text-xs space-y-1">
                      <button
                        type="button"
                        onClick={() => {
                          setShowExportMenu(false);
                          exportAsTXT(chatHistory, activeSessionName || fileName || undefined);
                        }}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-medium transition-colors cursor-pointer text-left"
                      >
                        <FileType className="w-3.5 h-3.5 text-blue-500" />
                        Export as Text (.txt)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowExportMenu(false);
                          exportAsPDF(chatHistory, activeSessionName || fileName || undefined);
                        }}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-medium transition-colors cursor-pointer text-left"
                      >
                        <FileText className="w-3.5 h-3.5 text-red-500" />
                        Export as PDF (.pdf)
                      </button>
                    </div>
                  )}
                </div>
              )}
              {chatHistory.length > 0 && (
                <Button variant="ghost" size="sm" onClick={clearHistory} className="text-xs text-zinc-500 h-8">
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          </div>

          {/* Messages Stream Container */}
          <div
            ref={messagesScrollRef}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6"
          >
            {chatHistory.length === 0 && !streamingAnswer && !isLoading ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
                <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40 shadow-xs">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div className="max-w-md space-y-1">
                  <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                    {isLoaded ? "The RAG pipeline is ready for your questions" : "Ready for Document Analysis"}
                  </h3>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
                    {isLoaded
                      ? "Click any suggested question below or type your custom query to analyze this document with context citations."
                      : "Upload a PDF document on the left sidebar to start chatting."}
                  </p>
                </div>

                {isLoaded && (
                  <div className="w-full max-w-xl grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2">
                    {[
                      { icon: FileText, title: "Summarize Document", prompt: "Please provide a comprehensive summary of this entire document." },
                      { icon: Key, title: "Key Information", prompt: "What are the key findings, main points, and key information in this PDF?" },
                      { icon: Lightbulb, title: "Explain Concepts", prompt: "Explain the core topics and background concepts of this document in simple terms." },
                      { icon: Zap, title: "Action Items & Takeaways", prompt: "What are the main conclusions, action items, and practical takeaways from this document?" },
                    ].map((item, i) => {
                      const IconComponent = item.icon;
                      return (
                        <button
                          key={i}
                          type="button"
                          onClick={() => handleSendMessage(item.prompt)}
                          className="flex flex-col items-start p-3 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-400 dark:hover:border-zinc-600 hover:bg-zinc-50 dark:hover:bg-zinc-800/80 transition-all text-left group shadow-xs cursor-pointer"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <IconComponent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                            <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                              {item.title}
                            </span>
                          </div>
                          <p className="text-[11px] text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-normal">
                            {item.prompt}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : (
              <>
                {chatHistory.map((entry, idx) => (
                  <React.Fragment key={getChatEntryReactKey(entry, idx)}>
                    <ChatMessage role="user" content={entry.question} timestamp={entry.timestamp} />
                    <ChatMessage
                      role="assistant"
                      content={entry.answer}
                      timestamp={entry.timestamp}
                      sources={entry.sources}
                      modelUsed={entry.modelUsed}
                    />
                  </React.Fragment>
                ))}

                {streamingAnswer !== null && (
                  <ChatMessage
                    role="assistant"
                    content={streamingAnswer}
                    modelUsed={selectedModel}
                  />
                )}

                {isLoading && streamingAnswer === null && (
                  <TypingIndicator statusMessage={statusMessage ?? undefined} />
                )}

                {chatError && (
                  <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/40 text-xs text-red-600 dark:text-red-400 flex items-center justify-between">
                    <span>{chatError}</span>
                    <Button variant="ghost" size="sm" onClick={() => handleSendMessage(chatHistory[chatHistory.length - 1]?.question || "")}>
                      Retry
                    </Button>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Bottom Chat Input Form */}
          <div className="p-3 sm:p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50">
            <ChatInput
              onSend={handleSendMessage}
              disabled={!isLoaded || isLoading}
              placeholder={
                isLoaded
                  ? "Ask a question about the document..."
                  : "Upload a PDF document to enable chat..."
              }
              isLoading={isLoading}
            />
          </div>
        </div>
      </div>

      {/* Confirmation Dialogs */}
      <ConfirmAlertDialog
        open={clearAllOpen}
        onOpenChange={setClearAllOpen}
        title="Clear All Sessions?"
        description="This will delete all saved chat history sessions stored on this device."
        confirmLabel="Clear All"
        onConfirm={handleClearAllConfirmed}
      />
      <ConfirmAlertDialog
        open={sessionToDelete !== null}
        onOpenChange={(open) => !open && setSessionToDelete(null)}
        title="Delete Session?"
        description={`Are you sure you want to delete session "${sessionToDelete}"?`}
        confirmLabel="Delete"
        onConfirm={() => {
          if (sessionToDelete) handleDeleteSession(sessionToDelete);
        }}
      />
    </div>
  );
}
