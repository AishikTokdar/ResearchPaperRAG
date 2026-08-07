import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Cpu, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { AI_MODELS } from "@/types";

const providerEnv: Record<string, string> = {
  gemini: "GOOGLE_API_KEY (Free)",
  groq: "GROQ_API_KEY (Free)",
  cerebras: "CEREBRAS_API_KEY (Free)",
  sambanova: "SAMBANOVA_API_KEY (Free)",
  huggingface: "HF_API_KEY (Free)",
  openrouter: "OPENROUTER_API_KEY (Free)",
};

export interface ModelInfoToggleProps {
  selectedModel: string;
  activeModelName: string;
  activeProvider: string;
}

export function ModelInfoToggle({
  selectedModel,
  activeModelName,
  activeProvider,
}: ModelInfoToggleProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 shadow-sm transition-colors">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 py-3 text-left"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 shrink-0">
            <Sparkles className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Free AI Pipeline & Models
              </span>
              <span className="text-xs font-medium px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                Active: {activeModelName}
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
              {activeModelName} ({activeProvider}) — 100% Free AI Provider
            </p>
          </div>
        </div>
        <ChevronDown
          className={cn("w-4 h-4 text-zinc-400 transition-transform duration-200", open && "rotate-180")}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-zinc-200 dark:border-zinc-800 py-3 space-y-3"
          >
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              This application exclusively uses 100% Free AI provider tiers (Google Gemini Free Tier, Groq Cloud Free Tier, Hugging Face Serverless, and OpenRouter Free Tier). If a free provider rate-limits, the backend automatically switches to the next free provider.
            </p>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {AI_MODELS.map((model) => {
                const isActive = model.id === selectedModel;
                const env = providerEnv[model.provider] ?? "GOOGLE_API_KEY (Free)";
                return (
                  <div
                    key={model.id}
                    className={cn(
                      "p-2 rounded-lg border text-xs flex items-center justify-between",
                      isActive
                        ? "bg-zinc-100 dark:bg-zinc-800 border-zinc-300 dark:border-zinc-700 font-medium"
                        : "border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400",
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Cpu className="w-3.5 h-3.5" />
                      <span>{model.name}</span>
                      <span className="text-[10px] opacity-70">({model.provider})</span>
                    </div>
                    <span className="font-mono text-[10px] text-zinc-400">{env}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
