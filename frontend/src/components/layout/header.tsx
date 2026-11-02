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
  RefreshCw,
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
  const { status, isOffline, isProlongedOffline, isChecking, checkNow } = useHealth();
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
      className="brand-header sticky top-0 z-50 border-b border-zinc-200 dark:border-zinc-800 bg-[var(--bg-main)] transition-colors"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-xl overflow-hidden flex items-center justify-center p-0.5 border border-zinc-200/80 dark:border-zinc-800/80 bg-zinc-950 shadow-xs group-hover:border-[var(--accent)] transition-colors">
              <img src="/logo.svg" alt="ResearchPaperRAG logo" className="h-full w-full object-contain" />
            </div>
            <span className="text-sm sm:text-base font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
              {APP_CONFIG.name}
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-3 lg:gap-5">
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
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-1.5 text-sm font-medium transition-colors px-2.5 py-2.5 rounded-lg",
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

            {status === "connected" ? (
              <div
                className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-emerald-500/20 bg-emerald-500/5 text-xs font-medium text-emerald-700 dark:text-emerald-400"
                title="Backend API: Connected & Ready"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Online</span>
              </div>
            ) : status === "disconnected" ? (
              <button
                type="button"
                onClick={() => void checkNow()}
                disabled={isChecking}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-colors cursor-pointer",
                  isProlongedOffline
                    ? "border-red-500/40 bg-red-500/15 text-red-600 dark:text-red-400 hover:bg-red-500/25"
                    : "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20"
                )}
                title={
                  isProlongedOffline
                    ? "Backend has been offline for a while. Click to test / wake up connection."
                    : "Backend offline. Click to test connection."
                }
              >
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span>{isProlongedOffline ? "Backend Offline" : "Offline"}</span>
                <RefreshCw className={cn("w-3 h-3 ml-0.5", isChecking && "animate-spin")} />
              </button>
            ) : (
              <div
                className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 text-xs font-medium text-zinc-600 dark:text-zinc-400"
                title="Checking Backend Health..."
              >
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <span>Checking...</span>
              </div>
            )}

            <button
              type="button"
              onClick={toggleTheme}
              className="min-h-11 min-w-11 flex items-center justify-center p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
              aria-label="Toggle dark/light theme"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-zinc-700" />}
            </button>

            <a
              href={SOCIAL_LINKS.repository}
              target="_blank"
              rel="noopener noreferrer"
              className="min-h-11 min-w-11 flex items-center justify-center p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              aria-label="GitHub Repository"
            >
              <Github className="w-4 h-4" />
            </a>

            <Button variant="default" size="sm" asChild>
              <Link to="/chat">Open workspace</Link>
            </Button>
          </div>

          <div className="flex items-center gap-2 lg:hidden">
            <button
              type="button"
              onClick={toggleTheme}
              className="min-h-11 min-w-11 flex items-center justify-center p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 cursor-pointer"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-5 h-5 text-amber-500" /> : <Moon className="w-5 h-5 text-zinc-700" />}
            </button>
            <button
              className="min-h-11 min-w-11 flex items-center justify-center p-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg transition-colors"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              aria-label="Toggle Menu"
              aria-expanded={isMenuOpen}
              aria-controls="mobile-navigation"
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
            id="mobile-navigation"
            className="lg:hidden border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-4 space-y-2"
          >
            {NAV_LINKS.map((link) => {
              const isActive = location.pathname === link.href;
              return (
                <Link
                  key={link.href}
                  to={link.href}
                  aria-current={isActive ? "page" : undefined}
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
            <div className="px-3 py-2 flex items-center justify-between text-xs border-t border-zinc-200 dark:border-zinc-800">
              <span className="text-zinc-500">Backend Status</span>
              {status === "connected" ? (
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Online
                </span>
              ) : status === "disconnected" ? (
                <button
                  type="button"
                  onClick={() => void checkNow()}
                  disabled={isChecking}
                  className="flex items-center gap-1.5 text-red-600 dark:text-red-400 font-medium"
                >
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  {isProlongedOffline ? "Backend Offline (Retry)" : "Offline"}
                  <RefreshCw className={cn("w-3 h-3 ml-0.5", isChecking && "animate-spin")} />
                </button>
              ) : (
                <span className="flex items-center gap-1.5 text-amber-500 font-medium">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  Checking...
                </span>
              )}
            </div>
            <div className="pt-2">
              <Button variant="default" className="w-full" asChild>
                <Link to="/chat">Open workspace</Link>
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
