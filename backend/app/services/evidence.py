"""Local evidence selection, token accounting, and citation resolution."""

import re
import unicodedata
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
    r"(?:[-*•]\s*)?(?:Insufficient evidence(?: (?:in|from) (?:the )?(?:supplied|selected|provided) (?:evidence|papers|documents?|sources?|record))?(?: to (?:answer(?: (?:this|the) question)?|verify(?: (?:this|the) (?:claim|passage|response))?))?|I cannot find sufficient evidence(?: in (?:the )?(?:document|supplied evidence))?|Not (?:provided|available)(?: in (?:the )?(?:supplied|selected) (?:evidence|record|document))?)[.!]?",
    re.I,
)
_PROPOSAL_PATTERN = re.compile(
    r"^(?:[-*•]\s*)?(?:Proposed (?:project|research|hypothesis)|Hypothesis|Suggestion)\s*:",
    re.I,
)
_GUIDANCE_PATTERN = re.compile(r"^(?:\*\*)?General guidance(?:\*\*)?\s*:", re.I)
_STRUCTURAL_HEADINGS = frozenset({
    "literature summary", "trend detection", "common methods", "limitations",
    "contradictions", "research gaps", "future directions", "novel paper suggestions",
    "background knowledge", "sources", "results", "summary", "answer", "methods", "comparison",
})
_CLAIM_REF_STRIP = re.compile(r"\[E\d+\]")
_CLAIM_NUM_PREFIX = re.compile(r"(?m)^\s*(?:[-*•]\s+)?(?:\d+[.)]\s+|\(\d+\)\s+)")
_ORDINAL_PATTERN = re.compile(r"\((\d+)\)(?=\s)")
_COLON_PREFIX_PATTERN = re.compile(
    r"\b(?:consists\s+of|includes?|(?:steps?|stages?|components?)\s+are)$",
    re.I,
)
_TITLE_DASH_RE = re.compile(r"^\s*(?:[-*•]\s*)?\*\*([^*]+)\*\*\s*[–—-]\s*")
_RECOVERY_TITLE_PREFIX_RE = re.compile(r"^\s*(?:[-*•]\s+)?\*\*[^*]+\*\*\s*[–—-]\s*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_TRAILING_REF_RE = re.compile(r"([.!?])\s+(\[E\d+\](?:\s*\[E\d+\])*)")
_PIECE_REF_SPLIT_RE = re.compile(r"(?<=\]\.)\s+|(?<=\]!)\s+|(?<=\]\?)\s+")
_QUOTE_STRIP_MAP = str.maketrans("", "", "*`\"“”‘’")


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


def _format_citation_entry(doc: Document) -> tuple[str, str]:
    meta = doc.metadata
    title = _clean_title(str(meta.get("paper_title") or meta.get("source_file") or "Document"))
    page = meta.get("page")
    label = f"{title} - Page {page + 1}" if isinstance(page, int) else title
    url = str(meta.get("source", ""))
    try:
        safe_url = urlsplit(url).scheme in {"https", "http"} and bool(urlsplit(url).hostname)
    except ValueError:
        safe_url = False
    citation = (
        f"[{label}]({url.replace(' ', '%20').replace(')', '%29')})"
        if safe_url
        else f"[{label}]"
    )
    return title, citation


def format_evidence(documents: list[Document]) -> tuple[str, dict[str, str]]:
    blocks = []
    sources: dict[str, str] = {}
    citations = {}
    for i, doc in enumerate(documents, 1):
        evidence_id = f"E{i}"
        meta = doc.metadata
        title, citations[evidence_id] = _format_citation_entry(doc)
        page = meta.get("page")
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


def _recovery_source_key(doc: Document) -> str:
    meta = doc.metadata
    return str(meta.get("paper_id") or meta.get("source") or meta.get("source_file") or "")


def _recovery_statement(text: str) -> str:
    text = _REF_PATTERN.sub("", text)
    text = _CLAIM_NUM_PREFIX.sub("", text)
    text = _RECOVERY_TITLE_PREFIX_RE.sub("", text)
    text = text.replace("**", "").replace("`", "")
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()).strip(" .!?;")


def recover_report_evidence(answer: str, documents: list[Document], candidates: list[Document],
                            max_recovery_tokens: int = 600) -> tuple[str, list[Document]]:
    """Recover exact statements from selected source text before report validation.

    This is deliberately extractive: matching metrics or lexical similarity do
    not establish support. Existing citations constrain recovery to those papers;
    an uncited statement needs a unique selected paper. Strict chat is unaffected.
    """
    answer = _normalize_citations(answer)
    expanded = list(documents)
    citations = {f"E{i}": _format_citation_entry(doc)[1] for i, doc in enumerate(expanded, 1)}
    statements: dict[str, list[Document]] = {}
    selected_keys = {_recovery_source_key(doc) for doc in documents} - {""}
    for doc in [*documents, *candidates]:
        if _recovery_source_key(doc) not in selected_keys or doc.metadata.get("evidence_scope") == "metadata_only":
            continue
        for sentence in _SENTENCE_SPLIT_RE.split(doc.page_content):
            normalized = _recovery_statement(sentence)
            if len(normalized) < 16 or len(normalized.split()) < 3:
                continue
            statements.setdefault(normalized, []).append(Document(page_content=sentence.strip(), metadata=doc.metadata))
    spent = 0
    recovered_refs: dict[tuple[str, str], str] = {}

    def recover(piece: str) -> str:
        nonlocal spent
        if not piece.strip() or piece.lstrip().startswith(("#", "|")):
            return piece
        refs = _REF_PATTERN.findall(piece)
        if set(refs) - citations.keys() or _UNSUPPLIED_REF_PATTERN.search(piece):
            return piece
        verdict = ground_answer(piece, citations, expanded)
        if not verdict.startswith(("I cannot verify this response:", "I cannot provide a grounded answer:")):
            return piece
        allowed_keys = {_recovery_source_key(expanded[int(ref[1:]) - 1]) for ref in refs}
        title = _TITLE_DASH_RE.match(piece)
        if title:
            title_keys = {_recovery_source_key(doc) for doc in documents if _recovery_statement(
                str(doc.metadata.get("paper_title") or doc.metadata.get("source_file") or "")) == _recovery_statement(title[1])}
            if not title_keys or (refs and not allowed_keys.intersection(title_keys)):
                return piece
            allowed_keys = allowed_keys.intersection(title_keys) if refs else title_keys
        matches = [doc for doc in statements.get(_recovery_statement(piece), [])
                   if not (refs or title) or _recovery_source_key(doc) in allowed_keys]
        keys = {_recovery_source_key(doc) for doc in matches}
        if len(keys) != 1:
            return piece
        doc = matches[0]
        identity = (_recovery_source_key(doc), doc.page_content)
        ref = recovered_refs.get(identity)
        if ref is None:
            cost = token_count(format_evidence([doc])[0])
            if spent + cost > max_recovery_tokens:
                return piece
            expanded.append(doc)
            ref = f"E{len(expanded)}"
            recovered_refs[identity] = ref
            spent += cost
            citations[ref] = _format_citation_entry(doc)[1]
        text = _REF_PATTERN.sub("", piece).rstrip()
        if text.endswith("."):
            text = text[:-1].rstrip()
        repaired = f"{text} [{ref}]."
        # All normal grounding rules still apply to recovered text.
        checked = ground_answer(repaired, citations, expanded)
        return piece if checked.startswith(("I cannot verify this response:", "I cannot provide a grounded answer:")) else repaired

    blocks = _BLOCK_SPLIT.split(answer)
    for index in range(0, len(blocks), 2):
        block = blocks[index]
        heading = _HEADING_PATTERN.match(block)
        prefix = heading[0] + "\n" if heading else ""
        prose = block[heading.end():].lstrip("\n") if heading else block
        pieces = _PIECE_REF_SPLIT_RE.split(prose)
        recovered = [recover(piece) for piece in pieces]
        if recovered != pieces:
            blocks[index] = prefix + " ".join(recovered)
    return "".join(blocks), expanded


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


@lru_cache(maxsize=2048)
def _support_text(text: str) -> str:
    """Normalize formatting, not meaning: keep word order, negation and units."""
    text = unicodedata.normalize("NFKC", text)
    if "−" in text:
        text = text.replace("−", "-")
    if _HAS_DIGIT.search(text):
        text = _NUMBER_PATTERN.sub(
            lambda match: " " + next(iter(_numbers(match[0])), match[0]) + " ", text
        )
    text = text.translate(_QUOTE_STRIP_MAP)
    return " ".join(text.split()).strip(" .!?;:—–•|>")


def _doc_support_sentences(doc: Document) -> set[str]:
    sentences: set[str] = set()
    if doc.metadata.get("evidence_scope") != "metadata_only":
        for sentence in _SENTENCE_SPLIT_RE.split(doc.page_content):
            if sentence.strip():
                sentences.add(_support_text(sentence))
    else:
        sentences.add(_support_text("The supplied record does not establish methods, results or limitations."))
    if year := doc.metadata.get("year"):
        sentences.add(_support_text(f"Published in {year}"))
    return sentences


def _supported_claims(
    prose: str,
    refs: list[str],
    documents: list[Document],
    doc_sentences: dict[int, set[str]] | None = None,
) -> bool:
    """Only source sentences establish facts; a citation is not entailment.

    Free-form paraphrase cannot be proven safe with lexical overlap. Require
    complete source sentences (format/number normalization only). Explicitly
    labeled proposals/background have a separate, non-factual contract.
    """
    text = _CLAIM_NUM_PREFIX.sub("", prose)
    title = _TITLE_DASH_RE.match(text)
    if title:
        text = text[title.end():]
        target_title = _support_text(title[1])
    else:
        target_title = ""
    # Accept citations immediately after punctuation as well as before it.
    text = _TRAILING_REF_RE.sub(r" \2\1", text)
    pieces = [piece for piece in _SENTENCE_SPLIT_RE.split(text) if piece.strip(" |")]
    allowed_refs = set(refs)
    cache = doc_sentences if doc_sentences is not None else {}
    num_docs = len(documents)
    for piece in pieces:
        own_refs = _REF_PATTERN.findall(piece)
        if not own_refs or set(own_refs) - allowed_refs:
            return False
        selected_indices = [
            idx
            for ref in dict.fromkeys(own_refs)
            if 0 <= (idx := int(ref[1:]) - 1) < num_docs
        ]
        if title:
            selected_indices = [
                idx
                for idx in selected_indices
                if target_title == _support_text(
                    str(documents[idx].metadata.get("paper_title") or documents[idx].metadata.get("source_file") or "")
                )
            ]
        if not selected_indices:
            return False
        if len(selected_indices) == 1:
            idx = selected_indices[0]
            source_sentences = cache.get(idx)
            if source_sentences is None:
                source_sentences = _doc_support_sentences(documents[idx])
                cache[idx] = source_sentences
        else:
            source_sentences = set()
            for idx in selected_indices:
                cached = cache.get(idx)
                if cached is None:
                    cached = _doc_support_sentences(documents[idx])
                    cache[idx] = cached
                source_sentences.update(cached)
        if "|" in piece:
            claims = [norm for cell in _REF_PATTERN.sub("", piece).split("|") if (norm := _support_text(cell))]
        else:
            norm = _support_text(_REF_PATTERN.sub("", piece))
            claims = [norm] if norm else []
        if not claims or any(claim not in source_sentences for claim in claims):
            return False
    return bool(pieces)


def _ground_answer_impl(
    answer: str,
    citations: dict[str, str],
    documents: list[Document] | None,
    *,
    allow_background: bool,
    preserve_valid_blocks: bool,
    allow_proposals: bool,
    allow_general_guidance: bool,
    rejected_passages: list[dict[str, str]] | None,
    evidence_nums: dict[str, set[str]],
    doc_sentences: dict[int, set[str]],
) -> str:
    answer = _normalize_citations(answer)
    if "](" in answer:
        answer = _MD_LINK_STRIP.sub(r"[\1]", answer)
    if "http" in answer:
        answer = _UNVERIFIED_URL_STRIP.sub("[unverified URL removed]", answer)
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
    doc_list = documents or []
    num_docs = len(doc_list)
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
        if heading and name not in _STRUCTURAL_HEADINGS:
            # Arbitrary factual text cannot hide in a Markdown heading.
            prose = block.strip()
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
                        idx = int(ref[1:]) - 1
                        if 0 <= idx < num_docs:
                            doc = doc_list[idx]
                            doc_title = doc.metadata.get("paper_title") or doc.metadata.get("source_file") or ""
                            nums = _numbers(f"{doc.page_content} {doc_title} {doc.metadata.get('year', '')}")
                        else:
                            nums = set()
                        evidence_nums[ref] = nums
                    source_nums.update(nums)
                if claim_nums - source_nums:
                    reason = "a numerical claim is absent from its cited evidence"
            proposed = allow_proposals and _PROPOSAL_PATTERN.match(prose)
            abstention = _ABSTENTION_PATTERN.fullmatch(_REF_PATTERN.sub("", prose).strip())
            if not reason and not proposed and not abstention and not (allow_background and background):
                if not _supported_claims(prose, refs, documents, doc_sentences):
                    reason = "a factual claim is not an extract from its cited evidence"
        if not reason:
            kept.append(block)
            continue
        if rejected_passages is not None and len(rejected_passages) < 5:
            rejected_passages.append({
                "rejected_paragraph": _REF_PATTERN.sub("", prose[:1000]),
                "reason": reason,
                "instruction": "Rewrite only from the current supplied evidence. Use its current citation IDs; omit unsupported details rather than guessing.",
            })
        if not preserve_valid_blocks:
            prefix = (
                "I cannot provide a grounded answer"
                if "did not cite" in reason
                else "I cannot verify this response"
            )
            return f"{prefix}: {reason}."
        else:
            if heading:
                kept.append(heading[0] + "\n\n")
            if not prose.startswith("|"):
                # Split only at explicit sentence-ending citations. Do not infer
                # a source for uncited sentences or borrow a neighbor's citation.
                pieces = _PIECE_REF_SPLIT_RE.split(prose)
                if len(pieces) > 1 and all(_REF_PATTERN.search(piece) for piece in pieces):
                    retained = []
                    for piece in pieces:
                        checked = _ground_answer_impl(
                            piece,
                            citations,
                            documents,
                            allow_background=False,
                            preserve_valid_blocks=False,
                            allow_proposals=False,
                            allow_general_guidance=False,
                            rejected_passages=None,
                            evidence_nums=evidence_nums,
                            doc_sentences=doc_sentences,
                        )
                        if not checked.startswith(("I cannot verify this response:", "I cannot provide a grounded answer:")):
                            retained.append(piece)
                    if retained:
                        kept.append(" ".join(retained) + "\n\n")
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


def ground_answer(
    answer: str,
    citations: dict[str, str],
    documents: list[Document] | None = None,
    *,
    allow_background: bool = False,
    preserve_valid_blocks: bool = False,
    allow_proposals: bool = False,
    allow_general_guidance: bool = False,
    rejected_passages: list[dict[str, str]] | None = None,
) -> str:
    return _ground_answer_impl(
        answer,
        citations,
        documents,
        allow_background=allow_background,
        preserve_valid_blocks=preserve_valid_blocks,
        allow_proposals=allow_proposals,
        allow_general_guidance=allow_general_guidance,
        rejected_passages=rejected_passages,
        evidence_nums={},
        doc_sentences={},
    )
