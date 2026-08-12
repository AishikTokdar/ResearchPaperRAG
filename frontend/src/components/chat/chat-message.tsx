import * as React from "react";
import { User, Bot, Copy, Check, FileText, Cpu, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";

export interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
  isLatest?: boolean;
  index?: number;
  sources?: string[];
  modelUsed?: string;
}

function parseInlineMarkdown(text: string): React.ReactNode[] {
  const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  const tokens = text.split(regex);

  return tokens.map((token, idx) => {
    if (token.startsWith("**") && token.endsWith("**") && token.length > 4) {
      return (
        <strong key={idx} className="font-bold text-zinc-900 dark:text-zinc-100">
          {token.slice(2, -2)}
        </strong>
      );
    }
    if (token.startsWith("`") && token.endsWith("`") && token.length > 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-zinc-200/80 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 font-mono text-xs"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    if (token.startsWith("*") && token.endsWith("*") && token.length > 2) {
      return <em key={idx}>{token.slice(1, -1)}</em>;
    }
    return token;
  });
}

function renderFormattedInlineText(text: string) {
  // Catch document citations in brackets: [Filename.pdf - Page 23] or [Page X, Chunk Y]
  const citationRegex = /(\[(?:[^\]]+\.(?:pdf|doc|docx|txt)\s*-\s*Page\s*\d+[^\]]*|Page\s*\d+[^\]]*)\])/gi;
  const parts = text.split(citationRegex);

  return parts.map((part, i) => {
    if (citationRegex.test(part)) {
      const cleanCitation = part.slice(1, -1).trim();
      return (
        <span
          key={i}
          className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold px-2 py-0.5 mx-1 my-0.5 rounded-md bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800/60 shadow-xs align-middle"
        >
          <FileText className="w-3 h-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>{cleanCitation}</span>
        </span>
      );
    }

    return <span key={i}>{parseInlineMarkdown(part)}</span>;
  });
}

export function FormattedMessageContent({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let currentList: React.ReactNode[] = [];
  let isNumbered = false;

  const flushList = (key: string) => {
    if (currentList.length > 0) {
      if (isNumbered) {
        elements.push(
          <ol key={key} className="list-decimal list-inside space-y-1.5 my-2 pl-2 text-zinc-800 dark:text-zinc-200">
            {currentList}
          </ol>
        );
      } else {
        elements.push(
          <ul key={key} className="list-disc list-inside space-y-1.5 my-2 pl-2 text-zinc-800 dark:text-zinc-200">
            {currentList}
          </ul>
        );
      }
      currentList = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList(`list-${index}`);
      elements.push(<div key={`blank-${index}`} className="h-2" />);
      return;
    }

    // Blockquote handling (Warnings & Fallback alerts)
    if (trimmed.startsWith(">")) {
      flushList(`list-${index}`);
      const cleanQuote = trimmed.replace(/^>\s*/, "");
      const isWarn =
        cleanQuote.includes("[PROVIDER API KEY WARNING]") ||
        cleanQuote.includes("[API KEY WARNING]") ||
        cleanQuote.includes("[FALLBACK ALERT]") ||
        cleanQuote.includes("⚠️");

      elements.push(
        <div
          key={`quote-${index}`}
          className={`p-3 rounded-lg border text-xs font-medium my-2 flex items-start gap-2.5 ${
            isWarn
              ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
              : "bg-zinc-100 dark:bg-zinc-800/60 border-zinc-200 dark:border-zinc-700 text-zinc-700 dark:text-zinc-300"
          }`}
        >
          <div className="flex-1">{renderFormattedInlineText(cleanQuote)}</div>
        </div>
      );
      return;
    }

    // Header 1, 2, 3

    if (trimmed.startsWith("### ")) {
      flushList(`list-${index}`);
      elements.push(
        <h3 key={`h3-${index}`} className="text-sm font-bold text-zinc-900 dark:text-zinc-100 mt-3 mb-1.5 tracking-tight">
          {renderFormattedInlineText(trimmed.slice(4))}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith("## ")) {
      flushList(`list-${index}`);
      elements.push(
        <h2 key={`h2-${index}`} className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-4 mb-2 tracking-tight">
          {renderFormattedInlineText(trimmed.slice(3))}
        </h2>
      );
      return;
    }
    if (trimmed.startsWith("# ")) {
      flushList(`list-${index}`);
      elements.push(
        <h1 key={`h1-${index}`} className="text-lg font-extrabold text-zinc-900 dark:text-zinc-100 mt-4 mb-2 tracking-tight">
          {renderFormattedInlineText(trimmed.slice(2))}
        </h1>
      );
      return;
    }

    // Numbered list items like "1. ", "2. ", "3. "
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      if (currentList.length > 0 && !isNumbered) {
        flushList(`list-${index}`);
      }
      isNumbered = true;
      currentList.push(
        <li key={`li-${index}`} className="leading-relaxed">
          {renderFormattedInlineText(numMatch[2])}
        </li>
      );
      return;
    }

    // Bullet list items like "- ", "• ", "* "
    const bulletMatch = trimmed.match(/^[-•*]\s+(.*)/);
    if (bulletMatch) {
      if (currentList.length > 0 && isNumbered) {
        flushList(`list-${index}`);
      }
      isNumbered = false;
      currentList.push(
        <li key={`li-${index}`} className="leading-relaxed">
          {renderFormattedInlineText(bulletMatch[1])}
        </li>
      );
      return;
    }

    // Normal paragraph line
    flushList(`list-${index}`);
    elements.push(
      <p key={`p-${index}`} className="leading-relaxed my-1">
        {renderFormattedInlineText(line)}
      </p>
    );
  });

  flushList("list-final");

  return <div className="space-y-1 text-sm sm:text-base leading-relaxed break-words">{elements}</div>;
}

export function ChatMessage({
  role,
  content,
  timestamp,
  isLatest: _isLatest = false,
  index: _index = 0,
  sources,
  modelUsed,
}: ChatMessageProps) {
  const [copied, setCopied] = React.useState(false);
  const [sourcesOpen, setSourcesOpen] = React.useState(false);
  const isUser = role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const formattedSources = React.useMemo(() => {
    if (!sources) return [];
    return sources.map((src) => {
      const raw = String(src).trim();
      if (/^\d+$/.test(raw)) {
        const pageNum = Number.parseInt(raw, 10) + 1;
        return `Page ${pageNum}`;
      }
      return raw;
    });
  }, [sources]);

  return (
    <div
      className={cn(
        "flex gap-3 group text-sm sm:text-base",
        isUser ? "flex-row-reverse" : "flex-row",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold border transition-colors",
          isUser
            ? "bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 border-transparent"
            : "bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-200 dark:border-zinc-700",
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message Content */}
      <div
        className={cn(
          "relative max-w-[85%] sm:max-w-[75%] flex flex-col",
          isUser ? "items-end" : "items-start",
        )}
      >
        <div
          className={cn(
            "px-4 py-3 rounded-2xl border leading-relaxed text-left transition-colors",
            isUser
              ? "bg-zinc-900 text-zinc-100 dark:bg-zinc-100 dark:text-zinc-900 border-transparent rounded-tr-xs"
              : "bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border-zinc-200 dark:border-zinc-800 rounded-tl-xs shadow-xs",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{content}</p>
          ) : (
            <FormattedMessageContent content={content} />
          )}
        </div>

        {/* Source Citations */}
        {!isUser && formattedSources.length > 0 && (
          <div className="mt-2 w-full">
            <button
              onClick={() => setSourcesOpen((p) => !p)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>{formattedSources.length} Source Citation{formattedSources.length > 1 ? "s" : ""}</span>
              {sourcesOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {sourcesOpen && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {formattedSources.map((src, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 font-mono text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/80 rounded-md px-2 py-0.5 border border-emerald-300 dark:border-emerald-800/60 shadow-xs"
                  >
                    <FileText className="w-3 h-3 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    {src}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Footer Meta */}
        <div
          className={cn(
            "flex items-center gap-2 mt-1.5 px-1 text-xs text-zinc-400 dark:text-zinc-500",
            isUser ? "justify-end" : "justify-start",
          )}
        >
          {timestamp && <span>{formatRelativeTime(timestamp)}</span>}

          {!isUser && modelUsed && (
            <span className="inline-flex items-center gap-1 text-[11px] bg-zinc-100 dark:bg-zinc-800/60 text-zinc-600 dark:text-zinc-400 rounded px-1.5 py-0.5 border border-zinc-200/60 dark:border-zinc-700/60 font-mono">
              <Cpu className="w-3 h-3" />
              {modelUsed.split("/").pop()}
            </span>
          )}

          {!isUser && (
            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 cursor-pointer"
              aria-label="Copy message"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export const TypingIndicator = React.forwardRef<
  HTMLDivElement,
  { streamingText?: string | null; statusMessage?: string | null }
>(function TypingIndicator({ streamingText, statusMessage }, ref) {
  const hasTokens = streamingText != null && streamingText.length > 0;

  return (
    <div ref={ref} className="space-y-2">
      {statusMessage && (
        <div className="flex items-center gap-2 text-xs font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 px-3 py-2 rounded-xl animate-pulse">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-500 shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}
      <div className="flex gap-3 text-sm sm:text-base">
        <div className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
          <Bot className="w-4 h-4" />
        </div>

        <div className="bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 rounded-2xl rounded-tl-xs px-4 py-3 max-w-[85%] sm:max-w-[75%] shadow-xs">
          {hasTokens ? (
            <FormattedMessageContent content={streamingText} />
          ) : (
            <span className="inline-flex items-center gap-1 align-middle" aria-hidden>
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-1.5 h-1.5 bg-zinc-400 dark:bg-zinc-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </span>
          )}
        </div>
      </div>
    </div>
  );
});
TypingIndicator.displayName = "TypingIndicator";
