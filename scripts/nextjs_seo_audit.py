#!/usr/bin/env python3
"""
Code-level SEO & GEO Auditor for Next.js App Router projects.

Inspects a local Next.js repository (`app/` or `src/app/`, `next.config.*`)
before deployment to catch framework-specific SEO/GEO pitfalls that external
URL crawlers miss:
- `'use client'` directives on `page.*` hurting SSR / AI crawler visibility
- Missing `metadataBase`, `metadata`, `generateMetadata`, or `alternates.canonical`
- Dynamic routes missing `generateStaticParams` / `revalidate`
- `robots.ts` failing to disallow discovered CMS/admin/affiliate redirect routes
  or missing explicit AI crawler directives (GPTBot, ClaudeBot, PerplexityBot)
- Missing `/llms.txt` or `/llms-full.txt` routes/files
- Root JSON-LD lacking `@graph` or missing structured data
- Affiliate / redirect links missing `rel="sponsored"` / `nofollow`
- `<img>` / `<Image>` tags missing `alt` attributes
- `next.config.*` missing defensive security headers or modern image formats

Usage:
    python scripts/nextjs_seo_audit.py /path/to/nextjs-app
    python scripts/nextjs_seo_audit.py /path/to/nextjs-app --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


AI_CRAWLERS = ("GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot", "Google-Extended")
SENSITIVE_ROUTE_HINTS = ("admin", "cms", "dashboard", "vault", "auth", "login", "go")
SECURITY_HEADER_KEYS = (
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
)

PAGE_NAMES = {"page.tsx", "page.ts", "page.jsx", "page.js"}
LAYOUT_NAMES = {"layout.tsx", "layout.ts", "layout.jsx", "layout.js"}
ROBOTS_NAMES = ("app/robots.ts", "app/robots.js", "src/app/robots.ts", "src/app/robots.js")
SITEMAP_NAMES = ("app/sitemap.ts", "app/sitemap.js", "src/app/sitemap.ts", "src/app/sitemap.js")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _find_app_dir(root: Path) -> Path | None:
    for candidate in (root / "app", root / "src" / "app"):
        if candidate.is_dir():
            return candidate
    return None


def _find_next_config(root: Path) -> Path | None:
    for name in ("next.config.ts", "next.config.mjs", "next.config.js", "next.config.cjs"):
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _route_from_file(file_path: Path, app_dir: Path) -> str:
    rel_parent = file_path.parent.relative_to(app_dir).as_posix()
    if rel_parent == ".":
        return "/"
    segments = [seg for seg in rel_parent.split("/") if not (seg.startswith("(") and seg.endswith(")"))]
    return "/" + "/".join(segments) if segments else "/"


def _is_sensitive_route(route: str, page_text: str = "", sibling_layout_text: str = "") -> bool:
    lowered = route.lower()
    segments = [seg for seg in lowered.strip("/").split("/") if seg]
    if any(seg == hint or seg.startswith(f"{hint}-") or seg.endswith(f"-{hint}") for seg in segments for hint in SENSITIVE_ROUTE_HINTS):
        return True
    combined = f"{page_text}\n{sibling_layout_text}"
    if "AdminGate" in combined or re.search(r"index\s*:\s*false", combined):
        return True
    return False


def _has_use_client(text: str) -> bool:
    head = "\n".join(text.splitlines()[:15])
    return bool(re.search(r"""^\s*['"]use client['"]\s*;?""", head, flags=re.MULTILINE))


def _check_layouts(app_dir: Path, root: Path, findings: list[dict]) -> dict:
    layouts = sorted(p for p in app_dir.rglob("*") if p.is_file() and p.name in LAYOUT_NAMES)
    root_layout = next((p for p in layouts if p.parent == app_dir), None)
    summary = {
        "layout_count": len(layouts),
        "root_layout": _rel(root_layout, root) if root_layout else None,
        "has_metadata_base": False,
        "has_json_ld": False,
        "has_graph_schema": False,
    }

    if not root_layout:
        findings.append({
            "area": "Metadata",
            "severity": "Critical",
            "file": _rel(app_dir, root),
            "finding": "Missing root layout file (app/layout.tsx or app/layout.js).",
            "fix": "Create a root layout exporting Metadata with metadataBase, openGraph, and twitter defaults.",
        })
        return summary

    root_text = _read_text(root_layout)
    summary["has_metadata_base"] = "metadataBase" in root_text
    if not summary["has_metadata_base"]:
        findings.append({
            "area": "Metadata",
            "severity": "Warning",
            "file": _rel(root_layout, root),
            "finding": "Root layout does not define `metadataBase`.",
            "fix": "Add `metadataBase: new URL('https://your-domain.com')` to root `metadata` so OG and canonical URLs resolve reliably.",
        })

    all_layout_and_page_texts = [root_text]
    for p in app_dir.rglob("page.*"):
        if p.name in PAGE_NAMES:
            all_layout_and_page_texts.append(_read_text(p))
    combined = "\n".join(all_layout_and_page_texts)

    summary["has_json_ld"] = "application/ld+json" in combined
    summary["has_graph_schema"] = '"@graph"' in combined or "'@graph'" in combined or "@graph" in combined

    if not summary["has_json_ld"]:
        findings.append({
            "area": "Schema",
            "severity": "Warning",
            "file": _rel(root_layout, root),
            "finding": "No `application/ld+json` structured data detected in App Router layouts/pages.",
            "fix": "Add a root JSON-LD `@graph` combining `WebSite` and `Person` or `Organization` entities.",
        })
    elif not summary["has_graph_schema"]:
        findings.append({
            "area": "Schema",
            "severity": "Info",
            "file": _rel(root_layout, root),
            "finding": "JSON-LD found, but top-level `@graph` entity linking was not detected.",
            "fix": "Consider unifying primary entities (`WebSite`, `Person`/`Organization`) in a root `@graph` for stronger entity disambiguation.",
        })

    return summary


def _check_pages(app_dir: Path, root: Path, findings: list[dict]) -> dict:
    pages = sorted(p for p in app_dir.rglob("*") if p.is_file() and p.name in PAGE_NAMES)
    client_pages: list[str] = []
    missing_metadata_pages: list[str] = []
    dynamic_routes_missing_static_params: list[str] = []
    discovered_routes: list[str] = []
    sensitive_routes: list[str] = []

    for page in pages:
        route = _route_from_file(page, app_dir)
        discovered_routes.append(route)
        text = _read_text(page)
        rel_path = _rel(page, root)
        sibling_layout = next((page.parent / name for name in LAYOUT_NAMES if (page.parent / name).is_file()), None)
        sibling_text = _read_text(sibling_layout) if sibling_layout else ""
        sensitive = _is_sensitive_route(route, text, sibling_text)
        if sensitive:
            sensitive_routes.append(route)

        if _has_use_client(text) and not sensitive:
            client_pages.append(rel_path)
            findings.append({
                "area": "SSR / GEO",
                "severity": "Warning",
                "file": rel_path,
                "finding": f"Public route `{route}` starts with `'use client'`, which limits Server Component metadata and risks thin HTML for AI crawlers (`GPTBot`, `ClaudeBot`).",
                "fix": "Keep `page.tsx` as a Server Component exporting `metadata`/`generateMetadata`, and move interactive UI into a child Client Component.",
            })

        has_meta = (
            "export const metadata" in text
            or "export async function generateMetadata" in text
            or "export function generateMetadata" in text
            or "export const metadata" in sibling_text
            or "generateMetadata" in sibling_text
        )
        if not has_meta and not sensitive and route != "/":
            missing_metadata_pages.append(rel_path)
            findings.append({
                "area": "On-Page Metadata",
                "severity": "Warning",
                "file": rel_path,
                "finding": f"Public route `{route}` does not export `metadata` or `generateMetadata` in `page` or sibling `layout`.",
                "fix": "Export unique `title`, `description`, `alternates.canonical`, and `openGraph` metadata for this route.",
            })

        is_dynamic = "[" in route and "]" in route
        if is_dynamic and not sensitive:
            has_static_or_isr = (
                "generateStaticParams" in text
                or "export const revalidate" in text
                or "export const dynamic" in text
            )
            if not has_static_or_isr:
                dynamic_routes_missing_static_params.append(rel_path)
                findings.append({
                    "area": "Performance / Crawlability",
                    "severity": "Info",
                    "file": rel_path,
                    "finding": f"Dynamic route `{route}` has no `generateStaticParams` or `revalidate` export.",
                    "fix": "Add `generateStaticParams` (for known slugs) or `export const revalidate = ...` for predictable caching and fast TTFB.",
                })

    return {
        "page_count": len(pages),
        "discovered_routes": sorted(set(discovered_routes)),
        "sensitive_routes": sorted(set(sensitive_routes)),
        "client_pages": client_pages,
        "missing_metadata_pages": missing_metadata_pages,
        "dynamic_routes_missing_static_params": dynamic_routes_missing_static_params,
    }


def _check_robots(root: Path, sensitive_routes: list[str], findings: list[dict]) -> dict:
    robots_ts = next((root / rel for rel in ROBOTS_NAMES if (root / rel).is_file()), None)
    robots_static = root / "public" / "robots.txt"
    target = robots_ts or (robots_static if robots_static.is_file() else None)

    summary = {
        "file": _rel(target, root) if target else None,
        "ai_crawlers_declared": [],
        "ai_crawlers_missing": [],
        "undisallowed_sensitive_routes": [],
    }

    if not target:
        findings.append({
            "area": "Robots / Crawlers",
            "severity": "Critical",
            "file": "app/robots.ts",
            "finding": "No `app/robots.ts` or `public/robots.txt` found.",
            "fix": "Create `app/robots.ts` declaring sitemap URL, private route disallows, and explicit AI crawler policies.",
        })
        summary["ai_crawlers_missing"] = list(AI_CRAWLERS)
        return summary

    text = _read_text(target)
    for crawler in AI_CRAWLERS:
        if crawler in text:
            summary["ai_crawlers_declared"].append(crawler)
        else:
            summary["ai_crawlers_missing"].append(crawler)

    if summary["ai_crawlers_missing"]:
        findings.append({
            "area": "GEO / AI Crawlers",
            "severity": "Warning",
            "file": summary["file"],
            "finding": f"AI crawlers not explicitly configured in robots: {', '.join(summary['ai_crawlers_missing'])}.",
            "fix": "Explicitly allow or manage `GPTBot`, `ClaudeBot`, `PerplexityBot`, `OAI-SearchBot`, and `Google-Extended` in `app/robots.ts`.",
        })

    for route in sensitive_routes:
        top_segment = "/" + route.strip("/").split("/")[0]
        if top_segment not in text and route not in text:
            summary["undisallowed_sensitive_routes"].append(route)

    if summary["undisallowed_sensitive_routes"]:
        routes_str = ", ".join(sorted(set(summary["undisallowed_sensitive_routes"])))
        findings.append({
            "area": "Index Hygiene",
            "severity": "Warning",
            "file": summary["file"],
            "finding": f"Sensitive/CMS/redirect route(s) ({routes_str}) found in `app/` are not disallowed in `{summary['file']}`.",
            "fix": "Disallow internal CMS/admin/redirect prefixes in `app/robots.ts` and/or add `robots: { index: false, follow: false }` on those routes.",
        })

    return summary


def _check_sitemap_and_llms(root: Path, findings: list[dict]) -> dict:
    sitemap_ts = next((root / rel for rel in SITEMAP_NAMES if (root / rel).is_file()), None)
    sitemap_static = root / "public" / "sitemap.xml"
    sitemap_target = sitemap_ts or (sitemap_static if sitemap_static.is_file() else None)

    llms_candidates = (
        root / "app" / "llms.txt" / "route.ts",
        root / "app" / "llms.txt" / "route.js",
        root / "src" / "app" / "llms.txt" / "route.ts",
        root / "public" / "llms.txt",
    )
    llms_target = next((p for p in llms_candidates if p.is_file()), None)

    llms_full_candidates = (
        root / "app" / "llms-full.txt" / "route.ts",
        root / "app" / "llms-full.txt" / "route.js",
        root / "src" / "app" / "llms-full.txt" / "route.ts",
        root / "public" / "llms-full.txt",
    )
    llms_full_target = next((p for p in llms_full_candidates if p.is_file()), None)

    if not sitemap_target:
        findings.append({
            "area": "Sitemap",
            "severity": "Critical",
            "file": "app/sitemap.ts",
            "finding": "No `app/sitemap.ts` or `public/sitemap.xml` found.",
            "fix": "Implement dynamic `app/sitemap.ts` pulling published pages, posts, and projects from your data source.",
        })

    if not llms_target:
        findings.append({
            "area": "GEO / llms.txt",
            "severity": "Warning",
            "file": "app/llms.txt/route.ts",
            "finding": "Missing `/llms.txt` route or `public/llms.txt`.",
            "fix": "Add `app/llms.txt/route.ts` (or `public/llms.txt`) with site summary, core skills/products, and priority markdown links.",
        })

    if not llms_full_target:
        findings.append({
            "area": "GEO / llms-full.txt",
            "severity": "Info",
            "file": "app/llms-full.txt/route.ts",
            "finding": "Missing `/llms-full.txt` extended context endpoint.",
            "fix": "Add `app/llms-full.txt/route.ts` serving consolidated plain-text/Markdown summaries of your articles and projects for LLM ingestion.",
        })

    return {
        "sitemap": _rel(sitemap_target, root) if sitemap_target else None,
        "llms_txt": _rel(llms_target, root) if llms_target else None,
        "llms_full_txt": _rel(llms_full_target, root) if llms_full_target else None,
    }


def _check_next_config(root: Path, findings: list[dict]) -> dict:
    cfg = _find_next_config(root)
    summary = {
        "file": _rel(cfg, root) if cfg else None,
        "present_security_headers": [],
        "missing_security_headers": list(SECURITY_HEADER_KEYS),
        "modern_image_formats": False,
    }
    if not cfg:
        findings.append({
            "area": "Config / Security",
            "severity": "Warning",
            "file": "next.config.ts",
            "finding": "No `next.config.*` file found.",
            "fix": "Configure `headers()` for security headers and `images.formats: ['image/avif', 'image/webp']`.",
        })
        return summary

    text = _read_text(cfg)
    present = [key for key in SECURITY_HEADER_KEYS if key in text]
    missing = [key for key in SECURITY_HEADER_KEYS if key not in text]
    summary["present_security_headers"] = present
    summary["missing_security_headers"] = missing
    summary["modern_image_formats"] = "image/avif" in text or "image/webp" in text

    if missing:
        findings.append({
            "area": "Security Headers",
            "severity": "Warning",
            "file": summary["file"],
            "finding": f"Security headers not detected in `{summary['file']}`: {', '.join(missing)}.",
            "fix": "Add missing security headers in `async headers()` inside `next.config.*` (unless injected at CDN/reverse-proxy layer).",
        })

    if not summary["modern_image_formats"]:
        findings.append({
            "area": "Image Performance",
            "severity": "Info",
            "file": summary["file"],
            "finding": "Modern image formats (`image/avif`, `image/webp`) not configured in `next.config.*`.",
            "fix": "Set `images: { formats: ['image/avif', 'image/webp'] }` to improve LCP.",
        })

    return summary


def _check_components_and_links(root: Path, findings: list[dict]) -> dict:
    scan_dirs = [d for d in (root / "app", root / "src" / "app", root / "components", root / "src" / "components") if d.is_dir()]
    img_missing_alt: list[str] = []
    affiliate_missing_rel: list[str] = []

    img_tag_re = re.compile(r"<(?:img|Image)\b([^>]*?)>", flags=re.DOTALL)
    affiliate_link_re = re.compile(
        r"""<(?:a|Link)\b(?=(?:(?!<(?:/a|/Link|a\b|Link\b)).){0,600}(?:/go/|[?&](?:aff|ref)=|amzn\.to|shp\.ee|shopee\.))((?:(?!</?(?:a|Link)\b).){0,600})""",
        flags=re.DOTALL | re.IGNORECASE,
    )

    for base_dir in scan_dirs:
        for file_path in base_dir.rglob("*"):
            if file_path.suffix not in {".tsx", ".jsx"} or not file_path.is_file():
                continue
            text = _read_text(file_path)
            rel_path = _rel(file_path, root)

            for match in img_tag_re.finditer(text):
                attrs = match.group(1)
                if "alt=" not in attrs and "{..." not in attrs:
                    img_missing_alt.append(rel_path)
                    break

            for match in affiliate_link_re.finditer(text):
                attrs = match.group(1).lower()
                if "sponsored" not in attrs and "nofollow" not in attrs:
                    affiliate_missing_rel.append(rel_path)
                    break

    if img_missing_alt:
        findings.append({
            "area": "Image SEO / Accessibility",
            "severity": "Warning",
            "file": ", ".join(sorted(set(img_missing_alt))[:5]),
            "finding": f"Found `<img>` or `<Image>` tags missing explicit `alt` props in {len(set(img_missing_alt))} file(s).",
            "fix": "Add descriptive `alt` text (or `alt=\"\"` for purely decorative images) on all `<Image>` / `<img>` elements.",
        })

    if affiliate_missing_rel:
        findings.append({
            "area": "Link Compliance",
            "severity": "Warning",
            "file": ", ".join(sorted(set(affiliate_missing_rel))[:5]),
            "finding": f"Affiliate/redirect links (`/go/` or tracking params) without `rel=\"sponsored nofollow\"` detected in {len(set(affiliate_missing_rel))} file(s).",
            "fix": "Add `rel=\"sponsored nofollow noopener\"` on monetized/affiliate outbound links to comply with Google Search link spam policies.",
        })

    return {
        "files_with_missing_alt": sorted(set(img_missing_alt)),
        "files_with_unmarked_affiliate_links": sorted(set(affiliate_missing_rel)),
    }


def audit_nextjs_project(project_dir: str | Path) -> dict:
    root = Path(project_dir).resolve()
    app_dir = _find_app_dir(root)
    if not app_dir:
        return {
            "project_dir": root.as_posix(),
            "detected": False,
            "error": "No Next.js App Router directory (`app/` or `src/app/`) found.",
            "findings": [],
        }

    findings: list[dict] = []
    layout_summary = _check_layouts(app_dir, root, findings)
    pages_summary = _check_pages(app_dir, root, findings)
    robots_summary = _check_robots(root, pages_summary["sensitive_routes"], findings)
    sitemap_llms_summary = _check_sitemap_and_llms(root, findings)
    config_summary = _check_next_config(root, findings)
    component_summary = _check_components_and_links(root, findings)

    severity_penalty = {"Critical": 15, "Warning": 6, "Info": 2}
    score = max(0, 100 - sum(severity_penalty.get(f["severity"], 0) for f in findings))

    return {
        "project_dir": root.as_posix(),
        "app_dir": _rel(app_dir, root),
        "detected": True,
        "score": score,
        "summary": {
            "layouts": layout_summary,
            "pages": pages_summary,
            "robots": robots_summary,
            "sitemap_and_llms": sitemap_llms_summary,
            "next_config": config_summary,
            "components": component_summary,
        },
        "counts": {
            "critical": sum(1 for f in findings if f["severity"] == "Critical"),
            "warning": sum(1 for f in findings if f["severity"] == "Warning"),
            "info": sum(1 for f in findings if f["severity"] == "Info"),
        },
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Code-level Next.js App Router SEO & GEO Auditor"
    )
    parser.add_argument("project_dir", nargs="?", default=".", help="Path to Next.js project root")
    parser.add_argument("--json", "-j", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    report = audit_nextjs_project(args.project_dir)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report.get("detected") else 1

    if not report.get("detected"):
        print(f"Error: {report.get('error')}")
        return 1

    print(f"Next.js App Router SEO & GEO Audit — {report['project_dir']}")
    print("=" * 64)
    print(f"Score: {report['score']}/100 | App dir: {report['app_dir']}")
    print(
        f"Pages: {report['summary']['pages']['page_count']} | "
        f"Critical: {report['counts']['critical']} | "
        f"Warning: {report['counts']['warning']} | "
        f"Info: {report['counts']['info']}"
    )
    if report["findings"]:
        print("\nFindings:")
        for idx, item in enumerate(report["findings"], 1):
            print(f"  {idx}. [{item['severity']}] ({item['area']}) {item['file']}")
            print(f"     Finding: {item['finding']}")
            print(f"     Fix:     {item['fix']}")
    else:
        print("\nNo issues detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
