import { PageWrapper } from "@/components/layout/page-wrapper";
import {
  HeroSection,
  FeaturesSection,
  HowItWorksSection,
  PipelineSection,
  ModelsSection,
  TechStackSection,
  CTASection,
} from "@/components/sections";

export function HomePage() {
  return (
    <PageWrapper showBackground showFooter className="w-full overflow-x-clip">
      <HeroSection />
      <HowItWorksSection />
      <FeaturesSection />
      <section className="technical-notes mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" aria-labelledby="technical-notes-title">
        <div className="mb-6">
          <h2 id="technical-notes-title" className="text-2xl font-medium tracking-tight">For a closer look</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">Processing, model support, and the tools behind the workspace.</p>
        </div>
        <details><summary>How papers are processed</summary><PipelineSection /></details>
        <details><summary>Models and providers</summary><ModelsSection /></details>
        <details><summary>Technology and architecture</summary><TechStackSection /></details>
      </section>
      <CTASection />
    </PageWrapper>
  );
}

export default HomePage;
