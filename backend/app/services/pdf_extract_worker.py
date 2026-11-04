"""Small isolated parser. Only bounded text and page numbers leave this process."""

import json
import sys

from pypdf import PdfReader


def extract(path: str, max_pages: int, max_chars: int) -> dict:
    reader = PdfReader(path)
    total = len(reader.pages)
    if total > max_pages:
        raise ValueError("PDF exceeds the page limit")
    pages = []
    chars = 0
    for number, page in enumerate(reader.pages):
        contents = page.get_contents()
        if contents is not None and len(contents.get_data()) > 10_000_000:
            raise ValueError("PDF page exceeds the content processing limit")
        text = page.extract_text(extraction_mode="layout") or ""
        chars += len(text)
        if chars > max_chars:
            raise ValueError("PDF exceeds the extracted text limit")
        if text.strip():
            pages.append({"page": number, "text": text.strip()})
    if not pages:
        raise ValueError(
            "No selectable text was found. Use an OCR-processed PDF for scanned documents."
        )
    return {"pages": pages, "total_pages": total, "complete": len(pages) == total}


if __name__ == "__main__":
    try:
        if sys.platform != "win32":
            import resource

            memory = int(sys.argv[4]) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
            resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        result = extract(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
    except Exception as exc:
        result = {"error": str(exc) if isinstance(exc, ValueError) else "PDF could not be parsed"}
    print(json.dumps(result, ensure_ascii=True))
