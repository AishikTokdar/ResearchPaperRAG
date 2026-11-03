/* Real frontend -> proxy -> FastAPI integration; start the fixture server first.
 * See docs/TESTING.md. External inference and downloads are deterministic fixtures.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");

async function main() {
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE_PATH || "playwright");
  const origin = process.env.FRONTEND_URL || "http://127.0.0.1:5188";
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}),
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    // Production must ignore an attacker-controlled API override in a shared URL.
    await page.goto(`${origin}/chat?api_url=https://invalid.example`);
    await page.getByRole("heading", { name: "Research Gap Analyzer", exact: true }).waitFor();
    await page.getByRole("button", { name: "Search Research Papers", exact: true }).click();
    await page.getByText("Fetched Papers (5)", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Deselect Retrieval evaluation study 1", exact: true }).click();
    await page.getByRole("button", { name: "Upload PDFs", exact: true }).click();
    const pdf = await fetch("http://127.0.0.1:8999/__test__/pdf").then(response => response.arrayBuffer());
    await page.getByLabel("Upload Custom Research Papers (PDF)").setInputFiles({
      name: "integration.PDF", mimeType: "application/pdf", buffer: Buffer.from(pdf),
    });
    await page.getByRole("button", { name: "Academic Search", exact: true }).click();
    // A new search must reserve space for an already attached PDF.
    const searchedAgain = page.waitForResponse(response => response.url().endsWith("/api/papers/search") && response.request().method() === "POST");
    await page.getByRole("button", { name: "Search Research Papers", exact: true }).click();
    assert.equal((await searchedAgain).status(), 200);
    await page.getByRole("button", { name: "Search Research Papers", exact: true }).waitFor();
    const run = page.getByRole("button", { name: "Run Multi-Paper Gap Analysis", exact: true });
    await run.click();
    await page.getByText("The evaluated retrieval method measured accuracy of 91%", { exact: false }).first().waitFor({ timeout: 60000 });
    assert.ok(await page.getByText("91%", { exact: false }).count());
    assert.equal(await page.getByRole("button", { name: "Save Model", exact: true }).isDisabled(), true);
    const topicInput = page.getByLabel("Research topic", { exact: true });
    const originalTopic = await topicInput.inputValue();
    await topicInput.fill("A different topic for the next search");
    assert.ok((await page.locator("#report").innerText()).includes(originalTopic), "Editing a search must not rename the existing report");
    await topicInput.fill(originalTopic);
    const modelTrigger = page.getByRole("button", { name: "Choose analysis model", exact: true });
    const selectedModel = await modelTrigger.innerText();
    await modelTrigger.click();
    await page.getByLabel("Filter model providers").selectOption("groq");
    await page.keyboard.press("Escape");
    assert.equal(await modelTrigger.innerText(), selectedModel, "Provider filtering must not select a different model");
    assert.equal(await modelTrigger.evaluate(element => element === document.activeElement), true);
    // Exercise the actual download handlers, including PDF rendering in dark mode.
    const originalClass = await page.locator("html").getAttribute("class");
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    for (const format of ["Markdown", "text", "PDF"]) {
      const downloading = page.waitForEvent("download", { timeout: 60000 });
      await page.getByRole("button", { name: `Download ${format} report`, exact: true }).click();
      const download = await downloading;
      assert.equal(await download.failure(), null);
      const bytes = await fs.readFile(await download.path());
      if (format === "PDF") {
        assert.equal(bytes.subarray(0, 5).toString(), "%PDF-");
        assert.ok(bytes.length > 1000);
      } else {
        const content = bytes.toString("utf8");
        assert.ok(content.includes("Literature Summary") && content.includes("Novel Paper Suggestions"));
        assert.ok(content.includes("91%"));
        if (format === "text") assert.ok(!content.includes("##") && !content.includes("**"));
      }
    }
    await page.evaluate(value => { document.documentElement.className = value || ""; }, originalClass);
    const input = page.getByPlaceholder(/Ask a follow-up|Ask about|Ask a question/i);
    const failFollowup = route => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Temporary follow-up failure" }) });
    await page.route("**/api/chat/followup", failFollowup);
    await input.fill("Keep this question if sending fails");
    await input.press("Enter");
    await page.getByText("Temporary follow-up failure", { exact: true }).waitFor();
    assert.equal(await input.inputValue(), "Keep this question if sending fails");
    await page.unroute("**/api/chat/followup", failFollowup);
    await input.fill("What accuracy did they measure?");
    const followupResponse = page.waitForResponse(response => response.url().endsWith("/api/chat/followup") && response.request().method() === "POST");
    await input.press("Enter");
    assert.equal((await followupResponse).status(), 200);
    await page.getByText("The evaluated retrieval method measured accuracy of 91%", { exact: false }).last().waitFor();
    let releaseClear;
    let clearStarted;
    const clearGate = new Promise(resolve => { releaseClear = resolve; });
    const clearing = new Promise(resolve => { clearStarted = resolve; });
    await page.route("**/api/chat/followup", async route => {
      if (route.request().method() !== "DELETE") return route.continue();
      const response = await route.fetch();
      clearStarted();
      await clearGate;
      await route.fulfill({ response });
    });
    const cleared = page.waitForResponse(response => response.url().endsWith("/api/chat/followup") && response.request().method() === "DELETE");
    await page.getByRole("button", { name: "Clear Chat", exact: true }).click();
    await clearing;
    assert.equal(await input.isDisabled(), true, "Follow-up must wait for history clearing");
    releaseClear();
    assert.equal((await cleared).status(), 200);
    const before = await page.evaluate(() => localStorage.getItem("research-paper-rag-api-session-id"));
    await page.getByRole("button", { name: "Clear Session", exact: true }).click();
    const after = await page.evaluate(() => localStorage.getItem("research-paper-rag-api-session-id"));
    assert.notEqual(after, before);

    // Attach a PDF while a search is in flight; late results must reserve its slot.
    const racePage = await browser.newPage();
    let releaseSearch;
    let searchStarted;
    const searchGate = new Promise(resolve => { releaseSearch = resolve; });
    const searching = new Promise(resolve => { searchStarted = resolve; });
    await racePage.route("**/api/papers/search", async route => {
      const response = await route.fetch();
      searchStarted();
      await searchGate;
      await route.fulfill({ response });
    });
    await racePage.goto(`${origin}/chat`);
    await racePage.getByRole("button", { name: "Search Research Papers", exact: true }).click();
    await searching;
    await racePage.getByRole("button", { name: "Upload PDFs", exact: true }).click();
    await racePage.getByLabel("Upload Custom Research Papers (PDF)").setInputFiles({
      name: "late-search.PDF", mimeType: "application/pdf", buffer: Buffer.from(pdf),
    });
    releaseSearch();
    await racePage.getByRole("button", { name: "Academic Search", exact: true }).click();
    await racePage.getByText("Fetched Papers (5)", { exact: true }).waitFor();
    assert.equal(await racePage.getByRole("button", { name: /^Deselect Retrieval evaluation/ }).count(), 4);
    await racePage.close();
    await page.goto(`${origin}/api-status`);
    await page.getByText("224 tokens", { exact: true }).waitFor();
    await page.getByText("32 tokens", { exact: true }).waitFor();
    for (const path of ["/health", "/status", "/models", "/runtime-summary", "/pipeline-info", "/openapi.json"]) {
      const response = await page.request.get(`${origin}${path}`, {
        headers: { "X-Chat-Session-Id": "00000000-0000-4000-8000-000000000001" },
      });
      assert.equal(response.status(), 200, path);
      assert.ok(response.headers()["content-type"].includes("application/json"), path);
    }
    for (const width of [320, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    }
    assert.deepEqual(errors, []);
    console.log("Real integration passed: production URL safety, search, uppercase PDF upload, mixed-source parsing/indexing/report, follow-up, runtime config, proxy API paths and responsive layouts.");
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
