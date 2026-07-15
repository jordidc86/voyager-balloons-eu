#!/usr/bin/env python3
"""Crawl Voyager Balloons' public sites and emit a technical SEO report."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urldefrag, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup


SITEMAPS = (
    "https://www.voyagerballoons.eu/sitemap_index.xml",
    "https://shop.voyagerballoons.eu/wp-sitemap.xml",
)
ALLOWED_HOSTS = {
    "voyagerballoons.eu",
    "www.voyagerballoons.eu",
    "shop.voyagerballoons.eu",
}
SKIP_PATH_PARTS = (
    "/wp-admin/",
    "/wp-json/",
    "/wp-login.php",
    "/feed/",
)
SKIP_QUERY_KEYS = {
    "add-to-cart",
    "remove_item",
    "wc-ajax",
    "orderby",
    "filter_",
    "min_price",
    "max_price",
}
HTML_TYPES = ("text/html", "application/xhtml+xml")


def normalize_url(raw: str, base: str | None = None) -> str | None:
    if not raw:
        return None
    raw = unescape(raw.strip())
    if raw.startswith(("mailto:", "tel:", "javascript:", "data:", "sms:", "whatsapp:")):
        return None
    absolute = urljoin(base or "", raw)
    absolute, _ = urldefrag(absolute)
    parsed = urlsplit(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = parsed.netloc.lower()
    if host.endswith(":80") and parsed.scheme == "http":
        host = host[:-3]
    if host.endswith(":443") and parsed.scheme == "https":
        host = host[:-4]
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key in SKIP_QUERY_KEYS or any(key.startswith(prefix) for prefix in SKIP_QUERY_KEYS):
            continue
        query_pairs.append((key, value))
    return urlunsplit((parsed.scheme.lower(), host, path, urlencode(query_pairs), ""))


def is_internal(url: str) -> bool:
    return urlsplit(url).netloc.lower() in ALLOWED_HOSTS


def should_crawl(url: str) -> bool:
    parsed = urlsplit(url)
    if not is_internal(url):
        return False
    if any(part in parsed.path for part in SKIP_PATH_PARTS):
        return False
    if parsed.path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".pdf", ".zip", ".xml", ".txt", ".css", ".js", ".woff", ".woff2")):
        return False
    return True


def fetch(session: requests.Session, url: str, timeout: float) -> requests.Response:
    # Keep the audit polite and retry transient rate limits. A 429 during a
    # fast crawl is a crawler artefact, not evidence that a public URL is dead.
    time.sleep(0.15)
    response = session.get(url, timeout=timeout, allow_redirects=True, stream=False)
    for attempt in range(3):
        if response.status_code not in {429, 502, 503, 504}:
            break
        retry_after = response.headers.get("retry-after", "")
        delay = float(retry_after) if retry_after.isdigit() else 1.5 * (attempt + 1)
        time.sleep(min(delay, 8))
        response = session.get(url, timeout=timeout, allow_redirects=True, stream=False)
    return response


def sitemap_urls(session: requests.Session, seeds: tuple[str, ...], timeout: float) -> tuple[list[str], list[dict[str, Any]]]:
    pending = deque(seeds)
    seen: set[str] = set()
    pages: set[str] = set()
    audits: list[dict[str, Any]] = []

    while pending:
        url = pending.popleft()
        if url in seen:
            continue
        seen.add(url)
        started = time.perf_counter()
        try:
            response = fetch(session, url, timeout)
            elapsed = round(time.perf_counter() - started, 3)
            item = {
                "url": url,
                "status": response.status_code,
                "final_url": response.url,
                "elapsed_s": elapsed,
                "error": None,
            }
            if response.status_code >= 400:
                audits.append(item)
                continue
            root = ElementTree.fromstring(response.content)
            tag = root.tag.rsplit("}", 1)[-1]
            locs = [node.text.strip() for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "loc" and node.text]
            item["type"] = tag
            item["entries"] = len(locs)
            audits.append(item)
            if tag == "sitemapindex":
                pending.extend(locs)
            elif tag == "urlset":
                for loc in locs:
                    normalized = normalize_url(loc)
                    if normalized and should_crawl(normalized):
                        pages.add(normalized)
        except Exception as exc:  # network/XML errors are report data
            audits.append({
                "url": url,
                "status": None,
                "final_url": None,
                "elapsed_s": round(time.perf_counter() - started, 3),
                "error": str(exc),
            })
    return sorted(pages), audits


def attr_content(soup: BeautifulSoup, name: str, attr: str = "name") -> str | None:
    node = soup.find("meta", attrs={attr: re.compile(rf"^{re.escape(name)}$", re.I)})
    value = node.get("content", "").strip() if node else ""
    return value or None


def audit_html(response: requests.Response) -> tuple[dict[str, Any], list[dict[str, str]]]:
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    description = attr_content(soup, "description")
    robots = attr_content(soup, "robots")
    canonical_node = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical = normalize_url(canonical_node.get("href", ""), response.url) if canonical_node else None
    h1s = [node.get_text(" ", strip=True) for node in soup.find_all("h1")]
    schema_errors: list[str] = []
    schema_types: list[str] = []
    for node in soup.find_all("script", attrs={"type": re.compile(r"application/ld\+json", re.I)}):
        raw = node.string or node.get_text()
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
            stack = [data]
            while stack:
                current = stack.pop()
                if isinstance(current, dict):
                    value = current.get("@type")
                    if isinstance(value, str):
                        schema_types.append(value)
                    elif isinstance(value, list):
                        schema_types.extend(str(item) for item in value)
                    stack.extend(current.values())
                elif isinstance(current, list):
                    stack.extend(current)
        except Exception as exc:
            schema_errors.append(str(exc))

    links: list[dict[str, str]] = []
    for node in soup.find_all("a", href=True):
        target = normalize_url(node.get("href", ""), response.url)
        if not target:
            continue
        links.append({
            "target": target,
            "text": node.get_text(" ", strip=True)[:240],
            "rel": " ".join(node.get("rel", [])) if isinstance(node.get("rel"), list) else str(node.get("rel", "")),
        })

    return ({
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": description,
        "meta_description_length": len(description) if description else 0,
        "canonical": canonical,
        "robots": robots,
        "h1_count": len(h1s),
        "h1": h1s[:3],
        "schema_types": sorted(set(schema_types)),
        "schema_errors": schema_errors,
        "link_count": len(links),
    }, links)


def crawl(max_pages: int, timeout: float) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "VoyagerBalloonsTechnicalAudit/1.0 (+https://www.voyagerballoons.eu/)"
    })
    seeded, sitemaps = sitemap_urls(session, SITEMAPS, timeout)
    pending = deque(seeded)
    queued = set(seeded)
    pages: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    while pending and len(pages) < max_pages:
        requested = pending.popleft()
        started = time.perf_counter()
        record: dict[str, Any] = {"url": requested}
        try:
            response = fetch(session, requested, timeout)
            record.update({
                "status": response.status_code,
                "final_url": normalize_url(response.url),
                "elapsed_s": round(time.perf_counter() - started, 3),
                "content_type": response.headers.get("content-type", "").split(";", 1)[0].lower(),
                "redirect_chain": [
                    {"status": item.status_code, "url": normalize_url(item.url), "location": item.headers.get("location")}
                    for item in response.history
                ],
                "error": None,
            })
            if response.status_code < 400 and record["content_type"] in HTML_TYPES:
                html_audit, links = audit_html(response)
                record.update(html_audit)
                for link in links:
                    edge = {"source": requested, **link}
                    edges.append(edge)
                    target = link["target"]
                    if should_crawl(target) and target not in queued and len(queued) < max_pages * 3:
                        queued.add(target)
                        pending.append(target)
        except Exception as exc:
            record.update({
                "status": None,
                "final_url": None,
                "elapsed_s": round(time.perf_counter() - started, 3),
                "content_type": None,
                "redirect_chain": [],
                "error": str(exc),
            })
        pages[requested] = record

    inbound: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if is_internal(edge["target"]):
            inbound[edge["target"]].append(edge["source"])

    broken = []
    redirects = []
    for url, page in pages.items():
        sources = sorted(set(inbound.get(url, [])))
        if page.get("status") is None or page.get("status", 0) >= 400:
            broken.append({
                "url": url,
                "status": page.get("status"),
                "error": page.get("error"),
                "linked_from": sources,
            })
        if page.get("redirect_chain"):
            redirects.append({
                "url": url,
                "final_url": page.get("final_url"),
                "hops": page["redirect_chain"],
                "linked_from": sources,
            })

    html_pages = [page for page in pages.values() if page.get("content_type") in HTML_TYPES and page.get("status", 999) < 400]
    issues = {
        "missing_title": [page["url"] for page in html_pages if not page.get("title")],
        "missing_meta_description": [page["url"] for page in html_pages if not page.get("meta_description")],
        "short_meta_description": [page["url"] for page in html_pages if 0 < page.get("meta_description_length", 0) < 70],
        "long_meta_description": [page["url"] for page in html_pages if page.get("meta_description_length", 0) > 165],
        "missing_canonical": [page["url"] for page in html_pages if not page.get("canonical")],
        "noindex": [page["url"] for page in html_pages if "noindex" in (page.get("robots") or "").lower()],
        "h1_not_one": [page["url"] for page in html_pages if page.get("h1_count") != 1],
        "schema_json_errors": [page["url"] for page in html_pages if page.get("schema_errors")],
        "slow_over_2s": [page["url"] for page in html_pages if page.get("elapsed_s", 0) > 2],
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sitemaps": sitemaps,
        "sitemap_page_count": len(seeded),
        "pages": pages,
        "page_count": len(pages),
        "html_page_count": len(html_pages),
        "edge_count": len(edges),
        "internal_edge_count": sum(1 for edge in edges if is_internal(edge["target"])),
        "external_edge_count": sum(1 for edge in edges if not is_internal(edge["target"])),
        "broken": broken,
        "redirects": redirects,
        "issues": issues,
        "status_counts": dict(sorted(Counter(str(page.get("status")) for page in pages.values()).items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/voyager-technical-crawl.json")
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()

    report = crawl(args.max_pages, args.timeout)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "output": str(output),
        "sitemap_pages": report["sitemap_page_count"],
        "crawled_pages": report["page_count"],
        "html_pages": report["html_page_count"],
        "internal_edges": report["internal_edge_count"],
        "broken_targets": len(report["broken"]),
        "redirect_targets": len(report["redirects"]),
        "status_counts": report["status_counts"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if report["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
