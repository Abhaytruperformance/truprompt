"""Extracts plain text from an uploaded file or a URL, for use as extra
generation context (see app/services/openai_service.py's `extra_context` param).
Extraction is a separate step from generation on purpose -- see the "Two
separate extraction endpoints" scope decision in the feature's plan.
"""

import ipaddress
import random
import socket
import threading
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader
from io import BytesIO

from app.core.config import settings

_ALLOWED_URL_SCHEMES = {"http", "https"}
_ALLOWED_URL_CONTENT_TYPES = ("text/html", "text/plain")
# Below this text-to-file-size ratio for a non-trivial file, extraction
# probably hit a scanned/image-only document -- not real OCR detection, just
# a heuristic so the user gets a useful note instead of silence.
_SUSPICIOUSLY_LOW_TEXT_THRESHOLD = 40


class UnsupportedFileType(Exception):
    pass


class ExtractionFailed(Exception):
    pass


class UnsafeUrl(Exception):
    pass


class UnsupportedContentType(Exception):
    pass


class ResponseTooLarge(Exception):
    pass


class FetchError(Exception):
    pass


def _finalize(text: str, source_bytes_len: int) -> dict:
    text = text.strip()
    truncated = len(text) > settings.MAX_CONTEXT_CHARS
    if truncated:
        text = text[: settings.MAX_CONTEXT_CHARS]

    warning = None
    if source_bytes_len > 10_000 and len(text) < _SUSPICIOUSLY_LOW_TEXT_THRESHOLD:
        warning = (
            "Very little text was extracted -- this file may contain scanned "
            "images rather than real text (OCR isn't supported)."
        )

    return {"text": text, "characters": len(text), "truncated": truncated, "warning": warning}


def extract_from_file(filename: str, content: bytes) -> dict:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    try:
        if ext in ("txt", "md"):
            text = content.decode("utf-8", errors="replace")
        elif ext == "pdf":
            reader = PdfReader(BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == "docx":
            doc = Document(BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            raise UnsupportedFileType(f"'.{ext}' files aren't supported (use .txt, .md, .pdf, or .docx)")
    except UnsupportedFileType:
        raise
    except Exception as exc:
        # Malformed/corrupt file -- a parser-library exception, not a bug in
        # this service. Never let this surface as a raw 500/traceback.
        raise ExtractionFailed("Unable to extract content from this document") from exc

    return _finalize(text, len(content))


def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _assert_safe_host(hostname: str) -> None:
    try:
        addrs = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrl(f"Could not resolve host '{hostname}'") from exc

    for family, _, _, _, sockaddr in addrs:
        if _is_unsafe_ip(ipaddress.ip_address(sockaddr[0])):
            raise UnsafeUrl(f"'{hostname}' resolves to a non-public address and can't be fetched")


def _assert_safe_peer(response: httpx.Response, hostname: str) -> None:
    """Re-validates the ACTUAL connected IP, not just the earlier, separate
    DNS lookup in _assert_safe_host -- closes the DNS-rebinding/TOCTOU window
    where a hostname resolves to a safe IP during that check but a different,
    unsafe IP by the time httpx itself resolves and connects moments later.
    Runs before any response body is read, so an unsafe peer never gets its
    response processed even though one TCP connection to it already happened
    (a residual, unavoidable minor signal -- but no data is read back)."""
    network_stream = response.extensions.get("network_stream")
    server_addr = network_stream.get_extra_info("server_addr") if network_stream else None
    if not server_addr:
        raise UnsafeUrl("Could not verify the connection address")
    if _is_unsafe_ip(ipaddress.ip_address(server_addr[0])):
        raise UnsafeUrl(f"'{hostname}' connected to a non-public address and can't be fetched")


# ponytail: in-process cache, not process-safe (resets on restart, not shared
# across workers if this ever runs as more than one uvicorn process) -- same
# tradeoff already accepted for the rate limiter in app/auth/api_key.py. Move
# to Redis if this ever runs multi-process.
_url_cache: dict[str, tuple[float, dict]] = {}
_url_cache_lock = threading.Lock()


def _cache_get(url: str) -> dict | None:
    now = time.monotonic()
    with _url_cache_lock:
        if random.randint(1, 200) == 1:
            expired = [
                k for k, (cached_at, _) in _url_cache.items()
                if now - cached_at >= settings.URL_CACHE_TTL_SECONDS
            ]
            for k in expired:
                del _url_cache[k]

        entry = _url_cache.get(url)
        if entry and now - entry[0] < settings.URL_CACHE_TTL_SECONDS:
            return entry[1]
    return None


def _cache_set(url: str, result: dict) -> None:
    with _url_cache_lock:
        _url_cache[url] = (time.monotonic(), result)


def extract_from_url(url: str) -> dict:
    cached = _cache_get(url)
    if cached is not None:
        return {**cached, "cached": True}

    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_URL_SCHEMES:
        raise UnsafeUrl(f"Only http/https URLs are supported, got '{parsed.scheme}'")
    if not parsed.hostname:
        raise UnsafeUrl("URL has no host")

    _assert_safe_host(parsed.hostname)

    try:
        # follow_redirects=False -- a redirect to an internal address after
        # the host check above passed must fail loudly, not be silently
        # followed (that check only covers the URL the caller gave us).
        with httpx.stream(
            "GET", url, timeout=settings.URL_FETCH_TIMEOUT_SECONDS, follow_redirects=False
        ) as response:
            _assert_safe_peer(response, parsed.hostname)

            if response.is_redirect:
                raise FetchError("This URL redirects, which isn't followed for safety reasons")
            if response.status_code >= 400:
                raise FetchError(f"The URL returned HTTP {response.status_code}")

            content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type not in _ALLOWED_URL_CONTENT_TYPES:
                raise UnsupportedContentType(f"Only HTML/plain-text pages are supported, got '{content_type}'")

            chunks = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > settings.MAX_URL_RESPONSE_BYTES:
                    raise ResponseTooLarge(
                        f"Response exceeds the {settings.MAX_URL_RESPONSE_BYTES // (1024 * 1024)}MB limit"
                    )
                chunks.append(chunk)
            body = b"".join(chunks)
    except httpx.TimeoutException as exc:
        raise FetchError("The URL took too long to respond") from exc
    except httpx.HTTPError as exc:
        raise FetchError("Could not fetch this URL") from exc

    if content_type == "text/html":
        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    else:
        text = body.decode("utf-8", errors="replace")

    result = _finalize(text, len(body))
    _cache_set(url, result)
    return {**result, "cached": False}
