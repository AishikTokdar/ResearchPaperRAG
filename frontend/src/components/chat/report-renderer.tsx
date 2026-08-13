import * as React from "react";
import { Download, FileText, FileCode, Printer, ExternalLink, Copy, Check, AlertTriangle } from "lucide-react";
// @ts-ignore
import html2pdf from "html2pdf.js";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";


interface ReportRendererProps {
  report: string;
  topic: string;
}

function getReportFilename(topic: string, ext: string): string {
  const cleanTopic = (topic || "research")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s_-]/g, "")
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .slice(0, 60);

  return `${cleanTopic}_gap_report.${ext}`;
}

export function ReportRenderer({ report, topic }: ReportRendererProps) {
  const [copiedFull, setCopiedFull] = React.useState(false);

  const handleCopyFullReport = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopiedFull(true);
      toast.success("Full gap analysis report copied to clipboard!");
      setTimeout(() => setCopiedFull(false), 2000);
    } catch {
      toast.error("Failed to copy report to clipboard.");
    }
  };

  const handleDownloadMd = () => {
    const cleanedMd = report.replace(/\[\*\*([^*]+)\*\*\]/g, "[$1]");
    const blob = new Blob([cleanedMd], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = getReportFilename(topic, "md");
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadTxt = () => {
    const sanitized = sanitizeReportMarkdown(report);
    let plainText = sanitized
      .replace(/^#\s+[^\n]+\n*/m, "")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, "$1 (Link: $2)")
      .replace(/\[\*\*([^*]+)\*\*\]/g, "$1")
      .replace(/\[([^\]]+)\]/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^##\s*(.+)$/gm, "\n================================================================================\n$1\n================================================================================")
      .replace(/^###\s*(.+)$/gm, "\n--- $1 ---")
      .replace(/^[*-]\s+/gm, "  • ")
      .replace(/^\d+\.\s+/gm, (m) => `  ${m}`)
      .replace(/\|/g, "  ")
      .replace(/^\s*[\+•\|]?\s*[\-\+=]{3,}.*$/gm, "")
      .replace(/```[a-zA-Z]*/g, "")
      .replace(/\n{3,}/g, "\n\n");

    const header = `RESEARCH ANALYSIS & GAP REPORT\nTopic: ${topic}\n\n`;
    const blob = new Blob([header + plainText.trim()], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = getReportFilename(topic, "txt");
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = async () => {
    const parsedHtml = renderMarkdownToHtmlString(report);
    const container = document.createElement("div");
    container.style.padding = "24px";
    container.style.maxWidth = "800px";
    container.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    container.style.color = "#1f2937";
    container.style.backgroundColor = "#ffffff";
    container.style.lineHeight = "1.65";

    container.innerHTML = `
      <div style="border-bottom: 3px solid #4f46e5; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
          <h1 style="font-size: 20px; font-weight: 800; color: #111827; margin: 0 0 4px 0;">Research Analysis & Gap Report</h1>
          <div style="font-size: 13px; color: #4f46e5; font-weight: 600;">Topic: ${topic}</div>
        </div>
        <div style="font-size: 10.5px; color: #6b7280; font-weight: 500;">AI Research Synthesis</div>
      </div>
      <div>${parsedHtml}</div>
      <div style="margin-top: 32px; border-top: 1px solid #e5e7eb; padding-top: 10px; font-size: 10.5px; color: #6b7280; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-weight: 500; color: #4b5563;">Research Analysis & Gap Report • ${topic}</span>
        <span style="background: #eef2ff; color: #4f46e5; padding: 2px 8px; border-radius: 10px; font-weight: 600; font-size: 10px; border: 1px solid #c7d2fe;">Interactive PDF</span>
      </div>
    `;

    document.body.appendChild(container);

    const opt = {
      margin: [12, 12, 15, 12] as [number, number, number, number],
      filename: getReportFilename(topic, "pdf"),
      image: { type: "jpeg" as const, quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true, logging: false },
      jsPDF: { unit: "mm" as const, format: "a4" as const, orientation: "portrait" as const },
    };


    try {
      await html2pdf().set(opt).from(container).save();
      toast.success("PDF report downloaded directly with clickable links!");
    } catch {
      const printWin = window.open("", "_blank", "width=900,height=1000");
      if (printWin) {
        printWin.document.write(`
          <!DOCTYPE html>
          <html>
            <head>
              <title>Research Analysis & Gap Report - ${topic}</title>
              <style>
                body { font-family: sans-serif; padding: 20px; color: #1f2937; }
                a { color: #4f46e5; text-decoration: underline; }
              </style>
            </head>
            <body>
              <div style="border-bottom: 2px solid #4f46e5; padding-bottom: 10px; margin-bottom: 20px;">
                <h1>Research Analysis & Gap Report</h1>
                <div>Topic: ${topic}</div>
              </div>
              <div>${parsedHtml}</div>
              <script>window.onload = function() { window.print(); }</script>
            </body>
          </html>
        `);
        printWin.document.close();
      }
    } finally {
      if (document.body.contains(container)) {
        document.body.removeChild(container);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-500" /> 8-Layer Structured Research Report
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            Topic: <span className="text-zinc-800 dark:text-zinc-200 font-semibold">{topic}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleCopyFullReport} className="gap-1.5 text-xs">
            {copiedFull ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500 stroke-[2.5]" /> Copied
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" /> Copy Full Report
              </>
            )}
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadMd} className="gap-1.5 text-xs">
            <FileCode className="w-3.5 h-3.5" /> .md
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadTxt} className="gap-1.5 text-xs">
            <Download className="w-3.5 h-3.5" /> .txt
          </Button>
          <Button variant="default" size="sm" onClick={handleDownloadPdf} className="gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
            <Printer className="w-3.5 h-3.5" /> .pdf
          </Button>
        </div>
      </div>

      <div className="space-y-6">
        <ReportSectionsRenderer report={report} />
      </div>
    </div>
  );
}

export function sanitizeReportMarkdown(raw: string): string {
  if (!raw) return "";

  let cleaned = raw;

  // 1. Separate subheaders directly attached to code fences like ``` ### Header
  cleaned = cleaned.replace(/```+\s*(###?\s+[^\n]+)/g, "\n\n$1");

  // 2. Strip ASCII box drawing borders like +-----------------+-----------------+ or • +-------+
  cleaned = cleaned.replace(/^\s*(?:```\s*)?[\+•\|]?\s*[\-\+=]{3,}.*$/gm, "");
  cleaned = cleaned.replace(/^\s*[\+•\|]\s*[\-\+=]{3,}.*$/gm, "");

  // 3. Remove orphaned backtick lines
  cleaned = cleaned.replace(/^\s*```[a-zA-Z]*\s*$/gm, "");

  // 4. Normalize section headers to standard "## N. Section Title"
  cleaned = cleaned.replace(/^###?\s*(\d+\.\s+[^\n]+?)\:?\s*$/gm, "## $1");
  cleaned = cleaned.replace(/^\*\*\s*(\d+\.\s+[^*]+)\s*\*\*:?\s*$/gm, "## $1");

  // 5. Ensure headers (## and ###) have clean newlines around them
  cleaned = cleaned.replace(/([^\n])\n(###?\s+)/g, "$1\n\n$2");
  cleaned = cleaned.replace(/(###?\s+[^\n]+)\n([^\n#])/g, "$1\n\n$2");

  // 6. Clean up multiple empty lines
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  return cleaned.trim();
}


function ReportSectionsRenderer({ report }: { report: string }) {
  const sanitized = sanitizeReportMarkdown(report);
  let cleanedReport = sanitized.replace(/^#\s+[^\n]+\n*/m, "").trim();
  cleanedReport = cleanedReport.replace(/^(---|---|\|\-\-+)\s*\n*/m, "").trim();

  const rawSections = cleanedReport.split(/(?=\n##\s|^##\s)/g);

  return (
    <div className="space-y-6">
      {rawSections.map((sec, idx) => {
        const trimmed = sec.trim();
        if (!trimmed) return null;

        const matchH2 = trimmed.match(/^##\s*(.+)$/m);
        const sectionTitle = matchH2 ? matchH2[1].replace(/#+\s?/, "").trim() : null;

        const sectionContent = matchH2 ? trimmed.replace(/^##\s*.+$/m, "").trim() : trimmed;

        const cleanContent = sectionContent.replace(/^(---|---|\|\-\-+)\s*\n*/g, "").trim();
        if (!cleanContent) return null;

        return (
          <ReportSectionCard key={idx} sectionTitle={sectionTitle} cleanContent={cleanContent} />
        );
      })}
    </div>
  );
}


function ReportSectionCard({ sectionTitle, cleanContent }: { sectionTitle: string | null; cleanContent: string }) {
  const [copied, setCopied] = React.useState(false);

  const isNotice = cleanContent.startsWith(">") || cleanContent.includes("[NOTICE]");
  const isFallbackAlert = cleanContent.includes("[FALLBACK ALERT]") || cleanContent.includes("[PROVIDER API KEY WARNING]") || cleanContent.includes("[API KEY WARNING]");
  const isExhaustedAlert = cleanContent.includes("[ALL MODELS EXHAUSTED]") || cleanContent.startsWith("Error generating research gap report:");

  if ((isNotice || isFallbackAlert || isExhaustedAlert) && !sectionTitle) {
    let alertMessage = cleanContent
      .replace(/^>\s*/gm, "")
      .replace(/\[(NOTICE|FALLBACK ALERT|PROVIDER API KEY WARNING|API KEY WARNING|ALL MODELS EXHAUSTED)\]/g, "")
      .trim();


    if (cleanContent.startsWith("Error generating research gap report:")) {
      alertMessage = "All AI model providers (Groq, OpenRouter, Cerebras, SambaNova, Gemini) were temporarily unable to process the request due to API rate limits or token quota constraints.\n\n**Action Required**: Please check your API keys in `backend/.env` (e.g. `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`) and verify your account usage limits at your provider console. Alternatively, reduce the number of selected papers and try again.";
    }

    return (
      <div className={`p-4.5 rounded-xl text-xs sm:text-sm font-medium flex items-start gap-3 shadow-xs border ${isExhaustedAlert
          ? "bg-red-500/10 border-red-500/30 text-red-900 dark:text-red-200"
          : "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
        }`}>
        <AlertTriangle className={`w-5 h-5 shrink-0 mt-0.5 ${isExhaustedAlert ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}`} />
        <div className="flex-1 leading-relaxed">
          <FormattedBlock text={alertMessage} />
        </div>
      </div>
    );
  }

  const handleCopySection = async () => {
    const textToCopy = sectionTitle ? `## ${sectionTitle}\n\n${cleanContent}` : cleanContent;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      toast.success(`Copied "${sectionTitle || "Section"}" to clipboard!`);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy section.");
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800 border-l-4 border-l-indigo-500 shadow-sm space-y-3 relative group">
      {sectionTitle ? (
        <div className="flex items-center justify-between pb-2 border-b border-zinc-200 dark:border-zinc-800">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block"></span>
            {sectionTitle}
          </h3>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopySection}
            className="h-7 px-2.5 text-xs text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 flex items-center gap-1.5 rounded-lg hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
            title="Copy section text"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500 stroke-[2.5]" />
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300" />
                <span>Copy Section</span>
              </>
            )}
          </Button>
        </div>
      ) : (
        <div className="flex justify-end">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCopySection}
            className="h-7 px-2.5 text-xs text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 flex items-center gap-1.5 rounded-lg hover:bg-zinc-200/60 dark:hover:bg-zinc-800 transition-colors"
            title="Copy section text"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-500 stroke-[2.5]" />
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300" />
                <span>Copy Section</span>
              </>
            )}
          </Button>
        </div>
      )}
      <FormattedBlock text={cleanContent} />
    </div>
  );
}

export function FormattedBlock({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split("\n");
  const tableLines: string[] = [];
  const contentBlocks: { type: "text" | "table"; content: string }[] = [];

  let inTable = false;
  let currentTextBuffer: string[] = [];

  for (const line of lines) {
    const trimmedLine = line.trim();
    if (trimmedLine.match(/^(---|---|\|\-\-+|\*\*\*)$/)) {
      continue;
    }

    if (trimmedLine.startsWith("|")) {
      if (!inTable) {
        inTable = true;
        if (currentTextBuffer.length > 0) {
          contentBlocks.push({ type: "text", content: currentTextBuffer.join("\n") });
          currentTextBuffer = [];
        }
      }
      tableLines.push(line);
    } else {
      if (inTable) {
        inTable = false;
        if (tableLines.length > 0) {
          contentBlocks.push({ type: "table", content: tableLines.join("\n") });
          tableLines.length = 0;
        }
      }
      currentTextBuffer.push(line);
    }
  }

  if (inTable && tableLines.length > 0) {
    contentBlocks.push({ type: "table", content: tableLines.join("\n") });
  } else if (currentTextBuffer.length > 0) {
    contentBlocks.push({ type: "text", content: currentTextBuffer.join("\n") });
  }

  return (
    <div className="space-y-3 text-xs sm:text-sm text-zinc-700 dark:text-zinc-300 leading-relaxed">
      {contentBlocks.map((block, i) => {
        if (block.type === "table") {
          return <TableRenderer key={i} tableMarkdown={block.content} />;
        }

        const blockText = block.content;

        const hasNumberedList = /^\d+\.\s/m.test(blockText);
        const hasBulletList = /^[*-]\s/m.test(blockText);

        if (hasNumberedList) {
          const rawItems = blockText
            .split(/\n(?=\d+\.\s)/)
            .map((s) => s.trim())
            .filter(Boolean);
          return (
            <ol key={i} className="space-y-3 pl-5 list-decimal marker:text-indigo-400 marker:font-semibold">
              {rawItems.map((rawItem, itemIdx) => {
                const cleaned = rawItem.replace(/^\d+\.\s+/, "").trim();
                return (
                  <li key={itemIdx} className="leading-relaxed pl-1">
                    <RichInlineText text={cleaned} />
                  </li>
                );
              })}
            </ol>
          );
        }

        if (hasBulletList) {
          const rawItems = blockText
            .split(/\n(?=[*-]\s)/)
            .map((s) => s.trim())
            .filter(Boolean);
          return (
            <ul key={i} className="space-y-1.5 pl-4 list-disc marker:text-zinc-400">
              {rawItems.map((rawItem, itemIdx) => {
                const cleaned = rawItem.replace(/^[*-]\s+/, "").trim();
                return (
                  <li key={itemIdx} className="leading-relaxed">
                    <RichInlineText text={cleaned} />
                  </li>
                );
              })}
            </ul>
          );
        }

        const paragraphs = blockText.split("\n\n");
        return (
          <React.Fragment key={i}>
            {paragraphs.map((p, pIdx) => {
              const cleanP = p.trim();
              if (!cleanP) return null;
              if (cleanP.match(/^(---|---| -{3,}|\|\-\-+|\*\*\*)$/)) return null;

              const isFallbackAlert = cleanP.includes("[FALLBACK ALERT]");
              const isExhaustedAlert = cleanP.includes("[ALL MODELS EXHAUSTED]");
              const isCallout = cleanP.startsWith(">") || isFallbackAlert || isExhaustedAlert;

              if (isCallout) {
                const alertText = cleanP
                  .replace(/^>\s*/gm, "")
                  .replace(/\[(FALLBACK ALERT|ALL MODELS EXHAUSTED|NOTICE)\]/g, "")
                  .trim();

                return (
                  <div
                    key={pIdx}
                    className={`my-2 p-3 rounded-xl text-xs font-medium flex items-start gap-2.5 border ${isExhaustedAlert
                        ? "bg-red-500/10 border-red-500/30 text-red-900 dark:text-red-200"
                        : "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                      }`}
                  >
                    <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${isExhaustedAlert ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}`} />
                    <div className="flex-1 leading-relaxed">
                      <RichInlineText text={alertText.replace(/\n/g, " ")} />
                    </div>
                  </div>
                );
              }

              if (cleanP.startsWith("### ")) {
                return (
                  <h4 key={pIdx} className="text-xs sm:text-sm font-bold text-indigo-600 dark:text-indigo-400 mt-4 mb-1.5 tracking-tight flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 inline-block"></span>
                    <RichInlineText text={cleanP.replace(/^###\s+/, "")} />
                  </h4>
                );
              }

              return (
                <p key={pIdx} className="leading-relaxed">
                  <RichInlineText text={cleanP.replace(/\n/g, " ")} />
                </p>
              );

            })}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function TableRenderer({ tableMarkdown }: { tableMarkdown: string }) {
  const lines = tableMarkdown.split("\n").filter((l) => l.trim().startsWith("|"));
  if (lines.length === 0) return null;

  const headerLine = lines[0];
  const bodyLines = lines.slice(1).filter((l) => !l.includes("---"));

  const parseRow = (line: string) =>
    line
      .split("|")
      .slice(1, -1)
      .map((c) => c.trim());

  const headers = parseRow(headerLine);

  return (
    <div className="overflow-x-auto my-3 rounded-xl border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-indigo-50/60 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 font-semibold border-b border-indigo-500/20">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="p-2.5 border-b border-zinc-200 dark:border-zinc-700">
                <RichInlineText text={h} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {bodyLines.map((rowLine, rIdx) => {
            const cells = parseRow(rowLine);
            return (
              <tr key={rIdx} className="hover:bg-zinc-100/50 dark:hover:bg-zinc-800/50">
                {cells.map((cell, cIdx) => (
                  <td key={cIdx} className="p-2.5 align-top">
                    <RichInlineText text={cell} />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function normalizeUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  if (
    trimmed.startsWith("doi.org/") ||
    trimmed.startsWith("dx.doi.org/") ||
    trimmed.startsWith("arxiv.org/") ||
    trimmed.startsWith("www.") ||
    trimmed.startsWith("10.") ||
    trimmed.includes(".org/") ||
    trimmed.includes(".com/") ||
    trimmed.includes(".edu/") ||
    trimmed.includes(".pdf")
  ) {
    return `https://${trimmed}`;
  }
  return trimmed;
}

function RichInlineText({ text }: { text: string }) {
  if (!text) return null;

  let cleaned = text.replace(/^#+\s*/, "");
  // Sanitize nested bracket links and strip internal chunk numbers (e.g. Chunk 19)
  cleaned = cleaned.replace(/\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*Chunk\s*\d+\]/gi, "[$1]($2)");
  cleaned = cleaned.replace(/\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^\]]+)\]/g, "[$1]($2)");
  cleaned = cleaned.replace(/\[\[([^\]]+)\]\(([^)]+)\)\]/g, "[$1]($2)");
  cleaned = cleaned.replace(/\[\*\*([^*]+)\*\*\]\(([^)]+)\)/g, "[$1]($2)");
  cleaned = cleaned.replace(/\s*\|\s*Chunk\s*\d+/gi, "");
  cleaned = cleaned.replace(/\s*\(\s*Chunk\s*\d+\s*\)/gi, "");
  cleaned = cleaned.replace(/\[\s*Chunk\s*\d+\s*\]/gi, "");

  const TOKEN_RE = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|\[([^\]]+)\])/g;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let m: RegExpExecArray | null;

  while ((m = TOKEN_RE.exec(cleaned)) !== null) {
    if (m.index > lastIndex) {
      parts.push(<span key={lastIndex}>{cleaned.slice(lastIndex, m.index)}</span>);
    }

    const full = m[0];
    const key = m.index;

    if (m[3] !== undefined) {
      const rawText = m[2].replace(/[\*\_]/g, "").trim();
      const rawUrl = m[3].trim();
      const finalUrl = normalizeUrl(rawUrl);
      const isHttpUrl = finalUrl.startsWith("http://") || finalUrl.startsWith("https://");

      if (isHttpUrl) {
        parts.push(
          <a
            key={key}
            href={finalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline inline gap-1 text-sm underline decoration-indigo-300 dark:decoration-indigo-700 underline-offset-2 transition-colors mx-0.5"
            title="Open research paper in a new tab"
          >
            {rawText} <ExternalLink className="w-3 h-3 inline align-baseline ml-0.5 text-indigo-500" />
          </a>
        );
      }
      else {
        parts.push(
          <span
            key={key}
            className="inline border border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 rounded px-1.5 py-0.5 font-mono text-[10px] font-medium leading-normal mx-0.5 break-words"
          >
            [{rawText}]
          </span>
        );
      }
    } else if (m[4] !== undefined) {
      parts.push(
        <strong key={key} className="font-semibold text-zinc-900 dark:text-zinc-100">
          {m[4]}
        </strong>
      );
    } else if (m[5] !== undefined) {
      parts.push(
        <em key={key} className="italic text-zinc-700 dark:text-zinc-300">
          {m[5]}
        </em>
      );
    } else if (m[6] !== undefined) {
      parts.push(
        <code key={key} className="px-1 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 font-mono text-xs text-indigo-600 dark:text-indigo-400">
          {m[6]}
        </code>
      );
    } else if (m[7] !== undefined && m[7].length > 1) {
      const cleanCitationText = m[7].replace(/[\*\_]/g, "").trim();
      parts.push(
        <span
          key={key}
          className="inline border border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 rounded px-1.5 py-0.5 font-mono text-[10px] font-medium leading-normal mx-0.5 break-words"
        >
          [{cleanCitationText}]
        </span>
      );
    } else {
      parts.push(<span key={key}>{full}</span>);
    }

    lastIndex = m.index + full.length;
  }

  if (lastIndex < cleaned.length) {
    parts.push(<span key={lastIndex + "end"}>{cleaned.slice(lastIndex)}</span>);
  }

  return <>{parts}</>;
}

function renderMarkdownToHtmlString(markdown: string): string {
  const sanitized = sanitizeReportMarkdown(markdown);
  let cleanMd = sanitized.replace(/^#\s+[^\n]+\n*/m, "").trim();

  cleanMd = cleanMd.replace(/\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*Chunk\s*\d+\]/gi, "[$1]($2)");
  cleanMd = cleanMd.replace(/\[\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^\]]+)\]/g, "[$1]($2)");
  cleanMd = cleanMd.replace(/\[\[([^\]]+)\]\(([^)]+)\)\]/g, "[$1]($2)");
  cleanMd = cleanMd.replace(/\[\*\*([^*]+)\*\*\]\(([^)]+)\)/g, "[$1]($2)");
  cleanMd = cleanMd.replace(/\[\*\*([^*]+)\*\*\]/g, "[$1]");

  cleanMd = cleanMd.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, rawText, rawUrl) => {
    const titleText = rawText.replace(/[\*\_]/g, "").trim();
    const url = normalizeUrl(rawUrl);
    const href = url.startsWith("http") ? url : `https://${url}`;
    return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="paper-link" style="color: #4f46e5; font-weight: 600; text-decoration: underline; font-size: 13px; display: inline;">${titleText} &#x2197;</a>`;
  });

  cleanMd = cleanMd.replace(/\[([^\]]+)\]/g, '<span class="citation">[$1]</span>');

  let html = cleanMd
    .replace(/^##\s+(.+)$/gm, "<h2>$1</h2>")
    .replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  const lines = html.split("\n");
  const outputLines: string[] = [];
  let tableLinesBuffer: string[] = [];

  const flushTable = () => {
    if (tableLinesBuffer.length === 0) return;

    let headerRowIndex = 0;
    const separatorIdx = tableLinesBuffer.findIndex((l) => l.includes("---"));
    if (separatorIdx > 0) {
      headerRowIndex = separatorIdx - 1;
    }

    let tHtml = '<table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 12px; border: 1px solid #cbd5e1; table-layout: auto;">';
    let inBody = false;
    let dataRowCounter = 0;

    tableLinesBuffer.forEach((line, idx) => {
      if (line.includes("---")) return;

      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());

      if (idx === headerRowIndex && !inBody) {
        tHtml += '<thead style="background-color: #4f46e5; color: #ffffff;"><tr>';
        tHtml += cells
          .map((c) => `<th style="padding: 10px 12px; border: 1px solid #3730a3; font-weight: 700; text-align: left; font-size: 12px; line-height: 1.4; color: #ffffff; background-color: #4f46e5;">${c}</th>`)
          .join("");
        tHtml += '</tr></thead>';
      } else {
        if (!inBody) {
          inBody = true;
          tHtml += '<tbody>';
        }
        dataRowCounter++;
        const rowBg = dataRowCounter % 2 === 0 ? "#f8fafc" : "#ffffff";
        tHtml += `<tr style="background-color: ${rowBg};">`;
        tHtml += cells
          .map((c) => `<td style="padding: 9px 12px; border: 1px solid #e2e8f0; color: #1e293b; vertical-align: top; font-size: 12px; line-height: 1.5; background-color: ${rowBg};">${c}</td>`)
          .join("");
        tHtml += '</tr>';
      }
    });

    if (inBody) {
      tHtml += '</tbody>';
    }
    tHtml += '</table>';
    outputLines.push(tHtml);
    tableLinesBuffer = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("|")) {
      tableLinesBuffer.push(trimmed);
    } else if (tableLinesBuffer.length > 0 && trimmed === "") {
      continue;
    } else {
      flushTable();
      if (trimmed.startsWith("<h2>") && trimmed.endsWith("</h2>")) {
        outputLines.push(`<h2 style="font-size: 18px; font-weight: 800; color: #111827; margin-top: 24px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #6366f1;">${trimmed.slice(4, -5)}</h2>`);
      } else if (trimmed.match(/^(\d+\.\s+(Literature Summary|Trend Detection|Common Methods|Limitations|Contradictions|Research Gaps|Future Directions|Novel Paper Suggestions))/i)) {
        outputLines.push(`<h2 style="font-size: 18px; font-weight: 800; color: #111827; margin-top: 24px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #6366f1;">${trimmed}</h2>`);
      } else if (trimmed.match(/^\d+\.\s+/)) {
        outputLines.push(`<p style="font-size: 13.5px; line-height: 1.65; color: #374151; margin-bottom: 8px; font-weight: 600; padding-left: 12px;">${trimmed}</p>`);
      } else if (!trimmed.match(/^(---|---|\|\-\-+|\*\*\*)$/)) {
        outputLines.push(trimmed ? `<p style="font-size: 13.5px; line-height: 1.65; color: #374151; margin-bottom: 12px;">${trimmed}</p>` : "");
      }
    }
  }

  flushTable();
  return outputLines.join("");
}

