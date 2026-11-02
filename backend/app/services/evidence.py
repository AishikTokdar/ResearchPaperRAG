"""Local evidence selection, token accounting, and citation resolution."""

import hashlib
import re
from functools import lru_cache
from urllib.parse import urlsplit

import tiktoken
from langchain_core.documents import Document


@lru_cache(maxsize=1)
def _encoding():
    # A common tokenizer for budgeting, not a claim of exact provider billing.
    return tiktoken.get_encoding("cl100k_base")


def token_count(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))


def truncate_tokens(text: str, budget: int) -> str:
    encoding = _encoding()
    return encoding.decode(encoding.encode(text, disallowed_special=())[:budget])


def terms(text: str) -> set[str]:
    return set(re.findall(r"[\w-]{2,}", text.lower()))


def rank_evidence(query: str, documents: list[Document]) -> list[Document]:
    """Fuse dense rank with local lexical rank; never use page position as relevance."""
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
            continue  # A large passage must not prevent smaller complete passages fitting.
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
            blocks.append(
                f"Source: {title}; year={meta.get('year', 'unknown')}"
            )
        scope = meta.get("evidence_scope", "full_text")
        location = f"; page={page + 1}" if isinstance(page, int) else ""
        blocks.append(
            f"[{evidence_id}; title={title}{location}; scope={scope}]\n{doc.page_content}"
        )
    return "\n\n".join(blocks), citations


def resolve_citations(answer: str, citations: dict[str, str]) -> str:
    # 1. Normalize fullwidth/Chinese brackets: 【E1】 -> [E1]
    answer = answer.replace("【", "[").replace("】", "]")

    # 2. Normalize compound and messy bracketed citation tags
    answer = re.sub(
        r"\[(E\d+(?:\s*,\s*E\d+)+)\]",
        lambda match: " ".join(f"[{part.strip()}]" for part in match[1].split(",")),
        answer,
    )
    answer = re.sub(r"\[(E\d+)[;:,\s][^\]]*\]", r"[\1]", answer)
    answer = re.sub(r"\(E(\d+)\)", r"[E\1]", answer)

    # 3. Clean prompt artifact prefixes like "• P1 / P4 (Title) –" -> "• **Title** –"
    def _clean_bullet_header(m: re.Match) -> str:
        prefix = m.group(1)
        inner = (m.group(2) or m.group(3) or "").strip()
        if inner.startswith("**") and inner.endswith("**"):
            return f"{prefix}{inner}"
        return f"{prefix}**{inner}**"

    answer = re.sub(
        r"(?m)^(\s*[-*•]\s*)(?:(?:Source\s+)?P\d+(?:\s*[/,-]\s*(?:P\d+|E\d+))*\s*[:\-–—]?\s*)(?:\(([^)\n]+)\)|([^\n–—:-]+[:\-–—]))",
        _clean_bullet_header,
        answer,
    )
    answer = re.sub(r"\bP\d+\s*[/,-]\s*(?:P\d+|E\d+)\b", "", answer)
    answer = re.sub(r"(?m)^(\s*[-*•]\s*)(?:Source\s+)?P\d+\s*[:\-–—]\s*", r"\1", answer)

    # 4. Replace evidence tags with citations
    def replace(match: re.Match) -> str:
        return citations.get(match.group(1), "[unverified source]")

    resolved = re.sub(r"\[(E\d+)\]", replace, answer)

    # 5. Deduplicate consecutive identical markdown links: [Title](url) [Title](url) -> [Title](url)
    resolved = re.sub(r"(\[[^\]]+\]\([^)]+\))(?:\s+\1)+", r"\1", resolved)

    # 6. Fix spaces before sentence punctuation after citation: [Title](url) . -> [Title](url).
    resolved = re.sub(r"(\[[^\]]+\](?:\([^)]+\))?)\s+([.,;:!?])", r"\1\2", resolved)

    return resolved


def ground_answer(
    answer: str,
    citations: dict[str, str],
    documents: list[Document] | None = None,
    *,
    allow_background: bool = False,
) -> str:
    """Fail closed on invalid citation IDs; this checks provenance, not entailment."""
    answer = answer.replace("【", "[").replace("】", "]")
    answer = re.sub(
        r"\[(E\d+(?:\s*,\s*E\d+)+)\]",
        lambda match: " ".join(f"[{part.strip()}]" for part in match[1].split(",")),
        answer,
    )
    answer = re.sub(r"\[(E\d+)[;:,\s][^\]]*\]", r"[\1]", answer)
    answer = re.sub(r"\(E(\d+)\)", r"[E\1]", answer)

    def _map_paper_to_evidence(m):
        num = m.group(1)
        eid = f"E{num}"
        return f"[{eid}]" if eid in citations else m.group(0)

    answer = re.sub(r"\[(?:Paper|P)\s*(\d+)\]", _map_paper_to_evidence, answer, flags=re.I)
    answer = re.sub(r"\bP\d+\s*[/,-]\s*(?:P\d+|E\d+)\b", "", answer)

    ids = set(re.findall(r"\[(E\d+)\]", answer))
    if ids - citations.keys():
        return "I cannot verify this response because it cited evidence that was not supplied."
    if not ids and not re.search(
        r"insufficient evidence|cannot find|not provided|not available|not enough evidence",
        answer,
        re.I,
    ):
        if allow_background and len(answer.split()) > 30:
            return resolve_citations(answer, citations)
        return "I cannot provide a grounded answer: the generated response did not cite the supplied evidence."
    # The model must not invent source links; URLs come exclusively from the citation map.
    answer = re.sub(
        r"\[([^\]]+)\]\(https?://[^)]+\)",
        lambda match: f"[{match[1]}]" if match[1] in citations else match[1],
        answer,
    )
    answer = re.sub(r"https?://[^\s<>]+", "[unverified URL removed]", answer)
    if documents is not None:
        evidence = {
            f"E{i}": doc.page_content + "\n" + str(doc.metadata.get("year", ""))
            for i, doc in enumerate(documents, 1)
        }
        # Check prose paragraphs, list items and table rows separately. A disclaimer in
        # another section cannot excuse an uncited factual claim.
        lines = answer.splitlines()
        table_headers = {
            line.strip()
            for i, line in enumerate(lines[:-1])
            if line.strip().startswith("|") and re.fullmatch(r"[\s|:-]+", lines[i + 1])
        }
        blocks = re.split(r"\n\s*\n|\n(?=\s*(?:[-*] |\d+[.)] |\|))", answer)
        background = False
        for block in blocks:
            headings = re.findall(r"(?m)^#{1,6}\s+([^\n]+)", block)
            if headings:
                last_h = headings[-1].strip().casefold()
                background = last_h == "background knowledge" or any(
                    s in last_h
                    for s in [
                        "future direction",
                        "novel paper",
                        "research gap",
                        "proposed",
                        "hypothesis",
                        "background",
                    ]
                )
            prose = "\n".join(
                line
                for line in block.splitlines()
                if not line.lstrip().startswith("#")
                and line.strip() not in table_headers
                and not re.fullmatch(r"[\s|:-]+", line)
            )
            prose = prose.strip()
            if not prose:
                continue
            refs = re.findall(r"\[(E\d+)\]", prose)
            if allow_background and background and not refs:
                continue
            # Only a wholly abstaining block or explicitly labeled proposal may omit citations.
            abstention = re.fullmatch(
                r"(?:[-*]\s*)?(?:Insufficient evidence(?: (?:in|to|for|from|about|on)[^.!?\n]*)?|I cannot find[^.]*|Not (?:provided|available)[^.]*)[.!]?",
                prose,
                re.I,
            )
            proposal = re.match(
                r"^(?:[-*]\s*)?(?:Proposed (?:project|research|hypothesis)|Hypothesis|Suggestion)\s*:",
                prose,
                re.I,
            )
            if not refs and not (abstention or proposal):
                return "I cannot provide a grounded answer: a factual passage did not cite the supplied evidence."
            if refs:
                claim = re.sub(r"\[E\d+\]", "", prose)
                claim = re.sub(r"(?m)^\s*\d+[.)]\s+", "", claim)
                numbers = set(re.findall(r"(?<![\w])\d+(?:[.,]\d+)*(?:%|\b)", claim))
                source = " ".join(evidence.get(ref, "") for ref in refs)
                supported = set(re.findall(r"(?<![\w])\d+(?:[.,]\d+)*(?:%|\b)", source))
                if numbers - supported:
                    return "I cannot verify this response: a numerical claim is absent from its cited evidence."
    return resolve_citations(answer, citations)
