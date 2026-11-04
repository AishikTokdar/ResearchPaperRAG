"""Use the retained MiniLM tokenizer to avoid silent embedding truncation."""

import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

LOCAL_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def embedding_tokenizer():
    return AutoTokenizer.from_pretrained(LOCAL_EMBEDDING_MODEL, trust_remote_code=False)


def document_splitter(chunk_size: int = 224, overlap: int = 32):
    tokenizer = embedding_tokenizer()
    return RecursiveCharacterTextSplitter(
        chunk_size=min(254, chunk_size),
        chunk_overlap=min(overlap, chunk_size - 1),
        length_function=lambda text: len(
            tokenizer.encode(text, add_special_tokens=False, verbose=False)
        ),
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
    )


def split_documents(
    documents: list[Document], chunk_size: int = 224, overlap: int = 32
) -> list[Document]:
    sections = []
    heading = re.compile(
        r"(?m)^(?:#{1,3}\s+.+|(?:\d+(?:\.\d+)*\.?\s+)?(?:Abstract|Introduction|Methods?|Materials and Methods|Results|Discussion|Conclusions?|Limitations|References))\s*$",
        re.I,
    )
    for doc in documents:
        matches = list(heading.finditer(doc.page_content))
        boundaries = sorted({0, *(match.start() for match in matches), len(doc.page_content)})
        for start, end in zip(boundaries, boundaries[1:], strict=False):
            text = doc.page_content[start:end].strip()
            if text:
                meta = dict(doc.metadata)
                if heading.match(text.splitlines()[0]):
                    meta["section"] = text.splitlines()[0]
                sections.append(Document(page_content=text, metadata=meta))
    return document_splitter(chunk_size, overlap).split_documents(sections) if sections else []
