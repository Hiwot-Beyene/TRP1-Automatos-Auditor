"""PDF ingestion and RAG-lite query for DocAnalyst."""

from pathlib import Path
from typing import Any

from pypdf import PdfReader


class DocIngestError(Exception):
    """Raised when PDF is missing or unreadable."""


DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100

THEORETICAL_DEPTH_TERMS = (
    "Dialectical Synthesis",
    "Fan-In / Fan-Out",
    "Fan-In",
    "Fan-Out",
    "Metacognition",
    "State Synchronization",
)


def ingest_pdf(pdf_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[dict[str, Any]]:
    """Parse PDF and return chunked representation for RAG-lite. Raises DocIngestError if missing/unreadable."""
    path = Path(pdf_path)
    if not path.exists():
        raise DocIngestError(f"PDF not found: {pdf_path}")
    if not path.is_file():
        raise DocIngestError(f"Not a file: {pdf_path}")

    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise DocIngestError(f"Cannot read PDF: {e}") from e

    chunks: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            raise DocIngestError(f"Failed to extract page {i + 1}: {e}") from e
        if not text.strip():
            continue
        page_chunks = _chunk_text(text, chunk_size, overlap)
        for j, block in enumerate(page_chunks):
            chunks.append({"text": block, "page": i + 1, "chunk_index": j})

    if not chunks:
        raise DocIngestError("No text extracted from PDF")
    return chunks


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return _chunk_by_size(text, size, overlap)
    result: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) + 2 > size and current:
            result.append("\n\n".join(current))
            if overlap > 0 and current:
                keep = []
                keep_len = 0
                for s in reversed(current):
                    if keep_len + len(s) + 2 <= overlap:
                        keep.insert(0, s)
                        keep_len += len(s) + 2
                    else:
                        break
                current = keep
                current_len = keep_len
            else:
                current = []
                current_len = 0
        current.append(p)
        current_len += len(p) + 2
    if current:
        result.append("\n\n".join(current))
    return result


def _chunk_by_size(text: str, size: int, overlap: int) -> list[str]:
    if not text.strip():
        return []
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            break_at = text.rfind(" ", start, end)
            if break_at > start:
                end = break_at + 1
        result.append(text[start:end].strip())
        if not result[-1]:
            start = end
            continue
        start = end - overlap if overlap < end - start else end
    return [r for r in result if r]


def query_chunks(chunks: list[dict[str, Any]], terms: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Search chunks for terms (e.g. theoretical_depth keywords). Returns matching chunks with highlighted terms."""
    if terms is None:
        terms = THEORETICAL_DEPTH_TERMS
    matches: list[dict[str, Any]] = []
    for c in chunks:
        text = c.get("text") or ""
        found_terms = [t for t in terms if t in text]
        if not found_terms:
            continue
        matches.append({
            **c,
            "matched_terms": found_terms,
            "excerpt": text[:500] + ("..." if len(text) > 500 else ""),
        })
    return matches


def search_theoretical_depth(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """RAG-lite search for theoretical_depth dimension: terms in detailed explanation vs buzzword-only."""
    matches = query_chunks(chunks, THEORETICAL_DEPTH_TERMS)
    sentences_with_terms: list[str] = []
    for m in matches:
        text = m.get("text") or ""
        for term in m.get("matched_terms", []):
            start = text.find(term)
            if start == -1:
                continue
            begin = max(0, text.rfind(".", 0, start) + 1)
            end = text.find(".", start + len(term))
            if end == -1:
                end = len(text)
            else:
                end += 1
            sentence = text[begin:end].strip()
            if sentence and sentence not in sentences_with_terms:
                sentences_with_terms.append(sentence)
    return {
        "matched_chunks": matches,
        "sentences_with_terms": sentences_with_terms,
        "term_count": len(set(t for m in matches for t in m.get("matched_terms", []))),
        "in_detailed_explanation": len(sentences_with_terms) > 0 and any(len(s) > 80 for s in sentences_with_terms),
    }
