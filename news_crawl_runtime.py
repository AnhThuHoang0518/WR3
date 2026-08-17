#!/usr/bin/env python3
"""Shared RSS discovery and source-content utilities for WR3 News stages 01-04.

This module discovers candidates, resolves source pages and extracts auditable
content for human review. It does not evaluate relevance, extract Signals,
classify Opportunity/Threat, or read the VSF product catalog.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


USER_AGENT = "WR3-News-Collector/1.0 (+human-review-required)"
REVIEW_TRANSLATION_FIELDS = ("title", "summary", "key_facts", "relevance_rationale")
MAX_FEED_BYTES = 5 * 1024 * 1024
MAX_PAGE_BYTES = 3 * 1024 * 1024
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
VIETNAMESE_RE = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệ"
    r"íìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    re.IGNORECASE,
)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
AGGREGATOR_HOSTS = {
    "bing.com", "www.bing.com", "google.com", "www.google.com", "news.google.com",
}
BLOCKED_SOURCE_NAMES = {"电玩巴士"}
BLOCKED_SOURCE_HOSTS = {"tgbus.com"}
SKIP_HTML_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "form"}
TITLE_STOPWORDS = {
    "about", "after", "from", "into", "news", "that", "the", "this", "with",
    "bài", "bản", "cho", "các", "của", "được", "một", "những", "theo", "trong", "với",
}


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    query: str
    geography: str
    entities: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageFetch:
    body: bytes
    final_url: str
    content_type: str = "text/html"


class _ArticleHTMLParser(HTMLParser):
    """Extract auditable page metadata and paragraph text without third-party packages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.article_depth = 0
        self.main_depth = 0
        self.in_title = False
        self.paragraph_context: str | None = None
        self.paragraph_parts: list[str] = []
        self.title_parts: list[str] = []
        self.article_paragraphs: list[str] = []
        self.main_paragraphs: list[str] = []
        self.other_paragraphs: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical_url = ""
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        values = {str(key).casefold(): value or "" for key, value in attrs}
        if tag in SKIP_HTML_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "article":
            self.article_depth += 1
        elif tag == "main":
            self.main_depth += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "p":
            self.paragraph_parts = []
            self.paragraph_context = "article" if self.article_depth else "main" if self.main_depth else "other"
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").casefold()
            content = _clean_text(values.get("content"))
            if key and content:
                self.meta.setdefault(key, content)
        elif tag == "link" and "canonical" in values.get("rel", "").casefold():
            self.canonical_url = values.get("href", "").strip()
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"].strip())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag in SKIP_HTML_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "p" and self.paragraph_context is not None:
            paragraph = _clean_text(" ".join(self.paragraph_parts))
            if len(paragraph) >= 40:
                target = {
                    "article": self.article_paragraphs,
                    "main": self.main_paragraphs,
                    "other": self.other_paragraphs,
                }[self.paragraph_context]
                target.append(paragraph)
            self.paragraph_context = None
            self.paragraph_parts = []
        elif tag == "title":
            self.in_title = False
        elif tag == "article" and self.article_depth:
            self.article_depth -= 1
        elif tag == "main" and self.main_depth:
            self.main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_title:
            self.title_parts.append(data)
        if self.paragraph_context is not None:
            self.paragraph_parts.append(data)

    def paragraphs(self) -> list[str]:
        candidates = self.article_paragraphs or self.main_paragraphs or self.other_paragraphs
        return list(dict.fromkeys(candidates))


class _WebSearchHTMLParser(HTMLParser):
    """Extract ordinary Bing Web Search result links without executing scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_result = False
        self.result_depth = 0
        self.in_heading = False
        self.in_link = False
        self.in_snippet = False
        self.current: dict[str, Any] = {}
        self.results: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        values = {str(key).casefold(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").casefold().split())
        if tag == "li":
            if not self.in_result and "b_algo" in classes:
                self.in_result = True
                self.result_depth = 1
                self.current = {"title_parts": [], "snippet_parts": []}
            elif self.in_result:
                self.result_depth += 1
        if not self.in_result:
            return
        if tag == "h2":
            self.in_heading = True
        elif tag == "a" and self.in_heading and values.get("href"):
            self.in_link = True
            self.current.setdefault("link", values["href"].strip())
        elif tag == "p":
            self.in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if not self.in_result:
            return
        if tag == "a":
            self.in_link = False
        elif tag == "h2":
            self.in_heading = False
        elif tag == "p":
            self.in_snippet = False
        elif tag == "li":
            self.result_depth -= 1
            if self.result_depth == 0:
                title = _clean_text(" ".join(self.current.get("title_parts", [])))
                link = _resolve_bing_result_url(
                    _absolute_http_url(str(self.current.get("link", "")), "https://www.bing.com/")
                )
                description = _clean_text(" ".join(self.current.get("snippet_parts", [])))
                if title and link and not _is_aggregator_url(link):
                    self.results.append({"title": title, "link": link, "description": description})
                self.in_result = False
                self.current = {}

    def handle_data(self, data: str) -> None:
        if self.in_result and self.in_link:
            self.current.setdefault("title_parts", []).append(data)
        if self.in_result and self.in_snippet:
            self.current.setdefault("snippet_parts", []).append(data)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value))).strip()


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_feed_date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def window_bounds(
    *,
    days: int,
    timezone_name: str,
    end_date: date | None = None,
) -> tuple[datetime, datetime]:
    """Return an inclusive rolling calendar-day window as half-open UTC bounds."""
    if days < 1:
        raise ValueError("days must be at least 1")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        if timezone_name != "Asia/Bangkok":
            raise ValueError(f"Timezone data unavailable for {timezone_name}")
        # Windows Python installations may not bundle IANA tzdata. Bangkok has
        # used UTC+07:00 without DST throughout the supported reporting period.
        zone = timezone(timedelta(hours=7), name="Asia/Bangkok")
    local_end = end_date or datetime.now(zone).date()
    local_start = local_end - timedelta(days=days - 1)
    start = datetime.combine(local_start, time.min, tzinfo=zone).astimezone(timezone.utc)
    end_exclusive = datetime.combine(local_end + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    return start, end_exclusive


def _provider_locale(geography: str) -> tuple[str, str, str, str]:
    """Return Google language/region/edition and Bing market for a query geography."""
    normalized = unicodedata.normalize("NFKC", geography).casefold()
    if any(value in normalized for value in ("china", "trung quốc", "中国")):
        return "zh-CN", "CN", "CN:zh-Hans", "zh-CN"
    if "singapore" in normalized or "新加坡" in normalized:
        return "en-SG", "SG", "SG:en", "en-SG"
    if any(value in normalized for value in ("global", "toàn cầu")):
        return "en-US", "US", "US:en", "en-US"
    return "vi", "VN", "VN:vi", "vi-VN"


def provider_url(provider: str, query: str, days: int, geography: str = "Việt Nam") -> str:
    google_language, google_region, google_edition, bing_market = _provider_locale(geography)
    if provider == "google":
        scoped = f"{query} when:{days}d"
        return (
            "https://news.google.com/rss/search?"
            + urllib.parse.urlencode({
                "q": scoped,
                "hl": google_language,
                "gl": google_region,
                "ceid": google_edition,
            })
        )
    if provider == "bing":
        return "https://www.bing.com/news/search?" + urllib.parse.urlencode(
            {"q": query, "format": "rss", "mkt": bing_market}
        )
    if provider == "web":
        return "https://www.bing.com/search?" + urllib.parse.urlencode({
            "q": query,
            "setlang": bing_market,
            "cc": bing_market.rsplit("-", 1)[-1],
            "count": 10,
        })
    raise ValueError(f"Unsupported provider: {provider}")


def fetch_bytes(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
        if len(payload) > MAX_FEED_BYTES:
            raise ValueError("RSS payload exceeds the 5 MiB safety limit")
        return payload


def fetch_page(url: str, timeout: float) -> PageFetch:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_PAGE_BYTES + 1)
        if len(payload) > MAX_PAGE_BYTES:
            raise ValueError("Source page exceeds the 3 MiB safety limit")
        return PageFetch(
            body=payload,
            final_url=response.geturl(),
            content_type=response.headers.get_content_type(),
        )


def parse_rss(payload: bytes) -> list[dict[str, str]]:
    """Parse RSS/Atom discovery metadata without treating snippets as verified facts."""
    root = ET.fromstring(payload)
    records: list[dict[str, str]] = []
    entries = list(root.findall(".//item"))
    if not entries:
        entries = list(root.findall(".//{*}entry"))
    for entry in entries:
        title = _clean_text(entry.findtext("title") or entry.findtext("{*}title"))
        link = _clean_text(entry.findtext("link"))
        if not link:
            link_node = entry.find("{*}link")
            if link_node is not None:
                link = _clean_text(link_node.attrib.get("href"))
        published = _clean_text(
            entry.findtext("pubDate")
            or entry.findtext("published")
            or entry.findtext("{*}published")
            or entry.findtext("{*}updated")
        )
        description = _clean_text(
            entry.findtext("description")
            or entry.findtext("summary")
            or entry.findtext("{*}summary")
            or entry.findtext("{*}content")
        )
        source = _clean_text(entry.findtext("source") or entry.findtext("{*}source"))
        if title and link and published:
            records.append({
                "title": title,
                "link": link,
                "published": published,
                "description": description,
                "source": source,
            })
    return records


def parse_web_search(payload: bytes) -> list[dict[str, str]]:
    parser = _WebSearchHTMLParser()
    parser.feed(_decode_html(payload))
    parser.close()
    return parser.results


def _page_publication_date(parser: _ArticleHTMLParser, payload: bytes) -> tuple[datetime | None, str | None]:
    for key in (
        "article:published_time", "og:published_time", "datepublished", "date",
        "pubdate", "publishdate", "dc.date", "sailthru.date",
    ):
        value = parser.meta.get(key, "")
        parsed = _parse_feed_date(value) if value else None
        if parsed is not None:
            return parsed, f"meta:{key}"
    match = re.search(
        r'["\']datePublished["\']\s*:\s*["\']([^"\']+)["\']',
        _decode_html(payload),
        flags=re.IGNORECASE,
    )
    if match:
        parsed = _parse_feed_date(html.unescape(match.group(1)))
        if parsed is not None:
            return parsed, "jsonld:datePublished"
    return None, None


def _web_experience_candidate_relevant(query_id: str, *values: str) -> bool:
    """Require the fetched Web result to contain the journey facets named by its query."""
    text = _semantic_text(" ".join(value for value in values if value))
    signal_groups: dict[str, tuple[tuple[str, ...], ...]] = {
        "citizen": (
            ("smart city", "urban", "city", "đô thị", "municipal"),
            ("citizen", "resident", "people", "người dân", "cư dân", "city service", "dịch vụ đô thị"),
        ),
        "parking": (
            ("smart parking", "parking", "bãi đỗ xe", "đỗ xe"),
            ("driver", "user", "resident", "người lái xe", "người dân", "payment", "queue", "wayfinding"),
        ),
        "venues-vn": (
            ("khu vui chơi", "công viên chủ đề", "sân vận động", "nhà thi đấu", "theme park", "stadium", "arena"),
            ("khách tham quan", "khán giả", "người hâm mộ", "visitor", "fan", "guest", "trải nghiệm", "xếp hàng"),
        ),
        "stadium": (
            ("stadium", "arena", "smart venue"),
            ("fan", "guest", "visitor", "experience", "journey", "queue", "accessibility", "wayfinding"),
        ),
        "attractions": (
            ("theme park", "amusement park", "attraction", "resort"),
            ("guest", "visitor", "experience", "journey", "queue", "accessibility", "itinerary"),
        ),
        "digital-twin": (
            ("digital twin", "3d city model"),
            ("city", "urban", "venue", "stadium", "attraction", "citizen", "visitor", "operator"),
        ),
        "safety-ai": (
            ("artificial intelligence", " ai ", "video analytics", "computer vision"),
            ("safety", "security", "incident", "crowd"),
        ),
        "places": (
            ("public space", "street", "plaza", "theme park", "amusement park", "smart parking", "màn hình led", "quảng cáo điện tử"),
            ("pedestrian", "visitor", "driver", "resident", "user experience", "người đi đường", "người đi bộ", "người lái xe", "cư dân"),
        ),
    }
    key_order = ("venues-vn", "digital-twin", "safety-ai", "citizen", "parking", "stadium", "attractions", "places")
    selected = next((key for key in key_order if key in query_id), None)
    if selected is None:
        return True
    return all(bool(_signal_hits(text, group)) for group in signal_groups[selected])


def _source_name(item: dict[str, str]) -> str:
    if item.get("source"):
        return item["source"]
    host = urllib.parse.urlsplit(item["link"]).hostname
    return host or "Nguồn RSS chưa xác định"


def _is_blocked_source(item: dict[str, str]) -> bool:
    source = _source_name(item).casefold()
    host = (urllib.parse.urlsplit(item.get("link", "")).hostname or "").casefold()
    blocked_name = any(name.casefold() in source for name in BLOCKED_SOURCE_NAMES)
    blocked_host = any(host == value or host.endswith(f".{value}") for value in BLOCKED_SOURCE_HOSTS)
    return blocked_name or blocked_host


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").casefold()


def _is_aggregator_url(url: str) -> bool:
    host = _host(url)
    return host in AGGREGATOR_HOSTS or host.endswith(".google.com") or host.endswith(".bing.com")


def _resolve_bing_result_url(url: str) -> str:
    """Unwrap Bing's ``/ck/a`` result redirect without requesting the redirector."""
    parsed = urllib.parse.urlsplit(url)
    if not (parsed.hostname or "").casefold().endswith("bing.com"):
        return url
    encoded = urllib.parse.parse_qs(parsed.query).get("u", [""])[0]
    if not encoded:
        return url
    candidate = urllib.parse.unquote(encoded)
    if candidate.startswith(("http://", "https://")):
        return candidate
    if candidate.startswith("a1"):
        candidate = candidate[2:]
    try:
        padding = "=" * (-len(candidate) % 4)
        decoded = base64.urlsafe_b64decode(candidate + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return url
    return decoded if decoded.startswith(("http://", "https://")) else url


def _absolute_http_url(value: str, base_url: str) -> str:
    candidate = urllib.parse.urljoin(base_url, html.unescape(value).strip())
    parsed = urllib.parse.urlsplit(candidate)
    return candidate if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _decode_html(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "windows-1258", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _parse_article_page(page: PageFetch) -> tuple[_ArticleHTMLParser, list[str]]:
    parser = _ArticleHTMLParser()
    parser.feed(_decode_html(page.body))
    parser.close()
    return parser, parser.paragraphs()


def _source_candidate(parser: _ArticleHTMLParser, base_url: str) -> str:
    candidates = [
        parser.canonical_url,
        parser.meta.get("og:url", ""),
        *parser.links,
    ]
    for value in candidates:
        candidate = _absolute_http_url(value, base_url)
        if candidate and not _is_aggregator_url(candidate):
            return candidate
    return ""


def _title_similarity(left: str, right: str) -> float:
    left_tokens = _content_tokens(_strip_publisher_suffix(left))
    right_tokens = _content_tokens(_strip_publisher_suffix(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _strip_publisher_suffix(title: str) -> str:
    return re.sub(r"\s+-\s+[^-]{2,80}$", "", title).strip()


def _identity_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold()).replace("đ", "d")
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    ignored = {"bao", "com", "news", "net", "org", "tapchi", "vn", "www"}
    return {
        token for token in re.findall(r"[a-z0-9]+", ascii_value)
        if len(token) >= 3 and token not in ignored
    }


def _publisher_matches(source_name: str, title: str, final_url: str, parser: _ArticleHTMLParser) -> bool:
    source_key = source_name.casefold()
    if (
        source_key in AGGREGATOR_HOSTS
        or source_key.endswith(".google.com")
        or source_key.endswith(".bing.com")
    ):
        return True
    suffix_match = re.search(r"\s+-\s+([^-]{2,80})$", title)
    expected = _identity_tokens(source_name)
    if suffix_match:
        expected.update(_identity_tokens(suffix_match.group(1)))
    if not expected:
        return True
    actual = _identity_tokens(_host(final_url))
    actual.update(_identity_tokens(parser.meta.get("og:site_name", "")))
    return bool(expected & actual)


def _bing_title_fallback(
    title: str,
    source_name: str,
    *,
    timeout: float,
    feed_fetcher: Callable[[str, float], bytes],
) -> str:
    source_hint = source_name if source_name.casefold() not in AGGREGATOR_HOSTS else ""
    query = " ".join(value for value in (_strip_publisher_suffix(title), source_hint) if value)
    payload = feed_fetcher(provider_url("bing", query, 30), timeout)
    candidates = parse_rss(payload)
    ranked = sorted(
        ((_title_similarity(title, item["title"]), item["link"]) for item in candidates),
        reverse=True,
    )
    if not ranked or ranked[0][0] < 0.55:
        return ""
    return ranked[0][1]


def _fetch_result(value: PageFetch | tuple[Any, ...] | bytes, requested_url: str) -> PageFetch:
    """Normalize injectable test fetchers while keeping the production fetch contract explicit."""
    if isinstance(value, PageFetch):
        return value
    if isinstance(value, bytes):
        return PageFetch(value, requested_url)
    if isinstance(value, tuple) and len(value) >= 2:
        return PageFetch(bytes(value[0]), str(value[1]), str(value[2]) if len(value) > 2 else "text/html")
    raise TypeError("content fetcher must return PageFetch, bytes, or (body, final_url[, content_type])")


def _excerpt(paragraphs: list[str], fallback: str, max_chars: int = 700) -> str:
    source = " ".join(paragraphs[:4]).strip() or _clean_text(fallback)
    if not source:
        return ""
    sentences = SENTENCE_RE.split(source)
    selected: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if selected and len(" ".join([*selected, sentence])) > max_chars:
            break
        selected.append(sentence)
        if len(selected) >= 3:
            break
    rendered = " ".join(selected) or source
    if len(rendered) > max_chars:
        rendered = rendered[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return rendered


def _content_status(paragraphs: list[str], text: str) -> str:
    if len(text) >= 600 and len(paragraphs) >= 3:
        return "FULL_TEXT"
    if len(text) >= 160:
        return "PARTIAL_TEXT"
    return "METADATA_ONLY"


def _content_tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[\wÀ-ỹ]+", value.casefold(), flags=re.UNICODE)
        if len(token) >= 3 and token not in TITLE_STOPWORDS
    }


def _ordered_content_tokens(value: str) -> list[str]:
    return [
        token for token in re.findall(r"[\wÀ-ỹ]+", value.casefold(), flags=re.UNICODE)
        if len(token) >= 2 and token not in TITLE_STOPWORDS
    ]


def _phrase_match_count(title: str, text: str) -> int:
    title_tokens = _ordered_content_tokens(title)
    text_tokens = _ordered_content_tokens(text)
    if len(title_tokens) < 2 or len(text_tokens) < 2:
        return 0
    width = 3 if len(title_tokens) >= 4 else 2
    title_phrases = {
        tuple(title_tokens[index:index + width])
        for index in range(len(title_tokens) - width + 1)
    }
    text_phrases = {
        tuple(text_tokens[index:index + width])
        for index in range(len(text_tokens) - width + 1)
    }
    return len(title_phrases & text_phrases)


def _alignment(title: str, text: str) -> tuple[int, float]:
    title_tokens = _content_tokens(title)
    if not title_tokens:
        return 0, 0.0
    matched = title_tokens & _content_tokens(text)
    return len(matched), len(matched) / len(title_tokens)


def _aligned_paragraphs(title: str, paragraphs: list[str]) -> tuple[list[str], int, float, int]:
    """Start at the paragraph most aligned with the RSS title and reject unrelated page chrome."""
    if not paragraphs:
        return [], 0, 0.0, 0
    scores = [
        (_phrase_match_count(title, paragraph), *_alignment(title, paragraph))
        for paragraph in paragraphs
    ]
    best_index = max(range(len(paragraphs)), key=lambda index: scores[index])
    body_match_count, body_overlap = _alignment(title, " ".join(paragraphs))
    body_phrase_matches = _phrase_match_count(title, " ".join(paragraphs))
    best_phrase_matches, best_count, _ = scores[best_index]
    required_body_phrases = 2 if len(_ordered_content_tokens(title)) >= 5 else 1
    if (
        body_match_count < 3 or body_overlap < 0.25
        or body_phrase_matches < required_body_phrases
        or best_count < 2 or best_phrase_matches < 1
    ):
        return [], body_match_count, body_overlap, body_phrase_matches
    return paragraphs[best_index:best_index + 12], body_match_count, body_overlap, body_phrase_matches


def _enrich_record(
    record: dict[str, Any],
    *,
    timeout: float,
    content_fetcher: Callable[[str, float], PageFetch | tuple[Any, ...] | bytes],
    resolution_fetcher: Callable[[str, float], bytes],
) -> dict[str, Any]:
    """Resolve a discovery URL and derive reviewer-facing fields only from fetched source text."""
    rss_url = str(record["source_url"])
    evidence = record["crawl_evidence"]
    evidence.update({
        "rss_source_url": rss_url,
        "resolved_source_url": None,
        "resolution_status": "PENDING",
        "extraction_method": None,
        "content_chars": 0,
    })
    try:
        first = _fetch_result(content_fetcher(rss_url, timeout), rss_url)
        parser, paragraphs = _parse_article_page(first)
        page = first
        if _is_aggregator_url(first.final_url):
            direct = _source_candidate(parser, first.final_url)
            fallback_used = False
            if not direct:
                try:
                    direct = _bing_title_fallback(
                        record["title"], str(record.get("source_name", "")),
                        timeout=timeout, feed_fetcher=resolution_fetcher,
                    )
                    fallback_used = bool(direct)
                    evidence["title_resolution_status"] = "MATCHED" if direct else "NO_MATCH"
                except Exception as exc:
                    evidence["title_resolution_status"] = "FAILED"
                    evidence["title_resolution_error"] = f"{type(exc).__name__}: {exc}"
            if direct:
                candidate_page = _fetch_result(content_fetcher(direct, timeout), direct)
                candidate_parser, candidate_paragraphs = _parse_article_page(candidate_page)
                if fallback_used and not _publisher_matches(
                    str(record.get("source_name", "")), record["title"],
                    candidate_page.final_url, candidate_parser,
                ):
                    evidence["title_resolution_status"] = "PUBLISHER_MISMATCH"
                    evidence["title_resolution_candidate_url"] = candidate_page.final_url
                else:
                    page, parser, paragraphs = candidate_page, candidate_parser, candidate_paragraphs
                    evidence["resolution_method"] = "bing_title_fallback" if fallback_used else "page_link"
        resolved_url = page.final_url
        if _is_aggregator_url(resolved_url):
            evidence["resolution_status"] = "RSS_ONLY"
        else:
            evidence["resolution_status"] = "RESOLVED"
            evidence["resolved_source_url"] = resolved_url
            record["source_url"] = resolved_url
            source_label = str(record.get("source_name", "")).casefold()
            if (
                source_label in AGGREGATOR_HOSTS
                or source_label.endswith(".google.com")
                or source_label.endswith(".bing.com")
            ):
                record["source_name"] = parser.meta.get("og:site_name") or _host(resolved_url).removeprefix("www.")

        meta_description = parser.meta.get("og:description") or parser.meta.get("description", "")
        aligned, match_count, overlap, phrase_matches = _aligned_paragraphs(record["title"], paragraphs)
        evidence["title_body_match_count"] = match_count
        evidence["title_body_overlap"] = round(overlap, 3)
        evidence["title_body_phrase_matches"] = phrase_matches
        body_text = "\n\n".join(aligned)
        meta_match_count, meta_overlap = _alignment(record["title"], meta_description)
        meta_phrase_matches = _phrase_match_count(record["title"], meta_description)
        usable_meta = _clean_text(meta_description) if meta_match_count >= 2 and meta_overlap >= 0.2 and meta_phrase_matches >= 1 else ""
        usable_text = body_text or usable_meta
        if VIETNAMESE_RE.search(usable_text):
            record["language"] = "vi"
        elif CJK_RE.search(usable_text):
            record["language"] = "zh"
        evidence["content_language"] = record["language"]
        translation_required = (
            str(evidence.get("original_language", "")).casefold() != "vi"
            or record["language"] != "vi"
        )
        evidence["review_translation_required"] = translation_required
        evidence["translation_status"] = "PENDING" if translation_required else "NOT_REQUIRED"
        status = _content_status(aligned, usable_text)
        evidence["content_chars"] = len(usable_text)
        evidence["extraction_method"] = "aligned_article_paragraphs" if body_text else "aligned_meta_description" if usable_text else None
        if paragraphs and not aligned:
            evidence["content_rejection_reason"] = "TITLE_BODY_MISMATCH"
        record["content_status"] = status
        if status == "METADATA_ONLY":
            return record

        excerpt = _excerpt(paragraphs, usable_text)
        evidence["original_excerpt"] = excerpt
        record["raw_content"] = usable_text
        record["summary"] = f"Nội dung lấy từ bài gốc cho biết: {excerpt}"
        record["key_facts"] = [
            f"{evidence.get('discovery_channel', 'RSS')} ghi nhận thời điểm xuất bản: {record['published_at']}.",
            f"Bài gốc đã được truy cập tại: {record['source_url']}.",
            f"Trích đoạn có thể đối chiếu từ bài gốc: {excerpt}",
        ]
        record["evidence_quality"] = "MEDIUM" if status == "FULL_TEXT" else "LOW"
        return record
    except Exception as exc:  # A single malformed/blocked page must not abort the whole crawl.
        evidence["resolution_status"] = "FAILED"
        evidence["resolution_error"] = f"{type(exc).__name__}: {exc}"
        return record


def _dedupe_key(title: str, link: str) -> str:
    parsed = urllib.parse.urlsplit(link)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    clean_query = urllib.parse.urlencode(
        [(key, value) for key, value in query if not key.lower().startswith("utm_")]
    )
    clean_url = urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), clean_query, ""))
    normalized_title = re.sub(r"[^\w]+", " ", title.casefold(), flags=re.UNICODE).strip()
    return f"{clean_url}|{normalized_title}"


def _raw_id(news_type: str, title: str, link: str) -> str:
    digest = hashlib.sha256(_dedupe_key(title, link).encode("utf-8")).hexdigest()[:16].upper()
    return f"RAW-LIVE-{news_type}-{digest}"


_CATEGORY_PRIORITY = ("POLICY", "COMPETITOR", "MARKET", "TECHNOLOGY")
_CATEGORY_SIGNALS = {
    "POLICY": (
        "regulation", "regulatory", "policy", "law", "legal framework", "decree",
        "directive", "ordinance", "standard", "guideline", "government program",
        "data governance", "privacy", "cybersecurity", "quy dinh", "chinh sach",
        "nghi dinh", "thong tu", "quyet dinh", "tieu chuan", "quy hoach",
        "huong dan", "phe duyet", "bao ve du lieu", "an ninh mang", "chinh quyen so",
        "政策", "标准", "规划", "指导意见", "数据治理", "法规",
    ),
    "MARKET": (
        "procurement", "tender", "bid", "contract", "award", "investment", "funding",
        "budget", "deployment", "pilot", "project", "adoption", "rollout",
        "implementation", "mua sam", "dau thau", "trung thau", "hop dong", "dau tu",
        "ngan sach", "du an", "trien khai", "thi diem", "khoi cong", "van hanh",
        "采购", "招标", "中标", "合同", "投资", "项目", "部署", "试点",
    ),
    "TECHNOLOGY": (
        "artificial intelligence", " ai ", "aiot", "iot", "sensor", "edge computing",
        "digital twin", "video analytics", "computer vision", "interoperability",
        "robot", "robotics", "smart parking", "intelligent transport",
        "traffic management", "environmental monitoring", "smart lighting",
        "city brain", "technology platform", "tri tue nhan tao", "cam bien",
        "dien toan bien", "ban sao so", "thi giac may tinh", "robot", "nen tang",
        "mobile ticketing", "digital identity", "frictionless entry", "wayfinding",
        "queue management", "crowd analytics", "cashless", "guest app", "digital pass",
        "virtual queue", "personalization", "accessibility", "3d city model", "bim gis",
        "anomaly detection", "incident response", "human in the loop",
        "人工智能", "物联网", "数字孪生", "计算机视觉", "智能交通", "城市大脑",
    ),
}
_COMPETITOR_ACTION_SIGNALS = (
    "launch", "partnership", "partner", "sign agreement", "memorandum", "mou",
    "wins contract", "awarded", "acquisition", "acquire", "expansion", "joint venture",
    "ra mat", "hop tac", "ky ket", "bien ban ghi nho", "trung thau", "mo rong",
    "lien doanh", "mua lai", "发布", "合作", "签署", "中标", "收购", "扩张",
)
_COMPETITOR_NEGATIVE_SIGNALS = (
    "stock", "share price", "profit growth", "earnings", "dividend", "annual meeting",
    "co phieu", "loi nhuan", "co tuc", "dai hoi dong co dong", "股价", "利润", "股息",
)
_HEADLINE_NOISE_SIGNALS = (
    *_COMPETITOR_NEGATIVE_SIGNALS,
    "stock market", "shareholder meeting", "securities", "casino", "betting",
    "thi truong chung khoan", "chung khoan", "dai hoi co dong", "ca cuoc",
    "赌场", "博彩", "股东大会",
)
_SMART_CITY_SIGNALS = (
    "smart city", "smart nation", "urban", "municipal", "city", "do thi thong minh",
    "thanh pho thong minh", "smart venue", "smart stadium", "smart attraction",
    "智慧城市", "数字城市", "城市大脑",
)
_SCOPE_SIGNALS = (
    *_SMART_CITY_SIGNALS,
    "digital", "data", "cybersecurity", "transport", "traffic", "parking",
    "municipal", "environmental", "air quality", "public safety", "pothole", "garbage",
    "stadium", "arena", "venue", "theme park", "amusement park", "resort", "attraction",
    "fan", "visitor", "guest", "user experience", "fan journey", "guest journey",
    "wayfinding", "accessibility", "queue", "crowd", "ticketing", "incident response",
    "du lieu", "an ninh mang", "giao thong", "do xe", "moi truong", "an ninh cong cong",
    "城市", "数字", "数据", "交通", "停车", "环境", "网络安全",
)
_CONTENT_RANK = {"UNAVAILABLE": 0, "METADATA_ONLY": 1, "PARTIAL_TEXT": 2, "FULL_TEXT": 3}


def _semantic_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " " + re.sub(r"[^\w]+", " ", unaccented, flags=re.UNICODE).strip() + " "


def _signal_hits(text: str, signals: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for signal in signals:
        needle = _semantic_text(signal).strip()
        if not needle:
            continue
        contains_cjk = bool(CJK_RE.search(needle))
        if (needle in text if contains_cjk else re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", text)):
            hits.append(signal.strip())
    return hits


def _global_dedupe_key(record: dict[str, Any]) -> str:
    evidence = record.get("crawl_evidence", {})
    original_title = str(evidence.get("original_title") or record.get("title") or "")
    title = _semantic_text(_strip_publisher_suffix(original_title)).strip()
    published_day = str(record.get("published_at", ""))[:10]
    return f"{published_day}|{title}"


def _classification_text(record: dict[str, Any]) -> str:
    evidence = record.get("crawl_evidence", {})
    values = (
        evidence.get("original_title", record.get("title", "")),
        evidence.get("original_rss_description", ""),
        record.get("raw_content", ""),
    )
    return _semantic_text(" ".join(str(value) for value in values if value))


def _classify_record(record: dict[str, Any], discovered_types: set[str]) -> dict[str, Any]:
    text = _classification_text(record)
    evidence = record.get("crawl_evidence", {})
    title_text = _semantic_text(str(evidence.get("original_title") or record.get("title", "")))
    matched = {
        category: _signal_hits(text, signals)
        for category, signals in _CATEGORY_SIGNALS.items()
    }
    scores = {
        "POLICY": len(matched["POLICY"]) * 3,
        "MARKET": len(matched["MARKET"]) * 2,
        "TECHNOLOGY": len(matched["TECHNOLOGY"]) * 2,
        "COMPETITOR": 0,
    }
    for category in discovered_types:
        if category in scores:
            scores[category] += 1
    competitor_actions = _signal_hits(text, _COMPETITOR_ACTION_SIGNALS)
    competitor_negatives = _signal_hits(text, _COMPETITOR_NEGATIVE_SIGNALS)
    smart_city_hits = _signal_hits(text, _SMART_CITY_SIGNALS)
    scope_hits = _signal_hits(text, _SCOPE_SIGNALS)
    headline_scope_hits = _signal_hits(title_text, _SCOPE_SIGNALS)
    headline_noise_hits = _signal_hits(title_text, _HEADLINE_NOISE_SIGNALS)
    headline_is_noise = bool(headline_noise_hits and not headline_scope_hits)
    entities = [str(value) for value in record.get("entities", []) if str(value).strip()]
    if "COMPETITOR" in discovered_types:
        scores["COMPETITOR"] += len(competitor_actions) * 3
        scores["COMPETITOR"] += 2 if entities else 0
        scores["COMPETITOR"] += 1 if smart_city_hits else 0
        scores["COMPETITOR"] -= len(competitor_negatives) * 4
    eligible_types = {
        "POLICY": bool(matched["POLICY"] and scope_hits and not headline_is_noise),
        "MARKET": bool(matched["MARKET"] and scope_hits and not headline_is_noise),
        "TECHNOLOGY": bool(matched["TECHNOLOGY"] and scope_hits and not headline_is_noise),
        "COMPETITOR": bool(
            "COMPETITOR" in discovered_types
            and competitor_actions
            and smart_city_hits
            and not competitor_negatives
            and not headline_is_noise
        ),
    }
    eligible_scores = {category: score for category, score in scores.items() if eligible_types[category]}
    ranked = sorted(
        eligible_scores or scores,
        key=lambda category: (-scores[category], _CATEGORY_PRIORITY.index(category)),
    )
    selected = ranked[0]
    best_score = scores[selected]
    runner_up = max((score for category, score in scores.items() if category != selected), default=0)
    margin = best_score - runner_up
    confidence = "HIGH" if best_score >= 6 and margin >= 2 else "MEDIUM" if best_score >= 4 else "LOW"
    if confidence == "LOW" and not eligible_scores and record.get("expected_candidate_type") in discovered_types:
        selected = str(record["expected_candidate_type"])
    return {
        "method": "deterministic-semantic-v1",
        "selected_type": selected,
        "confidence": confidence,
        "review_required": confidence == "LOW",
        "in_scope": bool(eligible_scores),
        "eligible_types": sorted(category for category, eligible in eligible_types.items() if eligible),
        "scores": scores,
        "matched_signals": {
            **matched,
            "COMPETITOR_ACTION": competitor_actions,
            "COMPETITOR_NEGATIVE": competitor_negatives,
            "SMART_CITY_CONTEXT": smart_city_hits,
            "SCOPE_CONTEXT": scope_hits,
            "HEADLINE_SCOPE_CONTEXT": headline_scope_hits,
            "HEADLINE_NOISE": headline_noise_hits,
        },
    }


def deduplicate_and_classify(
    stage_payloads: dict[str, dict[str, Any]], *, max_items_per_type: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deduplicate across News stages and assign one auditable candidate type per article."""
    if max_items_per_type < 1:
        raise ValueError("max_items_per_type must be at least 1")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in stage_payloads.values():
        for record in payload.get("records", []):
            grouped.setdefault(_global_dedupe_key(record), []).append(record)
    classified: list[dict[str, Any]] = []
    reassigned = 0
    duplicate_groups = 0
    for group in grouped.values():
        if len(group) > 1:
            duplicate_groups += 1
        selected = max(
            group,
            key=lambda record: (
                _CONTENT_RANK.get(str(record.get("content_status")), 0),
                len(str(record.get("raw_content", ""))),
                str(record.get("published_at", "")),
            ),
        )
        record = json.loads(json.dumps(selected, ensure_ascii=False))
        discovered_types = {
            str(candidate.get("expected_candidate_type"))
            for candidate in group
            if candidate.get("expected_candidate_type")
        }
        discoveries = []
        for candidate in group:
            evidence = candidate.get("crawl_evidence", {})
            discoveries.append({
                "candidate_type": candidate.get("expected_candidate_type"),
                "query_id": evidence.get("query_id"),
                "query": evidence.get("query"),
                "geography": list(candidate.get("geography", [])),
                "provider": evidence.get("provider"),
                "source_url": candidate.get("source_url"),
                "raw_news_id": candidate.get("raw_news_id"),
            })
        evidence = record.setdefault("crawl_evidence", {})
        evidence["discoveries"] = discoveries
        evidence["source_raw_news_ids"] = sorted({str(item.get("raw_news_id")) for item in group})
        evidence["discovered_candidate_types"] = sorted(discovered_types)
        record["geography"] = sorted({
            str(value) for candidate in group for value in candidate.get("geography", [])
        })
        record["entities"] = list(dict.fromkeys(
            str(value) for candidate in group for value in candidate.get("entities", []) if str(value).strip()
        ))
        classification = _classify_record(record, discovered_types)
        previous_type = str(record.get("expected_candidate_type"))
        selected_type = classification["selected_type"]
        if selected_type != previous_type:
            reassigned += 1
        record["expected_candidate_type"] = selected_type
        record["raw_news_id"] = _raw_id(
            selected_type,
            str(evidence.get("original_title") or record.get("title", "")),
            _global_dedupe_key(record),
        )
        evidence["classification"] = classification
        record["relevance_rationale"] = (
            f"Ứng viên được phân vào {selected_type} bằng bộ phân loại ngữ nghĩa xác định; "
            f"độ tin cậy {classification['confidence']}. Gate 1 vẫn phải quyết định KEEP/EXCLUDE/REVISE."
        )
        classified.append(record)
    in_scope = [
        record for record in classified
        if record.get("crawl_evidence", {}).get("classification", {}).get("in_scope")
    ]
    excluded = [
        record for record in classified
        if not record.get("crawl_evidence", {}).get("classification", {}).get("in_scope")
    ]
    output: list[dict[str, Any]] = []
    for category in _CATEGORY_PRIORITY:
        candidates = [record for record in in_scope if record["expected_candidate_type"] == category]
        candidates.sort(
            key=lambda record: (
                {"HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(
                    record.get("crawl_evidence", {}).get("classification", {}).get("confidence"), 0
                ),
                _CONTENT_RANK.get(str(record.get("content_status")), 0),
                str(record.get("published_at", "")),
            ),
            reverse=True,
        )
        output.extend(candidates[:max_items_per_type])
    counts = {
        category: sum(record["expected_candidate_type"] == category for record in output)
        for category in _CATEGORY_PRIORITY
    }
    return output, {
        "method": "cross-stage-title-day-dedupe-and-deterministic-semantic-v1",
        "input_records": sum(len(payload.get("records", [])) for payload in stage_payloads.values()),
        "unique_candidates_before_cap": len(classified),
        "in_scope_candidates_before_cap": len(in_scope),
        "output_records": len(output),
        "duplicate_groups": duplicate_groups,
        "duplicates_removed": sum(len(group) - 1 for group in grouped.values()),
        "reassigned_records": reassigned,
        "low_confidence_records": sum(
            record.get("crawl_evidence", {}).get("classification", {}).get("confidence") == "LOW"
            for record in output
        ),
        "scope_filtered_records": len(excluded),
        "scope_filtered_raw_news_ids": [record["raw_news_id"] for record in excluded],
        "counts_by_type": counts,
    }


def _stage_rationale(news_type: str) -> str:
    labels = {
        "MARKET": "nhu cầu, đầu tư, mua sắm hoặc triển khai Smart City",
        "COMPETITOR": "hoạt động cạnh tranh, quan hệ đối tác, hợp đồng hoặc triển khai Smart City",
        "TECHNOLOGY": "công nghệ, khả năng tích hợp hoặc mức độ trưởng thành Smart City",
        "POLICY": "chính sách, quy định, tiêu chuẩn hoặc chương trình công liên quan Smart City",
    }
    return f"Ứng viên thuộc nhóm {news_type}; Gate 1 cần kiểm tra mức liên quan đến {labels[news_type]}."


def _raw_record(
    *,
    item: dict[str, str],
    news_type: str,
    spec: QuerySpec,
    provider: str,
    published: datetime,
    collected: datetime,
) -> dict[str, Any]:
    source = _source_name(item)
    channel = "Web Search" if provider == "web" else "RSS"
    discovery_text = item["title"] + " " + item.get("description", "")
    language = "vi" if VIETNAMESE_RE.search(discovery_text) else "zh" if CJK_RE.search(discovery_text) else "en"
    entities = list(dict.fromkeys(spec.entities))
    raw_content = item.get("description") or f"{channel} chỉ cung cấp tiêu đề và thời điểm xuất bản."
    return {
        "synthetic": False,
        "raw_news_id": _raw_id(news_type, item["title"], item["link"]),
        "title": item["title"],
        "source_name": source,
        "source_url": item["link"],
        "published_at": _iso_utc(published),
        "collected_at": _iso_utc(collected),
        "raw_content": raw_content,
        "expected_candidate_type": news_type,
        "geography": [spec.geography],
        "language": language,
        "summary": (
            f"{channel} ghi nhận bản tin từ {source}: “{item['title']}”. "
            "Nội dung đầy đủ chưa được xác minh; reviewer cần mở nguồn trước khi quyết định KEEP."
        ),
        "key_facts": [
            f"{channel} ghi nhận thời điểm xuất bản: {_iso_utc(published)}.",
        ],
        "entities": entities,
        "relevance_rationale": _stage_rationale(news_type),
        "evidence_quality": "LOW",
        "content_status": "METADATA_ONLY",
        "crawl_evidence": {
            "provider": provider,
            "query_id": spec.query_id,
            "query": spec.query,
            "rss_description": item.get("description", ""),
            "discovery_channel": channel,
            "original_title": item["title"],
            "original_language": language,
            "original_rss_description": item.get("description", ""),
            "review_translation_required": language != "vi",
            "translation_status": "PENDING" if language != "vi" else "NOT_REQUIRED",
            "translated_fields": [],
        },
    }


def review_translation_gate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Require complete Vietnamese reviewer fields while retaining source provenance."""
    pending: list[dict[str, Any]] = []
    translated = 0
    not_required = 0
    required = set(REVIEW_TRANSLATION_FIELDS)
    for record in records:
        evidence = record.get("crawl_evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        original_language = str(
            evidence.get("original_language") or record.get("language") or ""
        ).casefold()
        translation_required = bool(
            evidence.get("review_translation_required", original_language != "vi")
        )
        if not translation_required:
            not_required += 1
            continue
        translated_fields = {
            str(value) for value in evidence.get("translated_fields", [])
        }
        missing_fields = sorted(required - translated_fields)
        status = str(evidence.get("translation_status", "PENDING")).upper()
        if status != "COMPLETE" or missing_fields:
            pending.append({
                "raw_news_id": record.get("raw_news_id"),
                "original_language": original_language or "unknown",
                "translation_status": status,
                "missing_fields": missing_fields,
            })
        else:
            translated += 1
    return {
        "status": "PASS" if not pending else "FAIL",
        "required_fields": list(REVIEW_TRANSLATION_FIELDS),
        "translated_records": translated,
        "not_required_records": not_required,
        "pending_records": pending,
    }


def crawl_queries(
    *,
    news_type: str,
    queries: Iterable[QuerySpec],
    days: int,
    timezone_name: str,
    providers: list[str],
    timeout: float,
    max_items: int,
    end_date: date | None = None,
    fetcher: Callable[[str, float], bytes] = fetch_bytes,
    fetch_content: bool = False,
    content_fetcher: Callable[[str, float], PageFetch | tuple[Any, ...] | bytes] = fetch_page,
    content_workers: int = 4,
) -> dict[str, Any]:
    """Discover candidates, audit every provider attempt, and retain the Gate 1 boundary."""
    start, end_exclusive = window_bounds(days=days, timezone_name=timezone_name, end_date=end_date)
    collected = datetime.now(timezone.utc)
    attempts: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    records_by_key: dict[str, dict[str, Any]] = {}
    web_page_cache: dict[str, PageFetch] = {}
    for spec in queries:
        rss_satisfied = False
        for provider in providers:
            if provider in {"bing", "google"} and rss_satisfied:
                continue
            if provider == "web" and "experience" not in spec.query_id:
                continue
            url = provider_url(provider, spec.query, days, spec.geography)
            attempt: dict[str, Any] = {
                "query_id": spec.query_id,
                "provider": provider,
                "url": url,
                "status": "PENDING",
                "discovery_method": "WEB_SEARCH_FETCH" if provider == "web" else "RSS",
                "feed_items": 0,
                "in_window_items": 0,
                "blocked_source_items": 0,
                "fetched_pages": 0,
                "undated_items": 0,
                "page_fetch_failed_items": 0,
                "irrelevant_items": 0,
            }
            try:
                if provider == "web":
                    search_items = parse_web_search(fetcher(url, timeout))[:5]
                    attempt["feed_items"] = len(search_items)
                    for search_item in search_items:
                        if _is_blocked_source(search_item):
                            attempt["blocked_source_items"] += 1
                            continue
                        try:
                            page = _fetch_result(
                                content_fetcher(search_item["link"], timeout),
                                search_item["link"],
                            )
                            attempt["fetched_pages"] += 1
                            parser, paragraphs = _parse_article_page(page)
                            relevance_values = (
                                search_item.get("title", ""),
                                search_item.get("description", ""),
                                parser.meta.get("og:title", ""),
                                parser.meta.get("og:description", ""),
                                parser.meta.get("description", ""),
                                " ".join(paragraphs),
                            )
                            if not _web_experience_candidate_relevant(spec.query_id, *relevance_values):
                                attempt["irrelevant_items"] += 1
                                continue
                            published, date_source = _page_publication_date(parser, page.body)
                            if published is None:
                                attempt["undated_items"] += 1
                                continue
                            if not (start <= published < end_exclusive):
                                continue
                            item = {
                                "title": parser.meta.get("og:title") or search_item["title"],
                                "link": page.final_url,
                                "published": _iso_utc(published),
                                "description": (
                                    parser.meta.get("og:description")
                                    or parser.meta.get("description")
                                    or _excerpt(paragraphs, search_item.get("description", ""))
                                ),
                                "source": parser.meta.get("og:site_name") or _host(page.final_url).removeprefix("www."),
                            }
                            if _is_blocked_source(item):
                                attempt["blocked_source_items"] += 1
                                continue
                            attempt["in_window_items"] += 1
                            key = _dedupe_key(item["title"], item["link"])
                            if key not in records_by_key:
                                record = _raw_record(
                                    item=item,
                                    news_type=news_type,
                                    spec=spec,
                                    provider=provider,
                                    published=published,
                                    collected=collected,
                                )
                                record["crawl_evidence"].update({
                                    "web_search_url": url,
                                    "web_result_url": search_item["link"],
                                    "publication_date_source": date_source,
                                })
                                records_by_key[key] = record
                            web_page_cache[item["link"]] = page
                            web_page_cache[search_item["link"]] = page
                        except Exception as exc:
                            attempt["page_fetch_failed_items"] += 1
                            errors.append({
                                "query_id": spec.query_id,
                                "provider": provider,
                                "source_url": search_item.get("link"),
                                "error": f"{type(exc).__name__}: {exc}",
                            })
                else:
                    feed_items = parse_rss(fetcher(url, timeout))
                    attempt["feed_items"] = len(feed_items)
                    for item in feed_items:
                        published = _parse_feed_date(item["published"])
                        if published is None or not (start <= published < end_exclusive):
                            continue
                        attempt["in_window_items"] += 1
                        if _is_blocked_source(item):
                            attempt["blocked_source_items"] += 1
                            continue
                        key = _dedupe_key(item["title"], item["link"])
                        if key not in records_by_key:
                            records_by_key[key] = _raw_record(
                                item=item,
                                news_type=news_type,
                                spec=spec,
                                provider=provider,
                                published=published,
                                collected=collected,
                            )
                attempt["status"] = "SUCCESS"
            except (ET.ParseError, UnicodeError, ValueError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, socket.timeout) as exc:
                attempt["status"] = "FAILED"
                attempt["error"] = f"{type(exc).__name__}: {exc}"
                errors.append({
                    "query_id": spec.query_id,
                    "provider": provider,
                    "error": attempt["error"],
                })
            attempts.append(attempt)
            if provider in {"bing", "google"} and attempt["status"] == "SUCCESS" and attempt["in_window_items"] > 0:
                rss_satisfied = True
    records = sorted(
        records_by_key.values(),
        key=lambda item: (item["published_at"], item["raw_news_id"]),
        reverse=True,
    )[:max_items]
    if content_workers < 1:
        raise ValueError("content_workers must be at least 1")
    if fetch_content and records:
        def cached_content_fetcher(url: str, fetch_timeout: float) -> PageFetch | tuple[Any, ...] | bytes:
            return web_page_cache.get(url) or content_fetcher(url, fetch_timeout)

        with ThreadPoolExecutor(max_workers=min(content_workers, len(records))) as executor:
            records = list(executor.map(
                lambda record: _enrich_record(
                    record, timeout=timeout, content_fetcher=cached_content_fetcher,
                    resolution_fetcher=fetcher,
                ),
                records,
            ))
    content_status_counts = {
        status: sum(record["content_status"] == status for record in records)
        for status in ("FULL_TEXT", "PARTIAL_TEXT", "METADATA_ONLY", "UNAVAILABLE")
    }
    return {
        "dataset_name": f"WR3 live {news_type} news candidates",
        "synthetic": False,
        "news_type": news_type,
        "timezone": timezone_name,
        "window_start": _iso_utc(start),
        "window_end_exclusive": _iso_utc(end_exclusive),
        "records": records,
        "crawl_audit": {
            "query_count": len({attempt["query_id"] for attempt in attempts}),
            "attempt_count": len(attempts),
            "successful_attempts": sum(attempt["status"] == "SUCCESS" for attempt in attempts),
            "failed_attempts": sum(attempt["status"] == "FAILED" for attempt in attempts),
            "web_search_attempts": sum(attempt["provider"] == "web" for attempt in attempts),
            "web_search_successful_attempts": sum(
                attempt["provider"] == "web" and attempt["status"] == "SUCCESS"
                for attempt in attempts
            ),
            "web_search_result_items": sum(
                attempt["feed_items"] for attempt in attempts if attempt["provider"] == "web"
            ),
            "web_search_fetched_pages": sum(
                attempt["fetched_pages"] for attempt in attempts if attempt["provider"] == "web"
            ),
            "web_search_undated_items": sum(
                attempt["undated_items"] for attempt in attempts if attempt["provider"] == "web"
            ),
            "web_search_page_fetch_failed_items": sum(
                attempt["page_fetch_failed_items"] for attempt in attempts if attempt["provider"] == "web"
            ),
            "web_search_irrelevant_items": sum(
                attempt["irrelevant_items"] for attempt in attempts if attempt["provider"] == "web"
            ),
            "web_search_retained_records": sum(
                record.get("crawl_evidence", {}).get("provider") == "web"
                for record in records
            ),
            "blocked_source_count": sum(attempt["blocked_source_items"] for attempt in attempts),
            "blocked_source_names": sorted(BLOCKED_SOURCE_NAMES),
            "blocked_source_hosts": sorted(BLOCKED_SOURCE_HOSTS),
            "record_count": len(records),
            "content_fetch_enabled": fetch_content,
            "content_status_counts": content_status_counts,
            "resolved_source_count": sum(
                record.get("crawl_evidence", {}).get("resolution_status") == "RESOLVED"
                for record in records
            ),
            "content_fetch_failed_count": sum(
                record.get("crawl_evidence", {}).get("resolution_status") == "FAILED"
                for record in records
            ),
            "attempts": attempts,
            "errors": errors,
        },
        "phase_boundary": {
            "signal_extraction_performed": False,
            "ot_evaluation_performed": False,
            "human_relevance_review_required": True,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
