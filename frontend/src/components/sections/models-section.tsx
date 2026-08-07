import { Globe, Sparkles, Library, Cpu, Layers, Zap } from "lucide-react";
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
    name: "Groq LPU (Primary Free)",
    icon: Zap,
    description: "Free tier via Google AI Studio — Gemini 2.5 Flash, Flash-Lite, Pro, and 2.0 Flash.",
    models: ["GPT-OSS 120B", "GPT-OSS 20B", "Qwen 3.6 27B"],
    badge: "Primary",
  },
  {
    name: "Google Gemini (Second)",
    icon: Sparkles,
    description: "Second-choice fallback via Google AI Studio's free tier.",
    models: ["Gemini 3.6 Flash", "Gemini 3.5 Flash", "Gemini 3.5 Flash-Lite", "Gemini 3.1 Flash-Lite"],
    badge: "Second Choice",
  },
  {
    name: "Cerebras (Free)",
    icon: Cpu,
    description: "Free 2000+ tokens/sec inference on Cerebras Wafer-Scale Engine.",
    models: ["GPT-OSS 120B", "Gemma 4 31B", "Qwen 3 32B"],
    badge: "Ultra Fast",
  },
  {
    name: "SambaNova (Free)",
    icon: Layers,
    description: "Free Cloud inference powered by SambaNova SN40L reconfigurable chips.",
    models: ["DeepSeek V3", "DeepSeek R1", "Llama 4 Maverick", "Llama 4 Scout"],
    badge: "High Speed",
  },
  {
    name: "Hugging Face (Free)",
    icon: Library,
    description: "Free serverless open-weight models via Hugging Face router.",
    models: ["Gemma 4 31B", "GPT-OSS 120B", "Qwen 3.5 27B"],
    badge: "Free Router",
  },
  {
    name: "OpenRouter (Free Tier)",
    icon: Globe,
    description: "100% free-tier zero-credit models via OpenRouter.",
    models: ["GPT-OSS 120B Free", "Gemini 3.1 Flash-Lite Free", "GLM 4.7 Free", "Auto Free Router"],
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
