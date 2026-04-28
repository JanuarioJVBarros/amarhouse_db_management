import argparse
import json
import logging
import re
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

import requests

from .crawler import AronlightCrawler
from .parser import AronlightParser
from .urls import BASE_URL, SKU_START_URLS

logger = logging.getLogger(__name__)

SKU_PATTERN = re.compile(r"\b(?:ILAR|ILDV)-\d+\b", re.IGNORECASE)
FILE_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".zip", ".rar")

DEFAULT_SKUS = [
    "ILAR-01013",
    "ILAR-01014",
    "ILAR-02538",
    "ILAR-02539",
    "ILAR-02540",
    "ILAR-02541",
    "ILAR-02952",
    "ILAR-02953",
    "ILAR-02164",
    "ILAR-02719",
    "ILAR-02718",
    "ILAR-02717",
    "ILAR-02885",
    "ILDV-00044",
    "ILDV-01139",
    "ILDV-00045",
    "ILAR-01447",
    "ILAR-02608",
    "ILAR-01993",
    "ILAR-02609",
    "ILAR-01615",
    "ILAR-02610",
    "ILAR-03010",
    "ILAR-01900",
    "ILAR-01901",
    "ILAR-02021",
    "ILAR-01904",
    "ILAR-01905",
    "ILAR-03013",
    "ILAR-03014",
]


def normalize_sku(value):
    return str(value or "").strip().upper()


def load_skus(path=None):
    if not path:
        return DEFAULT_SKUS

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [normalize_sku(line) for line in lines if normalize_sku(line)]


def sku_hits_in_text(text, wanted_skus):
    wanted = wanted_skus if isinstance(wanted_skus, set) else {normalize_sku(sku) for sku in wanted_skus}
    found = []
    for match in SKU_PATTERN.findall(text or ""):
        normalized = normalize_sku(match)
        if normalized in wanted and normalized not in found:
            found.append(normalized)
    return found


def analyze_page(url, html, wanted_skus):
    parser = AronlightParser(html)
    page_text = parser.soup.get_text(" ", strip=True)
    title = parser.page_title() or url
    link_entries = parser.link_entries(url)

    matches = {}

    for sku in sku_hits_in_text(page_text, wanted_skus):
        matches.setdefault(sku, []).append(
            {
                "source_url": url,
                "page_title": title,
                "match_type": "page_text",
            }
        )

    for entry in link_entries:
        # For drivers and accessories, the SKU often appears only in the
        # datasheet link rather than the visible product copy.
        combined = " ".join(filter(None, [entry.get("href"), entry.get("text"), entry.get("title")]))
        for sku in sku_hits_in_text(combined, wanted_skus):
            matches.setdefault(sku, []).append(
                {
                    "source_url": url,
                    "page_title": title,
                    "match_type": "link_reference",
                    "link_url": entry.get("href"),
                    "link_text": entry.get("text"),
                }
            )

    next_links = []
    base_netloc = urlparse(BASE_URL).netloc
    for entry in link_entries:
        href = entry.get("href")
        if not href:
            continue
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != base_netloc:
            continue
        if parsed.path.lower().endswith(FILE_EXTENSIONS):
            continue
        next_links.append(href)

    return matches, sorted(set(next_links))


def dedupe_matches(match_entries):
    deduped = []
    seen = set()
    for entry in match_entries:
        key = (
            entry.get("source_url"),
            entry.get("page_title"),
            entry.get("match_type"),
            entry.get("link_url"),
            entry.get("link_text"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def crawl_for_sku_references(start_urls, wanted_skus, crawler=None, max_pages=200):
    crawler = crawler or AronlightCrawler()
    queue = deque(start_urls)
    visited = set()
    normalized_wanted_skus = {normalize_sku(sku) for sku in wanted_skus}
    results = {sku: [] for sku in normalized_wanted_skus}

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        normalized_url = url.rstrip("/") + "/"
        if normalized_url in visited:
            continue
        visited.add(normalized_url)

        logger.info("[aronlight-sku-ref] [%s/%s] Inspecting %s", len(visited), max_pages, normalized_url)
        try:
            html = crawler.fetch(normalized_url)
        except requests.RequestException as exc:
            logger.warning("[aronlight-sku-ref] [SKIP] Failed to fetch %s: %s", normalized_url, exc)
            continue

        page_matches, next_links = analyze_page(normalized_url, html, normalized_wanted_skus)
        for sku, entries in page_matches.items():
            results.setdefault(sku, []).extend(entries)

        for link in next_links:
            normalized_link = link.rstrip("/") + "/"
            if normalized_link not in visited:
                queue.append(normalized_link)

    # Returning both matches and missing SKUs makes this script useful as an
    # audit artifact, not just a raw crawler result.
    cleaned = {sku: dedupe_matches(entries) for sku, entries in results.items() if entries}
    missing = sorted(normalized_wanted_skus - set(cleaned))
    return {
        "matches": cleaned,
        "missing_skus": missing,
        "visited_pages": len(visited),
    }


def save_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Crawl Aronlight pages and datasheet links to find where target SKUs are referenced.",
    )
    cli.add_argument("--sku-file", help="Optional text file with one SKU per line.")
    cli.add_argument(
        "--output-file",
        default="aronlight_sku_references.json",
        help="JSON file to write the SKU reference matches.",
    )
    cli.add_argument(
        "--report-file",
        default="aronlight_sku_reference_report.json",
        help="JSON file to write the summary report.",
    )
    cli.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum number of Aronlight HTML pages to crawl.",
    )
    cli.add_argument(
        "--start-url",
        action="append",
        dest="start_urls",
        help="Override default start URL(s). Can be passed multiple times.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    wanted_skus = load_skus(args.sku_file)
    start_urls = args.start_urls or SKU_START_URLS
    result = crawl_for_sku_references(start_urls, wanted_skus, max_pages=args.max_pages)

    save_json(args.output_file, result["matches"])
    save_json(
        args.report_file,
        {
            "found_skus": sorted(result["matches"]),
            "missing_skus": result["missing_skus"],
            "visited_pages": result["visited_pages"],
        },
    )

    print(f"Found SKUs: {len(result['matches'])}")
    print(f"Missing SKUs: {len(result['missing_skus'])}")
    print(f"Visited pages: {result['visited_pages']}")
    return result


if __name__ == "__main__":
    main()
