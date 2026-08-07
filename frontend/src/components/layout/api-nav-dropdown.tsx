import { Link, useLocation } from "react-router-dom";
import { BookOpen, ChevronDown, LineChart, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { joinApiUrl } from "@/lib/constants";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ApiNavDropdown({ className }: { className?: string }) {
  const location = useLocation();
  const docsUrl = joinApiUrl("/docs");
  const onApiStatus = location.pathname === "/api-status";

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex items-center gap-1 text-sm font-medium transition-colors px-2.5 py-1.5 rounded-lg",
            onApiStatus
              ? "text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800/60"
              : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-900",
            className,
          )}
        >
          API Details
          <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-60" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="w-48 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-md p-1 rounded-xl"
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <DropdownMenuItem
          className="gap-2 cursor-pointer text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg p-2"
          onSelect={(e) => {
            e.preventDefault();
            window.open(docsUrl, "_blank", "noopener,noreferrer");
          }}
        >
          <BookOpen className="h-3.5 w-3.5 text-zinc-500" />
          <span className="flex-1">API Docs</span>
          <ExternalLink className="h-3 w-3 opacity-40" />
        </DropdownMenuItem>
        <DropdownMenuItem asChild className="cursor-pointer gap-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg p-2">
          <Link to="/api-status" className="flex w-full items-center gap-2">
            <LineChart className="h-3.5 w-3.5 text-zinc-500" />
            API Status
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
