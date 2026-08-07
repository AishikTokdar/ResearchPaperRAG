import { Upload, Cpu, MessageCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { SectionWrapper } from "@/components/layout/page-wrapper";
import { HOW_IT_WORKS_STEPS } from "@/lib/constants";

const stepIcons: LucideIcon[] = [Upload, Cpu, MessageCircle];

export function HowItWorksSection() {
  return (
    <SectionWrapper id="how-it-works">
      <div className="mb-12 text-center">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight mb-3">
          How It Works
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          Three steps to process documents and generate grounded responses.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {HOW_IT_WORKS_STEPS.map((step, index) => {
          const Icon = stepIcons[index];
          return (
            <GlassCard key={step.step} variant="hover" padding="default">
              <GlassCardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-zinc-800 dark:text-zinc-200">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                    Step 0{step.step}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  {step.title}
                </h3>
                <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                  {step.description}
                </p>
              </GlassCardContent>
            </GlassCard>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
