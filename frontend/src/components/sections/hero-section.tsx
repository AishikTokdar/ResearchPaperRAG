import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, FileText, Brain, Zap } from "lucide-react";
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
          className="flex flex-col items-center max-w-3xl"
        >
          <div className="relative inline-block mb-6">
            <Badge variant="outline" className="px-3.5 py-1 text-xs">
              <Sparkles className="w-3.5 h-3.5 mr-1 text-emerald-500" />
              AI Document Intelligence &amp; Vector Search
            </Badge>
            <BorderBeam size={120} duration={8} colorFrom="#10b981" colorTo="#3b82f6" />
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold text-zinc-900 dark:text-zinc-100 tracking-tight leading-[1.1] mb-6">
            Intelligent PDF Chat Powered by{" "}
            <span className="text-emerald-600 dark:text-emerald-400">
              <ScrambleText text="Retrieval RAG" />
            </span>
          </h1>

          <p className="text-base sm:text-lg text-zinc-600 dark:text-zinc-400 leading-relaxed mb-8 max-w-2xl">
            Upload documents, parse context into local FAISS vector stores, and query grounded answers with automatic multi-provider model failover.
          </p>

          <div className="flex flex-wrap justify-center gap-2 mb-10">
            {[
              { icon: FileText, text: "PDF Analysis" },
              { icon: Brain, text: "7-Agent Pipeline" },
              { icon: Zap, text: "Real-time SSE Streaming" },
            ].map((f) => (
              <span
                key={f.text}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 shadow-xs"
              >
                <f.icon className="w-3.5 h-3.5 text-emerald-500" />
                {f.text}
              </span>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <Button size="lg" onClick={() => navigate("/chat")} className="w-full sm:w-auto relative group overflow-hidden">
              Get Started - Launch Chat
              <ArrowRight className="w-4 h-4 ml-1 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button variant="outline" size="lg" onClick={() => navigate("/about")} className="w-full sm:w-auto">
              View Architecture
            </Button>
          </div>

          <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 w-full pt-8 border-t border-zinc-200 dark:border-zinc-800">
            {[
              { value: "100%", label: "Open Source" },
              { value: "FAISS", label: "Vector Search" },
              { value: "50MB", label: "Max Cumulative Size" },
              { value: "SSE", label: "Live Streaming" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stat.value}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
