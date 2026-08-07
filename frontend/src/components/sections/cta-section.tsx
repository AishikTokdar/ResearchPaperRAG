import { useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, Check } from "lucide-react";
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
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
              <Sparkles className="w-3.5 h-3.5 text-zinc-500" />
              Ready to get started?
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
              Start Chatting with Your Documents Today
            </h2>

            <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto leading-relaxed">
              Upload any PDF document to begin context extraction and instant question answering.
            </p>

            <div>
              <Button size="lg" onClick={() => navigate("/chat")}>
                Launch Chat App
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4 text-xs font-medium text-zinc-600 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800">
              {["No Signup Required", "100% Open Source", "Device-Local Data Privacy"].map((item) => (
                <span key={item} className="inline-flex items-center gap-1.5">
                  <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
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
