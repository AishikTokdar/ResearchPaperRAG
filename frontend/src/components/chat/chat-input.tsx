import * as React from "react";
import { Send, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  isLoading = false,
  placeholder = "Ask a question about the document...",
}: ChatInputProps) {
  const [message, setMessage] = React.useState("");
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled || isLoading) return;

    onSend(trimmedMessage);
    setMessage("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = message.trim().length > 0 && !disabled && !isLoading;

  return (
    <div className="relative w-full min-w-0">
      <div
        className={cn(
          "relative flex w-full min-w-0 items-end gap-2.5 p-2 sm:p-2.5 rounded-2xl border transition-colors",
          "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 shadow-sm",
          "focus-within:border-zinc-400 dark:focus-within:border-zinc-600",
        )}
      >
        <Textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "Upload a document first..." : placeholder}
          disabled={disabled || isLoading}
          autoResize
          wrapperClassName="min-w-0 flex-1 self-stretch"
          className={cn(
            "w-full min-h-[40px] max-h-[160px] resize-none px-2 py-1.5 text-sm sm:text-base",
            "bg-transparent border-transparent outline-none ring-0 shadow-none",
            "focus:border-transparent focus:outline-none focus:ring-0 focus:shadow-none",
            "text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500",
          )}
          rows={1}
        />

        <Button
          onClick={handleSend}
          disabled={!canSend}
          size="icon"
          className={cn(
            "shrink-0 w-9 h-9 sm:w-10 sm:h-10 rounded-xl transition-all",
            canSend
              ? "bg-zinc-900 dark:bg-zinc-100 text-zinc-100 dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-zinc-200"
              : "bg-zinc-100 dark:bg-zinc-800 text-zinc-400 dark:text-zinc-500 border border-zinc-200 dark:border-zinc-700",
          )}
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </Button>
      </div>

      <div className="mt-1.5 flex items-center justify-between px-1 text-[11px] text-zinc-400 dark:text-zinc-500">
        <span>
          Press <kbd className="px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-mono">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-mono">Shift+Enter</kbd> for line break
        </span>
      </div>
    </div>
  );
}
