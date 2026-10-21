import { motion, useReducedMotion } from "framer-motion";
import { SectionWrapper } from "@/components/layout/page-wrapper";

const steps = [
  { title: "Choose a question", description: "Search recent literature by topic, or upload papers you already want to study." },
  { title: "Review the sources", description: "Read the abstracts and choose up to five papers to include in your analysis." },
  { title: "Follow the analysis", description: "See the current stage, sections being drafted, and an estimate of the time remaining." },
  { title: "Read and follow up", description: "Review the report and its citations. Ask a closer question or export it for later." },
];

export function HowItWorksSection() {
  const reducedMotion = useReducedMotion();
  return <SectionWrapper id="how-it-works" className="section-band">
    <div className="mb-9 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="section-kicker">The workflow</p><h2 className="text-2xl font-medium tracking-tight sm:text-3xl">From a question to a closer reading.</h2></div><p className="max-w-xs text-sm leading-6 text-[var(--text-muted)]">Your sources stay at the centre of the process.</p></div>
    <ol className="grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">{steps.map((step, index) => <motion.li key={step.title} initial={reducedMotion ? false : { opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.2, delay: index * 0.04 }} className="border-t border-[var(--border-color)] pt-5"><span className="text-xs text-[var(--text-muted)]">Step {index + 1}</span><h3 className="mb-3 mt-4 text-base font-semibold">{step.title}</h3><p className="text-sm leading-6 text-[var(--text-muted)]">{step.description}</p></motion.li>)}</ol>
  </SectionWrapper>;
}
