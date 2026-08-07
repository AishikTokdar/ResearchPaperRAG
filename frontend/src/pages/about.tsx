import {
  Layers,
  Shield,
  Cpu,
  Database,
  Globe,
  Code2,
} from "lucide-react";
import { PageWrapper, SectionWrapper } from "@/components/layout/page-wrapper";
import { CTASection } from "@/components/sections";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { APP_CONFIG, SOCIAL_LINKS } from "@/lib/constants";

const architectureHighlights = [
  {
    icon: Layers,
    title: "7-Agent RAG Pipeline",
    description:
      "Queries flow through Extractor, Analyzer, Preprocessor, Optimizer, Synthesizer, Validator, and Assembler agents.",
  },
  {
    icon: Globe,
    title: "Multi-Provider Failover",
    description:
      "Automated fallback chain between OpenRouter, Groq, Gemini, Hugging Face, and OpenAI.",
  },
  {
    icon: Database,
    title: "FAISS Vector Search",
    description:
      "Sub-millisecond similarity search across document text chunk embeddings.",
  },
  {
    icon: Shield,
    title: "Validation Layer",
    description:
      "Automated output verification for coherence, citation integrity, and length boundaries.",
  },
  {
    icon: Code2,
    title: "TypeScript + FastAPI",
    description:
      "Full type-safety across React frontend components and Pydantic backend models.",
  },
  {
    icon: Cpu,
    title: "Isolated Vector Sessions",
    description:
      "Anonymous per-browser session isolation preventing document data leakage.",
  },
];

export function AboutPage() {
  return (
    <PageWrapper>
      <SectionWrapper>
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
          <Badge variant="outline" className="px-3 py-1">
            System Architecture & Design
          </Badge>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
            About {APP_CONFIG.name}
          </h1>
          <p className="text-base sm:text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed">
            {APP_CONFIG.description} Built for production reliability, full source control transparency, and privacy.
          </p>
        </div>

        {/* Highlights Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {architectureHighlights.map((item) => {
            const Icon = item.icon;
            return (
              <GlassCard key={item.title} variant="hover" padding="default">
                <GlassCardContent className="space-y-3">
                  <div className="p-2.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 w-fit">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                    {item.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                    {item.description}
                  </p>
                </GlassCardContent>
              </GlassCard>
            );
          })}
        </div>

        {/* Repository info */}
        <div className="max-w-4xl mx-auto mb-16">
          <GlassCard padding="lg" className="text-center space-y-4">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              Open Source Architecture
            </h2>
            <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto leading-relaxed">
              ResearchPaperRAG is completely open source under the MIT license. Inspect source code, run locally with Docker, or customize retrieval parameters directly.
            </p>
            <div>
              <a
                href={SOCIAL_LINKS.repository}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
              >
                View Repository on GitHub
              </a>
            </div>
          </GlassCard>
        </div>

        <CTASection />
      </SectionWrapper>
    </PageWrapper>
  );
}
