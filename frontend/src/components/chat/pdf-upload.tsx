import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  X,
  File,
  Check,
  Loader2,
  ChevronDown,
  ChevronUp,
  Layers,
} from "lucide-react";
import { cn, isValidPDF, formatFileSize } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/ui/glass-card";
import { Spinner } from "@/components/ui/spinner";
import { MAX_FILE_SIZE } from "@/lib/constants";
import type { DocumentFileMeta } from "@/types";

const PIPELINE_STEPS = [
  { id: 1, label: "Ingest & validate PDF", detail: "Verify MIME, format, and cumulative size (<= 50 MB)" },
  { id: 2, label: "Extract text layer", detail: "Pull text layer from all document pages" },
  { id: 3, label: "Semantic chunking", detail: "Split into overlapping segments" },
  { id: 4, label: "Embedding pass", detail: "Vectorize chunks for similarity search" },
  { id: 5, label: "Vector index", detail: "Update FAISS store for retrieval" },
  { id: 6, label: "Session metadata", detail: "Wire document id and counters" },
  { id: 7, label: "Handoff to chat", detail: "RAG pipeline ready for questions" },
] as const;

export interface PDFUploadProps {
  onUpload: (files: File[]) => Promise<void>;
  isUploading: boolean;
  isLoaded: boolean;
  chunksCreated?: number;
  files?: DocumentFileMeta[];
  totalFiles?: number;
  error?: string | null;
  onReset?: () => void;
}

export function PDFUpload({
  onUpload,
  isUploading,
  isLoaded,
  chunksCreated,
  files = [],
  totalFiles = 0,
  error,
  onReset,
}: PDFUploadProps) {
  const [isDragOver, setIsDragOver] = React.useState(false);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = React.useState(0);
  const [showDetails, setShowDetails] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (!isUploading) {
      if (isLoaded) {
        setCompletedSteps(PIPELINE_STEPS.length);
      } else {
        setCompletedSteps(0);
      }
      return;
    }
    setCompletedSteps(0);
    const stepMs = 380;
    const interval = window.setInterval(() => {
      setCompletedSteps((c) => {
        if (c >= PIPELINE_STEPS.length) {
          return c;
        }
        return c + 1;
      });
    }, stepMs);
    return () => window.clearInterval(interval);
  }, [isUploading, isLoaded]);

  const handleFiles = async (fileList: FileList | File[]) => {
    setValidationError(null);
    const validFiles: File[] = [];

    const incoming = Array.from(fileList);
    if (incoming.length === 0) return;

    if (incoming.length > 3) {
      setValidationError("Maximum 3 document uploads allowed per session.");
      return;
    }

    let totalSize = 0;
    for (const f of incoming) {
      if (!isValidPDF(f)) {
        setValidationError(`File '${f.name}' is not a valid PDF file.`);
        return;
      }
      if (f.size > MAX_FILE_SIZE) {
        setValidationError(`File '${f.name}' exceeds the 50 MB limit.`);
        return;
      }
      totalSize += f.size;
      validFiles.push(f);
    }

    if (totalSize > MAX_FILE_SIZE) {
      setValidationError(`Total combined size of uploaded PDFs (${formatFileSize(totalSize)}) exceeds the 50 MB limit.`);
      return;
    }

    await onUpload(validFiles);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
    e.target.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const displayError = error || validationError;
  const activeDocCount = totalFiles > 0 ? totalFiles : files.length > 0 ? files.length : isLoaded ? 1 : 0;

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,application/pdf"
        onChange={handleInputChange}
        className="hidden"
        aria-label="Upload PDF files"
      />

      <AnimatePresence mode="wait">
        {isLoaded && !isUploading ? (
          <motion.div
            key="loaded"
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="space-y-2"
          >
            {/* Prominent Big Ready Card */}
            <GlassCard variant="default" padding="default" className="border-emerald-500/50 bg-emerald-500/15 dark:bg-emerald-950/40 shadow-sm overflow-hidden">
              <div className="flex flex-col space-y-3.5">
                {/* Header Row: Status Check & Action Buttons */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="p-2 rounded-xl bg-emerald-500/25 text-emerald-600 dark:text-emerald-300 shrink-0">
                      <CheckCircle className="w-5 h-5" />
                    </div>
                    <span className="text-sm sm:text-base font-extrabold tracking-tight text-emerald-700 dark:text-emerald-300 leading-snug">
                      The RAG pipeline is ready to answer
                    </span>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => setShowDetails((prev) => !prev)}
                      className="px-2 py-1 rounded-lg text-zinc-700 dark:text-zinc-200 hover:bg-emerald-500/20 dark:hover:bg-emerald-900/40 transition-colors text-xs flex items-center gap-1 font-semibold cursor-pointer border border-emerald-500/30"
                      title={showDetails ? "Hide pipeline steps" : "View pipeline steps"}
                    >
                      <span>{showDetails ? "Hide Steps" : "Steps"}</span>
                      {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {onReset && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={onReset}
                        className="h-7 w-7 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 cursor-pointer"
                        title="Remove documents & upload new"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>

                {/* Stat Badges Row: Clear, spacious horizontal pills */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-200 text-xs font-bold border border-emerald-300/40 dark:border-emerald-700/60 shadow-xs">
                    <Layers className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>{activeDocCount} PDF{activeDocCount > 1 ? "s" : ""} Loaded</span>
                  </div>

                  {chunksCreated !== undefined && (
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800/80 text-zinc-800 dark:text-zinc-200 text-xs font-bold border border-zinc-200 dark:border-zinc-700 shadow-xs">
                      <span className="font-mono text-emerald-600 dark:text-emerald-400">{chunksCreated}</span>
                      <span>chunks indexed</span>
                    </div>
                  )}
                </div>

                {/* Active Files List */}
                {files.length > 0 && (
                  <div className="pt-2 border-t border-emerald-500/20 space-y-1">
                    {files.map((doc, idx) => (
                      <div key={idx} className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-white/70 dark:bg-zinc-900/70 text-xs">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                          <span className="font-medium text-zinc-900 dark:text-zinc-100 truncate">{doc.file_name}</span>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-zinc-500 shrink-0">
                          <span className="px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 font-mono font-semibold">
                            {doc.page_count} pgs
                          </span>
                          <span>{doc.chunks_created} chunks</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Collapsible Pipeline Details */}
                {showDetails && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="pt-2 border-t border-emerald-500/20"
                  >
                    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white/90 dark:bg-zinc-950/90 p-3 font-mono text-[11px]">
                      <ul className="space-y-1.5">
                        {PIPELINE_STEPS.map((s) => (
                          <li key={s.id} className="flex items-center justify-between text-zinc-700 dark:text-zinc-300">
                            <span className="flex items-center gap-1.5">
                              <Check className="w-3.5 h-3.5 text-emerald-500" />
                              <span className="font-semibold">{s.label}</span>
                            </span>
                            <span className="text-[10px] text-zinc-400">{s.detail}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </motion.div>
                )}
              </div>
            </GlassCard>
          </motion.div>
        ) : (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
          >
            <GlassCard
              variant="default"
              padding="default"
              className={cn(
                "transition-colors duration-200",
                isDragOver && "border-zinc-500 bg-zinc-100/50 dark:bg-zinc-800/50",
                displayError && "border-red-500/50",
              )}
            >
              <div className="flex flex-col items-stretch">
                {isUploading ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Spinner size="default" />
                      <div>
                        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                          Processing Documents...
                        </p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">
                          Validating files &amp; building FAISS vector index
                        </p>
                      </div>
                    </div>
                    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 p-3 font-mono text-[11px] leading-relaxed">
                      <ul className="space-y-1.5">
                        {PIPELINE_STEPS.map((s, i) => {
                          const done = i < completedSteps;
                          const active = i === completedSteps && completedSteps < PIPELINE_STEPS.length;
                          return (
                            <li
                              key={s.id}
                              className={cn(
                                "flex items-center gap-2 rounded px-2 py-1 transition-colors",
                                active && "bg-zinc-200/50 dark:bg-zinc-800/50",
                              )}
                            >
                              <span className="shrink-0">
                                {done ? (
                                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                                ) : active ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-900 dark:text-zinc-100" />
                                ) : (
                                  <span className="h-1.5 w-1.5 rounded-full bg-zinc-300 dark:bg-zinc-700 block ml-1" />
                                )}
                              </span>
                              <div className="min-w-0 flex-1 flex items-center justify-between">
                                <span className={cn(done ? "text-zinc-900 dark:text-zinc-100 font-medium" : "text-zinc-500 dark:text-zinc-400")}>
                                  {s.label}
                                </span>
                                <span className="text-[10px] text-zinc-400 dark:text-zinc-500 hidden sm:inline">
                                  {s.detail}
                                </span>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleClick();
                        }
                      }}
                      onClick={handleClick}
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      className={cn(
                        "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-zinc-300 dark:border-zinc-800 p-5 text-center transition-colors hover:border-zinc-400 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-900/50",
                        isDragOver && "border-zinc-900 dark:border-zinc-100 bg-zinc-100 dark:bg-zinc-800/80",
                      )}
                    >
                      <div className="mb-2 rounded-full bg-zinc-100 dark:bg-zinc-800 p-2.5 text-zinc-700 dark:text-zinc-300">
                        {isDragOver ? <File className="h-5 w-5" /> : <Upload className="h-5 w-5" />}
                      </div>
                      <h3 className="mb-1 text-xs font-semibold text-zinc-900 dark:text-zinc-100">
                        {isDragOver ? "Drop PDF file(s) here" : "Upload Document(s) (PDF)"}
                      </h3>
                      <p className="mb-2 text-[11px] text-zinc-500 dark:text-zinc-400 max-w-xs">
                        Up to <strong className="text-zinc-900 dark:text-zinc-200">3 PDFs</strong> (max combined size 50 MB)
                      </p>
                      <Button type="button" variant="outline" size="sm" className="h-7 text-xs">
                        <FileText className="mr-1.5 h-3.5 w-3.5" />
                        Select File(s)
                      </Button>
                    </div>
                  </div>
                )}

                {displayError && !isUploading && (
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 flex items-center justify-center gap-2 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 p-2 rounded-lg border border-red-200 dark:border-red-800/40"
                  >
                    <AlertCircle className="h-3.5 w-3.5 shrink-0" />
                    {displayError}
                  </motion.div>
                )}
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
