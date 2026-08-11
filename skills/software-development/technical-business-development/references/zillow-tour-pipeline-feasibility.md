# Case Study: Zillow Virtual Tour Pipeline (Phase 0 Feasibility)

## The Idea

Build an automated pipeline that:
1. Scrapes Zillow listings with rich photo sets
2. OSINTs the listing agent's contact info
3. Generates an immersive scroll-through virtual tour website from their existing photos
4. Cold-emails the agent with a live preview link

## Competitive Landscape

- **Bounti.ai / GoCrazyAI / RealtReel** — Listing photos → social media video reels ($20-50/mo). Not interactive websites.
- **CloudPano / Kuula / Aryeo** — 360° photo tours requiring on-site 360° camera. Not automated.
- **Matterport** — Professional 3D scans at $300+/scan. Requires specialist on-site.
- **Zillow 3D Home / SkyTour** — Locked to Zillow's platform, exterior-only GS from drone.

**The Gap:** Nobody is doing Zillow-scrape → automated scroll-world immersive tour → agent outreach.

## FOSS Tools Found

| Tool | Use | Status |
|------|-----|--------|
| NoPoSplat (ICLR 2025) | Feed-forward 3DGS from sparse unposed photos — no camera calibration needed | Production-ready, open source |
| Splatt3R | Zero-shot GS from uncalibrated image pairs | Working demo, open source |
| Nerfstudio/gsplat (NVIDIA) | Full GS training pipeline | 12K+ stars, battle-tested |
| Postshot (Jawset) | Desktop GS training, currently free commercial license | GA, all tiers €0/mo |
| mkkellogg/GaussianSplats3D | Three.js web GS viewer, npm package | Production, free |
| Various Zillow scrapers | Zillow Scraper API ($0.01/listing), Apify, DIY | Available |

## Unit Economics (per house)

| Tier | What | Cost | Sell price |
|------|------|------|-----------|
| Standard | Photo scroll tour from Zillow's existing photos | $0.01 | $197 |
| Plus | Above + Higgsfield camera-flight video walkthrough | $9-11 | $297 |
| Premium | Above + full 3DGS (on-site capture) | $10-17 | $497 |
| Elite | Premium + drone + social cutdowns | $15-25 | $997 |

**Key insight:** Ultra Higgsfield plan ($99/mo) covers ~11 houses/month at Tier 2. Standard tier costs $0.01/house — unlimited volume for cold outreach.

## Repo

Results documented at https://github.com/pmb2/zillow-tour-pipeline (private)
