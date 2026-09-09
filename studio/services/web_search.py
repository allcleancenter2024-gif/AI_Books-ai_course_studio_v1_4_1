"""SearXNG-first web search with optional Firecrawl and safe local fallback."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import os
import re
import socket
import threading
import time
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from ..config import web_search_configuration

USER_AGENT = "AI-Course-Studio-Hybrid-RAG/1.23"
RETRYABLE_FIRECRAWL = {408, 429, 500, 502, 503, 504}
ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/xhtml+xml")
_SEARCH_CACHE: dict[str, tuple[float, list["SearchResult"]]] = {}
_CACHE_LOCK = threading.Lock()
_SEARCH_SLOT = threading.BoundedSemaphore(1)


def _search_cache_limit() -> int:
    return int(web_search_configuration()["cache_max_entries"])


@dataclass(frozen=True)
class SearchOptions:
    max_results: int = 8
    allowed_domains: tuple[str, ...] = ()
    freshness_days: int = 365
    high_quality: bool = False


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    published_at: str = ""


class WebSearchProvider:
    name = "disabled"

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        return []

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        return {"enabled": False, "provider": self.name, "status": "disabled"}


class WebContentExtractor:
    name = "disabled"

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def health_check(self) -> dict[str, Any]:
        return {"enabled": False, "extractor": self.name, "status": "disabled"}


class DisabledSearchProvider(WebSearchProvider):
    pass


class WebProviderError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _safe_query(query: str) -> str:
    value = " ".join(str(query or "").split())[:300]
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "", value)
    value = re.sub(r"(?i)(api[_ -]?key|token|password|secret)\s*[:=]\s*\S+", "", value)
    value = re.sub(r"(?i)(?:[A-Z]:\\|/home/|/users/)[^\s]+", "", value)
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("검색어가 비어 있거나 민감정보 제거 후 사용할 수 없습니다.")
    return value


def _safe_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("공개 HTTP/HTTPS URL만 허용됩니다.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    found = False
    for info in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM):
        found = True
        address = str(info[4][0]).split("%", 1)[0]
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("사설·로컬 네트워크 주소는 차단됩니다.")
    if not found:
        raise ValueError("URL 호스트 주소를 확인할 수 없습니다.")
    return value


def _robots_allowed(url: str, timeout: float) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        _safe_url(robots_url)
        response = httpx.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=min(timeout, 5.0), follow_redirects=False)
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def _clean_html(html: str, url: str) -> tuple[str, str]:
    extracted = ""
    try:
        import trafilatura
        extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=True, favor_precision=True, deduplicate=True) or ""
    except Exception:
        pass
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else urlparse(url).netloc
    if not extracted:
        for node in soup(["script", "style", "noscript", "nav", "footer", "aside", "form", "header"]):
            node.decompose()
        extracted = soup.get_text("\n", strip=True)
    lines: list[str] = []
    seen: set[str] = set()
    for line in extracted.splitlines():
        normalized = " ".join(line.split())
        key = normalized.casefold()
        if len(normalized) < 2 or key in seen:
            continue
        seen.add(key)
        lines.append(normalized)
    return title[:240], "\n".join(lines)


class LocalContentExtractor(WebContentExtractor):
    name = "local"

    def __init__(self, timeout: float = 15.0, max_bytes: int = 8 * 1024 * 1024, max_chars: int = 120_000):
        self.timeout, self.max_bytes, self.max_chars = timeout, max_bytes, max_chars

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        current = _safe_url(url)
        if os.getenv("LOCAL_WEB_EXTRACTOR_RESPECT_ROBOTS", "true").lower() != "false" and not _robots_allowed(current, self.timeout):
            raise WebProviderError("robots_blocked", "robots.txt 정책에 따라 본문을 가져오지 않았습니다.")
        timeout = httpx.Timeout(connect=min(self.timeout, 8), read=self.timeout, write=10, pool=5)
        with httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
            for _ in range(5):
                response = client.get(current)
                if response.status_code in (301, 302, 303, 307, 308) and response.headers.get("location"):
                    current = _safe_url(urljoin(current, response.headers["location"]))
                    continue
                response.raise_for_status()
                length = int(response.headers.get("content-length") or 0)
                if length > self.max_bytes or len(response.content) > self.max_bytes:
                    raise ValueError("웹 페이지가 허용 크기를 초과했습니다.")
                content_type = response.headers.get("content-type", "").lower()
                if not any(kind in content_type for kind in ALLOWED_CONTENT_TYPES):
                    raise ValueError(f"지원하지 않는 웹 콘텐츠 형식입니다: {content_type or 'unknown'}")
                break
            else:
                raise ValueError("리디렉션이 너무 많습니다.")
        title, text = _clean_html(response.text, current)
        return {"title": title, "url": current, "text": text[: self.max_chars], "publisher": urlparse(current).netloc, "retrieved_at": datetime.now(timezone.utc).isoformat(), "content_type": response.headers.get("content-type", "text/html"), "extractor": self.name}

    def health_check(self) -> dict[str, Any]:
        return {"enabled": True, "extractor": self.name, "status": "ready", "external_transfer": False}


class FirecrawlProvider(WebSearchProvider, WebContentExtractor):
    name = "firecrawl"

    def __init__(self, api_key: str = "", timeout: float = 30.0, max_retries: int = 1):
        self.api_key, self.timeout = api_key.strip(), timeout
        self.max_retries = max(0, min(max_retries, 2))
        self.base_url = "https://api.firecrawl.dev/v2"

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and os.getenv("FIRECRAWL_ENABLED", "false").lower() == "true"

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise WebProviderError("not_configured", "Firecrawl API 키가 없거나 사용하지 않도록 설정되어 있습니다.")
        if os.getenv("FIRECRAWL_MONTHLY_BUDGET_ENABLED", "true").lower() == "true":
            from ..db import connect
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            limit = max(1, int(os.getenv("FIRECRAWL_MONTHLY_REQUEST_LIMIT", "100")))
            with connect() as conn:
                row = conn.execute("SELECT request_count FROM web_api_usage WHERE month=? AND provider='firecrawl'", (month,)).fetchone()
                used = int(row["request_count"]) if row else 0
                if used >= limit:
                    raise WebProviderError("monthly_budget", "설정된 Firecrawl 월간 요청 상한에 도달했습니다.")
                conn.execute("""INSERT INTO web_api_usage(month,provider,request_count,updated_at) VALUES(?,'firecrawl',1,datetime('now'))
                    ON CONFLICT(month,provider) DO UPDATE SET request_count=request_count+1,updated_at=datetime('now')""", (month,))
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(self.max_retries + 1):
            response = httpx.post(f"{self.base_url}/{endpoint.lstrip('/')}", headers=headers, json=payload, timeout=self.timeout)
            if response.is_success:
                data = response.json()
                if not data.get("success", True):
                    raise WebProviderError("remote_error", "Firecrawl이 요청을 처리하지 못했습니다.")
                return data
            status = response.status_code
            if status not in RETRYABLE_FIRECRAWL or attempt >= self.max_retries:
                code = {401: "unauthorized", 402: "budget_exhausted", 408: "timeout", 429: "rate_limited"}.get(status, "server_error" if status >= 500 else "request_error")
                raise WebProviderError(code, f"Firecrawl 요청이 상태 코드 {status}로 실패했습니다.", retryable=status in RETRYABLE_FIRECRAWL)
            retry_after = response.headers.get("Retry-After", "")
            delay = min(float(retry_after), 5.0) if retry_after.replace(".", "", 1).isdigit() else min(2**attempt, 3)
            time.sleep(delay)
        raise WebProviderError("server_error", "Firecrawl 요청이 실패했습니다.")

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        limit = max(1, min(options.max_results, int(os.getenv("FIRECRAWL_MAX_RESULTS", "5")), 5))
        data = self._post("search", {"query": _safe_query(query), "limit": limit, "sources": ["web"], "ignoreInvalidURLs": True})
        rows = (data.get("data") or {}).get("web", [])
        return [SearchResult(str(row.get("title") or "")[:240], str(row.get("url") or ""), str(row.get("description") or "")[:500], str(row.get("date") or "")) for row in rows if row.get("url")]

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        current = _safe_url(url)
        data = self._post("scrape", {"url": current, "formats": ["markdown"], "onlyMainContent": True, "removeBase64Images": True, "blockAds": True, "timeout": min(int(self.timeout * 1000), 60_000)})
        page, metadata = data.get("data") or {}, (data.get("data") or {}).get("metadata") or {}
        text = str(page.get("markdown") or "")[:120_000]
        if not text.strip():
            raise WebProviderError("empty_content", "Firecrawl이 본문 없는 응답을 반환했습니다.")
        final_url = _safe_url(str(metadata.get("sourceURL") or metadata.get("url") or current))
        return {"title": str(metadata.get("title") or urlparse(final_url).netloc)[:240], "url": final_url, "text": text, "publisher": urlparse(final_url).netloc, "retrieved_at": datetime.now(timezone.utc).isoformat(), "content_type": "text/markdown", "extractor": self.name}

    def health_check(self) -> dict[str, Any]:
        status = "api_key_missing" if not self.api_key else "configured" if self.enabled else "disabled"
        return {"enabled": self.enabled, "provider": self.name, "extractor": self.name, "status": status, "external_transfer": self.enabled}


class SearXngProvider(WebSearchProvider):
    name = "searxng"

    def __init__(self, base_url: str = "http://127.0.0.1:8888", timeout: float = 15.0, extractor: WebContentExtractor | None = None):
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.extractor = extractor or LocalContentExtractor(timeout)

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        params: dict[str, Any] = {"q": _safe_query(query), "format": "json", "language": "ko-KR", "safesearch": 1}
        if 0 < options.freshness_days <= 31:
            params["time_range"] = "month"
        elif 0 < options.freshness_days <= 366:
            params["time_range"] = "year"
        response = httpx.get(f"{self.base_url}/search", params=params, headers={"Accept": "application/json", "User-Agent": USER_AGENT}, timeout=self.timeout)
        if response.status_code == 403:
            raise WebProviderError("json_disabled", "SearXNG JSON 검색 형식이 비활성화되어 있습니다.")
        response.raise_for_status()
        rows: list[SearchResult] = []
        seen: set[str] = set()
        for item in response.json().get("results", []):
            url = str(item.get("url") or "")
            try:
                _safe_url(url)
            except Exception:
                continue
            host = (urlparse(url).hostname or "").lower()
            if options.allowed_domains and not any(host == domain or host.endswith("." + domain) for domain in options.allowed_domains):
                continue
            normalized = url.rstrip("/")
            if normalized in seen:
                continue
            seen.add(normalized)
            rows.append(SearchResult(str(item.get("title") or host)[:240], url, str(item.get("content") or "")[:500], str(item.get("publishedDate") or item.get("published_date") or "")))
            if len(rows) >= options.max_results:
                break
        return rows

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.extractor.extract(url, options)

    def health_check(self) -> dict[str, Any]:
        if os.getenv("SEARXNG_ENABLED", "true").lower() != "true":
            return {"enabled": False, "provider": self.name, "status": "disabled", "base_url": self.base_url}
        try:
            response = httpx.get(self.base_url + "/", headers={"User-Agent": USER_AGENT}, timeout=min(self.timeout, 3.0))
            ready = response.status_code < 500
            return {"enabled": ready, "provider": self.name, "status": "connected" if ready else "error", "base_url": self.base_url}
        except Exception:
            return {"enabled": False, "provider": self.name, "status": "unavailable", "base_url": self.base_url}


class DuckDuckGoSearchProvider(WebSearchProvider):
    name = "duckduckgo"

    def __init__(self, timeout: float = 15.0, extractor: WebContentExtractor | None = None):
        self.timeout, self.extractor = timeout, extractor or LocalContentExtractor(timeout)

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        response = httpx.get("https://html.duckduckgo.com/html/?q=" + quote_plus(_safe_query(query)), headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
        response.raise_for_status()
        soup, rows = BeautifulSoup(response.text, "html.parser"), []
        for result in soup.select(".result"):
            link = result.select_one(".result__a")
            if not link or not link.get("href"):
                continue
            url = str(link.get("href"))
            if url.startswith("//duckduckgo.com/l/"):
                url = unquote(parse_qs(urlparse(url).query).get("uddg", [""])[0])
            if not url.startswith(("http://", "https://")):
                continue
            snippet = result.select_one(".result__snippet")
            rows.append(SearchResult(link.get_text(" ", strip=True)[:240], url, snippet.get_text(" ", strip=True)[:500] if snippet else ""))
            if len(rows) >= options.max_results:
                break
        return rows

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.extractor.extract(url, options)

    def health_check(self) -> dict[str, Any]:
        return {"enabled": True, "provider": self.name, "status": "legacy", "api_key_required": False}


class TavilySearchProvider(DuckDuckGoSearchProvider):
    name = "tavily"

    def __init__(self, api_key: str, timeout: float = 15.0, extractor: WebContentExtractor | None = None):
        super().__init__(timeout, extractor)
        self.api_key = api_key

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        body: dict[str, Any] = {"query": _safe_query(query), "max_results": max(1, min(options.max_results, 10)), "search_depth": "advanced"}
        if options.allowed_domains:
            body["include_domains"] = list(options.allowed_domains)
        response = httpx.post("https://api.tavily.com/search", json=body, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout)
        response.raise_for_status()
        return [SearchResult(str(item.get("title", ""))[:240], str(item.get("url", "")), str(item.get("content", ""))[:500], str(item.get("published_date", ""))) for item in response.json().get("results", []) if item.get("url")]

    def health_check(self) -> dict[str, Any]:
        return {"enabled": bool(self.api_key), "provider": self.name, "status": "legacy"}


class HybridWebProvider(WebSearchProvider):
    def __init__(self, search_provider: WebSearchProvider, local: LocalContentExtractor, firecrawl: FirecrawlProvider, high_quality: bool = False):
        self.search_provider, self.local, self.firecrawl = search_provider, local, firecrawl
        self.high_quality, self.name = high_quality, search_provider.name

    def search(self, query: str, options: SearchOptions) -> list[SearchResult]:
        raw_key = f"{self.name}|{_safe_query(query)}|{options}|{self.high_quality}"
        key = hashlib.sha256(raw_key.encode()).hexdigest()
        ttl = max(60, int(os.getenv("SEARXNG_CACHE_TTL_SECONDS", "86400")))
        now = time.time()
        with _CACHE_LOCK:
            for expired_key, (expires_at, _) in list(_SEARCH_CACHE.items()):
                if expires_at <= now:
                    _SEARCH_CACHE.pop(expired_key, None)
            cached = _SEARCH_CACHE.get(key)
            if cached and cached[0] > now:
                return list(cached[1])
        with _SEARCH_SLOT:
            try:
                rows = self.search_provider.search(query, options)
            except Exception:
                rows = []
            if self.high_quality and self.firecrawl.enabled and len(rows) < min(3, options.max_results):
                try:
                    fallback = self.firecrawl.search(query, SearchOptions(max_results=min(5, options.max_results), allowed_domains=options.allowed_domains, freshness_days=options.freshness_days, high_quality=True))
                    known = {item.url.rstrip("/") for item in rows}
                    rows.extend(item for item in fallback if item.url.rstrip("/") not in known)
                except Exception:
                    pass
            rows = rows[: options.max_results]
            with _CACHE_LOCK:
                _SEARCH_CACHE[key] = (time.time() + ttl, list(rows))
                overflow = len(_SEARCH_CACHE) - _search_cache_limit()
                if overflow > 0:
                    for old_key, _ in sorted(_SEARCH_CACHE.items(), key=lambda item: item[1][0])[:overflow]:
                        _SEARCH_CACHE.pop(old_key, None)
            return rows

    def extract(self, url: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        grade = str((options or {}).get("source_grade") or "C")
        if self.high_quality and grade in {"A", "B"} and self.firecrawl.enabled:
            try:
                return self.firecrawl.extract(url, options)
            except Exception:
                pass
        return self.local.extract(url, options)

    def health_check(self) -> dict[str, Any]:
        search = self.search_provider.health_check()
        return {"enabled": bool(search.get("enabled")), "provider": self.name, "status": search.get("status", "unknown"), "search": search, "firecrawl": self.firecrawl.health_check(), "local_extractor": self.local.health_check(), "mode": "high_quality" if self.high_quality else "free"}


def extract_public_page(url: str, timeout: float = 15.0, max_bytes: int = 8 * 1024 * 1024) -> dict[str, Any]:
    return LocalContentExtractor(timeout=timeout, max_bytes=max_bytes).extract(url)


def build_search_provider(high_quality: bool = False) -> WebSearchProvider:
    settings = web_search_configuration()
    if not settings["enabled"]:
        return DisabledSearchProvider()
    selected = str(settings["provider"])
    timeout = float(settings["timeout_seconds"])
    local = LocalContentExtractor(
        float(settings["extractor_timeout_seconds"]),
        int(settings["extractor_max_bytes"]),
        int(settings["extractor_max_text_chars"]),
    )
    firecrawl = FirecrawlProvider(os.getenv("FIRECRAWL_API_KEY", ""), float(os.getenv("FIRECRAWL_TIMEOUT_SECONDS", "30")), int(os.getenv("FIRECRAWL_MAX_RETRIES", "1")))
    if selected == "disabled":
        return DisabledSearchProvider()
    if selected == "tavily" and os.getenv("AI_COURSE_STUDIO_WEB_SEARCH_API_KEY"):
        search: WebSearchProvider = TavilySearchProvider(os.getenv("AI_COURSE_STUDIO_WEB_SEARCH_API_KEY", ""), timeout, local)
    elif selected in ("duckduckgo", "ddg"):
        search = DuckDuckGoSearchProvider(timeout, local)
    else:
        search = SearXngProvider(os.getenv("SEARXNG_BASE_URL", "http://127.0.0.1:8888"), timeout, local)
    return HybridWebProvider(search, local, firecrawl, high_quality)
