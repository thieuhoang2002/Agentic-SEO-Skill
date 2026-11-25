import importlib.util
import pathlib
import tempfile
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nextjs_seo_audit_handles_components_arrow_props_and_noindex():
    mod = load_script("nextjs_seo_audit")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "src" / "app" / "llms.txt").mkdir(parents=True)
        (root / "src" / "app" / "llms-full.txt").mkdir(parents=True)
        (root / "src" / "app" / "projects" / "admin-dashboard").mkdir(parents=True)
        (root / "src" / "app" / "secret-cms").mkdir(parents=True)
        (root / "src" / "components").mkdir(parents=True)

        (root / "next.config.ts").write_text(
            "export default { images: { formats: ['image/avif', 'image/webp'] }, async headers() { "
            "return [{ source: '/:path*', headers: ["
            "{ key: 'Content-Security-Policy', value: \"default-src 'self'\" },"
            "{ key: 'Strict-Transport-Security', value: 'max-age=63072000' },"
            "{ key: 'X-Frame-Options', value: 'SAMEORIGIN' },"
            "{ key: 'X-Content-Type-Options', value: 'nosniff' },"
            "{ key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },"
            "{ key: 'Permissions-Policy', value: 'camera=()' }"
            "] }]; } };",
            encoding="utf-8",
        )
        (root / "src" / "app" / "layout.tsx").write_text(
            "import JsonLd from '@/components/JsonLd';\n"
            "export const metadata = { metadataBase: new URL('https://example.com') };\n"
            "export default function RootLayout({ children }) { return <html><body><JsonLd />{children}</body></html>; }\n",
            encoding="utf-8",
        )
        (root / "src" / "components" / "JsonLd.tsx").write_text(
            "export default function JsonLd() {\n"
            "  return <script type=\"application/ld+json\" dangerouslySetInnerHTML={{ __html: JSON.stringify({ '@graph': [] }) }} />;\n"
            "}\n",
            encoding="utf-8",
        )
        (root / "src" / "app" / "page.tsx").write_text(
            "export default function Home() {\n"
            "  return <Image src=\"/hero.png\" onLoad={(e) => console.log(e)} alt=\"Hero\" />;\n"
            "}\n",
            encoding="utf-8",
        )
        (root / "src" / "app" / "projects" / "admin-dashboard" / "page.tsx").write_text(
            "export const metadata = { title: 'Admin Dashboard Case Study' };\n"
            "export default function Page() { return <main>Case study</main>; }\n",
            encoding="utf-8",
        )
        (root / "src" / "app" / "secret-cms" / "layout.tsx").write_text(
            "import AdminGate from '@/components/AdminGate';\n"
            "export const metadata = { robots: { index: false, follow: false } };\n"
            "export default function L({ children }) { return <AdminGate>{children}</AdminGate>; }\n",
            encoding="utf-8",
        )
        (root / "src" / "app" / "secret-cms" / "page.tsx").write_text(
            "'use client';\nexport default function CMS() { return <div />; }\n",
            encoding="utf-8",
        )
        (root / "src" / "app" / "robots.ts").write_text(
            "export default function robots() { return { rules: [{ userAgent: ['GPTBot','ClaudeBot','PerplexityBot','OAI-SearchBot','Google-Extended'], allow: '/' }] }; }",
            encoding="utf-8",
        )
        (root / "src" / "app" / "sitemap.ts").write_text("export default function sitemap() { return []; }", encoding="utf-8")
        (root / "src" / "app" / "llms.txt" / "route.js").write_text("export function GET() {}", encoding="utf-8")
        (root / "src" / "app" / "llms-full.txt" / "route.js").write_text("export function GET() {}", encoding="utf-8")

        report = mod.audit_nextjs_project(root)
        assert report["detected"] is True
        assert report["summary"]["layouts"]["has_json_ld"] is True
        assert report["summary"]["layouts"]["has_graph_schema"] is True
        assert report["summary"]["sitemap_and_llms"]["llms_txt"] == "src/app/llms.txt/route.js"
        assert report["summary"]["components"]["files_with_missing_alt"] == []
        assert report["counts"]["critical"] == 0
        assert report["counts"]["warning"] == 0, report["findings"]
        assert report["score"] == 100, report["findings"]


def test_nextjs_seo_audit_flags_missing_noindex_on_admingate_and_affiliate_rel():
    mod = load_script("nextjs_seo_audit")
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "app" / "vault").mkdir(parents=True)
        (root / "app" / "layout.tsx").write_text("export default function L({ children }) { return children; }", encoding="utf-8")
        (root / "app" / "page.tsx").write_text("export default function Home() { return <a href='/go/tool'>Deal</a>; }", encoding="utf-8")
        (root / "app" / "vault" / "page.tsx").write_text(
            "import AdminGate from '@/components/AdminGate';\nexport default function V() { return <AdminGate />; }",
            encoding="utf-8",
        )
        report = mod.audit_nextjs_project(root)
        findings_text = "\n".join(f["finding"] for f in report["findings"])
        assert "does not explicitly declare `robots: { index: false, follow: false }`" in findings_text
        assert "/vault" not in "\n".join(f.get("fix", "") for f in report["findings"] if f["area"] == "Robots / Crawlers")
        assert report["summary"]["components"]["files_with_unmarked_affiliate_links"] == ["app/page.tsx"]


def test_gtm_funnel_spy_validates_id_parses_vtp_eventname_and_checks_status():
    mod = load_script("gtm_funnel_spy")
    sample_js = (
        'var x={"function":"__awct","vtp_conversionId":"AW-987654321",'
        '"vtp_conversionLabel":"AbC_123-xyz=","vtp_eventName":"purchase"};'
        'var y={"vtp_eventName":"trial_started"};'
        'var z={"vtp_eventName":"evil\x1b[31mpayload"};'
        'gtag("config","G-ABCD123456");'
    )
    parsed = mod.extract_gtm_signals_from_js(sample_js, "GTM-TEST123")
    assert parsed["awct_count"] == 1
    assert parsed["google_ads_conversions"] == [{"conversion_id": "AW-987654321", "conversion_label": "AbC_123-xyz="}]
    assert "snippet" not in parsed["google_ads_conversions"][0]
    assert "purchase" in parsed["detected_event_names"]
    assert "trial_started" in parsed["detected_event_names"]
    assert all("evil" not in name for name in parsed["detected_event_names"])

    def fake_fetch(url, **kwargs):
        if "GTM-404TEST" in url:
            return {"status": 404, "text": "<html>Not Found</html>", "error": None}
        return {"status": 200, "text": sample_js, "error": None}

    with patch.object(mod, "fetch_url", side_effect=fake_fetch):
        res = mod.inspect_target(
            "",
            explicit_gtm_ids=["gtm-ok1234", "GTM-404TEST", "GTM-BAD&gtm_auth=evil"],
            fetch_gtm=True,
        )

    assert res["gtm_ids"] == ["GTM-404TEST", "GTM-OK1234"]
    assert res["invalid_gtm_ids"] == ["GTM-BAD&gtm_auth=evil"]
    by_id = {c["gtm_id"]: c for c in res["containers"]}
    assert by_id["GTM-OK1234"]["fetched"] is True
    assert by_id["GTM-404TEST"]["fetched"] is False
    assert by_id["GTM-404TEST"]["status"] == 404


def test_llms_txt_generator_full_body_norm_url_and_sanitization():
    mod = load_script("llms_txt_generator")

    def fake_fetch(url, **kwargs):
        if url == "https://example.com/":
            return {
                "url": url,
                "status": 200,
                "headers": {"content-type": "text/html; charset=utf-8"},
                "text": "<html><head><title>Site\n# Injected</title><meta name='description' content='Desc > quote'></head><body><main><p>Home text</p></main></body></html>",
            }
        if url == "https://example.com/about":
            return {
                "url": url,
                "status": 200,
                "headers": {"content-type": "text/html"},
                "text": "<html><head><title>About [Team]</title><meta name='description' content='About desc'></head><body><main><p>Real body content for LLM.</p></main></body></html>",
            }
        raise AssertionError(f"Unexpected fetch URL: {url}")

    with patch.object(mod, "fetch_url", side_effect=fake_fetch):
        res = mod.generate(
            "https://example.com",
            ["/about", "javascript:alert(1)"],
            fetch_titles=True,
            full=True,
        )

    assert res["count"] == 1
    assert res["skipped_urls"] == ["javascript:alert(1)"]
    assert "javascript:alert(1)" not in res["llms_txt"]
    assert "https://example.com/about" in res["llms_txt"]
    assert "Real body content for LLM." in res["llms_full_txt"]
    assert "\\# Injected" in res["llms_txt"]
    assert "\\[Team\\]" in res["llms_txt"]


def test_gsc_checker_clamping_and_page_one_threshold():
    mod = load_script("gsc_checker")
    assert mod.resolve_query_params(days=-5, months=24, row_limit=999999) == (480, 25000)
    assert mod.resolve_query_params(days=999, months=0, row_limit=0) == (480, 1)
    assert "long-tail-questions" in mod.PRESET_REGEXES
    opps = mod.detect_opportunities([
        {"query": "how to optimize nextjs", "page": "https://example.com/a", "position": 10.5, "impressions": 45, "ctr": 1.2},
    ])
    assert len(opps) == 1
    assert opps[0]["type"] == "page_one_threshold"
