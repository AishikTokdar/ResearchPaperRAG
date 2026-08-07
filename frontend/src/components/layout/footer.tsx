import { Link } from "react-router-dom";
import { Github, Linkedin } from "lucide-react";
import {
  APP_CONFIG,
  NAV_LINKS,
  SOCIAL_LINKS,
  TECH_STACK,
} from "@/lib/constants";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 transition-colors">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          <div className="md:col-span-2 space-y-4">
            <Link to="/" className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center text-zinc-100 dark:text-zinc-900 font-bold text-sm">
                R
              </div>
              <span className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                {APP_CONFIG.name}
              </span>
            </Link>
            <p className="max-w-sm text-sm text-zinc-600 dark:text-zinc-400 leading-relaxed">
              {APP_CONFIG.description}
            </p>
            <div className="flex items-center gap-3 pt-2">
              <a
                href={SOCIAL_LINKS.github}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                aria-label="GitHub"
              >
                <Github className="h-4 w-4" />
              </a>
              <a
                href={SOCIAL_LINKS.linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                aria-label="LinkedIn"
              >
                <Linkedin className="h-4 w-4" />
              </a>
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-4">
              Navigation
            </h3>
            <ul className="space-y-2.5">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    className="text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500 mb-4">
              Built With
            </h3>
            <ul className="space-y-2.5">
              {TECH_STACK.slice(0, 5).map((tech) => (
                <li key={tech.name}>
                  <span className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    {tech.name}
                    <span className="text-xs text-zinc-400 dark:text-zinc-600">
                      ({tech.category})
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-zinc-200 dark:border-zinc-800 pt-6 flex items-center justify-between text-xs text-zinc-500 dark:text-zinc-500">
          <span>&copy; {new Date().getFullYear()} {APP_CONFIG.name}. All rights reserved.</span>
          <span>Open Source Document Intelligence</span>
        </div>
      </div>
    </footer>
  );
}
