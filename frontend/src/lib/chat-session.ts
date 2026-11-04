const STORAGE_KEY = "research-paper-rag-api-session-id";

const UUID_V4_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isValidChatApiSessionId(value: string): boolean {
  return UUID_V4_RE.test(value.trim());
}

let volatileSessionId = "";

function newSessionUuid(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") {
    return c.randomUUID();
  }
  throw new Error("crypto.randomUUID is not available");
}

export function getChatApiSessionId(): string {
  try {
    const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (stored && isValidChatApiSessionId(stored)) {
      volatileSessionId = stored;
      return stored;
    }
    if (!volatileSessionId) volatileSessionId = newSessionUuid();
    if (typeof window !== "undefined") localStorage.setItem(STORAGE_KEY, volatileSessionId);
  } catch {
    if (!volatileSessionId) {
      try { volatileSessionId = newSessionUuid(); } catch { return ""; }
    }
  }
  return volatileSessionId;
}

export function resetChatApiSessionId(): void {
  volatileSessionId = newSessionUuid();
  try { localStorage.setItem(STORAGE_KEY, volatileSessionId); } catch { /* In-memory session remains usable. */ }
}
