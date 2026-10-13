export const ANALYSIS_STAGES = [
  { id: "prepare", title: "Validate request", detail: "Check selected sources and documents" },
  { id: "sources", title: "Read source documents", detail: "Download papers and extract PDF text" },
  { id: "index", title: "Build knowledge base", detail: "Chunk, embed and index the passages" },
  { id: "retrieve", title: "Find supporting evidence", detail: "Select passages for the report" },
  { id: "generate", title: "Generate the report", detail: "Write the eight research sections" },
  { id: "verify", title: "Check & finalize", detail: "Validate citation IDs and prepare the result" },
] as const;

export const REPORT_SECTIONS = ["Literature Summary", "Trend Detection", "Common Methods", "Limitations", "Contradictions", "Research Gaps", "Future Directions", "Novel Paper Suggestions"];
export type AnalysisStage = typeof ANALYSIS_STAGES[number]["id"] | "complete";
export type AnalysisStatus = "idle" | "running" | "complete" | "error";
export interface AnalysisProgress {
  stage: AnalysisStage;
  percent: number;
  message: string;
  current_section?: number;
  sections_started: number[];
  sections_completed: number[];
  documents_completed?: number;
  documents_total?: number;
  document_name?: string;
  words_generated?: number;
  chunks?: number;
  elapsed_seconds?: number;
  limited?: boolean;
}
export const INITIAL_ANALYSIS_PROGRESS: AnalysisProgress = {
  stage: "prepare", percent: 0, message: "Sending sources to the analysis pipeline",
  sections_started: [], sections_completed: [],
};

export function mergeAnalysisProgress(current: AnalysisProgress, update: Partial<AnalysisProgress>): AnalysisProgress {
  const validStage = ANALYSIS_STAGES.some(({ id }) => id === update.stage) || update.stage === "complete";
  const sections = (value: number[] | undefined, previous: number[]) => Array.isArray(value)
    ? [...new Set(value.filter((id) => Number.isInteger(id) && id >= 1 && id <= 8))] : previous;
  return {
    ...current, ...update,
    stage: validStage ? update.stage! : current.stage,
    percent: Number.isFinite(update.percent) ? Math.max(current.percent, Math.min(99, update.percent!)) : current.percent,
    sections_started: sections(update.sections_started, current.sections_started),
    sections_completed: sections(update.sections_completed, current.sections_completed),
  };
}

export function formatElapsed(seconds: number): string {
  const value = Math.max(0, Math.floor(seconds));
  return value < 60 ? `${value}s` : `${Math.floor(value / 60)}m ${String(value % 60).padStart(2, "0")}s`;
}

export function estimateRemaining(elapsed: number, percent: number, baseline: number): string {
  if (elapsed > baseline * 1.5) return "Taking longer than estimated";
  const fractionLeft = Math.max(0, 1 - percent / 100);
  const milestoneRemaining = baseline * fractionLeft;
  const observedRemaining = percent >= 10 && elapsed >= 10 ? elapsed / (percent / 100) * fractionLeft : milestoneRemaining;
  const remaining = Math.max(5, milestoneRemaining * 0.5 + observedRemaining * 0.5);
  if (remaining < 60) return `~${Math.max(5, Math.round(remaining * 0.8 / 5) * 5)}–${Math.ceil(remaining * 1.3 / 5) * 5}s`;
  return `~${Math.max(1, Math.floor(remaining * 0.8 / 60))}–${Math.max(2, Math.ceil(remaining * 1.3 / 60))} min`;
}
