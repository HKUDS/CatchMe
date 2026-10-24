"""Extract readable text from a URL — handles HTML pages and online PDFs.

Downloaded PDFs and extracted text are persisted to workspace_dir for reuse.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

log = logging.getLogger(__name__)

_SKIP_SCHEMES = {"chrome", "chrome-extension", "about", "file", "data", "blob"}
_SKIP_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
_TIMEOUT = 15
_MAX_CHARS = 8000

_PDF_KNOWN_HOSTS = {
    "openreview.net": re.compile(r"/pdf\b"),
    "arxiv.org": re.compile(r"/pdf/"),
}

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _url_key(url: str) -> str:
    """Short, filesystem-safe key derived from the URL."""
    h = hashlib.sha256(url.encode()).hexdigest()[:12]
    parsed = urlparse(url)
    host = (parsed.hostname or "unknown").replace(".", "_")
    slug = re.sub(r"[^a-zA-Z0-9]", "_", parsed.path.strip("/"))[:40]
    return f"{host}__{slug}__{h}"


def fetch_url_content(
    url: str,
    max_chars: int = _MAX_CHARS,
    workspace_dir: Path | str | None = None,
) -> str:
    """Fetch and extract readable text from a URL.

    If workspace_dir is provided, downloaded files and extracted text
    are cached there for reuse.
    """
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.scheme in _SKIP_SCHEMES:
        return ""
    if parsed.hostname in _SKIP_HOSTS:
        return ""

    ws = Path(workspace_dir) if workspace_dir else None

    if ws:
        cached = _read_text_cache(ws, url)
        if cached:
            return cached[:max_chars]

    if _is_pdf_url(url, parsed):
        text = _fetch_pdf(url, max_chars, ws)
        if text:
            if ws:
                _write_text_cache(ws, url, text)
            return text

    text = _fetch_html(url, max_chars)
    if text and ws:
        _write_text_cache(ws, url, text)
    return text


# ── Cache ──


def _read_text_cache(ws: Path, url: str) -> str | None:
    p = ws / "html" / f"{_url_key(url)}.txt"
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass
    return None


def _write_text_cache(ws: Path, url: str, text: str) -> None:
    try:
        p = ws / "html" / f"{_url_key(url)}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", errors="ignore")
    except Exception:
        pass


# ── Detection ──


def _is_pdf_url(url: str, parsed=None) -> bool:
    if ".pdf" in url.lower().split("?")[0].split("#")[0]:
        return True
    parsed = parsed or urlparse(url)
    host = (parsed.hostname or "").lower()
    for domain, pattern in _PDF_KNOWN_HOSTS.items():
        if host.endswith(domain) and pattern.search(parsed.path):
            return True
    return False


# ── HTML ──


def _fetch_html(url: str, max_chars: int) -> str:
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        return (text or "")[:max_chars]
    except ImportError:
        log.warning("trafilatura not installed, falling back to requests")
        return _fetch_html_fallback(url, max_chars)
    except Exception:
        log.debug("trafilatura extraction failed for %s", url[:80])
        return ""


def _fetch_html_fallback(url: str, max_chars: int) -> str:
    try:
        import requests

        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


# ── PDF ──


def _fetch_pdf(url: str, max_chars: int, ws: Path | None = None) -> str:
    """Download PDF and extract text. Saves PDF to workspace if provided."""
    try:
        import requests

        pdf_path = None
        if ws:
            pdf_path = ws / "pdf" / f"{_url_key(url)}.pdf"
            if pdf_path.is_file() and pdf_path.stat().st_size > 1000:
                return _extract_pdf_text(str(pdf_path), max_chars)

        session = requests.Session()
        session.headers.update(_BROWSER_HEADERS)
        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.hostname}/"
        session.headers["Referer"] = referer
        session.get(referer, timeout=_TIMEOUT)

        resp = session.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()

        ct = resp.headers.get("content-type", "").lower()
        if "pdf" not in ct and len(resp.content) < 1000:
            return ""

        if pdf_path:
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(resp.content)
            save_path = str(pdf_path)
        else:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(resp.content)
                save_path = f.name

        text = _extract_pdf_text(save_path, max_chars)

        if not pdf_path:
            Path(save_path).unlink(missing_ok=True)

        return text
    except Exception:
        log.debug("PDF download/extract failed for %s", url[:80])
        return ""


def _extract_pdf_text(path: str, max_chars: int) -> str:
    from .file import extract_pdf_text

    return extract_pdf_text(path, max_chars, max_pages=20)
