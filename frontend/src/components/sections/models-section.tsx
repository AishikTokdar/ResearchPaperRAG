import { Globe, Zap, Sparkles, Library, Cpu, Layers } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { Badge } from "@/components/ui/badge";
import { SectionWrapper } from "@/components/layout/page-wrapper";

type ProviderBlock = {
  name: string;
  icon: LucideIcon;
  description: string;
  models: string[];
  badge: string;
};

const providers: ProviderBlock[] = [
  {
    name: "Google Gemini (Free)",
    icon: Sparkles,
    description: "Free tier via Google AI Studio — Gemini 2.5 Flash, Flash-Lite, Pro, and 2.0 Flash.",
    models: ["Gemini 2.5 Flash", "Gemini 2.5 Flash-Lite", "Gemini 2.5 Pro", "Gemini 2.0 Flash"],
    badge: "Primary Free",
  },
  {
    name: "Groq LPU (Free)",
    icon: Zap,
    description: "Free ultra-fast inference on Groq Cloud LPU hardware.",
    models: ["Llama 3.3 70B", "Llama 3.1 8B", "Mixtral 8x7B", "DeepSeek R1 70B"],
    badge: "Fast Free",
  },
  {
    name: "Cerebras (Free)",
    icon: Cpu,
    description: "Free 2000+ tokens/sec inference on Cerebras Wafer-Scale Engine.",
    models: ["Llama 3.3 70B", "Llama 3.1 8B"],
    badge: "Ultra Fast",
  },
  {
    name: "SambaNova (Free)",
    icon: Layers,
    description: "Free Cloud inference powered by SambaNova SN40L reconfigurable chips.",
    models: ["Llama 3.3 70B", "DeepSeek R1 70B", "Qwen 2.5 72B"],
    badge: "High Speed",
  },
  {
    name: "Hugging Face (Free)",
    icon: Library,
    description: "Free serverless open-weight models via Hugging Face router.",
    models: ["Mistral 7B", "Zephyr 7B", "Llama 3 8B", "Qwen 2.5 Coder"],
    badge: "Free Router",
  },
  {
    name: "OpenRouter (Free Tier)",
    icon: Globe,
    description: "100% free-tier zero-credit models via OpenRouter.",
    models: ["Llama 3.3 70B Free", "Gemini 2.0 Flash Free", "DeepSeek R1 Free", "Qwen 2.5 72B Free"],
    badge: "Free Tier",
  },
];

export function ModelsSection() {
  return (
    <SectionWrapper id="models">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          Supported AI Models &amp; Providers
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Six free-tier AI providers offering sub-second responses with zero costs and automatic failover.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {providers.map((provider) => {
          const Icon = provider.icon;
          return (
            <SpotlightCard key={provider.name} spotlightColor="rgba(59, 130, 246, 0.12)">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/50 border border-blue-200/60 dark:border-blue-800/60 flex items-center justify-center text-blue-600 dark:text-blue-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                      {provider.name}
                    </h3>
                  </div>
                  <Badge variant="success" size="sm">
                    {provider.badge}
                  </Badge>
                </div>
                <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {provider.description}
                </p>
                <div className="pt-2 border-t border-zinc-200 dark:border-zinc-800">
                  <div className="flex flex-wrap gap-1">
                    {provider.models.map((m) => (
                      <span
                        key={m}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 font-mono"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </SpotlightCard>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
