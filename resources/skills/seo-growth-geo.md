---
name: seo-growth-geo
description: >
  Off-page SEO, zero-to-one backlink acquisition, Search Console query mining,
  borrowed authority, Reddit anti-ban playbook, AI citation hunting, and
  competitor GTM conversion funnel spying. Complements technical/on-page audits
  with practical distribution workflows for portfolios, SaaS products, and client
  sites. Use when user says "growth SEO", "off-page SEO", "free backlinks",
  "Reddit SEO", "borrowed authority", "get cited by ChatGPT", "GSC goldmine",
  or "spy competitor ads funnel".
---

# Growth SEO & Off-Page GEO Playbook

Technical and on-page SEO make a site crawlable; **distribution, brand mentions, and off-page citations** make Google and LLMs (ChatGPT, Perplexity, Google AI Overviews) actually recommend it.

> See `resources/references/growth-geo-playbook.md` for checklists and thresholds.

## 1. Free High-DR Entity & Backlink Launchpad (Zero-to-One)

High-DR profile and directory links are mostly `nofollow`, yet they help new sites get discovered, establish entity consistency (`sameAs`), and pass initial trust:

1. **Developer / Product Ecosystems:**
   - **GitHub:** Link your site from your GitHub profile bio and pinned repo `README.md`s (run `seo github` to optimize repos).
   - **Chrome Web Store:** Publishing a small companion utility ($5 one-time dev fee) creates a high-trust Google-hosted listing.
   - **Product Hunt / Crunchbase:** Claim your organization/product page and fill every field.
   - **G2 / Capterra:** List B2B/SaaS tools where buyers actively compare alternatives (also feeds AI training/search citations).
2. **Canonical Content Syndication:**
   - Cross-post technical articles to **Dev.to**, **Hashnode**, and **Medium** with `canonical_url` pointing back to your primary domain.
   - Start a **Substack** for founder/engineering notes linking home from each issue.
3. **Bio & Identity Hubs:**
   - Populate **about.me**, **Carrd**, and **Linktree** consistently pointing to your canonical domain.

## 2. Search Console Goldmine Workflow

Use `scripts/gsc_checker.py` with extended lookback and regex mining (GSC retains up to 16 months):

```bash
# Pull 16 months (480 days) of 8+ word long-tail queries
python3 <SKILL_DIR>/scripts/gsc_checker.py https://example.com --months 16 --preset long-tail-questions --row-limit 100 --json

# Pull how / what / why question queries
python3 <SKILL_DIR>/scripts/gsc_checker.py https://example.com --months 16 --preset how-what-why --row-limit 100 --json
```

**Action rules:**
1. **High impressions + low CTR** = you already rank for a question you fail to answer clearly → put a direct 40–60 word answer in the **first lines** of that ranking page.
2. **Positions 8–15 (`page_one_threshold`)** = highest-ROI quick wins; prioritize internal links, H1/title sharpening, and missing sub-answers before writing brand-new pages.
3. **Brand tracking:** Filter by your brand/personal name after every launch to measure branded search lift.
4. **Fast indexing:** Run GSC *URL Inspection → Request indexing* (and `indexnow_checker.py` for Bing/ChatGPT Search) on every newly shipped page.

## 3. Borrowed Authority (Parasite SEO) & Distribution

Renting authority on trusted domains accelerates discovery while your own domain builds authority:
- **LinkedIn Articles:** Feed an AI assistant a 20–30 min founder/engineer voice transcript to draft a deep-dive LinkedIn article linking back to your canonical guide.
- **Multi-platform Coverage:** Cover high-intent topics across multiple trusted surfaces (LinkedIn, Dev.to, Hashnode, GitHub Gist, YouTube/video descriptions) in a coordinated launch week.
- **Upgrade Winning Reddit Threads:** Find the top-ranking Reddit thread for a target problem and publish a more comprehensive, structured guide on your own domain.
- **Expectation management:** Borrowed-authority pages often fluctuate or drop from SERPs over time; **brand mentions and links from strong sources** are what compound long-term.

## 4. Reddit Anti-Ban Playbook (High AI Citation Leverage)

Reddit is heavily cited by Google SERPs, ChatGPT, and Perplexity. Operate without triggering spam filters:
1. Find threads that already rank on Google: `site:reddit.com <your problem or category>`.
2. Target focused subreddits (**10k–50k+ members**) where buyers/peers compare tools or architectures.
3. Read subreddit rules first (many allow self-promotion only in weekly threads).
4. **Warm up new accounts 1–3 weeks** to **30–50+ karma** before mentioning any project.
5. Maintain a **4–5 helpful, non-promotional comments** ratio for every 1 product/article mention.
6. Use transparent disclosure (*"I built this, so I'm biased..."*) rather than astroturfing.
7. Keep direct links out of comments when rules prohibit them — place your link in your **Reddit profile** instead.
8. Sort target subreddits by **Top → All time** to mirror proven post formats.

## 5. Off-Page GEO & Active AI Citation Hunting

On-page `llms.txt` and SSR only make your site *readable*. To actually **get recommended by ChatGPT / Perplexity / AI Overviews**:
1. **Test category prompts directly:** Ask ChatGPT/Perplexity *"What's the best [tool/engineer/solution] for [my category]?"*
2. **Audit the cited sources:** If AI names competitors, inspect every URL it cites (listicles, comparison posts, review directories, Reddit threads).
3. **Get on the cited pages:** Pitch inclusion in those listicles, earn reviews on those directories, contribute authentic answers in those threads, or publish a page covering those exact structural patterns better than the cited sources.
4. **Track AI Overview citations** for your target query over 7 days to spot volatile vs stable citation slots, and ensure your `About` page explains who you are, what you do, and who it's for in plain words.

## 6. Competitor Paid Funnel & SERP Spying

Before targeting commercial keywords, inspect what competitors actually monetize:

```bash
# Extract GTM container IDs and Google Ads (__awct) / GA4 funnel events
python3 <SKILL_DIR>/scripts/gtm_funnel_spy.py https://competitor.com --json
```

1. **Read competitor conversion funnels:** `gtm_funnel_spy.py` inspects `googletagmanager.com/gtm.js?id=GTM-...` for `__awct` Google Ads conversion tags and event names (e.g., `Registration → Trial → First Payment`), revealing which pages/keywords drive paid conversions.
2. **Filter SERPs smartly:** Skip SERPs overwhelmingly dominated by unassailable parasite/megadomain pages unless you have a unique tool or first-hand data angle.
3. **Match the #1 SERP format:** If #1 is a listicle, build a listicle; if it's an interactive tool or comparison table, build that format.
4. **Day-one internal linking & weekly checks:** Add internal links pointing to a new page the day you publish, and recheck rankings weekly to refresh slipping pages (`content_decay_detector.py`).
