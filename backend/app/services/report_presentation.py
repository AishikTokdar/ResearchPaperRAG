"""Report coverage, validated model guidance and compact citations."""

import re
import unicodedata

from langchain_core.documents import Document

from .evidence import OMITTED_PASSAGE, format_evidence, ground_answer

GENERAL_GUIDANCE = "General guidance (not findings from the selected papers)"
SECTIONS = (
    "Literature Summary",
    "Trend Detection",
    "Common Methods",
    "Limitations",
    "Contradictions",
    "Research Gaps",
    "Future Directions",
    "Novel Paper Suggestions",
)
GUIDANCE = (
    "A literature summary should compare each study's objective, data, approach and contribution. Consult the full texts before treating a method or result as established.",
    "To identify trends, compare how research questions, data and evaluation practices change across publication periods. Treat an apparent pattern as a hypothesis until a broader literature search supports it.",
    "A useful methods comparison covers data preparation, model or analytical approach, validation design and evaluation criteria. Compare methods under similar conditions before ranking their performance.",
    "When assessing limitations, consider sample representativeness, data leakage, external validation, reproducibility and uncertainty. These are review questions rather than confirmed weaknesses of the selected studies.",
    "Different conclusions do not necessarily contradict each other. Check whether studies examine the same population, task, dataset and outcome under comparable conditions. Where those conditions differ, describe the results as complementary or not directly comparable rather than declaring a contradiction.",
    "Potential gaps can be explored through external validation, reproducibility, robustness and practical feasibility. Check a wider literature search before claiming that a problem has not been studied.",
    "Proposed research: prioritize independent validation, transparent baselines, robustness checks and reproducible reporting. Choose the next experiment around a clearly stated hypothesis and evaluate whether it generalizes beyond the development setting.",
    "Proposed research: design a reproducible comparison of alternative approaches under a shared evaluation protocol. State the research question, data requirements and evaluation criteria in advance; treat any anticipated improvement as a hypothesis to test.",
)


def section_bodies(report: str) -> dict[int, str]:
    return {int(match[1]): match[2].strip() for match in re.finditer(
        r"(?ms)^##\s+([1-8])\.\s+[^\n]*\n(.*?)(?=^##\s+[1-8]\.\s+|\Z)", report
    )}


def sections_needing_guidance(report: str) -> list[int]:
    bodies = section_bodies(report)
    return [number for number in range(1, 9) if not bodies.get(number)
            or OMITTED_PASSAGE in bodies[number] or GUIDANCE[number - 1] in bodies[number]]


def parse_model_guidance(response: str, requested: list[int]) -> dict[int, str]:
    guidance = {}
    for number, body in section_bodies(response).items():
        if number not in requested:
            continue
        body = re.sub(r"^(?:\*\*)?(?:General guidance|Proposed research)(?:\*\*)?\s*:\s*(?:\*\*)?", "", body, flags=re.I)
        body = " ".join(body.split()).strip()
        if re.search(r"\b(?:papers?|stud(?:y|ies)|authors?|surveys?|results?)\s+(?:reports?|claims?|shows?|found|achieves?|outperforms?|concludes?)\b", body, re.I):
            continue
        # Sequential list labels and model identifiers are not result metrics.
        # Keep the original prose for display; relax only these explicit forms
        # when validating qualitative advice (not factual paper findings).
        numeric_text = re.sub(r"\b(?:ChatGPT|GPT|Llama|Gemma|Qwen|Gemini)[\s_\-\u2010-\u2015]*\d+(?:\.\d+)*\b", "model", body, flags=re.I)
        markers = list(dict.fromkeys(int(value) for value in re.findall(r"\((\d+)\)(?=\s)", numeric_text)))
        if len(markers) >= 2 and markers == list(range(1, len(markers) + 1)):
            numeric_text = re.sub(r"\(\d+\)(?=\s)", "", numeric_text)
        candidate = f"General guidance: {numeric_text}"
        if body and ground_answer(candidate, {}, [], allow_general_guidance=True) == candidate:
            guidance[number] = body
    return guidance


def _normalized_title(value: str) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", value).casefold())


def ensure_source_summaries(report: str, documents: list[Document]) -> str:
    """Never silently lose a selection when a model omits/rejects its summary.

    An explicitly quoted retrieved passage is a source extract, not an invented
    model summary. Metadata-only selections retain an honest coverage note.
    """
    summary = section_bodies(report).get(1, "")
    selected_titles = {_normalized_title(str(doc.metadata.get("paper_title") or doc.metadata.get("source_file") or "Selected paper")) for doc in documents}
    # A paper cited in a bibliography is not an additional selected source.
    entries = list(re.finditer(r"(?m)^(?:[-*•]\s+)?\*\*([^*\n]{20,})\*\*\s*[—–-]\s*", summary))
    if entries:
        kept = [summary[:entries[0].start()]]
        for index, entry in enumerate(entries):
            end = entries[index + 1].start() if index + 1 < len(entries) else len(summary)
            if _normalized_title(entry[1]) in selected_titles:
                kept.append(summary[entry.start():end])
        summary = "\n\n".join(part.strip() for part in kept if part.strip())
    additions = []
    for doc in documents:
        citation = format_evidence([doc])[1]["E1"]
        if citation in summary or (doc.metadata.get("source") and str(doc.metadata["source"]) in summary):
            continue
        title = str(doc.metadata.get("paper_title") or doc.metadata.get("source_file") or "Selected paper")
        title = re.sub(r"[\[\]<>\n\r*]", " ", title)
        if doc.metadata.get("evidence_scope") == "metadata_only":
            text = "Bibliographic record retrieved; experimental findings cannot be verified from this record."
        else:
            excerpt = " ".join(doc.page_content.split())
            excerpt = " ".join(excerpt.split()[:90])
            text = f'Retrieved excerpt: “{excerpt}…”'
        additions.append(f"- **{title}** — {text} {citation}")
    if not additions and summary == section_bodies(report).get(1, ""):
        return report
    replacement = "## 1. Literature Summary\n\n" + "\n\n".join(filter(None, [summary, *additions])) + "\n\n"
    if re.search(r"(?m)^##\s+1\.\s+", report):
        return re.sub(r"(?ms)^##\s+1\.\s+[^\n]*\n.*?(?=^##\s+[2-8]\.\s+|\Z)", lambda _: replacement, report, count=1)
    return replacement + report


def complete_report_sections(report: str, guidance: dict[int, str] | None = None, *, allow_static_fallback: bool = True) -> str:
    matches = list(re.finditer(r"(?m)^##\s+([1-8])\.\s+[^\n]*", report))
    bodies: dict[int, list[str]] = {}
    preamble = report[: matches[0].start()].strip() if matches else ""
    preamble = "\n".join(
        line for line in preamble.splitlines() if OMITTED_PASSAGE not in line
    ).strip()
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(report)
        bodies.setdefault(int(match[1]), []).append(report[match.end() : end].strip())
    sections = []
    for number, title in enumerate(SECTIONS, 1):
        body = "\n\n".join(bodies.get(number, []))
        body = re.sub(
            r"(?im)^(?:\*\*)?General guidance(?:\*\*)?\s*:\s*",
            f"**{GENERAL_GUIDANCE}**\n\n",
            body,
        )
        rejected = OMITTED_PASSAGE in body
        body = "\n".join(line for line in body.splitlines() if OMITTED_PASSAGE not in line).strip()
        body = re.sub(r"(?m)^\|[^\n]*\|[ \t]*\n\|[ :|\-]+\|[ \t]*(?:\n(?![ \t]*\|)|\Z)", "", body).strip()
        if rejected and body.endswith(":"):
            paragraphs = body.split("\n\n")
            if not re.search(r"\[[^\]]+\]", paragraphs[-1]):
                body = "\n\n".join(paragraphs[:-1]).strip()
        if guidance and number in guidance and GUIDANCE[number - 1] in body:
            body = body.replace(GUIDANCE[number - 1], "").strip()
            rejected = True
        if (
            rejected
            or not body
            or re.fullmatch(
                r"(?:Insufficient evidence|Not (?:provided|available))[^\n]*", body, re.I
            )
        ):
            if not allow_static_fallback and number not in (guidance or {}):
                if body and not re.fullmatch(r"(?:Insufficient evidence|Not (?:provided|available))[^\n]*", body, re.I):
                    sections.append(f"## {number}. {title}\n\n{body}")
                continue
            text = (guidance or {}).get(number, GUIDANCE[number - 1])
            advice = text if GENERAL_GUIDANCE in body else f"**{GENERAL_GUIDANCE}**\n\n{text}"
            body = (
                f"{body}\n\n{advice}"
                if body
                and not re.fullmatch(
                    r"(?:Insufficient evidence|Not (?:provided|available))[^\n]*", body, re.I
                )
                else advice
            )
        sections.append(f"## {number}. {title}\n\n{body}")
    return "\n\n".join(([preamble] if preamble else []) + sections)


def compact_report_citations(report: str) -> str:
    sources: dict[str, tuple[int, str]] = {}

    def replace(match: re.Match) -> str:
        label, url = match[1], match[2]
        if re.fullmatch(r"Source \d+(?:, p\. \d+)?", label):
            return match[0]
        page = re.search(r" - Page (\d+)$", label)
        title = label[: page.start()] if page else label
        if url not in sources:
            sources[url] = (len(sources) + 1, title)
        number = sources[url][0]
        location = f", p. {page[1]}" if page else ""
        return f"[Source {number}{location}]({url})"

    report = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", replace, report)
    report = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s*\1)+", r"\1", report)
    report = re.sub(r"(\]\([^)]+\))(?=\[)", r"\1 ", report)
    if sources:
        references = "\n".join(
            f"- **Source {number}:** [{title}]({url})" for url, (number, title) in sources.items()
        )
        report += "\n\n## Sources\n\n" + references
    return report
