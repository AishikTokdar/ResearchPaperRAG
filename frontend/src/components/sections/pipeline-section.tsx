import {
  Download,
  Filter,
  Sparkles,
  SlidersHorizontal,
  Brain,
  ShieldCheck,
  Package,
} from "lucide-react";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { SectionWrapper } from "@/components/layout/page-wrapper";

const pipelineSteps = [
  { name: "Extractor", description: "Retrieves document chunks from FAISS vector store using similarity search.", icon: Download, badge: "Retrieval" },
  { name: "Analyzer", description: "Filters low-quality chunks and scores remaining context for relevance.", icon: Filter, badge: "Quality" },
  { name: "Preprocessor", description: "Normalizes unicode, collapses whitespace, and cleans text structure.", icon: Sparkles, badge: "Clean" },
  { name: "Optimizer", description: "Reorders chunks by similarity score to maximize context window utility.", icon: SlidersHorizontal, badge: "Optimize" },
  { name: "Synthesizer", description: "Generates grounded response using LLM based on context and query.", icon: Brain, badge: "Generate" },
  { name: "Validator", description: "Quality-checks generated output for coherence and uncertainty markers.", icon: ShieldCheck, badge: "Verify" },
  { name: "Assembler", description: "Packages final response with source citations, page numbers, and model metadata.", icon: Package, badge: "Output" },
];

export function PipelineSection() {
  return (
    <SectionWrapper id="pipeline">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          7-Agent RAG Pipeline Architecture
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Every query passes through seven specialized background stages for factual accuracy.
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-3">
        {pipelineSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <GlassCard key={step.name} variant="hover" padding="sm" className="border-zinc-200 dark:border-zinc-800">
              <GlassCardContent className="flex items-center gap-4">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-mono text-xs font-bold shrink-0">
                  0{index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <Icon className="w-4 h-4 text-zinc-500" />
                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {step.name}
                    </h3>
                    <Badge variant="secondary" size="sm">
                      {step.badge}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 truncate">
                    {step.description}
                  </p>
                </div>
              </GlassCardContent>
            </GlassCard>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
