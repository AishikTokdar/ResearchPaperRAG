import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Header } from "./header";
import { Footer } from "./footer";

export interface PageWrapperProps {
  children: React.ReactNode;
  showBackground?: boolean;
  showFooter?: boolean;
  className?: string;
  noAnimation?: boolean;
  clipHorizontal?: boolean;
}

const pageVariants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.15,
    },
  },
};

export function PageWrapper({
  children,
  showFooter = true,
  className,
  noAnimation = false,
  clipHorizontal = true,
}: PageWrapperProps) {
  const content = (
    <main className={cn("flex-1 min-h-0", className)}>{children}</main>
  );

  return (
    <div
      className={cn(
        "min-h-screen w-full flex flex-col relative bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors duration-250",
        clipHorizontal ? "overflow-x-clip" : "overflow-x-visible",
      )}
    >
      <Header />

      {noAnimation ? (
        content
      ) : (
        <motion.div
          className="flex-1 min-h-0 flex flex-col"
          initial="initial"
          animate="animate"
          exit="exit"
          variants={pageVariants}
        >
          {content}
        </motion.div>
      )}

      {showFooter && <Footer />}
    </div>
  );
}

export interface SectionWrapperProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export function SectionWrapper({
  children,
  className,
  id,
}: SectionWrapperProps) {
  return (
    <section
      id={id}
      className={cn(
        "w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16",
        className,
      )}
    >
      {children}
    </section>
  );
}
