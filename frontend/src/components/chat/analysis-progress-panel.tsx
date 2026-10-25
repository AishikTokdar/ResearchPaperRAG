import { motion, useReducedMotion } from "framer-motion";
import { Check, Circle, Loader2, Clock3, ArrowRight, AlertCircle, FileText } from "lucide-react";
import { ANALYSIS_STAGES, REPORT_SECTIONS, estimateRemaining, formatElapsed, type AnalysisProgress, type AnalysisStatus } from "@/lib/analysis-progress";

interface ProgressProps {
  progress: AnalysisProgress;
  status: AnalysisStatus;
  elapsed: number;
  baseline: number;
  error: string | null;
}

export function AnalysisProgressPanel({ progress, status, elapsed, baseline, error }: ProgressProps) {
  const reducedMotion = useReducedMotion();
  const running = status === "running";
  const complete = status === "complete";
  const failed = status === "error";
  const active = complete ? ANALYSIS_STAGES.length : ANALYSIS_STAGES.findIndex(({ id }) => id === progress.stage);
  const next = ANALYSIS_STAGES[active + 1];
  const percent = complete ? 100 : progress.percent;
  return (
    <div className="space-y-5 border-t border-zinc-200 pt-5 dark:border-zinc-800">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Analysis progress</p>
          <p className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100" role="status" aria-live="polite">
            {complete ? (progress.limited ? "Ready · limited evidence" : "Your report is ready") : failed ? "Analysis stopped" : running ? `Step ${active + 1} of ${ANALYSIS_STAGES.length}` : "Ready when you are"}
          </p>
        </div>
        <span className={`shrink-0 text-3xl font-bold tabular-nums tracking-tight ${complete ? "text-emerald-700 dark:text-emerald-400" : "text-indigo-600 dark:text-indigo-400"}`}>{percent}<span className="ml-0.5 text-lg">%</span></span>
      </div>
      <div>
        <div role="progressbar" aria-label="Estimated overall analysis progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-valuetext={`${percent} percent. ${progress.message}`} className="h-2.5 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800">
          <motion.div initial={false} animate={{ width: `${percent}%` }} transition={{ duration: reducedMotion ? 0 : 0.5, ease: "easeOut" }} className={`h-full rounded-full ${failed ? "bg-rose-500" : complete ? "bg-emerald-500" : "bg-indigo-600"}`} />
        </div>
        <p className="mt-2 text-xs leading-relaxed text-zinc-500">{complete ? "Final result received and ready to read." : "Estimated overall progress, based on processing milestones."}</p>
      </div>
      {status !== "idle" && <div className="grid grid-cols-2 gap-2.5">
        <div className="min-w-0 rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950/50">
          <span className="flex items-center gap-1.5 text-xs font-medium text-zinc-500"><Clock3 className="h-3 w-3" aria-hidden="true" /> Elapsed</span>
          <p className="mt-1 text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">{formatElapsed(elapsed)}</p>
        </div>
        <div className="min-w-0 rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950/50">
          <span className="text-xs font-medium text-zinc-500">Estimated remaining</span>
          <p className="mt-1 break-words text-sm font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">{complete ? "Complete" : failed ? "Stopped" : estimateRemaining(elapsed, percent, baseline)}</p>
        </div>
      </div>}
      {(running || failed) && <div className={`rounded-xl border p-3.5 ${failed ? "border-rose-500/25 bg-rose-500/5" : "border-indigo-500/20 bg-indigo-500/5"}`}>
        <div className="flex items-start gap-2.5">
          {failed ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" /> : <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-indigo-500 motion-reduce:animate-none" />}
          <div className="min-w-0">
            <p className="text-xs font-semibold leading-relaxed text-zinc-900 dark:text-zinc-100">{failed ? error : progress.message}</p>
            {running && progress.stage === "sources" && progress.document_name && <p className="mt-1 break-words text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">{progress.document_name}</p>}
            {running && <p className="mt-1.5 text-xs text-zinc-500">{progress.words_generated ? `${progress.words_generated.toLocaleString()} words drafted` : progress.documents_total ? `${progress.documents_completed ?? 0} of ${progress.documents_total} sources read` : "Updates arrive as work completes"}</p>}
          </div>
        </div>
      </div>}
      {status !== "idle" && <ol className="space-y-1" aria-label="Analysis stages">
        {ANALYSIS_STAGES.map((step, index) => {
          const done = index < active;
          const current = index === active;
          return <li key={step.id} aria-current={current ? "step" : undefined} className={`flex items-start gap-3 rounded-lg px-2 py-2.5 ${current ? "bg-zinc-100 dark:bg-zinc-800/70" : ""}`}>
            <div className="mt-0.5 shrink-0">{done ? <Check className="h-4 w-4 text-emerald-500" /> : current && running ? <Loader2 className="h-4 w-4 animate-spin text-indigo-500 motion-reduce:animate-none" /> : current && failed ? <AlertCircle className="h-4 w-4 text-rose-500" /> : <Circle className="h-4 w-4 text-zinc-300 dark:text-zinc-700" />}</div>
            <div className="min-w-0 flex-1"><p className={`text-xs font-semibold ${done || current ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-500"}`}>{step.title}</p><p className="mt-0.5 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">{step.detail}</p></div>
            <span className={`shrink-0 pt-0.5 text-xs font-medium ${done ? "text-emerald-700 dark:text-emerald-400" : current ? "text-indigo-500" : "text-zinc-400 dark:text-zinc-600"}`}>{done ? "Done" : current ? failed ? "Stopped" : "Active" : "Next"}</span>
          </li>;
        })}
      </ol>}
      {running && next && <p className="flex items-start gap-2 border-t border-zinc-200 pt-3 text-xs text-zinc-500 dark:border-zinc-800"><ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Up next: {next.title}</p>}
      {running && <p className="text-xs leading-relaxed text-zinc-500">Time estimates adjust as processing advances. Provider queues or fallback attempts can take longer.</p>}
    </div>
  );
}

export function ReportGenerationPreview({ progress, status, error }: Pick<ProgressProps, "progress" | "status" | "error">) {
  const failed = status === "error";
  return <div className="space-y-6 py-2 sm:py-4" aria-busy={status === "running"}>
    <div className="flex items-start gap-3">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-indigo-500/20 bg-indigo-500/10"><FileText className="h-5 w-5 text-indigo-500" /></div>
      <div className="min-w-0"><p className="text-xs font-medium text-indigo-500">Research synthesis</p><h2 className="mt-1 text-lg font-bold tracking-tight text-zinc-900 dark:text-zinc-100 sm:text-xl">{failed ? "Let’s get your analysis back on track" : "Your report is taking shape"}</h2><p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">{failed ? error : "Follow each section as it is drafted. The final report appears here after citation checks."}</p></div>
    </div>
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-200 pb-3 dark:border-zinc-800"><p className="flex items-center gap-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300"><FileText className="h-4 w-4" /> Report outline</p><span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium tabular-nums text-zinc-500 dark:bg-zinc-800">{progress.sections_completed.length} / 8 sections drafted</span></div>
    <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {REPORT_SECTIONS.map((section, index) => {
        const done = progress.sections_completed.includes(index + 1);
        const current = !done && progress.current_section === index + 1 && progress.stage === "generate";
        return <li key={section} aria-current={current ? "step" : undefined} className={`min-w-0 rounded-xl border p-3.5 transition-colors ${current ? "border-indigo-500/40 bg-indigo-500/5 ring-1 ring-indigo-500/10" : "border-zinc-200 bg-zinc-50/60 dark:border-zinc-800 dark:bg-zinc-950/30"}`}>
          <div className="flex items-start gap-2.5"><span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-xs font-semibold tabular-nums ${done ? "bg-emerald-500/10 text-emerald-500" : current ? "bg-indigo-500/10 text-indigo-500" : "bg-zinc-200/60 text-zinc-500 dark:bg-zinc-800"}`}>{done ? <Check className="h-3.5 w-3.5" /> : String(index + 1).padStart(2, "0")}</span><div className="min-w-0"><h3 className="text-xs font-semibold leading-relaxed text-zinc-800 dark:text-zinc-200">{section}</h3><p className={`mt-1 text-xs ${current ? "text-indigo-500" : "text-zinc-500"}`}>{done ? "Drafted · citation check follows" : current ? failed ? "Stopped while drafting" : "Writing now…" : "Waiting for earlier steps"}</p></div></div>
          {current && !failed && <div aria-hidden="true" className="mt-3 space-y-1.5 pl-8"><div className="h-1.5 w-full animate-pulse rounded-full bg-indigo-500/15 motion-reduce:animate-none" /><div className="h-1.5 w-3/4 animate-pulse rounded-full bg-indigo-500/10 motion-reduce:animate-none" /></div>}
        </li>;
      })}
    </ol>
    <p className="rounded-xl border border-zinc-200 p-3 text-xs leading-relaxed text-zinc-500 dark:border-zinc-800">{failed ? "Your progress has been preserved on screen. Use Run Multi-Paper Gap Analysis to retry." : "Sections are marked as drafted when the model moves to the next heading. Progress percentages and time remaining are estimates."}</p>
  </div>;
}
