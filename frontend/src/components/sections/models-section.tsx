import modelCatalog from "@/lib/model-catalog.json";
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

const icons: Record<string, LucideIcon> = { gemini: Sparkles, groq: Zap, cerebras: Cpu, sambanova: Layers, huggingface: Library, openrouter: Globe };
const labels: Record<string, string> = { gemini: "Google Gemini", groq: "Groq", cerebras: "Cerebras", sambanova: "SambaNova", huggingface: "Hugging Face", openrouter: "OpenRouter" };
const providers: ProviderBlock[] = modelCatalog.providers.map(provider => ({
  name: labels[provider.name], icon: icons[provider.name],
  description: provider.access_tier === "free" ? "Free API tier, subject to account eligibility and quotas." : provider.access_tier === "trial" ? "Trial credits. Requires an explicit server opt-in; excluded from free fallback." : "Purchased credits. Requires an explicit server opt-in; excluded from free fallback.",
  models: provider.models.map(model => model.name),
  badge: provider.access_tier === "free" ? "Free tier" : provider.access_tier === "trial" ? "Trial" : "Credits",
}));

export function ModelsSection() {
  return (
    <SectionWrapper className="editorial-section" id="models">
      <div className="mb-12 text-center">
        <p className="section-kicker">Model support</p>
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          Supported AI Models &amp; Providers
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Four providers with documented free API tiers, plus two optional credit-based integrations. The workspace shows which are configured on this server.
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
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-500 dark:text-zinc-400">
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
