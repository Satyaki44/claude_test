"""
scraper.py
Fetches posts from 20 publications via free RSS feeds (Substack + open RSS).
No API key required.
"""

import re
import time
import socket
import logging
import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FEEDS = [
    # --- Original 10 ---
    "https://thegtmnewsletter.substack.com/feed",         # GTMnow
    "https://gtmengineerschool.substack.com/feed",        # GTM Engineer Pulse
    "https://growthwithalex.substack.com/feed",           # Growth with Alex
    "https://buildingcreativemachines.substack.com/feed", # Building Creative Machines
    "https://startupgtm.substack.com/feed",               # StartupGTM
    "https://aimaker.substack.com/feed",                  # AI Maker
    "https://aidrivenmarketing.substack.com/feed",        # AI Driven Marketing
    "https://revengine.substack.com/feed",                # RevEngine
    "https://nathanbenaich.substack.com/feed",            # State of AI
    "https://20vc.substack.com/feed",                     # 20VC Newsletter

    # --- New 10: GTM, AI marketing, PLG, RevOps ---
    "https://gtmonday.substack.com/feed",                 # GTMonday by GTM Partners
    "https://knowledge.gtmstrategist.com/feed",           # GTM Strategist (Maja Voje)
    "https://www.gtmaipodcast.com/feed",                  # GTM AI Podcast & Newsletter
    "https://www.kieranflanagan.io/feed",                 # AI Marketing Generalist (Kieran Flanagan)
    "https://newsletter.mkt1.co/feed",                    # MKT1 Newsletter (Emily Kramer)
    "https://fullfunnel.substack.com/feed",               # Full-Funnel B2B Marketing
    "https://pierreherubel.substack.com/feed",            # Pierre's Content Guides
    "https://www.lennysnewsletter.com/feed",              # Lenny's Newsletter (PLG, SaaS)
    "https://www.news.aakashg.com/feed",                  # Product Growth (Aakash Gupta)
    "https://blog.hubspot.com/marketing/rss.xml",         # HubSpot Marketing Blog

    # --- New 20: GTM, Sales, RevOps, PLG, AI, B2B Marketing ---
    "https://outboundkitchen.substack.com/feed",          # Outbound Kitchen (Elric Legloire) — SDR math, cold email, AI-assisted prospecting
    "https://kylepoyar.substack.com/feed",                # Growth Unhinged (Kyle Poyar) — PLG, pricing, SaaS benchmarks, 80k+ readers
    "https://www.elenaverna.com/feed",                    # Elena's Growth Scoop (Elena Verna) — PLG, freemium, product-led sales, 85k+
    "https://thetransaction.substack.com/feed",           # The Transaction (Craig Rosenberg) — CRO/CMO interviews, sales motion design
    "https://revopsfm.substack.com/feed",                 # RevOps FM (Justin Norris) — RevOps, HubSpot/Salesforce, GTM ops
    "https://koenstam.substack.com/feed",                 # GTM OS (Koen Stam) — signal-based outbound, AI-native GTM workflows
    "https://claygtmengineering.substack.com/feed",       # Claymation (Alex Lindahl) — Clay workflows, AI enrichment, outbound automation
    "https://demandloops.substack.com/feed",              # Looped In (Kaylee Edmondson) — demand gen, pipeline generation, B2B SaaS
    "https://b2bmarketingstrategies.substack.com/feed",   # B2B Marketing Strategies (Arpit Mishra) — ICP, positioning, launch playbooks
    "https://www.saastr.com/feed",                        # SaaStr (Jason Lemkin) — SaaS benchmarks, hiring, ARR milestones
    "https://openviewpartners.com/feed",                  # OpenView Blog — PLG research, pricing, product-led sales frameworks
    "https://tomtunguz.com/index.xml",                    # Tomasz Tunguz (Theory Ventures) — AI + SaaS metrics, GTM trends
    "https://www.exitfive.com/rss.xml",                   # Exit Five (Dave Gerhardt) — B2B marketing, positioning, demand gen, 40k+
    "https://peeplaja.com/feed",                          # Peep Laja (Wynter/CXL) — B2B differentiation, competitive positioning
    "https://www.swipefiles.com/feed",                    # Swipe Files (Corey Haines) — SaaS marketing playbooks, growth experiments
    "https://cxl.com/blog/feed/",                         # CXL Blog — conversion optimization, B2B messaging, SaaS growth research
    "https://www.dearstage2.com/feed",                    # Dear Stage 2 (Liz Christo) — founder GTM questions, VC-backed operator advice
    "https://thegtme.com/feed",                           # The GTM Engineer by Clay — AI + automation for pipeline
    "https://feeds.captivate.fm/the-b2b-playbook/",       # The B2B Playbook — demand gen, ABM, intent signals
    "https://www.refinelabs.com/feed",                    # Refine Labs (Chris Walker) — dark-social demand gen, B2B buyer behavior
]


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def fetch_posts() -> list[dict]:
    """
    Fetch and deduplicate posts from all Substack feeds.
    Each post dict has: title, author, url, date, summary
    """
    posts: list[dict] = []
    seen: set[str] = set()

    for feed_url in FEEDS:
        log.info(f"Fetching: {feed_url}")
        try:
            socket.setdefaulttimeout(10)
            feed = feedparser.parse(feed_url)
            publication = feed.feed.get("title", feed_url)

            if feed.bozo and not feed.entries:
                log.warning(f"  Failed to parse feed: {feed_url}")
                continue

            log.info(f"  {publication}: {len(feed.entries)} entries")

            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in seen:
                    continue
                seen.add(url)

                summary = _strip_html(
                    entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
                )

                posts.append({
                    "title":       entry.get("title", "").strip(),
                    "author":      entry.get("author", publication),
                    "publication": publication,
                    "url":         url,
                    "date":        entry.get("published", ""),
                    "summary":     summary[:1000],
                })

        except Exception as e:
            log.warning(f"  Error fetching {feed_url}: {e}")

        time.sleep(1)

    log.info(f"Total unique posts fetched: {len(posts)}")
    return posts
