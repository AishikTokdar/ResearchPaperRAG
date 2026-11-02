import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import { build } from "esbuild";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);

async function load(entry, plugins = []) {
  const result = await build({
    entryPoints: [path.join(root, entry)], bundle: true, write: false,
    platform: "node", format: "cjs", jsx: "automatic",
    alias: { "@": path.join(root, "src") }, external: ["html2pdf.js"], plugins,
  });
  const module = { exports: {} };
  new Function("require", "module", "exports", result.outputFiles[0].text)(require, module, module.exports);
  return module.exports;
}

const renderer = await load("src/components/chat/report-renderer.tsx", [{
  name: "expose-export-renderer",
  setup(plugin) {
    plugin.onLoad({ filter: /report-renderer\.tsx$/ }, async ({ path: file }) => ({
      contents: (await readFile(file, "utf8")) + "\nexport { renderMarkdownToHtmlString };", loader: "tsx",
    }));
  },
}]);

const api = await load("src/lib/api.ts", [{
  name: "offline-browser-config",
  setup(plugin) {
    plugin.onResolve({ filter: /^\.\/(constants|chat-session)$/ }, ({ path: name }) => ({ path: name, namespace: "test-config" }));
    plugin.onLoad({ filter: /.*/, namespace: "test-config" }, ({ path: name }) => ({ contents: name.endsWith("constants")
      ? 'export const API_ENDPOINTS = {ASK_STREAM:"/ask/stream",PAPER_INGEST:"/api/papers/ingest"}; export const joinApiUrl = (path) => path;'
      : 'export const getChatApiSessionId = () => "00000000-0000-4000-8000-000000000001"; export const isValidChatApiSessionId = () => true;', loader: "js" }));
  },
}]);

async function telemetryConfig(dsn) {
  return load("src/lib/sentry.ts", [{
    name: "isolated-telemetry",
    setup(plugin) {
      plugin.onResolve({ filter: /^@sentry\/react$/ }, () => ({ path: "sentry", namespace: "telemetry-mock" }));
      plugin.onLoad({ filter: /.*/, namespace: "telemetry-mock" }, () => ({ contents: "export function init(options) { globalThis.__telemetryOptions = options; }", loader: "js" }));
      plugin.onLoad({ filter: /sentry\.ts$/ }, async ({ path: file }) => ({
        contents: (await readFile(file, "utf8")).replaceAll("import.meta.env", JSON.stringify({ VITE_SENTRY_DSN: dsn, MODE: "test" })),
        loader: "ts",
      }));
    },
  }]);
}

test("telemetry requires an explicit deployment DSN", async () => {
  delete globalThis.__telemetryOptions;
  (await telemetryConfig("")).initSentry();
  assert.equal(globalThis.__telemetryOptions, undefined);
});

test("opted-in telemetry excludes research content and personal data", async () => {
  try {
    (await telemetryConfig("https://configured.example")).initSentry();
    const options = globalThis.__telemetryOptions;
    assert.equal(options.sendDefaultPii, false);
    assert.equal(options.replaysOnErrorSampleRate, 0);
    assert.equal(options.tracesSampleRate, 0);
    assert.equal(options.enableLogs, false);
    assert.equal(options.beforeBreadcrumb({ message: "private research" }), null);
    const event = options.beforeSend({
      message: "private research", user: { email: "private research" },
      request: { data: "private research" }, extra: { answer: "private research" },
      contexts: { prompt: "private research" }, logentry: { message: "private research" },
      exception: { values: [{ value: "private research", mechanism: { data: "private research" },
        stacktrace: { frames: [{ filename: "https://app.example/app.js?question=private research", vars: { query: "private research" } }] } }] },
    });
    assert.ok(!JSON.stringify(event).includes("private research"));
    assert.equal(event.exception.values[0].stacktrace.frames[0].filename, "https://app.example/app.js");
  } finally {
    delete globalThis.__telemetryOptions;
  }
});

test("blocked browser storage still keeps a stable session and reset rotates it", async () => {
  const previousWindow = globalThis.window;
  const previousStorage = globalThis.localStorage;
  try {
    globalThis.window = {};
    globalThis.localStorage = {
      getItem() { throw new Error("blocked"); },
      setItem() { throw new Error("blocked"); },
    };
    const session = await load("src/lib/chat-session.ts");
    const first = session.getChatApiSessionId();
    assert.ok(session.isValidChatApiSessionId(first));
    assert.equal(session.getChatApiSessionId(), first);
    session.resetChatApiSessionId();
    assert.notEqual(session.getChatApiSessionId(), first);
  } finally {
    globalThis.window = previousWindow;
    globalThis.localStorage = previousStorage;
  }
});

test("production API origin ignores query and stored development overrides", async () => {
  const previousWindow = globalThis.window;
  try {
    globalThis.window = { location: { search: "?api_url=https://attacker.example", hostname: "app.example" } };
    const config = await load("src/lib/env.ts", [{
      name: "production-origin",
      setup(plugin) {
        plugin.onLoad({ filter: /env\.ts$/ }, async ({ path: file }) => ({
          contents: (await readFile(file, "utf8")).replaceAll("import.meta.env", JSON.stringify({ DEV: false, VITE_API_BASE_URL: "" })),
          loader: "ts",
        }));
      },
    }]);
    assert.equal(config.resolveApiBaseUrl(), "");
    assert.equal(config.joinApiUrl("/api/papers/search"), "/api/papers/search");
  } finally {
    globalThis.window = previousWindow;
  }
});

test("PDF export escapes raw HTML and event-handler injection", async () => {
  const html = await renderer.renderMarkdownToHtmlString('<img src=x onerror="alert(1)">\n\n<script>alert(2)</script>');
  assert.ok(!html.includes("<img"));
  assert.ok(!html.includes("<script"));
  assert.ok(html.includes("&lt;img"));
});

test("schema validation errors show useful text instead of object placeholders", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: [{ msg: "Question is too long" }] }), {
    status: 422, headers: { "Content-Type": "application/json" },
  });
  try {
    await assert.rejects(api.api.askQuestion("question"), /Question is too long/);
  } finally {
    globalThis.fetch = previous;
  }
});

test("streamed validation errors are readable strings", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => Response.json({ detail: [null, { msg: "Question is too long" }] }, { status: 422 });
  try {
    const error = await new Promise((resolve, reject) => api.streamQuestion({ question: "q" }, {
      onToken: () => {}, onDone: () => reject(new Error("Unexpected completion")), onError: resolve,
    }));
    assert.equal(error, "Question is too long");
  } finally { globalThis.fetch = previous; }
});

test("search and follow-up forward caller cancellation signals", async () => {
  const previous = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (_url, options) => {
    requests.push(options.signal);
    return Response.json({ papers: [], answer: "Supported" });
  };
  try {
    const controller = new AbortController();
    await api.api.searchPapers("topic", 3, controller.signal);
    await api.api.chatFollowup("question", "gemini", "test", undefined, controller.signal);
    assert.equal(requests.length, 2);
    assert.ok(requests.every(signal => !signal.aborted));
    controller.abort();
    assert.ok(requests.every(signal => signal.aborted));
  } finally { globalThis.fetch = previous; }
});

test("cleared PDF chat cannot be repopulated by a late JSON answer, and unmount cancels streams", async () => {
  const hooks = await load("src/hooks/use-chat.ts", [{
    name: "isolated-chat-lifecycle",
    setup(plugin) {
      plugin.onResolve({ filter: /^(react|@\/lib\/api)$/ }, ({ path: name }) => ({ path: name, namespace: "chat-lifecycle" }));
      plugin.onLoad({ filter: /.*/, namespace: "chat-lifecycle" }, ({ path: name }) => ({ contents: name === "react" ? `
        export const useState = initial => { globalThis.__chatState = initial; return [initial, update => {
          globalThis.__chatState = typeof update === 'function' ? update(globalThis.__chatState) : update;
        }]; };
        export const useRef = current => ({current});
        export const useCallback = callback => callback;
        export const useEffect = setup => { globalThis.__chatCleanup = setup(); };
      ` : `
        export class ApiError extends Error {};
        export const api = { askQuestion: (...args) => {
          globalThis.__chatSignal = args[4];
          return new Promise(resolve => { globalThis.__resolveChat = resolve; });
        } };
        export const streamQuestion = () => (globalThis.__chatStream = new AbortController());
      `, loader: "js" }));
    },
  }]);
  try {
    const chat = hooks.useChat();
    const pending = chat.sendMessage("question");
    chat.clearHistory();
    assert.equal(globalThis.__chatSignal.aborted, true);
    globalThis.__resolveChat({ answer: "Old response" });
    await pending;
    assert.deepEqual(globalThis.__chatState.chatHistory, []);
    assert.equal(globalThis.__chatState.isLoading, false);
    chat.sendMessageStreaming("question");
    globalThis.__chatCleanup();
    assert.equal(globalThis.__chatStream.signal.aborted, true);
  } finally {
    for (const key of ["__chatState", "__chatCleanup", "__chatSignal", "__resolveChat", "__chatStream"]) delete globalThis[key];
  }
});

test("PDF export rejects script links and escapes attribute quotes", async () => {
  const html = await renderer.renderMarkdownToHtmlString('[bad](javascript:alert) [safe](https://example.org/paper) [quoted](https://example.org/"onmouseover="alert)');
  assert.ok(!html.includes('href="javascript:'));
  assert.ok(html.includes('href="https://example.org/paper"'));
  assert.ok(!html.includes(' onmouseover="'));
  assert.ok(html.includes("&quot;"));
});

test("SSE parsing survives event/data lines split across network chunks", async () => {
  const previous = globalThis.fetch;
  const encoder = new TextEncoder();
  const chunks = ['event: token\n', 'data: {"content":"hello"}\n\n', 'event: done\n', 'data: {"answer":"final grounded answer"}\n\n'];
  globalThis.fetch = async () => new Response(new ReadableStream({ start(controller) {
    for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
    controller.close();
  } }));
  try {
    const tokens = [];
    const result = await new Promise((resolve, reject) => api.streamQuestion({ question: "q" }, {
      onToken: (text) => tokens.push(text), onDone: resolve, onError: reject,
    }));
    assert.deepEqual(tokens, ["hello"]);
    assert.equal(result.answer, "final grounded answer");
  } finally { globalThis.fetch = previous; }
});

test("SSE EOF without completion is reported as interruption", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response('event: token\ndata: {"content":"partial"}\n\n');
  try {
    const error = await new Promise((resolve, reject) => api.streamQuestion({ question: "q" }, {
      onToken: () => {}, onDone: () => reject(new Error("Unexpected completion")), onError: resolve,
    }));
    assert.match(error, /interrupted/);
  } finally { globalThis.fetch = previous; }
});

test("ingestion sends paper IDs without client URLs or abstracts", async () => {
  const previous = globalThis.fetch;
  let body;
  globalThis.fetch = async (_url, options) => {
    body = JSON.parse(options.body);
    return Response.json({ status: "success" });
  };
  try {
    await api.api.ingestPapers([{ id: "known-paper", pdf_url: "http://127.0.0.1", abstract: "untrusted" }]);
    assert.deepEqual(body, { fetched_papers: [{ id: "known-paper" }] });
  } finally { globalThis.fetch = previous; }
});

const progressHelpers = await load("src/lib/analysis-progress.ts");

test("analysis progress is monotonic and never reaches 100 before completion", () => {
  let state = { ...progressHelpers.INITIAL_ANALYSIS_PROGRESS };
  state = progressHelpers.mergeAnalysisProgress(state, { stage: "generate", percent: 80, sections_completed: [1, 2] });
  state = progressHelpers.mergeAnalysisProgress(state, { percent: 60, message: "Trying fallback" });
  assert.equal(state.percent, 80);
  state = progressHelpers.mergeAnalysisProgress(state, { percent: 100, sections_completed: [1, 1, 99, -1] });
  assert.equal(state.percent, 99);
  assert.deepEqual(state.sections_completed, [1]);
  assert.equal(progressHelpers.estimateRemaining(200, 70, 90), "Taking longer than estimated");
});

test("analysis stream handles CRLF framing and reserves report display for done", async () => {
  const previous = globalThis.fetch;
  const encoder = new TextEncoder();
  const chunks = ['event: progress\r', '\ndata: {"stage":"generate","percent":60,"message":"Writing summary"}\r\n\r\n', 'event: done\r\ndata: {"report":"Final report","percent":100,"stage":"complete"}'];
  globalThis.fetch = async () => new Response(new ReadableStream({ start(controller) {
    chunks.forEach(chunk => controller.enqueue(encoder.encode(chunk)));
    controller.close();
  } }));
  try {
    const updates = [];
    const result = await api.api.runAnalysis({ topic: "q", provider: "gemini", model: "test", paperIds: ["known"], files: [] }, (event) => updates.push(event), new AbortController().signal);
    assert.equal(result.report, "Final report");
    assert.equal(updates.length, 1);
    assert.equal(updates[0].percent, 60);
  } finally { globalThis.fetch = previous; }
});

test("analysis stream failure cannot become a completed report", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response('event: progress\ndata: {"percent":35}\n\nevent: error\ndata: {"message":"Provider unavailable"}\n\n');
  try {
    await assert.rejects(api.api.runAnalysis({ topic: "q", provider: "gemini", model: "test", paperIds: [], files: [] }, () => {}, new AbortController().signal), /Provider unavailable/);
  } finally { globalThis.fetch = previous; }
});

test("reports and exports hide internal batching notices but retain source caveats", async () => {
  const notice = '> [NOTICE] Large context detected. Prompt was automatically split into 3 focused generation batches to ensure 100% complete synthesis across all 8 sections.';
  const body = '## 1. Literature Summary\n\nSupported findings.\n\n> Some sources contain abstracts only; detailed findings may be unavailable.';
  const cleaned = renderer.sanitizeReportMarkdown(`${notice}\n\n> [FALLBACK ALERT] Automatically changed provider.\n\n${body}`);
  assert.ok(!cleaned.includes("generation batches"));
  assert.ok(!cleaned.includes("changed provider"));
  assert.ok(cleaned.includes("Supported findings"));
  assert.ok(cleaned.includes("abstracts only"));
  const html = await renderer.renderMarkdownToHtmlString(`${notice}\n\n${body}`);
  assert.ok(!html.includes("Large context detected"));
  assert.ok(html.includes("Supported findings"));
  assert.ok(!renderer.sanitizeReportMarkdown(`Large context detected. Prompt was automatically split into batches.\n\n${body}`).includes("automatically split"));
});
