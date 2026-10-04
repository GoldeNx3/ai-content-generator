"""Discover evidence linked from article content; never crawl navigation or recurse."""

import ipaddress
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from app.services.research.search import SearchResult
from app.services.research.urls import normalize_url

_UTILITY_PATH = re.compile(
    r"(^|/)(privacy|terms|cookies?|careers|contact|about|login|signin|signup|subscribe|search|tags?|category|authors?)(/|$)",
    re.IGNORECASE,
)


def _content_root(html: str):
    soup = BeautifulSoup(html, "html.parser")
    # Prune assets before serialization so scripts cannot consume the retained-HTML budget.
    for node in soup.select("script, style, svg, canvas, template, noscript"):
        node.decompose()
    root = (soup.select_one('[itemprop="articleBody"], [role="main"], .uni-article__body, .article-body, .post-content')
            or soup.find("article") or soup.find("main") or soup.body or soup)
    for node in root.select("nav, header, footer, aside, form, [role=navigation]"):
        node.decompose()
    for node in list(root.find_all(["div", "section", "ul"])):
        if node.attrs is None:
            continue
        attrs = " ".join([node.get("id", ""), *node.get("class", [])])
        if re.search(r"(^|[\s_-])(nav|footer|sidebar|related|recommend|social|share|cookie)([\s_-]|$)", attrs, re.I):
            node.decompose()
    return root


def compact_source_html(html: str, max_chars: int, base_url: str | None = None) -> str:
    """Retain editorial markup for diagnostics and link discovery, without large UI assets."""
    if not html:
        return ""
    root = _content_root(html)
    if base_url:
        for anchor in root.find_all("a", href=True):
            href = str(anchor["href"]).strip()
            if href.startswith("#"):
                continue
            try:
                absolute = urljoin(base_url, href)
                if normalize_url(absolute) == normalize_url(base_url):
                    del anchor["href"]
                    continue
                anchor["href"] = absolute
            except ValueError:
                del anchor["href"]
    return str(root)[:max(0, max_chars)]


def discover_article_links(html: str, article_url: str) -> list[SearchResult]:
    root = _content_root(html)
    seen = {normalize_url(article_url)}
    results = []
    for anchor in root.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if not href or href.startswith("#"):
            continue
        try:
            url = urljoin(article_url, href)
            parsed = urlsplit(url)
            key = normalize_url(url)
        except ValueError:
            continue
        host = parsed.hostname or ""
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            continue
        if "." not in host or host.endswith((".local", ".internal", ".localhost")):
            continue
        try:
            if not ipaddress.ip_address(host).is_global:
                continue
        except ValueError:
            pass
        if not parsed.path.strip("/") or _UTILITY_PATH.search(parsed.path):
            continue
        # Binary/media targets are not evidence our text extractor can read.
        if re.search(r"\.(pdf|png|jpe?g|gif|webp|mp4|zip|exe)$", parsed.path, re.I):
            continue
        url = urlunsplit(parsed._replace(fragment=""))
        if key in seen:
            continue
        title = anchor.get_text(" ", strip=True)
        if not title:
            continue
        seen.add(key)
        results.append(SearchResult(title=title, url=url, snippet="Linked from the original article"))
    return results
