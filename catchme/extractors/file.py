"""Lightweight file content extraction for code, PDF, and text files."""

from __future__ import annotations

from pathlib import Path

_CODE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".lua",
    ".sh",
    ".bash",
    ".zsh",
    ".r",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".vue",
    ".svelte",
    ".md",
    ".rst",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".xml",
}

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def read_file_content(filepath: str, max_chars: int = 8000) -> tuple[str, str]:
    """Extract text content from a file. Returns (content, file_type)."""
    p = Path(filepath)
    if not p.is_file():
        return "", "unknown"

    ext = p.suffix.lower()

    if ext in _CODE_EXTS:
        return _read_text(p, max_chars), "code"

    if ext == ".pdf":
        return _read_pdf(p, max_chars), "pdf"

    if ext in _IMAGE_EXTS:
        return "", "image"

    return _read_text(p, max_chars), "text"


def _read_text(path: Path, max_chars: int) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception:
        return ""


def extract_pdf_text(path: str, max_chars: int, max_pages: int = 20) -> str:
    """Extract text from a PDF file using pymupdf."""
    try:
        import pymupdf

        doc = pymupdf.open(path)
        try:
            pages = []
            total = 0
            for page in doc[:max_pages]:
                text = page.get_text()
                pages.append(text)
                total += len(text)
                if total >= max_chars:
                    break
            return "\n".join(pages)[:max_chars]
        finally:
            doc.close()
    except ImportError:
        return ""
    except Exception:
        return ""


def _read_pdf(path: Path, max_chars: int) -> str:
    text = extract_pdf_text(str(path), max_chars, max_pages=20)
    if not text:
        return _read_text(path, max_chars)
    return text
