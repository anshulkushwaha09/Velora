"""
trend_fetcher.py — Real-Time Trend Intelligence Module (Part 1)

Fetches global trends from FREE RSS sources, scores them for virality,
and returns niche-relevant candidates for fusion with the channel identity.

Sources (all free, no API key required):
- Google Trends (India)
- NASA Breaking News
- Science Daily
- Phys.org
- Archaeology Magazine / Heritage Daily

Caching: Results stored in trend_cache.json with 6-hour TTL.
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta

try:
    import feedparser
except ImportError:
    feedparser = None
    print("⚠️ feedparser not installed. Run: pip install feedparser")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

TREND_CATEGORIES = [
    "technology", "science", "space", "archaeology",
    "geopolitics", "health", "internet culture", "paranormal",
    "history", "religion", "environment"
]

# Free RSS feeds — no authentication needed
RSS_SOURCES = {
    "google_trends_india": {
        "url": "https://trends.google.com/trending/rss?geo=IN",
        "category": "trending",
        "weight": 1.5,  # Higher weight = more viral potential
    },
    "nasa_breaking": {
        "url": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "category": "space",
        "weight": 1.3,
    },
    "science_daily": {
        "url": "https://www.sciencedaily.com/rss/all.xml",
        "category": "science",
        "weight": 1.2,
    },
    "phys_org": {
        "url": "https://phys.org/rss-feed/",
        "category": "science",
        "weight": 1.1,
    },
    "heritage_daily": {
        "url": "https://www.heritagedaily.com/feed",
        "category": "archaeology",
        "weight": 1.4,  # High weight — directly relevant to our niche
    },
}

# Keywords that boost a trend's relevance to our niche
NICHE_KEYWORDS = [
    "ancient", "temple", "discovery", "mystery", "civilization",
    "archaeological", "artifact", "sacred", "ruins", "tomb",
    "pyramid", "ritual", "scripture", "manuscript", "hidden",
    "forbidden", "secret", "underground", "cave", "lost city",
    "satellite", "anomaly", "unexplained", "cosmic", "space",
    "AI", "robot", "quantum", "genetic", "DNA", "brain",
    "volcano", "earthquake", "eclipse", "comet", "asteroid",
    "war", "military", "classified", "government", "conspiracy",
    "india", "hindu", "vedic", "sanskrit", "yoga", "meditation",
]

# Keywords that make a trend unsafe/irrelevant — skip these
BLACKLIST_KEYWORDS = [
    "stock market", "cricket score", "IPL", "bollywood gossip",
    "reality show", "influencer drama", "sale", "discount",
    "recipe", "fashion", "makeup", "tutorial",
]

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trend_cache.json")
CACHE_TTL_HOURS = 6


# ─────────────────────────────────────────────────────────────────────────────
# Cache Management
# ─────────────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    """Load cached trends if they exist and are fresh."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.utcnow() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
                return data
        except (json.JSONDecodeError, ValueError, IOError):
            pass
    return {}


def _save_cache(trends: list):
    """Save trends to cache with timestamp."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "cached_at": datetime.utcnow().isoformat(),
                "trends": trends,
            }, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"   Warning: Could not save trend cache: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Core Functions
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_single_feed(name: str, config: dict) -> list:
    """Fetches and parses a single RSS feed. Returns list of trend dicts."""
    if not feedparser:
        return []

    url = config["url"]
    category = config["category"]
    weight = config["weight"]
    trends = []

    try:
        # Use requests first for better timeout control, then parse
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Velora Trend Engine)"
        })
        if resp.status_code != 200:
            print(f"      Warning: {name} returned HTTP {resp.status_code}")
            return []

        feed = feedparser.parse(resp.text)

        for entry in feed.entries[:15]:  # Max 15 items per source
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            published = entry.get("published", entry.get("updated", ""))
            link = entry.get("link", "")

            if not title:
                continue

            trends.append({
                "title": title,
                "summary": summary[:200],  # Truncate long summaries
                "source": name,
                "category": category,
                "weight": weight,
                "published": published,
                "link": link,
            })

    except requests.RequestException as e:
        print(f"      Warning: Failed to fetch {name}: {e}")
    except Exception as e:
        print(f"      Warning: Error parsing {name}: {e}")

    return trends


def categorize_trend(title: str, summary: str = "") -> str:
    """Maps a trend to the most relevant category based on keywords."""
    text = (title + " " + summary).lower()

    category_keywords = {
        "space": ["nasa", "mars", "moon", "asteroid", "satellite", "cosmic", "galaxy", "planet", "orbit", "spacecraft"],
        "archaeology": ["ancient", "archaeological", "artifact", "ruins", "excavation", "tomb", "fossil", "civilization"],
        "science": ["research", "study", "scientists", "discovery", "quantum", "physics", "biology", "DNA", "genetic"],
        "technology": ["AI", "robot", "algorithm", "neural", "machine learning", "crypto", "blockchain", "digital"],
        "health": ["health", "virus", "disease", "medical", "brain", "therapy", "vaccine", "mental"],
        "geopolitics": ["war", "military", "government", "nuclear", "classified", "intelligence", "sanctions"],
        "paranormal": ["ghost", "UFO", "unexplained", "paranormal", "supernatural", "mystery", "anomaly"],
        "history": ["history", "historical", "medieval", "empire", "dynasty", "kingdom", "colonial"],
        "environment": ["climate", "earthquake", "volcano", "tsunami", "flood", "wildfire", "storm", "eclipse"],
    }

    best_cat = "trending"
    best_score = 0

    for cat, keywords in category_keywords.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > best_score:
            best_score = score
            best_cat = cat

    return best_cat


def score_trend(trend: dict) -> float:
    """
    Scores a trend for viral potential on our channel.
    
    Factors:
    - Source weight (some feeds are more relevant)
    - Niche keyword density (how well it fits our channel)
    - Blacklist penalty (skip irrelevant trends)
    - Recency bonus (newer = better)
    """
    title = trend.get("title", "").lower()
    summary = trend.get("summary", "").lower()
    text = title + " " + summary
    weight = trend.get("weight", 1.0)

    # Blacklist check — instant disqualification
    if any(bw in text for bw in BLACKLIST_KEYWORDS):
        return -1.0

    score = 0.0

    # Base score from source weight
    score += weight * 2.0

    # Niche keyword density (each matching keyword = +1.5)
    niche_hits = sum(1 for kw in NICHE_KEYWORDS if kw.lower() in text)
    score += niche_hits * 1.5

    # Curiosity/shock word bonus
    curiosity_words = ["mystery", "secret", "hidden", "shocking", "impossible",
                       "unexplained", "banned", "classified", "discover"]
    score += sum(2.0 for w in curiosity_words if w in text)

    # Penalize very short/vague titles
    if len(title) < 15:
        score -= 2.0

    return round(score, 1)


def fetch_daily_trends() -> list:
    """
    Main entry point: Fetches trends from all RSS sources.
    Returns a sorted list of scored trend dicts.
    Uses cache if fresh (< 6 hours old).
    """
    # Check cache first
    cached = _load_cache()
    if cached.get("trends"):
        print("   Using cached trends (less than 6 hours old)")
        return cached["trends"]

    print("   Fetching fresh trends from RSS feeds...")
    all_trends = []

    for name, config in RSS_SOURCES.items():
        print(f"      Fetching: {name}...")
        trends = _fetch_single_feed(name, config)
        all_trends.extend(trends)
        time.sleep(0.5)  # Be polite to servers

    # Score and categorize all trends
    for trend in all_trends:
        trend["virality_score"] = score_trend(trend)
        if trend.get("category") == "trending":
            trend["category"] = categorize_trend(trend["title"], trend.get("summary", ""))

    # Filter out blacklisted (score < 0) and sort by virality
    all_trends = [t for t in all_trends if t["virality_score"] >= 0]
    all_trends.sort(key=lambda t: t["virality_score"], reverse=True)

    # Cache results
    _save_cache(all_trends)

    print(f"   Fetched {len(all_trends)} trends total")
    return all_trends


def get_top_trends(n: int = 10, category: str = None) -> list:
    """
    Returns the top N trends, optionally filtered by category.
    This is the primary function called by content_planner.
    """
    trends = fetch_daily_trends()

    if category:
        trends = [t for t in trends if t.get("category") == category]

    return trends[:n]


def get_trend_summary() -> str:
    """Returns a human-readable summary of today's top trends for logging."""
    trends = get_top_trends(5)
    if not trends:
        return "No trends available"
    
    lines = []
    for i, t in enumerate(trends, 1):
        lines.append(f"   {i}. [{t['category']}] {t['title'][:60]} (score: {t['virality_score']})")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Trend Fetcher...")
    trends = fetch_daily_trends()
    print(f"\nTop 10 Trends:")
    for i, t in enumerate(trends[:10], 1):
        print(f"  {i}. [{t['category']}] {t['title'][:70]} — score: {t['virality_score']}")
