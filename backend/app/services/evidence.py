"""Local evidence selection, token accounting, and citation resolution."""

import hashlib
import re
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from urllib.parse import urlsplit

import tiktoken
from langchain_core.documents import Document


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def token_count(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))


def truncate_tokens(text: str, budget: int) -> str:
    encoding = _encoding()
    return encoding.decode(encoding.encode(text, disallowed_special=())[:budget])


def terms(text: str) -> set[str]:
    return set(re.findall(r"[\w-]{2,}", text.lower()))


def rank_evidence(query: str, documents: list[Document]) -> list[Document]:
    query_terms = terms(query)
    lexical = sorted(
        range(len(documents)),
        key=lambda i: len(query_terms & terms(documents[i].page_content)),
        reverse=True,
    )
    lexical_rank = {index: rank for rank, index in enumerate(lexical)}
    return [
        documents[i]
        for i in sorted(
            range(len(documents)),
            key=lambda i: 1 / (60 + i + 1) + 1 / (60 + lexical_rank[i] + 1),
            reverse=True,
        )
    ]


def fit_evidence(documents: list[Document], budget: int) -> list[Document]:
    kept: list[Document] = []
    seen: set[tuple[str, str]] = set()
    for doc in documents:
        source = str(
            doc.metadata.get("paper_id")
            or doc.metadata.get("source_file")
            or doc.metadata.get("source", "")
        )
        digest = hashlib.sha256(" ".join(doc.page_content.split()).encode()).hexdigest()
        key = (source, digest)
        if key in seen:
            continue
        cost = token_count(format_evidence(kept + [doc])[0])
        if cost > budget:
            continue
        kept.append(doc)
        seen.add(key)
    return kept


def format_evidence(documents: list[Document]) -> tuple[str, dict[str, str]]:
    blocks = []
    sources: dict[str, str] = {}
    citations = {}
    for i, doc in enumerate(documents, 1):
        evidence_id = f"E{i}"
        meta = doc.metadata
        title = str(meta.get("paper_title") or meta.get("source_file") or "Document")
        title = re.sub(r"[\[\]<>\n\r]", " ", title)
        title = re.sub(r"\s+", " ", title).strip()
        page = meta.get("page")
        label = f"{title} - Page {page + 1}" if isinstance(page, int) else title
        url = str(meta.get("source", ""))
        try:
            safe_url = urlsplit(url).scheme in {"https", "http"} and bool(urlsplit(url).hostname)
        except ValueError:
            safe_url = False
        citations[evidence_id] = (
            f"[{label}]({url.replace(' ', '%20').replace(')', '%29')})"
            if safe_url
            else f"[{label}]"
        )
        source_key = str(meta.get("paper_id") or meta.get("source_file") or title)
        if source_key not in sources:
            sources[source_key] = f"P{len(sources) + 1}"
            blocks.append(f"Source: {title}; year={meta.get('year', 'unknown')}")
        scope = meta.get("evidence_scope", "full_text")
        location = f"; page={page + 1}" if isinstance(page, int) else ""
        blocks.append(
            f"[{evidence_id}; title={title}{location}; scope={scope}]\n{doc.page_content}"
        )
    return "\n\n".join(blocks), citations


OMITTED_PASSAGE = "Insufficient evidence to verify this passage"


def _normalize_citations(answer: str) -> str:
    answer = answer.replace("【", "[").replace("】", "]")
    return re.sub(
        r"\[(E\d+(?:\s*[,;]\s*E\d+)*)\]|\(E(\d+)\)",
        lambda m: " ".join(f"[{ref.upper()}]" for ref in re.findall(r"E\d+", m[0], re.I)),
        answer,
        flags=re.I,
    )


def resolve_citations(answer: str, citations: dict[str, str]) -> str:
    answer = _normalize_citations(answer)
    answer = re.sub(r"(?<=[\w)*`])(?=\[E\d+\])", " ", answer)
    answer = re.sub(
        r"(?m)^(\s*[-*•]\s*)(?:Source\s+)?P\d+(?:\s*[/,-]\s*(?:P\d+|E\d+))*\s*\(([^)\n]+)\)",
        lambda m: f"{m[1]}**{m[2].strip().strip('*')}**",
        answer,
    )
    resolved = re.sub(r"\[(E\d+)\]", lambda m: citations.get(m[1], "[unverified source]"), answer)
    resolved = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s+\1)+", r"\1", resolved)
    return re.sub(r"(\[[^\]]+\](?:\([^)]+\))?)\s+([.,;:!?])", r"\1\2", resolved)


def _numbers(text: str) -> set[str]:
    text = re.sub(r"https?://\S+", "", text).replace("−", "-")
    result = set()
    pattern = r"(?<![\w.])([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(\s*%|\s+percent\b)?(?!\w|\.\d)"
    for match in re.finditer(pattern, text, re.I):
        try:
            number = Decimal(match[1].replace(",", ""))
            exponent = number.as_tuple().exponent
            if not isinstance(exponent, int) or abs(exponent) > 308:
                value = str(number)
            else:
                value = format(number, "f")
                if "." in value:
                    value = value.rstrip("0").rstrip(".")
        except InvalidOperation:
            value = match[1]
        result.add(value + ("%" if match[2] else ""))
    return result


def ground_answer(
    answer: str,
    citations: dict[str, str],
    documents: list[Document] | None = None,
    *,
    allow_background: bool = False,
    preserve_valid_blocks: bool = False,
    allow_proposals: bool = False,
    allow_general_guidance: bool = False,
) -> str:
    answer = _normalize_citations(answer)
    answer = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"[\1]", answer)
    answer = re.sub(r"https?://[^\s<>]+", "[unverified URL removed]", answer)
    evidence = {}
    for i, doc in enumerate(documents or [], 1):
        title = doc.metadata.get("paper_title") or doc.metadata.get("source_file") or ""
        evidence[f"E{i}"] = f"{doc.page_content} {title} {doc.metadata.get('year', '')}"
    lines = answer.splitlines()
    table_headers = {
        line.strip()
        for i, line in enumerate(lines[:-1])
        if line.strip().startswith("|") and re.fullmatch(r"[\s|:-]+", lines[i + 1])
    }
    blocks = re.split(r"(\n\s*\n|\n(?=\s*(?:#{1,6} |[-*•] |\d+[.)] |\|)))", answer)
    background = False
    proposal_section = False
    kept = []
    for index, block in enumerate(blocks):
        if index % 2:
            kept.append(block)
            continue
        heading = re.match(r"^#{1,6}\s+([^\n]+)", block)
        if heading:
            name = re.sub(r"^\d+\.\s*", "", heading[1]).strip().casefold()
            background = name == "background knowledge"
            proposal_section = name == "novel paper suggestions"
        prose = "\n".join(
            line
            for line in block.splitlines()
            if not line.lstrip().startswith("#")
            and line.strip() not in table_headers
            and not re.fullmatch(r"[\s|:-]+", line)
        ).strip()
        if not prose:
            kept.append(block)
            continue
        refs = re.findall(r"\[(E\d+)\]", prose)
        reason = ""
        if set(refs) - citations.keys() or re.search(r"\[(?:Paper\s*|P)\d+\]", prose, re.I):
            reason = "it cited evidence that was not supplied"
        elif not refs:
            abstention = re.fullmatch(
                r"(?:[-*•]\s*)?(?:Insufficient evidence(?: (?:in|to|for|from|about|on)[^.!?\n]*)?|I cannot find[^.]*|Not (?:provided|available)[^.]*)[.!]?",
                prose,
                re.I,
            )
            proposal = re.match(
                r"^(?:[-*•]\s*)?(?:Proposed (?:project|research|hypothesis)|Hypothesis|Suggestion)\s*:",
                prose,
                re.I,
            )
            hypothesis_row = (
                allow_proposals
                and proposal_section
                and prose.startswith("|")
                and any(
                    "hypothesis" in h.casefold() and "proposed" in h.casefold()
                    for h in table_headers
                )
            )
            general_guidance = (
                allow_general_guidance
                and re.match(r"^(?:\*\*)?General guidance(?:\*\*)?\s*:", prose, re.I)
                and not _numbers(prose)
            )
            if not (
                abstention
                or proposal
                or hypothesis_row
                or general_guidance
                or (allow_background and background)
            ):
                reason = "a factual passage did not cite the supplied evidence"
        elif documents is not None:
            claim = re.sub(r"\[E\d+\]", "", prose)
            claim = re.sub(r"(?m)^\s*(?:[-*•]\s+)?(?:\d+[.)]\s+|\(\d+\)\s+)", "", claim)
            source = " ".join(evidence.get(ref, "") for ref in refs)
            if _numbers(claim) - _numbers(source):
                reason = "a numerical claim is absent from its cited evidence"
        if not reason:
            kept.append(block)
        elif not preserve_valid_blocks:
            prefix = (
                "I cannot provide a grounded answer"
                if "did not cite" in reason
                else "I cannot verify this response"
            )
            return f"{prefix}: {reason}."
        else:
            if heading:
                kept.append(heading[0] + "\n\n")
            notice = f"{OMITTED_PASSAGE} ({reason})."
            if prose.startswith("|"):
                columns = len(prose.strip().strip("|").split("|"))
                notice = "| " + notice + " |" + " — |" * (columns - 1)
            kept.append(notice)
    return (
        resolve_citations("".join(kept), citations)
        if answer.strip()
        else "Insufficient evidence to produce an answer."
    )
