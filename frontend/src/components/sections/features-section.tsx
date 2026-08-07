import {
  Search,
  Calendar,
  Layers,
  FileText,
  MessageSquare,
  Download,
  Cpu,
  Database,
  ExternalLink,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { SectionWrapper } from "@/components/layout/page-wrapper";
import { FEATURES } from "@/lib/constants";

const featureIcons: LucideIcon[] = [
  Search,
  Calendar,
  Layers,
  FileText,
  MessageSquare,
  Download,
  Cpu,
  Database,
  ExternalLink,
];

export function FeaturesSection() {
  return (
    <SectionWrapper id="features">
      <div className="mb-12 text-center space-y-3">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
          Research Capabilities &amp; Architecture
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Everything required for automated academic paper retrieval, 3-year publication filtering, vector embedding, and 8-layer LLM synthesis.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURES.map((feature, index) => {
          const Icon = featureIcons[index % featureIcons.length];
          return (
            <SpotlightCard key={feature.title} spotlightColor="rgba(99, 102, 241, 0.12)">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                  {feature.title}
                </h3>
                <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </SpotlightCard>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
