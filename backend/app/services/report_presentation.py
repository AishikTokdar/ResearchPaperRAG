"""Report coverage, validated model guidance and compact citations."""

import re
import unicodedata
from functools import lru_cache

from langchain_core.documents import Document

from .evidence import OMITTED_PASSAGE, format_evidence, ground_answer

GENERAL_GUIDANCE = "General guidance"
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


_SECTION_BODIES_RE = re.compile(r"(?ms)^##\s+([1-8])\.\s+[^\n]*\n(.*?)(?=^##\s+|\Z)")
_TITLE_PREFIX_RE = re.compile(r"^\s*(?:[-*]\s+)?\*\*[^*]+\*\*\s*[–—:-]?")
_CITATION_STRIP_RE = re.compile(r"\[[^\]]*\](?:\([^)]*\))?")
_METHOD_CLAIM_RE = re.compile(
    r"\b(?:retriev\w*|generat\w*|architect\w*|pipeline|model\w*|method\w*|embed\w*|vector|index\w*|train\w*|corpus|corpora)\b",
    re.I,
)
_EXPLICIT_BOUNDARY_RE = re.compile(
    r"\b(?:no|not(?!\s+only\b)|cannot|without|lack\w*|missing|unavailable|undisclosed|unknown|unspecified|unreported|indeterminate|absent|omitted)\b|\b(?:doesn|isn|aren)['’]t\b",
    re.I,
)
_SPECULATIVE_RE = re.compile(
    r"\b(?:(?:study|paper|authors?|framework)\s+(?:likely|probably|possibly|may|might)\s+(?:use|employ|adopt|acknowledge|note)\w*|(?:title|metadata|validation)\b[^.!?\n]{0,100}\b(?:impli|suggest)\w*)",
    re.I,
)
_PARA_SPLIT_RE = re.compile(r"\n\s*\n")


def section_bodies(report: str) -> dict[int, str]:
    return {int(match[1]): match[2].strip() for match in _SECTION_BODIES_RE.finditer(report)}


def concise_guidance(report: str) -> str:
    report = re.sub(r"General guidance\s*\(not findings from the selected papers\)", GENERAL_GUIDANCE, report, flags=re.I)
    report = re.sub(r"(?im)^(?:\*\*)?General guidance[ \t]*:?(?:\*\*)?[ \t]*:?[ \t]*\n?",
                    f"**{GENERAL_GUIDANCE}**\n", report)
    pattern = r"(?ms)^(?:\*\*)?General guidance(?:\*\*)?\s*(?::|\n)\s*(.*?)(?=\n\s*\n|^##|\Z)"
    def shorten(match: re.Match) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", match[1].strip())
        kept: list[str] = []
        for sentence in sentences[:2]:
            if len(" ".join([*kept, sentence]).split()) > 60:
                break
            kept.append(sentence)
        return f"**{GENERAL_GUIDANCE}**\n\n" + " ".join(kept) if kept else ""
    return re.sub(pattern, shorten, report)


_NON_WORD_PATTERN = re.compile(r"[\W_]+")


@lru_cache(maxsize=512)
def _normalized_title(value: str) -> str:
    return _NON_WORD_PATTERN.sub("", unicodedata.normalize("NFKC", value).casefold())


def covered_papers(body: str, docs: list[Document]) -> set[str]:
    covered = set()
    norm_body = None
    for doc in docs:
        metadata = doc.metadata
        key = str(metadata.get("paper_id") or metadata.get("source") or metadata.get("source_file") or metadata.get("paper_title") or "document")
        url = str(metadata.get("source") or "")
        if url and url in body:
            covered.add(key)
            continue
        title = str(metadata.get("paper_title") or metadata.get("source_file") or "")
        if title:
            if norm_body is None:
                norm_body = _normalized_title(body)
            if _normalized_title(title) in norm_body:
                covered.add(key)
    return covered


def thin_paper_analysis(body: str, docs: list[Document], minimum_words: int = 40) -> bool:
    """Detect token mentions replacing analysis of substantive source evidence."""
    for doc in docs:
        if doc.metadata.get("evidence_scope") == "metadata_only":
            continue
        paragraphs = [part for part in _PARA_SPLIT_RE.split(body)
                      if covered_papers(part, [doc])]
        words = sum(len(_CITATION_STRIP_RE.sub("", _TITLE_PREFIX_RE.sub("", part)).split())
                    / max(1, len(covered_papers(part, docs))) for part in paragraphs)
        if words < minimum_words:
            return True
    return False


def reject_speculative_methods(report: str, docs: list[Document] | None = None) -> str:
    """A guess about authors' methods/limitations is not a cited finding."""
    for number, body in section_bodies(report).items():
        if number not in (3, 4):
            continue
        paragraphs = _PARA_SPLIT_RE.split(body)
        for index, paragraph in enumerate(paragraphs):
            metadata_method = number == 3 and any(
                doc.metadata.get("evidence_scope") == "metadata_only" and covered_papers(paragraph, [doc])
                for doc in docs or []
            )
            prose = _TITLE_PREFIX_RE.sub("", paragraph)
            prose = _CITATION_STRIP_RE.sub("", prose)
            method_claim = _METHOD_CLAIM_RE.search(prose)
            explicit_boundary = _EXPLICIT_BOUNDARY_RE.search(prose)
            if (metadata_method and method_claim and not explicit_boundary) or _SPECULATIVE_RE.search(paragraph):
                paragraphs[index] = f"{OMITTED_PASSAGE} (speculative attribution of methods or limitations)."
        replacement = "\n\n".join(paragraphs)
        def replace_section(match: re.Match, content: str = replacement) -> str:
            return match[1] + content + "\n\n"
        report = re.sub(rf"(?ms)(^##\s+{number}\.\s+[^\n]*\n).*?(?=^##\s+|\Z)",
                        replace_section, report, count=1)
    return report


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
        numeric_text = re.sub(r"\b(?:ChatGPT|GPT|Llama|Gemma|Qwen|Gemini)[\s_\-\u2010-\u2015]*\d+(?:\.\d+)*\b", "model", body, flags=re.I)
        markers = list(dict.fromkeys(int(value) for value in re.findall(r"\((\d+)\)(?=\s)", numeric_text)))
        if len(markers) >= 2 and markers == list(range(1, len(markers) + 1)):
            numeric_text = re.sub(r"\(\d+\)(?=\s)", "", numeric_text)
        candidate = f"General guidance: {numeric_text}"
        if body and ground_answer(candidate, {}, [], allow_general_guidance=True) == candidate:
            guidance[number] = body
    return guidance


def ensure_source_summaries(report: str, documents: list[Document]) -> str:
    """Never silently lose a selection when a model omits/rejects its summary.

    An explicitly quoted retrieved passage is a source extract, not an invented
    model summary. Metadata-only selections retain an honest coverage note.
    """
    summary = section_bodies(report).get(1, "")
    selected_titles = {_normalized_title(str(doc.metadata.get("paper_title") or doc.metadata.get("source_file") or "Selected paper")) for doc in documents}
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
    report = concise_guidance(report)
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
    unlinked_sources: list[str] = []
    appendices = list(re.finditer(r"(?ms)^##\s+(?:Selected sources|Sources)\s*\n(.*?)(?=^##\s+|\Z)", report))
    for appendix in appendices:
        for entry in re.finditer(r"\*\*Source (\d+):\*\*\s*\[([^\]]+)\]\((https?://[^\s)]+)\)", appendix[1]):
            sources.setdefault(entry[3], (int(entry[1]), entry[2]))
        for entry in re.finditer(r"(?m)^-\s+(\[[^\]\n]+\])(?!\()\s*$", appendix[1]):
            if entry[1] not in unlinked_sources:
                unlinked_sources.append(entry[1])
    report = re.sub(r"(?ms)^##\s+(?:Selected sources|Sources)\s*\n.*?(?=^##\s+|\Z)", "", report).rstrip()

    def replace(match: re.Match) -> str:
        label, url = match[1], match[2]
        if re.fullmatch(r"Source \d+(?:, p\. \d+)?", label):
            return match[0]
        page = re.search(r" - Page (\d+)$", label)
        title = label[: page.start()] if page else label
        if url not in sources:
            sources[url] = (max((entry[0] for entry in sources.values()), default=0) + 1, title)
        number = sources[url][0]
        location = f", p. {page[1]}" if page else ""
        return f"[Source {number}{location}]({url})"

    report = re.sub(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", replace, report)
    for appendix in appendices:
        for entry in re.finditer(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)", appendix[1]):
            replace(entry)
    report = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s*\1)+", r"\1", report)
    report = re.sub(r"(\]\([^)]+\))(?=\[)", r"\1 ", report)
    if sources or unlinked_sources:
        references = "\n".join([
            *(f"- **Source {number}:** [{title}]({url})" for url, (number, title) in sources.items()),
            *(f"- {title}" for title in unlinked_sources),
        ])
        report += "\n\n## Sources\n\n" + references
    return report
