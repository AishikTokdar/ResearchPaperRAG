import { Code2, Server, Brain, Database } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { SectionWrapper } from "@/components/layout/page-wrapper";

type TechCategory = {
  name: string;
  icon: LucideIcon;
  techs: { name: string; description: string }[];
};

const techCategories: TechCategory[] = [
  {
    name: "Frontend Stack",
    icon: Code2,
    techs: [
      { name: "React 18", description: "UI Framework" },
      { name: "TypeScript 5", description: "Type Safety" },
      { name: "Tailwind CSS 3", description: "Styling" },
      { name: "Vite 5", description: "Bundler" },
      { name: "Framer Motion", description: "Transitions" },
    ],
  },
  {
    name: "Backend Framework",
    icon: Server,
    techs: [
      { name: "FastAPI", description: "ASGI Web API" },
      { name: "Python 3.11+", description: "Core Language" },
      { name: "Uvicorn", description: "ASGI Server" },
      { name: "Pydantic v2", description: "Validation" },
    ],
  },
  {
    name: "AI & Pipeline",
    icon: Brain,
    techs: [
      { name: "LangChain", description: "RAG Pipeline" },
      { name: "OpenRouter", description: "API Gateway" },
      { name: "SSE Streaming", description: "Real-time Responses" },
      { name: "SentenceTransformers", description: "Local Embeddings" },
    ],
  },
  {
    name: "Vector & Storage",
    icon: Database,
    techs: [
      { name: "FAISS", description: "Vector Store" },
      { name: "PyPDF", description: "PDF Parsing" },
      { name: "IndexedDB", description: "Device-local History" },
    ],
  },
];

export function TechStackSection() {
  return (
    <SectionWrapper id="tech-stack">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          Technology Stack
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Modern libraries and tools powering the document intelligence engine.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {techCategories.map((cat) => {
          const Icon = cat.icon;
          return (
            <GlassCard key={cat.name} variant="hover" padding="default">
              <GlassCardContent className="space-y-4">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
                    {cat.name}
                  </h3>
                </div>

                <div className="flex flex-wrap gap-2">
                  {cat.techs.map((tech) => (
                    <Badge key={tech.name} variant="outline" size="sm">
                      <span className="font-semibold text-zinc-900 dark:text-zinc-100">{tech.name}</span>
                      <span className="ml-1 text-zinc-500">• {tech.description}</span>
                    </Badge>
                  ))}
                </div>
              </GlassCardContent>
            </GlassCard>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
