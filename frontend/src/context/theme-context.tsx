import * as React from "react";

export type Theme = "dark" | "light" | "system";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  isDark: boolean;
  toggleTheme: () => void;
}

const STORAGE_KEY = "document-rag-theme";

const ThemeContext = React.createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY) as Theme;
      if (saved && ["dark", "light", "system"].includes(saved)) {
        return saved;
      }
    }
    return "dark";
  });

  const [isDark, setIsDark] = React.useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY) as Theme;
      if (saved === "light") return false;
      if (saved === "dark") return true;
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return true;
  });

  React.useEffect(() => {
    const root = document.documentElement;

    const applyTheme = (t: Theme) => {
      let activeDark = true;
      if (t === "system") {
        activeDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      } else {
        activeDark = t === "dark";
      }

      setIsDark(activeDark);

      if (activeDark) {
        root.classList.add("dark");
        root.classList.remove("light");
      } else {
        root.classList.remove("dark");
        root.classList.add("light");
      }
    };

    applyTheme(theme);
  }, [theme]);

  const setTheme = React.useCallback((newTheme: Theme) => {
    try {
      localStorage.setItem(STORAGE_KEY, newTheme);
    } catch {
      /* ignore */
    }
    setThemeState(newTheme);
  }, []);

  const toggleTheme = React.useCallback(() => {
    const next = isDark ? "light" : "dark";
    setTheme(next);
  }, [isDark, setTheme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
