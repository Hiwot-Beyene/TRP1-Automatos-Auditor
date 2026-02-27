"""PDF ingestion and RAG-lite query for DocAnalyst."""

import os
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
    result: dict[str, Any] = {
        "matched_chunks": matches,
        "sentences_with_terms": sentences_with_terms,
        "term_count": len(set(t for m in matches for t in m.get("matched_terms", []))),
        "in_detailed_explanation": len(sentences_with_terms) > 0 and any(len(s) > 80 for s in sentences_with_terms),
    }
    if os.environ.get("GOOGLE_API_KEY"):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
            context = "\n\n".join(c.get("text", "")[:500] for c in chunks[:10])
            prompt = f"""Given this PDF excerpt, assess theoretical depth (e.g. use of Fan-In/Fan-Out, State Synchronization, Metacognition). Reply in 1-2 sentences. Excerpt:\n\n{context}"""
            response = llm.invoke(prompt)
            if hasattr(response, "content") and response.content:
                result["llm_rationale"] = response.content.strip()
        except Exception:
            result["llm_rationale"] = None
    else:
        result["llm_rationale"] = None
    return result


def extract_file_paths_from_text(text: str) -> list[str]:
    """Extract file-path-like strings (e.g. src/state.py) from text for cross-reference."""
    import re
    seen: set[str] = set()
    out: list[str] = []
    for m in re.finditer(r"(?:^|[\s`'\"])((?:src|tests|scripts)/[a-zA-Z0-9_/.-]+\.(?:py|json|md|toml)|[a-zA-Z0-9_/.-]+\.(?:py|json|md|toml))(?:[\s`'\"]|$)", text):
        p = m.group(1).strip("`'\"")
        if p not in seen and len(p) > 2:
            seen.add(p)
            out.append(p)
    return out


def extract_images_from_pdf(pdf_path: str) -> list[dict[str, Any]]:
    """Extract images from PDF. Returns list of {page: int, data: bytes, name: str}. Empty if none or on error."""
    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        return []
    result: list[dict[str, Any]] = []
    try:
        reader = PdfReader(str(path))
        for i, page in enumerate(reader.pages):
            images = getattr(page, "images", None)
            if images is None:
                continue
            items = list(images.values()) if isinstance(images, dict) else list(images) if hasattr(images, "__iter__") else []
            for j, img in enumerate(items):
                try:
                    data = getattr(img, "get_data", lambda: None)()
                    if data is None and hasattr(img, "get_object"):
                        obj = img.get_object()
                        if hasattr(obj, "get_data"):
                            data = obj.get_data()
                    if data:
                        result.append({"page": i + 1, "data": data, "name": f"page{i+1}_img{j}"})
                except Exception:
                    continue
    except Exception:
        pass
    return result
