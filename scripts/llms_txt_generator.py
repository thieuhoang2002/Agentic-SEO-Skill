#!/usr/bin/env python3
"""Generate an llms.txt draft from site metadata and priority URLs."""

from __future__ import annotations

import argparse
import json
from urllib.parse import urlparse

from seo_common import fetch_url, normalize_url, parse_html, read_urls


def page_details(url: str, timeout: int, include_body: bool = False) -> tuple[str, str, str]:
    fetched = fetch_url(url, timeout=timeout, max_bytes=1_000_000)
    if fetched.get("text") and "html" in fetched.get("headers", {}).get("content-type", ""):
        html = parse_html(fetched["text"], fetched.get("url") or url)
        title = html.get("title") or urlparse(url).path.strip("/") or url
        desc = html.get("meta_description") or ""
        body = (html.get("text") or "").strip()[:3000] if include_body else ""
        return title, desc, body
    return urlparse(url).path.strip("/") or url, "", ""


def page_title(url: str, timeout: int) -> tuple[str, str]:
    title, desc, _ = page_details(url, timeout, include_body=False)
    return title, desc


def generate(
    site: str,
    urls: list[str],
    title: str | None = None,
    description: str | None = None,
    timeout: int = 15,
    fetch_titles: bool = False,
    full: bool = False,
) -> dict:
    site = normalize_url(site)
    if not title or not description:
        fetched = fetch_url(site, timeout=timeout, max_bytes=1_000_000)
        if fetched.get("text"):
            html = parse_html(fetched["text"], fetched.get("url") or site)
            title = title or html.get("title") or urlparse(site).netloc
            description = description or html.get("meta_description") or f"Official information and priority pages for {urlparse(site).netloc}."
    title = title or urlparse(site).netloc
    description = description or f"Official information and priority pages for {urlparse(site).netloc}."

    links = []
    full_sections = [f"# {title} — Full Context", "", f"> {description}", ""]
    for url in urls:
        norm_url = normalize_url(url, site)
        if fetch_titles or full:
            label, desc, body = page_details(url, timeout, include_body=full)
        else:
            label, desc, body = (urlparse(url).path.strip("/") or "Home", "", "")
        links.append({"title": label, "url": norm_url, "description": desc})
        if full:
            full_sections.append(f"## {label}")
            full_sections.append(f"URL: {norm_url}")
            if desc:
                full_sections.append(f"Summary: {desc}")
            if body:
                full_sections.extend(["", body])
            full_sections.append("")

    lines = [f"# {title}", "", f"> {description}", "", "## Priority pages"]
    for link in links:
        suffix = f": {link['description']}" if link["description"] else ""
        lines.append(f"- [{link['title']}]({link['url']}){suffix}")
    lines.extend(["", "## Notes", "- Use these URLs as the preferred starting points for understanding this site."])
    text = "\n".join(lines) + "\n"
    result = {"site": site, "count": len(links), "llms_txt": text, "links": links}
    if full:
        result["llms_full_txt"] = "\n".join(full_sections).strip() + "\n"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a draft llms.txt (and optional llms-full.txt)")
    parser.add_argument("site")
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--url-file")
    parser.add_argument("--title")
    parser.add_argument("--description")
    parser.add_argument("--fetch-titles", action="store_true")
    parser.add_argument("--full", action="store_true", help="Also generate llms-full.txt content from fetched pages")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--json", "-j", action="store_true")
    args = parser.parse_args()
    urls = read_urls(args.urls, args.url_file) or [args.site]
    result = generate(args.site, urls, args.title, args.description, args.timeout, args.fetch_titles, args.full)
    if args.json:
        print(json.dumps(result, indent=2))
    elif args.full:
        print(result["llms_txt"])
        print("--- llms-full.txt ---")
        print(result["llms_full_txt"])
    else:
        print(result["llms_txt"])


if __name__ == "__main__":
    main()
