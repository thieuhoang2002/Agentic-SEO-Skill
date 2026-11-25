#!/usr/bin/env python3
"""Generate an llms.txt (and optional llms-full.txt) draft from site metadata and priority URLs."""

from __future__ import annotations

import argparse
import json
import re
from urllib.parse import urlparse

from seo_common import fetch_url, normalize_url, parse_html, read_urls


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_text(text: str | None, single_line: bool = True, max_len: int = 0) -> str:
    """Strip ANSI/C0 control characters and optionally collapse lines."""
    if not text:
        return ""
    cleaned = ANSI_ESCAPE_RE.sub("", str(text))
    cleaned = CONTROL_CHARS_RE.sub(" ", cleaned)
    if single_line:
        cleaned = re.sub(r"[\r\n]+", " ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    else:
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n").strip()
    if max_len > 0:
        cleaned = cleaned[:max_len].strip()
    return cleaned


def _escape_markdown_inline(text: str) -> str:
    """Escape characters that break Markdown headings, blockquotes, or link labels."""
    escaped = _sanitize_text(text, single_line=True)
    for ch in ("\\", "[", "]", "(", ")", "#", ">"):
        escaped = escaped.replace(ch, f"\\{ch}")
    return escaped


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def page_details(url: str, timeout: int, include_body: bool = False) -> tuple[str, str, str]:
    if not _is_http_url(url):
        return urlparse(url).path.strip("/") or url, "", ""
    fetched = fetch_url(url, timeout=timeout, max_bytes=1_000_000)
    if fetched.get("text") and "html" in fetched.get("headers", {}).get("content-type", "").lower():
        html = parse_html(fetched["text"], fetched.get("url") or url)
        title = _sanitize_text(html.get("title"), single_line=True, max_len=200) or urlparse(url).path.strip("/") or url
        desc = _sanitize_text(html.get("meta_description"), single_line=True, max_len=500)
        body = _sanitize_text(html.get("body_text"), single_line=True, max_len=3000) if include_body else ""
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
    if not _is_http_url(site):
        raise ValueError(f"Unsupported or invalid site URL: {site}")

    if not title or not description:
        fetched = fetch_url(site, timeout=timeout, max_bytes=1_000_000)
        if fetched.get("text"):
            html = parse_html(fetched["text"], fetched.get("url") or site)
            title = title or html.get("title") or urlparse(site).netloc
            description = description or html.get("meta_description") or f"Official information and priority pages for {urlparse(site).netloc}."

    safe_title = _escape_markdown_inline(title or urlparse(site).netloc)
    safe_desc = _escape_markdown_inline(
        description or f"Official information and priority pages for {urlparse(site).netloc}."
    )

    links = []
    skipped_urls = []
    full_sections = [f"# {safe_title} — Full Context", "", f"> {safe_desc}", ""]

    for raw_url in urls:
        norm_url = normalize_url(raw_url, site)
        if not _is_http_url(norm_url):
            skipped_urls.append(raw_url)
            continue

        if fetch_titles or full:
            label, desc, body = page_details(norm_url, timeout, include_body=full)
        else:
            label, desc, body = (urlparse(norm_url).path.strip("/") or "Home", "", "")

        safe_label = _escape_markdown_inline(label)
        safe_link_desc = _escape_markdown_inline(desc)
        links.append({"title": label, "url": norm_url, "description": desc})

        if full:
            full_sections.append(f"## {safe_label}")
            full_sections.append(f"URL: {norm_url}")
            if safe_link_desc:
                full_sections.append(f"Summary: {safe_link_desc}")
            if body:
                # Neutralize leading markdown headings/quotes inside extracted body text
                safe_body = body.replace("#", "").replace(">", "")
                full_sections.extend(["", safe_body])
            full_sections.append("")

    lines = [f"# {safe_title}", "", f"> {safe_desc}", "", "## Priority pages"]
    for link in links:
        link_label = _escape_markdown_inline(link["title"])
        link_desc = _escape_markdown_inline(link["description"])
        suffix = f": {link_desc}" if link_desc else ""
        lines.append(f"- [{link_label}]({link['url']}){suffix}")
    lines.extend(["", "## Notes", "- Use these URLs as the preferred starting points for understanding this site."])
    text = "\n".join(lines) + "\n"

    result: dict = {"site": site, "count": len(links), "llms_txt": text, "links": links}
    if skipped_urls:
        result["skipped_urls"] = skipped_urls
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
