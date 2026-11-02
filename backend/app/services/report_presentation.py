"""Readable report fallbacks and compact citations; no additional generation calls."""

import re

from .evidence import OMITTED_PASSAGE

GENERAL_GUIDANCE = "General guidance (not findings from the selected papers)"
SECTIONS = (
    "Literature Summary", "Trend Detection", "Common Methods", "Limitations",
    "Contradictions", "Research Gaps", "Future Directions", "Novel Paper Suggestions",
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


def complete_report_sections(report: str) -> str:
    """Keep valid text; replace technical refusals and fill absent sections transparently.

    The primary model is prompted to supply general guidance itself. These local
    defaults ensure a truncated or rejected section still has useful review advice.
    They never claim to summarize findings from a paper.
    """
    matches = list(re.finditer(r"(?m)^##\s+([1-8])\.\s+[^\n]*", report))
    bodies: dict[int, list[str]] = {}
    preamble = report[:matches[0].start()].strip() if matches else ""
    preamble = "\n".join(line for line in preamble.splitlines() if OMITTED_PASSAGE not in line).strip()
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(report)
        bodies.setdefault(int(match[1]), []).append(report[match.end():end].strip())
    sections = []
    for number, title in enumerate(SECTIONS, 1):
        body = "\n\n".join(bodies.get(number, []))
        body = re.sub(
            r"(?im)^(?:\*\*)?General guidance(?:\*\*)?\s*:\s*",
            f"**{GENERAL_GUIDANCE}**\n\n", body,
        )
        rejected = OMITTED_PASSAGE in body
        body = "\n".join(line for line in body.splitlines() if OMITTED_PASSAGE not in line).strip()
        if rejected or not body or re.fullmatch(r"(?:Insufficient evidence|Not (?:provided|available))[^\n]*", body, re.I):
            advice = f"**{GENERAL_GUIDANCE}**\n\n{GUIDANCE[number - 1]}"
            body = f"{body}\n\n{advice}" if body and not re.fullmatch(r"(?:Insufficient evidence|Not (?:provided|available))[^\n]*", body, re.I) else advice
        sections.append(f"## {number}. {title}\n\n{body}")
    return "\n\n".join(([preamble] if preamble else []) + sections)


def compact_report_citations(report: str) -> str:
    """Number source links, preserve page references, and list each title once."""
    sources: dict[str, tuple[int, str]] = {}

    def replace(match: re.Match) -> str:
        label, url = match[1], match[2]
        if re.fullmatch(r"Source \d+(?:, p\. \d+)?", label):
            return match[0]
        page = re.search(r" - Page (\d+)$", label)
        title = label[:page.start()] if page else label
        if url not in sources:
            sources[url] = (len(sources) + 1, title)
        number = sources[url][0]
        location = f", p. {page[1]}" if page else ""
        return f"[Source {number}{location}]({url})"

    report = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", replace, report)
    # Adjacent identical citations occur with zero whitespace too.
    report = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s*\1)+", r"\1", report)
    report = re.sub(r"(\]\([^)]+\))(?=\[)", r"\1 ", report)
    if sources:
        references = "\n".join(f"- **Source {number}:** [{title}]({url})" for url, (number, title) in sources.items())
        report += "\n\n## Sources\n\n" + references
    return report
