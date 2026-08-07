import * as React from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Menu,
  X,
  FileText,
  MessageSquare,
  Info,
  Github,
  Sun,
  Moon,
  BookOpen,
  LineChart,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { APP_CONFIG, NAV_LINKS, SOCIAL_LINKS } from "@/lib/constants";
import { useHealth } from "@/hooks/use-health";
import { useTheme } from "@/context/theme-context";
import { ApiNavDropdown } from "@/components/layout/api-nav-dropdown";
import { joinApiUrl } from "@/lib/constants";

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const location = useLocation();
  const { status } = useHealth();
  const { isDark, toggleTheme } = useTheme();

  React.useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  const healthColor =
    status === "connected"
      ? "bg-emerald-500"
      : status === "disconnected"
        ? "bg-red-500"
        : "bg-amber-500 animate-pulse";

  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="sticky top-0 z-50 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md transition-colors"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="h-8 w-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-zinc-100 dark:text-zinc-900 font-bold text-sm transition-transform group-hover:scale-105">
              R
            </div>
            <span className="text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
              {APP_CONFIG.name}
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            {NAV_LINKS.map((link) => {
              const isActive = location.pathname === link.href;
              const iconMap: Record<string, typeof FileText> = {
                "/": FileText,
                "/chat": MessageSquare,
                "/about": Info,
              };
              const Icon = iconMap[link.href] ?? FileText;

              return (
                <Link
                  key={link.href}
                  to={link.href}
                  className={cn(
                    "flex items-center gap-1.5 text-sm font-medium transition-colors px-2.5 py-1.5 rounded-lg",
                    isActive
                      ? "text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800/60"
                      : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900",
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {link.label}
                </Link>
              );
            })}

            <ApiNavDropdown />

            <div
              className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400"
              title={`Backend Status: ${status}`}
            >
              <span className={cn("w-2 h-2 rounded-full", healthColor)} />
              <span>{status === "connected" ? "Online" : status === "disconnected" ? "Offline" : "Checking..."}</span>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              aria-label="Toggle dark/light theme"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-zinc-700" />}
            </button>

            <a
              href={SOCIAL_LINKS.repository}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              aria-label="GitHub Repository"
            >
              <Github className="w-4 h-4" />
            </a>

            <Button variant="default" size="sm" asChild>
              <Link to="/chat">Launch App</Link>
            </Button>
          </div>

          <div className="flex items-center gap-2 md:hidden">
            <button
              type="button"
              onClick={toggleTheme}
              className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 cursor-pointer"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-5 h-5 text-amber-500" /> : <Moon className="w-5 h-5 text-zinc-700" />}
            </button>
            <button
              className="p-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle Menu"
            >
              {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </nav>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-4 space-y-2"
          >
            {NAV_LINKS.map((link) => {
              const isActive = location.pathname === link.href;
              return (
                <Link
                  key={link.href}
                  to={link.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                      : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900",
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
            <a
              href={joinApiUrl("/docs")}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              <BookOpen className="w-4 h-4" />
              API Documentation
              <ExternalLink className="w-3.5 h-3.5 ml-auto opacity-50" />
            </a>
            <Link
              to="/api-status"
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              <LineChart className="w-4 h-4" />
              API Status
            </Link>
            <div className="pt-2">
              <Button variant="default" className="w-full" asChild>
                <Link to="/chat">Launch App</Link>
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
