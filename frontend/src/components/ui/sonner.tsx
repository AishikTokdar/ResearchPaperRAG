import { Toaster as SonnerToaster } from "sonner";
import { useTheme } from "@/context/theme-context";

export function Toaster() {
  const { isDark } = useTheme();
  return (
    <SonnerToaster
      position="bottom-right"
      theme={isDark ? "dark" : "light"}
      richColors
      closeButton
      expand={false}
      toastOptions={{
        classNames: {
          toast:
            "group border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-main)] shadow-md",
          title: "text-sm font-semibold",
          description: "text-xs text-[var(--text-muted)]",
        },
      }}
    />
  );
}
