import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { REPORT_SECTIONS } from "@/lib/analysis-progress";

export function HeroSection() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();
  return (
    <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8 lg:py-24">
      <motion.div initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="grid items-start gap-12 lg:grid-cols-[1.4fr_1fr] lg:gap-24">
        <div>
          <p className="section-kicker mb-6">A workspace for the literature</p>
          <h1 className="editorial-title max-w-3xl text-5xl leading-[1.08] sm:text-6xl lg:text-7xl">Read across papers.<br />Find your next question.</h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-zinc-600 dark:text-zinc-400">Bring related studies into one workspace. Compare their methods, examine what they leave unanswered, and trace the findings back to your sources.</p>
          <Button size="lg" onClick={() => navigate("/chat")} className="mt-8 w-full px-6 sm:w-auto">Start Research Analysis <ArrowRight className="h-4 w-4" /></Button>
          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3 text-sm text-[var(--text-muted)]"><span>Search or bring your own PDFs.</span><a href="#how-it-works" className="inline-flex min-h-8 items-center underline underline-offset-4 hover:text-[var(--text-main)]">See the workflow</a></div>
        </div>
        <aside className="report-specimen lg:mt-4" aria-labelledby="report-outline-title">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--border-color)] pb-4 text-xs text-[var(--text-muted)]"><span>Report structure</span><span>8 sections</span></div>
          <h2 id="report-outline-title" className="editorial-title mb-3 mt-6 text-3xl">A considered view<br />of your sources.</h2>
          <p className="mb-5 text-sm leading-6 text-[var(--text-muted)]">One report to read across the studies you choose.</p>
          <ol className="divide-y divide-[var(--border-color)]">
            {REPORT_SECTIONS.map((section, index) => <li key={section} className="flex items-baseline gap-4 py-2.5"><span className="font-mono text-xs text-[var(--text-muted)]">{String(index + 1).padStart(2, "0")}</span><span className="text-sm">{section}</span></li>)}
          </ol>
          <p className="mt-5 border-t border-[var(--border-color)] pt-4 text-xs leading-5 text-[var(--text-muted)]">Follow up with questions. Copy or export as PDF, Markdown, or text.</p>
        </aside>
      </motion.div>
      <div className="mt-14 border-t border-[var(--border-color)] pt-6 sm:mt-20">
        <p className="text-xs text-zinc-500 dark:text-zinc-400">Literature from</p>
        <p className="mt-3 text-sm leading-7 text-zinc-600 dark:text-zinc-400">arXiv <span className="mx-2 text-zinc-400">/</span> Crossref <span className="mx-2 text-zinc-400">/</span> Semantic Scholar <span className="mx-2 text-zinc-400">/</span> OpenAlex <span className="mx-2 text-zinc-400">/</span> PubMed <span className="mx-2 text-zinc-400">/</span> DOAJ</p>
      </div>
    </section>
  );
}
