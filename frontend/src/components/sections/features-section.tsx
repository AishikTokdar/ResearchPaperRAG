import { SectionWrapper } from "@/components/layout/page-wrapper";

const capabilities = [
  { title: "Build a focused reading list", description: "Search arXiv, Crossref, Semantic Scholar, OpenAlex, PubMed, and DOAJ. Review recent results, open the original papers, and select up to five sources. You can also upload your own PDFs." },
  { title: "Read the connections", description: "Compare methods and findings across papers. The report brings together shared limitations, contradictions, and research gaps, with citations back to the available evidence." },
  { title: "Keep the work moving", description: "Watch the analysis progress, ask a follow-up question, and take the report into your own writing. Copy the full text or export a PDF, Markdown, or plain text file." },
];

export function FeaturesSection() {
  return (
    <SectionWrapper id="features" className="reading-capabilities">
      <div className="grid gap-8 lg:grid-cols-[1fr_2fr] lg:gap-20">
        <div><p className="section-kicker">Working with your sources</p><h2 className="editorial-title text-3xl sm:text-4xl">Less scattered reading.<br />More room to think.</h2><p className="mt-5 max-w-sm text-sm leading-7 text-[var(--text-muted)]">A place to work through a small set of papers before deciding where to go next.</p></div>
        <div className="divide-y divide-[var(--border-color)] border-t border-[var(--border-color)]">
          {capabilities.map(item => <article key={item.title} className="py-6 first:pt-5"><h3 className="text-lg font-medium tracking-tight">{item.title}</h3><p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)]">{item.description}</p></article>)}
        </div>
      </div>
    </SectionWrapper>
  );
}
