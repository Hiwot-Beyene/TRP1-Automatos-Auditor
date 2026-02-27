"""PDF ingestion and RAG-lite query for DocAnalyst."""

import io
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from pypdf import PdfReader


class DocIngestError(Exception):
    """Raised when PDF is missing or unreadable."""


PDF_MAGIC = b"%PDF"

# Google Drive view URL -> direct download (export=download returns PDF bytes when possible)
_DRIVE_FILE_ID_RE = re.compile(
    r"(?:drive\.google\.com/file/d/|/open\?id=)([a-zA-Z0-9_-]+)|drive\.google\.com/uc\?export=download&id=([a-zA-Z0-9_-]+)"
)


def _google_drive_download_url(pdf_path: str) -> str | None:
    """If pdf_path is a Google Drive view/open URL, return direct download URL."""
    s = (pdf_path or "").strip()
    if "drive.google.com" not in s:
        return None
    m = _DRIVE_FILE_ID_RE.search(s)
    if not m:
        return None
    file_id = m.group(1) or m.group(2)
    if not file_id:
        return None
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def _is_pdf_bytes(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == PDF_MAGIC


def pdf_to_binary(pdf_path: str) -> bytes:
    """Resolve PDF to binary once: download URL (with Drive handling) or read local file. Use same bytes for ingest and image extraction."""
    s = (pdf_path or "").strip()
    if s.startswith("http://") or s.startswith("https://"):
        url = s
        drive_url = _google_drive_download_url(s)
        if drive_url:
            url = drive_url
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AutomatonAuditor/1.0)"})
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        if not _is_pdf_bytes(data):
            if b"confirm=" in data or b"virus scan" in data.lower():
                confirm = re.search(rb"confirm=([0-9A-Za-z_-]+)", data)
                if confirm:
                    url2 = url + "&confirm=" + confirm.group(1).decode("utf-8", errors="replace")
                    req2 = Request(url2, headers={"User-Agent": "Mozilla/5.0 (compatible; AutomatonAuditor/1.0)"})
                    with urlopen(req2, timeout=60) as r2:
                        data = r2.read()
            if not _is_pdf_bytes(data):
                raise DocIngestError(
                    "URL did not return a PDF (response may be HTML or an error page). "
                    "For Google Drive, use a share link that allows 'Anyone with the link' to view."
                )
        return data
    path = Path(s)
    if not path.exists() or not path.is_file():
        raise DocIngestError(f"PDF not found: {pdf_path!r}")
    with path.open("rb") as f:
        data = f.read()
    if not _is_pdf_bytes(data):
        raise DocIngestError(f"File is not a valid PDF (wrong magic bytes): {pdf_path!r}")
    return data


def _resolve_pdf_path(pdf_path: str) -> Path:
    """Path to local PDF file; for URLs uses pdf_to_binary then temp file."""
    s = (pdf_path or "").strip()
    if s.startswith("http://") or s.startswith("https://"):
        data = pdf_to_binary(pdf_path)
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.write(data)
        tmp.close()
        return Path(tmp.name)
    return Path(s)


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


def ingest_pdf(
    pdf_path: str | None = None,
    pdf_bytes: bytes | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Parse PDF and return chunked text. Prefer pdf_bytes (binary) when provided so one load is reused."""
    if pdf_bytes is not None and _is_pdf_bytes(pdf_bytes):
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)
    else:
        if not pdf_path:
            raise DocIngestError("Either pdf_path or pdf_bytes required")
        path = _resolve_pdf_path(pdf_path)
        if not path.exists() or not path.is_file():
            raise DocIngestError(f"PDF not found: {pdf_path}")
        try:
            with path.open("rb") as f:
                if not _is_pdf_bytes(f.read(4)):
                    raise DocIngestError(f"Not a valid PDF: {pdf_path}")
        except DocIngestError:
            raise
        except OSError as e:
            raise DocIngestError(f"Cannot read file: {e}") from e
        try:
            reader = PdfReader(str(path))
        except Exception as e:
            raise DocIngestError(f"Cannot parse PDF: {e}") from e

    chunks: list[dict[str, Any]] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            page_chunks = _chunk_text(text, chunk_size, overlap)
            for j, block in enumerate(page_chunks):
                chunks.append({"text": block, "page": i + 1, "chunk_index": j})

    if not chunks and len(reader.pages) > 0:
        chunks.append({
            "text": f"PDF has {len(reader.pages)} page(s). No extractable text (content may be image-based or scanned).",
            "page": 1,
            "chunk_index": 0,
        })
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


def _terms_from_forensic_instruction(instruction: str) -> list[str]:
    """Extract quoted search terms from rubric; expand 'Fan-In / Fan-Out' into variants for flexible match."""
    if not instruction:
        return []
    out: list[str] = []
    for m in re.finditer(r"""['"]([^'"]+)['"]""", instruction):
        t = m.group(1).strip()
        if not t or t in out:
            continue
        out.append(t)
        if "Fan-In" in t and "Fan-Out" in t:
            if "Fan-In" not in out:
                out.append("Fan-In")
            if "Fan-Out" not in out:
                out.append("Fan-Out")
            out.append("Fan-In/Fan-Out")
    return out if out else list(THEORETICAL_DEPTH_TERMS)


def query_chunks(chunks: list[dict[str, Any]], terms: tuple[str, ...] | list[str] | None = None) -> list[dict[str, Any]]:
    """Search chunks for terms; case-insensitive and flexible (e.g. Fan-In / Fan-Out vs Fan-In/Fan-Out)."""
    if terms is None:
        terms = THEORETICAL_DEPTH_TERMS
    terms = list(terms)
    matches: list[dict[str, Any]] = []
    for c in chunks:
        text = c.get("text") or ""
        text_lower = text.lower()
        found_terms = [t for t in terms if t in text or (len(t) > 2 and t.lower() in text_lower)]
        if not found_terms:
            continue
        matches.append({
            **c,
            "matched_terms": found_terms,
            "excerpt": text[:500] + ("..." if len(text) > 500 else ""),
        })
    return matches


def search_theoretical_depth(
    chunks: list[dict[str, Any]],
    terms: tuple[str, ...] | list[str] | None = None,
    success_pattern: str = "",
    failure_pattern: str = "",
) -> dict[str, Any]:
    """RAG-lite search for theoretical_depth: terms from rubric (or default). Optional success/failure for LLM."""
    search_terms = tuple(terms) if terms else THEORETICAL_DEPTH_TERMS
    matches = query_chunks(chunks, search_terms)
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
            model = os.environ.get("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash")
            llm = ChatGoogleGenerativeAI(model=model)
            context = "\n\n".join((c.get("text", "") or "")[:400] for c in chunks[:8])
            prompt = f"""Given this PDF excerpt, assess theoretical depth (terms: {', '.join(search_terms[:6])}). Reply in 1-2 sentences."""
            if success_pattern:
                prompt += f" Success looks like: {success_pattern[:150]}."
            if failure_pattern:
                prompt += f" Avoid: {failure_pattern[:150]}."
            prompt += f"\n\nExcerpt:\n\n{context}"""
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


def extract_images_from_pdf(pdf_path: str | None = None, pdf_bytes: bytes | None = None) -> list[dict[str, Any]]:
    """Extract images using only PyMuPDF (fitz): fitz.open, page.get_images(), doc.extract_image(xref)."""
    source: Path | bytes
    if pdf_bytes is not None and _is_pdf_bytes(pdf_bytes):
        source = pdf_bytes
    elif pdf_path:
        try:
            path = _resolve_pdf_path(pdf_path)
            if not path.exists() or not path.is_file():
                return []
            with path.open("rb") as f:
                if not _is_pdf_bytes(f.read(4)):
                    return []
            source = path
        except (DocIngestError, OSError):
            return []
    else:
        return []

    result: list[dict[str, Any]] = []
    try:
        result = _extract_images_fitz(source)
    except Exception:
        pass
    if not result:
        try:
            result = _render_pages_as_images_fitz(source)
        except Exception:
            pass
    _filter_and_limit_images(result)
    return result


def _extract_images_fitz(source: Path | bytes) -> list[dict[str, Any]]:
    """Image extraction via PyMuPDF only: fitz.open, page.get_images(), doc.extract_image(xref)."""
    import fitz
    out: list[dict[str, Any]] = []
    seen_xrefs: set[int] = set()
    min_side = 60
    if isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        doc = fitz.open(str(source))
    try:
        for page in doc:
            page_num = page.number + 1
            for item in page.get_images():
                xref = item[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                try:
                    info = doc.extract_image(xref)
                    if not info:
                        continue
                    data = info.get("image")
                    w = info.get("width") or 0
                    h = info.get("height") or 0
                    if not data or len(data) < 100:
                        continue
                    if w < min_side and h < min_side:
                        continue
                    ext = (info.get("ext") or "png").lower()
                    if ext == "jpeg":
                        ext = "jpg"
                    out.append({
                        "page": page_num,
                        "data": bytes(data),
                        "name": f"page{page_num}_xref{xref}.{ext}",
                        "ext": ext,
                    })
                except Exception:
                    continue
    finally:
        doc.close()
    return out


def _render_pages_as_images_fitz(source: Path | bytes) -> list[dict[str, Any]]:
    """When no embedded images: render each page as PNG using fitz (PyMuPDF) only."""
    import fitz
    out: list[dict[str, Any]] = []
    if isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        doc = fitz.open(str(source))
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=150, alpha=False)
            data = pix.tobytes("png")
            if data and len(data) >= 100:
                out.append({"page": page.number + 1, "data": data, "name": f"page{page.number + 1}_rendered.png", "ext": "png"})
    finally:
        doc.close()
    return out


def _filter_and_limit_images(images: list[dict[str, Any]]) -> None:
    """In-place: cap size/count for vision API; resize huge with Pillow."""
    max_pixels = 2048 * 2048
    max_count = 10
    max_bytes = 4 * 1024 * 1024
    for img in images:
        data = img.get("data") or b""
        if len(data) > max_bytes:
            try:
                from PIL import Image
                buf = io.BytesIO(data)
                pil = Image.open(buf).convert("RGB")
                w, h = pil.size
                if w * h > max_pixels:
                    ratio = (max_pixels / (w * h)) ** 0.5
                    pil = pil.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                pil.save(out, format="PNG")
                img["data"] = out.getvalue()
            except Exception:
                pass
    while len(images) > max_count:
        images.pop()
