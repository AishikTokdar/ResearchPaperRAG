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
                f"Source {sources[source_key]}: {title}; year={meta.get('year', 'unknown')}"
            )
        scope = meta.get("evidence_scope", "full_text")
        location = f"; page={page + 1}" if isinstance(page, int) else ""
        blocks.append(
            f"[{evidence_id}; paper={sources[source_key]}{location}; scope={scope}]\n{doc.page_content}"
        )
    return "\n\n".join(blocks), citations


def resolve_citations(answer: str, citations: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        return citations.get(match.group(1), "[unverified source]")

    return re.sub(r"\[(E\d+)\]", replace, answer)


def ground_answer(
    answer: str,
    citations: dict[str, str],
    documents: list[Document] | None = None,
    *,
    allow_background: bool = False,
) -> str:
    """Fail closed on invalid citation IDs; this checks provenance, not entailment."""
    answer = re.sub(
        r"\[(E\d+(?:\s*,\s*E\d+)+)\]",
        lambda match: " ".join(f"[{part.strip()}]" for part in match[1].split(",")),
        answer,
    )
    ids = set(re.findall(r"\[(E\d+)\]", answer))
    if ids - citations.keys():
        return "I cannot verify this response because it cited evidence that was not supplied."
    if not ids and not re.search(
        r"insufficient evidence|cannot find|not provided|not available|not enough evidence",
        answer,
        re.I,
    ):
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
                background = headings[-1].strip().casefold() == "background knowledge"
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
