<!-- Updated: 2026-11-25 -->

# Growth SEO & Off-Page GEO Playbook Reference

> Reference for `seo-growth-geo` and `seo-nextjs` skills.

## Free High-DR Entity & Backlink Targets

| Platform | Typical Purpose | Link / Entity Value | Notes |
|---|---|---|---|
| Chrome Web Store | Companion extension / utility | DR 100 Google-hosted listing | \$5 one-time developer registration |
| GitHub Profile & READMEs | Open-source tools, portfolio links | DR 97 + GitHub SEO | Pin key repos, link canonical site |
| Product Hunt | Product / side-project launches | DR 92 + early adopters | Valuable even outside top #1 |
| Crunchbase | Company / founder profile | DR 91 entity signal | Complete every profile field |
| G2 / Capterra | B2B / SaaS buyer comparisons | High commercial & LLM citation trust | Feeds AI recommendation lists |
| Dev.to / Hashnode / Medium | Technical article syndication | High reach + developer trust | **Always set `canonical_url`** to original post |
| Substack | Founder / engineering notes | Recurring audience + links | Link home from every post |
| about.me / Carrd / Linktree | Identity & social hubs | Consistent entity `sameAs` graph | Use exact brand/person name |

## Search Console Goldmine Filters

| Filter / Setting | Exact Pattern / Value | Goal |
|---|---|---|
| Lookback window | `16 months` (`--months 16` / ~480 days) | Capture rare high-intent long-tail queries |
| 8+ word queries (RE2) | `^(?:\S+\s+){7,}\S+$` | Uncover exact natural-language questions |
| Question intent | `(?i)\b(how\|what\|why)\b` | Extract user pain points word-for-word |
| High imps + low CTR | Position visible, CTR < 2% | Answer the question in the **first lines** |
| Page-one threshold | Positions `8.0–15.0` | Highest-ROI internal linking & on-page push |
| Brand tracking | Filter by brand / founder name | Measure launch & GEO awareness lift |

## Reddit Anti-Ban Guardrails

| Parameter | Recommended Threshold |
|---|---|
| Target subreddit size | 10k–50k+ active members in niche |
| Account warmup duration | 1–3 weeks before any product mention |
| Minimum karma before mention | 30–50 karma |
| Value-to-mention ratio | 4–5 helpful comments per 1 mention |
| Disclosure style | Transparent (*"I built this, so I'm biased"*) |
| Link placement | Profile bio when subreddit rules restrict links |

## Off-Page GEO Priority Loop

1. Ask ChatGPT / Perplexity / Google AI Mode: *"What's the best [category] for [use case]?"*
2. Record every cited URL (listicles, comparison blogs, G2/Capterra, Reddit threads).
3. Classify whether AI cites **primary vendor pages** or **third-party roundups**.
4. Earn presence on the third-party roundups/threads **and** ship `/llms.txt` + `/llms-full.txt` + SSR HTML so crawlers can verify your claims directly.
