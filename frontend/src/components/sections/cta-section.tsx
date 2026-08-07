import { useNavigate } from "react-router-dom";
import { ArrowRight, Search, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { SectionWrapper } from "@/components/layout/page-wrapper";

export function CTASection() {
  const navigate = useNavigate();

  return (
    <SectionWrapper id="cta">
      <div className="mx-auto max-w-4xl">
        <GlassCard variant="default" padding="lg">
          <GlassCardContent className="text-center space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              <Search className="w-3.5 h-3.5 text-indigo-500" />
              Automated Academic Gap Analysis
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
              Start Researching Academic Literature Today
            </h2>

            <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto leading-relaxed">
              Search 6 free academic sources, filter literature from 2024–2026, select up to 3 papers, and synthesize structured 8-layer research gap reports.
            </p>

            <div>
              <Button size="lg" onClick={() => navigate("/chat")} className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-8 shadow-md">
                Launch Research Analyzer
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-6 pt-4 text-xs font-medium text-zinc-600 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800">
              {["6 Free Academic APIs", "Strict 3-Year Publication Window", "Export to PDF / MD / TXT"].map((item) => (
                <span key={item} className="inline-flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-emerald-500 stroke-[2.5]" />
                  {item}
                </span>
              ))}
            </div>
          </GlassCardContent>
        </GlassCard>
      </div>
    </SectionWrapper>
  );
}
