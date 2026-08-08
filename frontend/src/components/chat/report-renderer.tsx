import * as React from "react";
import { Download, FileText, FileCode, Printer, ExternalLink, Copy, Check, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface ReportRendererProps {
  report: string;
  topic: string;
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
    a.download = `research_report_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadTxt = () => {
    const plainText = report
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, "$1 ($2)")
      .replace(/\[\*\*([^*]+)\*\*\]/g, "[$1]")
      .replace(/#+\s?/g, "")
      .replace(/\*\*/g, "")
      .replace(/\*/g, "")
      .replace(/\|/g, " ")
      .replace(/-{3,}/g, "");

    const blob = new Blob([plainText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research_report_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadPdf = () => {
    const printWin = window.open("", "_blank", "width=900,height=1000");
    if (!printWin) return;

    const parsedHtml = renderMarkdownToHtmlString(report);

    printWin.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Research Analysis & Gap Report - ${topic}</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
              color: #18181b;
              line-height: 1.6;
              padding: 40px;
              max-width: 900px;
              margin: 0 auto;
            }
            h1 {
              font-size: 24px;
              font-weight: 800;
              border-bottom: 2px solid #e4e4e7;
              padding-bottom: 12px;
              margin-bottom: 24px;
            }
            h2 {
              font-size: 18px;
              font-weight: 700;
              color: #27272a;
              margin-top: 28px;
              margin-bottom: 12px;
              border-bottom: 1px solid #f4f4f5;
              padding-bottom: 6px;
            }
            p {
              margin-bottom: 12px;
              font-size: 14px;
            }
            a {
              color: #4f46e5;
              font-weight: 600;
              text-decoration: underline;
            }
            a:hover {
              color: #3730a3;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              margin: 16px 0;
              font-size: 13px;
            }
            th, td {
              border: 1px solid #e4e4e7;
              padding: 8px 12px;
              text-align: left;
            }
            th {
              background-color: #f4f4f5;
              font-weight: 600;
            }
            ul, ol {
              padding-left: 24px;
              margin-bottom: 12px;
            }
            li {
              margin-bottom: 6px;
              font-size: 13.5px;
            }
            .citation {
              background-color: #e0e7ff;
              color: #3730a3;
              padding: 2px 6px;
              border-radius: 4px;
              font-family: monospace;
              font-size: 11px;
              border: 1px solid #c7d2fe;
            }
            @media print {
              body { padding: 20px; }
              @page { margin: 1.5cm; }
              a { color: #4f46e5 !important; text-decoration: underline !important; }
            }
          </style>
        </head>
        <body>
          <h1>Research Analysis & Gap Report: ${topic}</h1>
          <div>${parsedHtml}</div>
          <script>
            window.onload = function() {
              window.print();
            }
          </script>
        </body>
      </html>
    `);
    printWin.document.close();
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

function ReportSectionsRenderer({ report }: { report: string }) {
  let cleanedReport = report.replace(/^#\s+[^\n]+\n*/m, "").trim();
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
  const isFallbackAlert = cleanContent.includes("[FALLBACK ALERT]");
  const isExhaustedAlert = cleanContent.includes("[ALL MODELS EXHAUSTED]") || cleanContent.startsWith("Error generating research gap report:");

  if ((isNotice || isFallbackAlert || isExhaustedAlert) && !sectionTitle) {
    let alertMessage = cleanContent
      .replace(/^>\s*/gm, "")
      .replace(/\[(NOTICE|FALLBACK ALERT|ALL MODELS EXHAUSTED)\]/g, "")
      .trim();

    if (cleanContent.startsWith("Error generating research gap report:")) {
      alertMessage = "All AI model providers (Groq, OpenRouter, Cerebras, SambaNova, Gemini) were temporarily unable to process the request due to API rate limits or token quota constraints.\n\n**Action Required**: Please check your API keys in `backend/.env` (e.g. `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`) and verify your account usage limits at your provider console. Alternatively, reduce the number of selected papers and try again.";
    }

    return (
      <div className={`p-4.5 rounded-xl text-xs sm:text-sm font-medium flex items-start gap-3 shadow-xs border ${
        isExhaustedAlert
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

function FormattedBlock({ text }: { text: string }) {
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

function RichInlineText({ text }: { text: string }) {
  if (!text) return null;

  const cleaned = text.replace(/^#+\s*/, "");

  const TOKEN_RE = /(\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*|\[([^\]]+)\])/g;

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
      const linkText = m[2];
      const linkUrl = m[3];
      const isHttpUrl = linkUrl.startsWith("http");
      if (isHttpUrl) {
        parts.push(
          <a
            key={key}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-semibold text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:underline bg-indigo-50 dark:bg-indigo-950/40 px-1.5 py-0.5 rounded border border-indigo-200 dark:border-indigo-800 text-xs transition-colors my-0.5 mx-0.5"
            title={`Open paper in a new tab`}
          >
            <span>{linkText}</span>
            <ExternalLink className="w-3 h-3 inline shrink-0 text-indigo-500" />
          </a>
        );
      } else {
        parts.push(<span key={key}>{full}</span>);
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
    } else if (m[6] !== undefined && m[6].length > 1) {
      const cleanCitationText = m[6].replace(/\*\*/g, "").trim();
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
  let cleanMd = markdown.replace(/\[\*\*([^*]+)\*\*\]/g, "[$1]");

  let html = cleanMd
    .replace(/^#\s+(.+)$/gm, "<h1>$1</h1>")
    .replace(/^##\s+(.+)$/gm, "<h2>$1</h2>")
    .replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; font-weight: 600; text-decoration: underline;">$1 &#x2197;</a>')
    .replace(/\[([^\]]+)\]/g, '<span class="citation">[$1]</span>');

  const lines = html.split("\n");
  let inTable = false;
  let tableHtml = "";
  const outputLines: string[] = [];

  for (const line of lines) {
    if (line.trim().startsWith("|")) {
      if (line.includes("---")) continue;
      if (!inTable) {
        inTable = true;
        tableHtml = "<table><tbody>";
      }
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => `<td>${c.trim()}</td>`)
        .join("");
      tableHtml += `<tr>${cells}</tr>`;
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += "</tbody></table>";
        outputLines.push(tableHtml);
        tableHtml = "";
      }
      if (!line.trim().match(/^(---|---|\|\-\-+|\*\*\*)$/)) {
        outputLines.push(line ? `<p>${line}</p>` : "");
      }
    }
  }

  if (inTable) {
    tableHtml += "</tbody></table>";
    outputLines.push(tableHtml);
  }

  return outputLines.join("");
}
