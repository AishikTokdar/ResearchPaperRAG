import * as React from "react";
import { Download, FileText, FileCode, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ReportRendererProps {
  report: string;
  topic: string;
}

export function ReportRenderer({ report, topic }: ReportRendererProps) {
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

        <div className="flex items-center gap-2">
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
          <div
            key={idx}
            className="p-5 rounded-2xl bg-zinc-50 dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800 border-l-4 border-l-indigo-500 shadow-sm space-y-3"
          >
            {sectionTitle && (
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 pb-2 border-b border-zinc-200 dark:border-zinc-800 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500 inline-block"></span>
                {sectionTitle}
              </h3>
            )}
            <FormattedBlock text={cleanContent} />
          </div>
        );
      })}
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

        const paragraphs = block.content.split("\n\n");
        return (
          <React.Fragment key={i}>
            {paragraphs.map((p, pIdx) => {
              const cleanP = p.trim();
              if (!cleanP) return null;
              if (cleanP.match(/^(---|---|\|\-\-+|\*\*\*)$/)) return null;

              if (cleanP.startsWith("- ") || cleanP.startsWith("* ") || cleanP.match(/^\d+\.\s/)) {
                const items = cleanP.split("\n").filter((l) => l.trim() && !l.trim().match(/^(---|---|\|\-\-+|\*\*\*)$/));
                return (
                  <ul key={pIdx} className="space-y-1.5 pl-4 list-disc marker:text-zinc-400">
                    {items.map((item, itemIdx) => (
                      <li key={itemIdx}>
                        <RichInlineText text={item.replace(/^[-*\d.]+\s*/, "")} />
                      </li>
                    ))}
                  </ul>
                );
              }

              return (
                <p key={pIdx} className="leading-relaxed">
                  <RichInlineText text={cleanP} />
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
  const parts = cleaned.split(/(\*\*[^*]+\*\*|\[[^\]]+\])/g);

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={i} className="font-semibold text-zinc-900 dark:text-zinc-100">
              {part.slice(2, -2)}
            </strong>
          );
        } else if (part.startsWith("[") && part.endsWith("]") && part.length > 3) {
          const cleanCitationText = part.slice(1, -1).replace(/\*\*/g, "").trim();
          return (
            <span
              key={i}
              className="inline border border-indigo-500/30 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 rounded px-1.5 py-0.5 font-mono text-[10px] font-medium leading-normal mx-0.5 break-words"
            >
              [{cleanCitationText}]
            </span>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function renderMarkdownToHtmlString(markdown: string): string {
  let cleanMd = markdown.replace(/\[\*\*([^*]+)\*\*\]/g, "[$1]");

  let html = cleanMd
    .replace(/^#\s+(.+)$/gm, "<h1>$1</h1>")
    .replace(/^##\s+(.+)$/gm, "<h2>$1</h2>")
    .replace(/^###\s+(.+)$/gm, "<h3>$1</h3>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
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
