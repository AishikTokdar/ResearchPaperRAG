import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Filter } from "lucide-react";
import { Button, Badge, AnimatedGridPattern, BorderBeam, ScrambleText } from "@/components/ui";

export function HeroSection() {
  const navigate = useNavigate();

  return (
    <section className="relative py-16 sm:py-24 overflow-hidden">
      <AnimatedGridPattern />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="flex flex-col items-center max-w-4xl"
        >
          <div className="relative inline-block mb-6">
            <Badge variant="outline" className="px-4 py-1.5 text-xs font-semibold uppercase tracking-wider bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20">
              <Filter className="w-3.5 h-3.5 mr-1.5 text-indigo-500" />
              Automated Academic Literature Search &amp; ResearchPaper RAG Synthesis
            </Badge>
            <BorderBeam size={140} duration={8} colorFrom="#6366f1" colorTo="#3b82f6" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight leading-[1.1] mb-6">
            Discover Research Gaps with{" "}
            <span className="text-indigo-600 dark:text-indigo-400">
              <ScrambleText text="ResearchPaper RAG" />
            </span>
          </h1>

          <p className="text-base sm:text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed mb-8 max-w-3xl">
            Query 6 free academic sources (arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, DOAJ) across the last 3 publication years (2024-2026), ingest up to 5 papers, and generate structured 8-layer literature synthesis reports with grounded follow-up chat.
          </p>

          <div className="flex flex-wrap justify-center gap-2 mb-10 text-xs font-medium">
            <span className="px-2.5 py-1 rounded-full bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20">arXiv</span>
            <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">Crossref</span>
            <span className="px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/20">Semantic Scholar</span>
            <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-500/20">OpenAlex</span>
            <span className="px-2.5 py-1 rounded-full bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/20">PubMed (Healthcare)</span>
            <span className="px-2.5 py-1 rounded-full bg-orange-500/10 text-orange-700 dark:text-orange-400 border border-orange-500/20">DOAJ</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3.5">
            <Button size="lg" onClick={() => navigate("/chat")} className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white font-bold shadow-md px-8 py-6 text-base">
              Start Research Analysis
              <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>

          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 w-full pt-8 border-t border-zinc-200 dark:border-zinc-800">
            {[
              { value: "6 Free APIs", label: "Academic Sources" },
              { value: "2024–2026", label: "3-Year Literature Window" },
              { value: "8 Layers", label: "Structured Analysis" },
              { value: "5 Papers", label: "Max Knowledge Base" },
            ].map((stat, idx) => (
              <div key={idx} className="text-center space-y-1">
                <div className="text-xl sm:text-2xl font-extrabold text-indigo-600 dark:text-indigo-400 font-mono">{stat.value}</div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
