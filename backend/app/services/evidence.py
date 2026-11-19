"""Local evidence selection, token accounting, and citation resolution."""

import re
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from urllib.parse import urlsplit

import tiktoken
from langchain_core.documents import Document

_WORD_PATTERN = re.compile(r"[\w-]{2,}")
_RRF_SCORES = tuple(1.0 / (60 + r) for r in range(1, 2001))
_TERMS_PATTERN = re.compile(r"[\w-]{2,}")
_TITLE_BRACKETS = re.compile(r"[\[\]<>\n\r]")
_TITLE_MULTI_SPACE = re.compile(r"\s+")
_NORM_CITATIONS_PATTERN = re.compile(
    r"\[(E\d+(?:\s*[,;/]\s*E\d+)*)\]|\((E\d+(?:\s*[,;/]\s*E\d+)*)\)",
    re.I,
)
_NORM_E_DIGIT = re.compile(r"E\d+", re.I)

_RESOLVE_LOOKBEHIND = re.compile(r"(?<=[\w)*`])(?=\[E\d+\])")
_RESOLVE_BULLET = re.compile(
    r"(?m)^(\s*[-*•]\s*)(?:Source\s+)?P\d+(?:\s*[/,-]\s*(?:P\d+|E\d+))*\s*\(([^)\n]+)\)"
)
_RESOLVE_E_KEY = re.compile(r"\[(E\d+)\]")
_RESOLVE_DEDUP_LINKS = re.compile(r"(\[[^\]]+\]\([^)]+\))(?:\s+\1)+")
_RESOLVE_PUNCT_SPACING = re.compile(r"(\[[^\]]+\](?:\([^)]+\))?)\s+([.,;:!?])")

_URL_PATTERN = re.compile(r"https?://\S+")
_HAS_DIGIT = re.compile(r"\d")
_NUMBER_PATTERN = re.compile(
    r"(?<![\w.])([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)(\s*%|\s+percent\b)?(?!\w|\.\d)",
    re.I,
)

_MD_LINK_STRIP = re.compile(r"\[([^\]]+)\]\(https?://[^)]+\)")
_UNVERIFIED_URL_STRIP = re.compile(r"https?://[^\s<>]+")
_BLOCK_SPLIT = re.compile(r"(\n\s*\n|\n(?=\s*(?:#{1,6} |[-*•] |\d+[.)] |\|)))")
_HEADING_PATTERN = re.compile(r"^#{1,6}\s+([^\n]+)")
_HEADING_NUM_PREFIX = re.compile(r"^\d+\.\s*")
_TABLE_BORDER_PATTERN = re.compile(r"[\s|:-]+")
_UNSUPPLIED_REF_PATTERN = re.compile(r"\[(?:Paper\s*|P)\d+\]", re.I)
_REF_PATTERN = re.compile(r"\[(E\d+)\]")
_ABSTENTION_PATTERN = re.compile(
    r"(?:[-*•]\s*)?(?:Insufficient evidence(?: (?:in|to|for|from|about|on)[^.!?\n]*)?|I cannot find[^.]*|Not (?:provided|available)[^.]*)[.!]?",
    re.I,
)
_PROPOSAL_PATTERN = re.compile(
    r"^(?:[-*•]\s*)?(?:Proposed (?:project|research|hypothesis)|Hypothesis|Suggestion)\s*:",
    re.I,
)
_GUIDANCE_PATTERN = re.compile(r"^(?:\*\*)?General guidance(?:\*\*)?\s*:", re.I)
_CLAIM_REF_STRIP = re.compile(r"\[E\d+\]")
_CLAIM_NUM_PREFIX = re.compile(r"(?m)^\s*(?:[-*•]\s+)?(?:\d+[.)]\s+|\(\d+\)\s+)")
_ORDINAL_PATTERN = re.compile(r"\((\d+)\)(?=\s)")
_COLON_PREFIX_PATTERN = re.compile(
    r"\b(?:consists\s+of|includes?|(?:steps?|stages?|components?)\s+are)$",
    re.I,
)


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("cl100k_base")


def token_count(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))


def truncate_tokens(text: str, budget: int) -> str:
    encoding = _encoding()
    return encoding.decode(encoding.encode(text, disallowed_special=())[:budget])


def terms(text: str) -> set[str]:
    return set(_TERMS_PATTERN.findall(text.lower()))


def rank_evidence(query: str, documents: list[Document]) -> list[Document]:
    query_terms = terms(query)
    lexical = sorted(
        range(len(documents)),
        key=lambda i: len(query_terms & terms(documents[i].page_content)),
        reverse=True,
    )
    lexical_rank = {index: rank for rank, index in enumerate(lexical)}
    rrf_len = len(_RRF_SCORES)
    return [
        documents[i]
        for i in sorted(
            range(len(documents)),
            key=lambda i: (
                (_RRF_SCORES[i] if i < rrf_len else 1.0 / (61 + i))
                + (_RRF_SCORES[lexical_rank[i]] if lexical_rank[i] < rrf_len else 1.0 / (61 + lexical_rank[i]))
            ),
            reverse=True,
        )
    ]


@lru_cache(maxsize=256)
def _clean_title(raw_title: str) -> str:
    title = _TITLE_BRACKETS.sub(" ", raw_title)
    return _TITLE_MULTI_SPACE.sub(" ", title).strip()


def fit_evidence(documents: list[Document], budget: int) -> list[Document]:
    kept: list[Document] = []
    seen: set[tuple[str, int]] = set()
    current_text = ""
    current_sources: set[str] = set()
    current_cost = 0

    for doc in documents:
        source = str(
            doc.metadata.get("paper_id")
            or doc.metadata.get("source_file")
            or doc.metadata.get("source", "")
        )
        content_hash = hash(" ".join(doc.page_content.split()))
        key = (source, content_hash)
        if key in seen:
            continue

        meta = doc.metadata
        title = _clean_title(str(meta.get("paper_title") or meta.get("source_file") or "Document"))
        source_key = str(meta.get("paper_id") or meta.get("source_file") or title)

        new_blocks: list[str] = []
        if source_key not in current_sources:
            new_blocks.append(f"Source: {title}; year={meta.get('year', 'unknown')}")

        page = meta.get("page")
        location = f"; page={page + 1}" if isinstance(page, int) else ""
        scope = meta.get("evidence_scope", "full_text")
        evidence_id = f"E{len(kept) + 1}"
        new_blocks.append(
            f"[{evidence_id}; title={title}{location}; scope={scope}]\n{doc.page_content}"
        )

        candidate_addition = "\n\n".join(new_blocks)
        candidate_text = (
            (current_text + "\n\n" + candidate_addition)
            if current_text
            else candidate_addition
        )

        add_cost = token_count(candidate_addition)
        if current_cost + add_cost + 4 <= budget:
            cost = current_cost + add_cost + 1
        else:
            cost = token_count(candidate_text)

        if cost > budget:
            continue

        kept.append(doc)
        seen.add(key)
        current_text = candidate_text
        current_cost = cost
        current_sources.add(source_key)

    return kept


def format_evidence(documents: list[Document]) -> tuple[str, dict[str, str]]:
    blocks = []
    sources: dict[str, str] = {}
    citations = {}
    for i, doc in enumerate(documents, 1):
        evidence_id = f"E{i}"
        meta = doc.metadata
        title = _clean_title(str(meta.get("paper_title") or meta.get("source_file") or "Document"))
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
    if "【" in answer:
        answer = answer.replace("【", "[").replace("】", "]")
    if "E" not in answer and "e" not in answer:
        return answer
    return _NORM_CITATIONS_PATTERN.sub(
        lambda m: " ".join(f"[{ref.upper()}]" for ref in _NORM_E_DIGIT.findall(m[0])),
        answer,
    )


def resolve_citations(answer: str, citations: dict[str, str]) -> str:
    answer = _normalize_citations(answer)
    if "E" in answer or "e" in answer or "P" in answer:
        answer = _RESOLVE_LOOKBEHIND.sub(" ", answer)
        answer = _RESOLVE_BULLET.sub(
            lambda m: f"{m[1]}**{m[2].strip().strip('*')}**",
            answer,
        )
        resolved = _RESOLVE_E_KEY.sub(lambda m: citations.get(m[1], "[unverified source]"), answer)
    else:
        resolved = answer
    if "](" in resolved:
        resolved = _RESOLVE_DEDUP_LINKS.sub(r"\1", resolved)
        resolved = _RESOLVE_PUNCT_SPACING.sub(r"\1\2", resolved)
    return resolved


def _numbers(text: str) -> set[str]:
    if not _HAS_DIGIT.search(text):
        return set()
    if "http" in text:
        text = _URL_PATTERN.sub("", text)
    if "−" in text:
        text = text.replace("−", "-")
    result = set()
    for match in _NUMBER_PATTERN.finditer(text):
        try:
            m1 = match[1]
            number = Decimal(m1.replace(",", "") if "," in m1 else m1)
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
    if "](" in answer:
        answer = _MD_LINK_STRIP.sub(r"[\1]", answer)
    if "http" in answer:
        answer = _UNVERIFIED_URL_STRIP.sub("[unverified URL removed]", answer)
    evidence = {}
    evidence_nums: dict[str, set[str]] = {}
    for i, doc in enumerate(documents or [], 1):
        title = doc.metadata.get("paper_title") or doc.metadata.get("source_file") or ""
        evidence[f"E{i}"] = f"{doc.page_content} {title} {doc.metadata.get('year', '')}"
    if "|" in answer:
        lines = answer.splitlines()
        table_headers = {
            line.strip()
            for i, line in enumerate(lines[:-1])
            if line.strip().startswith("|") and _TABLE_BORDER_PATTERN.fullmatch(lines[i + 1])
        }
    else:
        table_headers = set()
    blocks = _BLOCK_SPLIT.split(answer)
    background = False
    proposal_section = False
    kept = []
    for index, block in enumerate(blocks):
        if index % 2:
            kept.append(block)
            continue
        heading = _HEADING_PATTERN.match(block)
        if heading:
            name = _HEADING_NUM_PREFIX.sub("", heading[1]).strip().casefold()
            background = name == "background knowledge"
            proposal_section = name == "novel paper suggestions"
        if "|" in block:
            prose = "\n".join(
                line
                for line in block.splitlines()
                if not line.lstrip().startswith("#")
                and line.strip() not in table_headers
                and not _TABLE_BORDER_PATTERN.fullmatch(line)
            ).strip()
        else:
            prose = "\n".join(
                line
                for line in block.splitlines()
                if not line.lstrip().startswith("#")
            ).strip()
        if not prose:
            kept.append(block)
            continue
        refs = _REF_PATTERN.findall(prose)
        reason = ""
        if set(refs) - citations.keys() or _UNSUPPLIED_REF_PATTERN.search(prose):
            reason = "it cited evidence that was not supplied"
        elif not refs:
            abstention = _ABSTENTION_PATTERN.fullmatch(prose)
            proposal = allow_proposals and _PROPOSAL_PATTERN.match(prose)
            hypothesis_row = (
                allow_proposals
                and proposal_section
                and prose.startswith("|")
                and any(
                    "hypothesis" in h.casefold() and "proposed" in h.casefold()
                    for h in table_headers
                )
                and not _numbers(prose)
            )
            general_guidance = (
                allow_general_guidance
                and _GUIDANCE_PATTERN.match(prose)
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
            claim = _CLAIM_REF_STRIP.sub("", prose)
            claim = _CLAIM_NUM_PREFIX.sub("", claim)
            ordinals = list(_ORDINAL_PATTERN.finditer(claim))
            if len(ordinals) >= 2 and [int(m[1]) for m in ordinals] == list(range(1, len(ordinals) + 1)):
                prefix = claim[:ordinals[0].start()].rstrip()
                if prefix.endswith(":") or _COLON_PREFIX_PATTERN.search(prefix):
                    claim = _ORDINAL_PATTERN.sub("", claim)
            if claim_nums := _numbers(claim):
                source_nums: set[str] = set()
                for ref in refs:
                    nums = evidence_nums.get(ref)
                    if nums is None:
                        nums = _numbers(evidence.get(ref, ""))
                        evidence_nums[ref] = nums
                    source_nums.update(nums)
                if claim_nums - source_nums:
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
