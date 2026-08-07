import {
  FileText,
  Search,
  Brain,
  Layers,
  Workflow,
  Radio,
  RefreshCw,
  BookOpen,
  HardDrive,
  Container,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { SectionWrapper } from "@/components/layout/page-wrapper";
import { FEATURES } from "@/lib/constants";

const featureIcons: LucideIcon[] = [
  FileText,
  Search,
  Brain,
  Layers,
  Workflow,
  Radio,
  RefreshCw,
  BookOpen,
  HardDrive,
  Container,
];

export function FeaturesSection() {
  return (
    <SectionWrapper id="features">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          Key Capabilities &amp; Architecture
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Everything required for production-ready document retrieval, local vector search, and failover model inference.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURES.map((feature, index) => {
          const Icon = featureIcons[index % featureIcons.length];
          return (
            <SpotlightCard key={feature.title} spotlightColor="rgba(16, 185, 129, 0.12)">
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200/60 dark:border-emerald-800/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
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
