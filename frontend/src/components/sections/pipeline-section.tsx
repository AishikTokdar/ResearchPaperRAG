import {
  FileCheck,
  FileText,
  Scissors,
  Brain,
  Database,
  Sliders,
  Sparkles,
} from "lucide-react";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { SectionWrapper } from "@/components/layout/page-wrapper";

const pipelineSteps = [
  { name: "Ingest & Validate PDF", description: "Verify MIME type, paper headers, and cumulative document size (<= 50MB).", icon: FileCheck, badge: "Validation" },
  { name: "Extract Text Layer", description: "Pull native text layers and abstracts from document pages.", icon: FileText, badge: "Extraction" },
  { name: "Semantic Chunking", description: "Split extracted text into overlapping semantic segments for dense vector retrieval.", icon: Scissors, badge: "Chunking" },
  { name: "Embedding Pass", description: "Vectorize text segments using sentence-transformers (all-MiniLM-L6-v2).", icon: Brain, badge: "Vectorize" },
  { name: "Vector Indexing", description: "Update local Chroma / FAISS vector stores for similarity search.", icon: Database, badge: "Indexing" },
  { name: "Session Metadata", description: "Wire document ID, 3-year publication filters, and active paper counters.", icon: Sliders, badge: "Session" },
  { name: "8-Layer RAG Synthesis", description: "Handoff vector context to LLM for literature summary, trend detection, and gap analysis.", icon: Sparkles, badge: "Synthesis" },
];

export function PipelineSection() {
  return (
    <SectionWrapper id="pipeline">
      <div className="mb-12 text-center space-y-3">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
          Step-by-Step RAG Processing Pipeline
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Every research paper selected passes through seven automated background stages before generating 8-layer research reports.
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-3">
        {pipelineSteps.map((step, index) => {
          const Icon = step.icon;
          return (
            <GlassCard key={step.name} variant="hover" padding="sm" className="border-zinc-200 dark:border-zinc-800">
              <GlassCardContent className="flex items-center gap-4">
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-mono text-xs font-bold shrink-0 border border-indigo-500/20">
                  0{index + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <Icon className="w-4 h-4 text-indigo-500" />
                    <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                      {step.name}
                    </h3>
                    <Badge variant="secondary" size="sm" className="bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/20 font-mono text-[10px]">
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
