import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Cpu, Check, AlertCircle, CheckCircle2, Sparkles, Zap, Layers, Library, Globe, Filter } from "lucide-react";
import { cn } from "@/lib/utils";
import { AI_MODELS, type AIModel, type AIProvider } from "@/types";
import { API_ENDPOINTS, joinApiUrl } from "@/lib/constants";

export interface ModelSelectorProps {
  value: string;
  onChange: (model: AIModel) => void;
  disabled?: boolean;
}

const providerLabels: Record<AIProvider, { label: string; icon: React.ElementType }> = {
  gemini: { label: "Google Gemini", icon: Sparkles },
  groq: { label: "Groq LPU", icon: Zap },
  cerebras: { label: "Cerebras Engine", icon: Cpu },
  sambanova: { label: "SambaNova", icon: Layers },
  huggingface: { label: "Hugging Face", icon: Library },
  openrouter: { label: "OpenRouter Free", icon: Globe },
};

export function ModelSelector({
  value,
  onChange,
  disabled = false,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [models, setModels] = React.useState<AIModel[]>(AI_MODELS);
  const [selectedProviderFilter, setSelectedProviderFilter] = React.useState<string>("all");
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(joinApiUrl(API_ENDPOINTS.MODELS));
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled && Array.isArray(data.models) && data.models.length > 0) {
          const live: AIModel[] = data.models.map(
            (m: {
              id: string;
              name: string;
              provider: string;
              is_default: boolean;
              is_available?: boolean;
              api_key_env?: string;
            }) => ({
              id: m.id,
              name: m.name,
              provider: m.provider as AIProvider,
              isDefault: m.is_default,
              isAvailable: m.is_available ?? true,
              apiKeyEnv: m.api_key_env,
            }),
          );
          setModels(live);

          const firstAvailable = live.find((m) => m.isAvailable !== false);
          const current = live.find((m) => m.id === value);
          if (firstAvailable && (!current || current.isAvailable === false)) {
            onChange(firstAvailable);
          }
        }
      } catch {
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sortedModels = React.useMemo(() => {
    const active = models.filter((m) => m.isAvailable !== false);
    const inactive = models.filter((m) => m.isAvailable === false);
    return [...active, ...inactive];
  }, [models]);

  const availableModels = React.useMemo(() => {
    return sortedModels.filter((m) => m.isAvailable !== false);
  }, [sortedModels]);

  const hasAvailable = availableModels.length > 0;
  const selected = sortedModels.find((m) => m.id === value) ?? availableModels[0] ?? sortedModels[0];

  const groupedProviders = React.useMemo(() => {
    const map = new Map<AIProvider, AIModel[]>();
    sortedModels.forEach((m) => {
      const list = map.get(m.provider) ?? [];
      list.push(m);
      map.set(m.provider, list);
    });
    return Array.from(map.entries()).sort((a, b) => {
      const aReady = a[1].some((m) => m.isAvailable !== false);
      const bReady = b[1].some((m) => m.isAvailable !== false);
      if (aReady && !bReady) return -1;
      if (!aReady && bReady) return 1;
      return 0;
    });
  }, [sortedModels]);

  React.useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectModel = (model: AIModel) => {
    onChange(model);
    setIsOpen(false);
  };

  const handleProviderSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const prov = e.target.value;
    setSelectedProviderFilter(prov);
    if (prov !== "all") {
      const provModels = sortedModels.filter((m) => m.provider === prov);
      const readyModel = provModels.find((m) => m.isAvailable !== false) ?? provModels[0];
      if (readyModel) {
        onChange(readyModel);
      }
    }
  };

  const SelectedIcon = providerLabels[selected?.provider]?.icon ?? Cpu;

  return (
    <div ref={containerRef} className="relative w-full">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        className={cn(
          "flex items-center justify-between gap-2 px-3.5 py-2.5 rounded-xl text-xs font-medium border transition-all w-full cursor-pointer",
          "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 shadow-xs",
          "hover:bg-zinc-50 dark:hover:bg-zinc-800/80 hover:border-zinc-300 dark:hover:border-zinc-700",
          "disabled:pointer-events-none disabled:opacity-50",
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <SelectedIcon className="w-4 h-4 text-zinc-500 shrink-0" />
          <span className="truncate font-semibold">{selected?.name ?? "Select model"}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500 uppercase font-mono border border-zinc-200 dark:border-zinc-700 shrink-0">
            {selected?.provider}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 ml-1">
          {selected?.isAvailable !== false ? (
            <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 font-semibold bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md border border-emerald-200 dark:border-emerald-800/60">
              <CheckCircle2 className="w-2.5 h-2.5" />
              Ready
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-400 font-semibold bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded-md border border-amber-200 dark:border-amber-800/60">
              <AlertCircle className="w-2.5 h-2.5" />
              Key Needed
            </span>
          )}
          <ChevronDown className={cn("w-3.5 h-3.5 transition-transform text-zinc-400", isOpen && "rotate-180")} />
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.12 }}
            className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-2xl overflow-hidden max-h-96 flex flex-col"
          >
            <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-950/80 space-y-2 shrink-0">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-zinc-900 dark:text-zinc-100">Select AI Model</span>
                <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded-md border border-emerald-200 dark:border-emerald-800/40">
                  {availableModels.length} Ready
                </span>
              </div>

              <div className="relative flex items-center">
                <Filter className="w-3.5 h-3.5 absolute left-2.5 text-zinc-400 pointer-events-none" />
                <select
                  value={selectedProviderFilter}
                  onChange={handleProviderSelectChange}
                  className="w-full pl-8 pr-8 py-1.5 rounded-xl text-xs bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 appearance-none font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-zinc-400"
                >
                  <option value="all">Filter Provider: All ({sortedModels.length} models)</option>
                  {groupedProviders.map(([provKey, provModels]) => {
                    const isReady = provModels.some((m) => m.isAvailable !== false);
                    return (
                      <option key={provKey} value={provKey}>
                        {providerLabels[provKey]?.label ?? provKey} ({provModels.length} models) {isReady ? "— READY" : "— Key Needed"}
                      </option>
                    );
                  })}
                </select>
                <ChevronDown className="w-3.5 h-3.5 absolute right-2.5 text-zinc-400 pointer-events-none" />
              </div>
            </div>

            <div className="p-2 overflow-y-auto space-y-3 flex-1">
              {!hasAvailable && (
                <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-[11px] text-amber-800 dark:text-amber-300 space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-500" />
                    No API keys configured on backend
                  </div>
                  <p>Add a free key (e.g. <code className="font-mono font-bold">GROQ_API_KEY</code>) to <code className="font-mono">backend/.env</code> file.</p>
                </div>
              )}

              {groupedProviders
                .filter(([provKey]) => selectedProviderFilter === "all" || selectedProviderFilter === provKey)
                .map(([provKey, provModels]) => {
                  const provInfo = providerLabels[provKey] ?? { label: provKey, icon: Cpu };
                  const ProvIcon = provInfo.icon;
                  const hasReadyInProv = provModels.some((m) => m.isAvailable !== false);

                  return (
                    <div key={provKey} className="space-y-1">
                      <div className="flex items-center justify-between px-2 py-1 text-[11px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider bg-zinc-100/60 dark:bg-zinc-800/40 rounded-lg">
                        <div className="flex items-center gap-1.5">
                          <ProvIcon className="w-3.5 h-3.5" />
                          <span>{provInfo.label}</span>
                        </div>
                        {hasReadyInProv ? (
                          <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.2 rounded border border-emerald-200 dark:border-emerald-800/40">
                            Ready
                          </span>
                        ) : (
                          <span className="text-[9px] font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.2 rounded border border-amber-200 dark:border-amber-800/40">
                            Key Needed
                          </span>
                        )}
                      </div>

                      {provModels.map((model) => {
                        const isConfigured = model.isAvailable !== false;
                        const isSelected = model.id === value;

                        return (
                          <div
                            key={model.id}
                            role="button"
                            tabIndex={0}
                            onMouseDown={(e) => {
                              e.preventDefault();
                              handleSelectModel(model);
                            }}
                            onClick={() => handleSelectModel(model)}
                            className={cn(
                              "w-full flex items-center justify-between px-3 py-2 rounded-xl text-left text-xs transition-all cursor-pointer select-none group",
                              isConfigured
                                ? "bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                                : "opacity-50 hover:opacity-75 bg-zinc-50/50 dark:bg-zinc-950/50 text-zinc-500 dark:text-zinc-400",
                              isSelected && "bg-zinc-100 dark:bg-zinc-800 font-semibold ring-1 ring-zinc-300 dark:ring-zinc-700",
                            )}
                          >
                            <div className="min-w-0 pr-2">
                              <div className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                                {model.name}
                              </div>
                              {model.description && (
                                <p className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">
                                  {model.description}
                                </p>
                              )}
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              {isConfigured ? (
                                <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded font-mono border border-emerald-200 dark:border-emerald-800/40">
                                  Ready
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[9px] font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded font-mono border border-amber-200 dark:border-amber-800/40">
                                  Key Needed
                                </span>
                              )}
                              {isSelected && <Check className="w-4 h-4 text-emerald-500 shrink-0 ml-1" />}
                            </div>
                          </div>
                        );
                      })}
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
