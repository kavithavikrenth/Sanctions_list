#!/usr/bin/env python3
"""
src/scraper.py

A small, general-purpose web scraper for extracting structured data from a sanctions list page.
This starter script:
- fetches a URL
- tries to parse an HTML table (preferred)
- falls back to parsing list items (<li>) if no table present
- writes results to a JSON file

Usage:
  python src/scraper.py --url https://example.com/sanctions --output data.json

Dependencies: requests, beautifulsoup4

Keep this file minimal and adapt parsing logic to the specific sanctions source you target.
"""

from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("scraper")


def fetch(url: str, timeout: int = 10) -> str:
    """Fetch the raw HTML for a URL.

    Raises requests.HTTPError on bad status codes.
    """
    logger.info("Fetching %s", url)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_html(html: str) -> List[Dict[str, Any]]:
    """Parse HTML and return a list of records.

    Strategy:
    - If the page contains a <table>, parse rows into dicts (use <th> as headers if present).
    - Otherwise, collect text from <li> elements as individual records.
    - This is a starter heuristic — adapt to the target site for production use.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, Any]] = []

    table = soup.find("table")
    if table:
        logger.info("Found a table — attempting to parse rows")
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue
            texts = [c.get_text(strip=True) for c in cells]
            if headers and len(headers) == len(texts):
                row = {headers[i]: texts[i] for i in range(len(texts))}
            else:
                # fallback: index-based keys
                row = {f"col_{i}": texts[i] for i in range(len(texts))}
            results.append(row)
        return results

    # fallback: list items
    lis = soup.find_all("li")
    if lis:
        logger.info("No table found — parsing %d <li> elements", len(lis))
        for li in lis:
            text = li.get_text(" ", strip=True)
            if text:
                results.append({"text": text})
        return results

    # last resort: try to extract paragraphs with likely names or lines
    ps = [p.get_text(strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    if ps:
        logger.info("No table or list — parsing %d <p> elements", len(ps))
        for p in ps:
            results.append({"text": p})
        return results

    logger.warning("No obvious data structures found on page — returning empty list")
    return results


def save_json(data: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d records to %s", len(data), out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Small scraper for sanctions list pages")
    parser.add_argument("--url", required=True, help="Page URL to scrape")
    parser.add_argument("--output", default="data/sanctions.json", help="JSON file to write results to")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds")
    args = parser.parse_args()

    try:
        html = fetch(args.url, timeout=args.timeout)
    except requests.RequestException as e:
        logger.error("Failed to fetch URL: %s", e)
        raise SystemExit(1)

    data = parse_html(html)
    save_json(data, Path(args.output))


if __name__ == "__main__":
    main()