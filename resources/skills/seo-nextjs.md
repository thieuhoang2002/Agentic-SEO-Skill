---
name: seo-nextjs
description: >
  Code-level SEO & GEO audit and implementation guide for Next.js App Router
  (13/14/15/16) + React + TypeScript + DB/CMS applications. Covers SSR/CSR
  boundaries for AI crawlers, generateMetadata, canonicals, JSON-LD @graph,
  robots.ts, dynamic sitemap.ts, /llms.txt + /llms-full.txt route handlers,
  security headers, image optimization, and affiliate link compliance. Use when
  user says "Next.js SEO", "App Router SEO", "audit my Next.js repo", or
  "code-level SEO".
---

# Next.js App Router SEO & GEO

Audits and fixes SEO/GEO directly at the source-code level before deployment — catching framework pitfalls that external URL crawlers cannot see.

## Automated Code Audit Script

```bash
python3 <SKILL_DIR>/scripts/nextjs_seo_audit.py <project_dir>
python3 <SKILL_DIR>/scripts/nextjs_seo_audit.py <project_dir> --json
```

## Core App Router Checks

### 1. Server vs Client Boundaries (SSR & AI Crawlers)
AI crawlers (`GPTBot`, `ClaudeBot`, `PerplexityBot`) generally do not execute client-side JavaScript.
- **Rule:** Keep `app/**/page.tsx` and `layout.tsx` as **Server Components** so initial HTML contains complete headings, body copy, metadata, and JSON-LD.
- **Pattern for heavy interactive/3D/canvas pages (e.g., Three.js, audio players, dashboards):**
  - Wrap the page in a Server Component `page.tsx` (or sibling `layout.tsx`) exporting `metadata` / `generateMetadata`, plus a semantic SSR summary or `<noscript>`/crawlable content block.
  - Isolate `'use client'` inside child view components (`*ClientView.tsx`).

### 2. Metadata & Canonical Consistency
- Define `metadataBase: new URL("https://your-domain.com")` in root `app/layout.tsx`.
- Every public route (`page.tsx` or sibling `layout.tsx`) must define unique `title`, `description`, `alternates.canonical`, `openGraph`, and `twitter` metadata.
- Dynamic routes (`[slug]`, `[id]`) should implement `generateMetadata()` and either `generateStaticParams()` or `export const revalidate = <seconds>` for predictable caching and low TTFB.

### 3. Root JSON-LD `@graph` Entity Architecture
Unify core entities inside a top-level `@graph` rather than nesting `Person` inside `ProfilePage` alone:
```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "url": "https://example.com",
      "name": "Site Name"
    },
    {
      "@type": "Person",
      "@id": "https://example.com/#person",
      "name": "Your Name",
      "url": "https://example.com",
      "sameAs": ["https://github.com/username", "https://www.linkedin.com/in/username"]
    }
  ]
}
```
- Article routes (`/posts/[slug]`): `BlogPosting` / `Article` referencing `@id` of `Person`/`Organization`.
- Project/tool routes (`/projects/[id]`): `SoftwareApplication` or `CreativeWork`.

### 4. `app/robots.ts` & Index Hygiene
- Explicitly allow/manage search and AI search crawlers (`Googlebot`, `Bingbot`, `Applebot`, `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`).
- **Disallow internal/sensitive routes** discovered in `app/`: `/api/`, admin/CMS paths (`/admin`, `/cms`, `/dashboard`, `/vault`, etc.), and affiliate redirect paths (`/go/`).
- Pair with `robots: { index: false, follow: false }` on admin/auth layouts or `X-Robots-Tag: noindex, nofollow` headers on redirect/API endpoints.

### 5. Dynamic `app/sitemap.ts`
- Query published records dynamically from your database/CMS (MongoDB, Prisma, Sanity, MDX) with fallback data if DB is unreachable at build time.
- Filter out `hidden`, `draft`, or `noindex` items and force canonical custom domain (never leak `*.vercel.app` or `localhost`).

### 6. Dynamic `/llms.txt` & `/llms-full.txt` Route Handlers
- Ship `app/llms.txt/route.ts` returning `text/plain; charset=utf-8` with `Cache-Control` / ISR `revalidate`.
- Pull published posts, featured projects, and key sections dynamically from your database.
- Also ship `app/llms-full.txt/route.ts` providing consolidated Markdown/plain-text summaries of deep technical articles and projects so LLMs can ingest full context in one request.

### 7. Security Headers, Images & Affiliate Compliance
- Configure `headers()` in `next.config.ts` with `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and `Permissions-Policy`.
- Configure `images: { formats: ['image/avif', 'image/webp'] }` and verify every `<img>` / `<Image>` has a meaningful `alt`.
- Add `rel="sponsored nofollow noopener"` on monetized/affiliate outbound links (`/go/*`, partner links).

## Output Format

1. Run `nextjs_seo_audit.py <project_dir> --json`
2. Combine code-level findings with live HTTP checks (`security_headers.py`, `llms_txt_checker.py`, `javascript_render_audit.py`)
3. Report exact file paths + line-level fixes prioritized by impact (`Critical` → `Warning` → `Info`).
