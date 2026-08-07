import { motion } from "framer-motion";
import { Search, CheckSquare, Database, Layers } from "lucide-react";
import { SectionWrapper } from "@/components/layout/page-wrapper";
import { HOW_IT_WORKS_STEPS } from "@/lib/constants";

const stepIcons = [Search, CheckSquare, Database, Layers];

export function HowItWorksSection() {
  return (
    <SectionWrapper id="how-it-works" className="bg-zinc-50/50 dark:bg-zinc-950/50">
      <div className="mb-12 text-center space-y-3">
        <h2 className="text-3xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight">
          How the Research Pipeline Works
        </h2>
        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          From multi-source academic query to vector database indexing and 8-layer RAG gap report synthesis.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {HOW_IT_WORKS_STEPS.map((step, idx) => {
          const Icon = stepIcons[idx % stepIcons.length];
          return (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: idx * 0.1 }}
              className="p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm relative space-y-4"
            >
              <div className="flex items-center justify-between">
                <span className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400 font-bold text-xs flex items-center justify-center font-mono">
                  0{step.step}
                </span>
                <Icon className="w-5 h-5 text-indigo-500/70" />
              </div>
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 tracking-tight">
                {step.title}
              </h3>
              <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
                {step.description}
              </p>
            </motion.div>
          );
        })}
      </div>
    </SectionWrapper>
  );
}
