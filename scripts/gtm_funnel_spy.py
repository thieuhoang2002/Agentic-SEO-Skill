#!/usr/bin/env python3
"""
GTM Competitor Conversion Funnel Inspector

Extracts Google Tag Manager container IDs (`GTM-XXXXXX`) from a target URL
(or local HTML file), fetches `googletagmanager.com/gtm.js?id=<ID>`, and
parses `__awct` Google Ads conversion tracking markers, GA4 (`G-...`) IDs,
and conversion labels/event names to reveal competitor acquisition funnels.

Usage:
    python scripts/gtm_funnel_spy.py https://competitor.com --json
    python scripts/gtm_funnel_spy.py --gtm-id GTM-XXXXXXX --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from seo_common import fetch_url, normalize_url


GTM_ID_RE = re.compile(r"\bGTM-[A-Z0-9]{4,10}\b")
GA4_ID_RE = re.compile(r"\bG-[A-Z0-9]{6,12}\b")
AW_ID_RE = re.compile(r"\bAW-[0-9]{6,12}\b")
META_PIXEL_RE = re.compile(r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d{10,20})['\"]")
AWCT_BLOCK_RE = re.compile(r"__awct.{0,450}", flags=re.DOTALL)
CONVERSION_LABEL_RE = re.compile(r"""vtp_conversionLabel["']?\s*[:=]\s*["']([^"']+)["']""")
CONVERSION_ID_RE = re.compile(r"""vtp_conversionId["']?\s*[:=]\s*["']([^"']+)["']""")
EVENT_NAME_RE = re.compile(r"""(?:vtp_eventName|event["']?\s*[:=])\s*["']([a-zA-Z0-9_.\- ]{2,60})["']""")


def extract_gtm_signals_from_js(gtm_js: str, gtm_id: str) -> dict:
    """Parse Google Ads (__awct), GA4, and event names from raw gtm.js payload."""
    awct_matches = AWCT_BLOCK_RE.findall(gtm_js)
    conversions: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for block in awct_matches:
        cid_match = CONVERSION_ID_RE.search(block)
        label_match = CONVERSION_LABEL_RE.search(block)
        cid = cid_match.group(1) if cid_match else ""
        label = label_match.group(1) if label_match else ""
        key = (cid, label)
        if key not in seen and (cid or label):
            seen.add(key)
            conversions.append({
                "conversion_id": cid or None,
                "conversion_label": label or None,
                "snippet": block[:180].replace("\n", " "),
            })

    events = sorted({
        m.group(1).strip()
        for m in EVENT_NAME_RE.finditer(gtm_js)
        if not m.group(1).startswith("gtm.")
    })

    return {
        "gtm_id": gtm_id,
        "awct_count": len(awct_matches),
        "google_ads_conversions": conversions,
        "aw_ids": sorted(set(AW_ID_RE.findall(gtm_js))),
        "ga4_ids": sorted(set(GA4_ID_RE.findall(gtm_js))),
        "meta_pixels": sorted(set(META_PIXEL_RE.findall(gtm_js))),
        "detected_event_names": events[:40],
    }


def inspect_target(source: str, explicit_gtm_ids: list[str] | None = None, fetch_gtm: bool = True, timeout: int = 15) -> dict:
    """Inspect a URL or local HTML file for GTM containers and conversion tags."""
    gtm_ids: set[str] = set(explicit_gtm_ids or [])
    resolved_source = source
    fetch_error = None

    if source:
        path = Path(source)
        if path.is_file():
            html = path.read_text(encoding="utf-8", errors="replace")
            gtm_ids.update(GTM_ID_RE.findall(html))
        else:
            resolved_source = normalize_url(source)
            fetched = fetch_url(resolved_source, timeout=timeout, max_bytes=2_000_000)
            fetch_error = fetched.get("error")
            if fetched.get("text"):
                gtm_ids.update(GTM_ID_RE.findall(fetched["text"]))

    containers: list[dict] = []
    for gtm_id in sorted(gtm_ids):
        if not fetch_gtm:
            containers.append({"gtm_id": gtm_id, "fetched": False})
            continue
        gtm_url = f"https://www.googletagmanager.com/gtm.js?id={gtm_id}"
        gtm_resp = fetch_url(gtm_url, timeout=timeout, max_bytes=3_000_000)
        if gtm_resp.get("text"):
            parsed = extract_gtm_signals_from_js(gtm_resp["text"], gtm_id)
            parsed["fetched"] = True
            parsed["gtm_url"] = gtm_url
            containers.append(parsed)
        else:
            containers.append({
                "gtm_id": gtm_id,
                "fetched": False,
                "gtm_url": gtm_url,
                "error": gtm_resp.get("error") or f"HTTP {gtm_resp.get('status')}",
            })

    return {
        "source": resolved_source or None,
        "fetch_error": fetch_error,
        "gtm_ids": sorted(gtm_ids),
        "containers": containers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect competitor GTM containers for Google Ads (__awct) and GA4 funnel signals"
    )
    parser.add_argument("source", nargs="?", default="", help="Target URL or local HTML file")
    parser.add_argument("--gtm-id", action="append", default=[], help="Explicit GTM-XXXXXX container ID")
    parser.add_argument("--no-fetch-gtm", action="store_true", help="Only extract GTM IDs without fetching gtm.js")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--json", "-j", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    if not args.source and not args.gtm_id:
        parser.error("Provide a target URL/file or at least one --gtm-id GTM-XXXXXX.")

    result = inspect_target(
        args.source,
        explicit_gtm_ids=args.gtm_id,
        fetch_gtm=not args.no_fetch_gtm,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"GTM Funnel Spy — {result['source'] or ', '.join(result['gtm_ids'])}")
    print("=" * 60)
    if result["fetch_error"]:
        print(f"Fetch warning: {result['fetch_error']}")
    print(f"GTM Containers: {', '.join(result['gtm_ids']) or 'None found'}")
    for container in result["containers"]:
        print(f"\n[{container['gtm_id']}]")
        if container.get("error"):
            print(f"  Error: {container['error']}")
            continue
        if not container.get("fetched"):
            print("  (Skipped gtm.js fetch)")
            continue
        print(f"  __awct markers: {container['awct_count']}")
        print(f"  GA4 IDs:        {', '.join(container['ga4_ids']) or 'None'}")
        print(f"  AW IDs:         {', '.join(container['aw_ids']) or 'None'}")
        if container["google_ads_conversions"]:
            print("  Google Ads Conversions:")
            for conv in container["google_ads_conversions"]:
                print(f"    - id={conv['conversion_id']} label={conv['conversion_label']}")
        if container["detected_event_names"]:
            print(f"  Event names:    {', '.join(container['detected_event_names'][:15])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
