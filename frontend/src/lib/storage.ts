import type { ChatEntry } from "@/types";

const LS_PREFIX = "document-rag:";

const LS_KEYS = {
  SELECTED_MODEL: `${LS_PREFIX}selectedModel`,
  INCLUDE_SOURCES: `${LS_PREFIX}includeSources`,
  STREAMING_ENABLED: `${LS_PREFIX}streamingEnabled`,
  LAST_PDF_NAME: `${LS_PREFIX}lastPdfName`,
  DISMISSED_LOCAL_BANNER: `${LS_PREFIX}dismissedLocalBanner`,
} as const;

export function loadPreference<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (raw === null) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function savePreference<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
  }
}

export const prefKeys = LS_KEYS;

const DB_NAME = "document-rag-db";
const DB_VERSION = 1;
const STORE_NAME = "chat-sessions";

export interface ChatSession {
  pdfName: string;
  entries: ChatEntry[];
  updatedAt: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "pdfName" });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveChatSession(
  pdfName: string,
  entries: ChatEntry[],
): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const session: ChatSession = {
      pdfName,
      entries: entries.map((e) => ({
        ...e,
        timestamp: e.timestamp ? new Date(e.timestamp) : undefined,
      })),
      updatedAt: Date.now(),
    };
    store.put(session);
    await new Promise<void>((res, rej) => {
      tx.oncomplete = () => res();
      tx.onerror = () => rej(tx.error);
    });
  } catch {
  }
}

export async function loadChatSession(
  pdfName: string,
): Promise<ChatEntry[]> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(pdfName);
    return new Promise((resolve) => {
      request.onsuccess = () => {
        const result = request.result as ChatSession | undefined;
        if (result?.entries) {
          resolve(
            result.entries.map((e) => ({
              ...e,
              timestamp: e.timestamp ? new Date(e.timestamp) : undefined,
            })),
          );
        } else {
          resolve([]);
        }
      };
      request.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

/** Delete a single session */
export async function deleteChatSession(pdfName: string): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(pdfName);
    await new Promise<void>((res, rej) => {
      tx.oncomplete = () => res();
      tx.onerror = () => rej(tx.error);
    });
  } catch {
    /* silently skip */
  }
}

/** List all saved sessions (most recent first) */
export async function listChatSessions(): Promise<ChatSession[]> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.getAll();
    return new Promise((resolve) => {
      request.onsuccess = () => {
        const sessions = (request.result as ChatSession[]) || [];
        sessions.sort((a, b) => b.updatedAt - a.updatedAt);
        resolve(sessions);
      };
      request.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

/** Clear all stored sessions */
export async function clearAllSessions(): Promise<void> {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).clear();
    await new Promise<void>((res, rej) => {
      tx.oncomplete = () => res();
      tx.onerror = () => rej(tx.error);
    });
  } catch {
    /* silently skip */
  }
}
