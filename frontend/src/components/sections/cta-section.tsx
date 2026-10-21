import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SectionWrapper } from "@/components/layout/page-wrapper";

export function CTASection() {
  const navigate = useNavigate();
  return (
    <SectionWrapper id="cta">
      <div className="flex flex-col items-start justify-between gap-7 border-t border-[var(--border-color)] py-8 sm:flex-row sm:items-center">
        <div><h2 className="editorial-title text-3xl sm:text-4xl">Start with a question.</h2><p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">Gather your papers. See where the evidence leads.</p></div>
        <Button size="lg" onClick={() => navigate("/chat")} className="w-full sm:w-auto">Launch Research Analyzer <ArrowRight className="h-4 w-4" /></Button>
      </div>
    </SectionWrapper>
  );
}
