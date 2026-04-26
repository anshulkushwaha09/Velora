"""
content_planner.py — 4-Pillar Content Orchestrator (Parts 5, 6, 11, 13)

The strategic brain that decides WHAT type of content to produce today.
Implements the 4-pillar content model:

  50% Evergreen   — Core niche from topic bank (angle rotation)
  30% Trend Fusion — Real trends fused with niche via Gemini
  15% Seasonal     — Festival/event-based content
  5%  Experimental — Wild card viral angles

Also handles:
- Multi-topic candidate generation (all text, no Pexels)
- Virality scoring for topic selection
- Seasonal calendar awareness
- Content rotation tracking
"""

import os
import json
import random
from datetime import datetime

from modules.topic_bank import TopicBank, EXPANSION_ANGLES
from modules.trend_fetcher import get_top_trends, fetch_daily_trends
from modules.trend_fusion import generate_fused_topic, batch_fuse_trends
from modules.brain import _call_with_fallback


# ─────────────────────────────────────────────────────────────────────────────
# Content Mix Configuration
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_MIX = {
    "evergreen": 0.50,
    "trend_fusion": 0.30,
    "seasonal": 0.15,
    "experimental": 0.05,
}

# ─────────────────────────────────────────────────────────────────────────────
# Seasonal Calendar — Indian festivals, astronomical events, key dates
# Lead time: content is generated 2-3 days BEFORE the event
# ─────────────────────────────────────────────────────────────────────────────

SEASONAL_EVENTS = [
    # Major Hindu Festivals (approximate dates — vary by lunar calendar)
    {"name": "Makar Sankranti", "month": 1, "day": 14, "topic_seed": "Sun worship science in ancient India", "niche": "Spiritual Science"},
    {"name": "Republic Day", "month": 1, "day": 26, "topic_seed": "Ancient Indian republic systems before democracy", "niche": "Untold History"},
    {"name": "Maha Shivaratri", "month": 3, "day": 8, "topic_seed": "Scientific secrets behind Shiva Linga vibrations", "niche": "Spiritual Science"},
    {"name": "Holi", "month": 3, "day": 25, "topic_seed": "Hidden chemistry behind ancient color science", "niche": "Ancient Indian Scientists & Inventions"},
    {"name": "Ram Navami", "month": 4, "day": 17, "topic_seed": "Archaeological evidence of Ram's birth city", "niche": "Indian Mythology"},
    {"name": "Hanuman Jayanti", "month": 4, "day": 23, "topic_seed": "Scientific analysis of Hanuman's powers in Ramayana", "niche": "Indian Mythology"},
    {"name": "Buddha Purnima", "month": 5, "day": 12, "topic_seed": "Neuroscience of Buddhist meditation techniques", "niche": "Spiritual Science"},
    {"name": "Rath Yatra", "month": 7, "day": 7, "topic_seed": "Engineering secrets of Jagannath temple chariot", "niche": "Temple Secrets"},
    {"name": "Independence Day", "month": 8, "day": 15, "topic_seed": "Ancient Indian military strategies that inspired modern warfare", "niche": "Untold History"},
    {"name": "Janmashtami", "month": 8, "day": 26, "topic_seed": "Archaeological search for Krishna's Dwaraka", "niche": "Indian Mythology"},
    {"name": "Ganesh Chaturthi", "month": 9, "day": 7, "topic_seed": "Elephant-headed deity symbolism across world civilizations", "niche": "Ancient Mysteries"},
    {"name": "Navratri", "month": 10, "day": 3, "topic_seed": "9 forms of energy in Vedic quantum physics", "niche": "Spiritual Science"},
    {"name": "Dussehra", "month": 10, "day": 12, "topic_seed": "Was Lanka a real island? Satellite evidence", "niche": "Indian Mythology"},
    {"name": "Diwali", "month": 11, "day": 1, "topic_seed": "Ancient light science and oil lamp frequencies", "niche": "Spiritual Science"},
    {"name": "Guru Nanak Jayanti", "month": 11, "day": 15, "topic_seed": "Guru Nanak's mysterious travels to forbidden lands", "niche": "Untold History"},
    {"name": "Winter Solstice", "month": 12, "day": 21, "topic_seed": "Ancient Indian observatories that tracked solstice perfectly", "niche": "Ancient Indian Scientists & Inventions"},

    # Astronomical Events (recurring)
    {"name": "Solar Eclipse Season", "month": 4, "day": 8, "topic_seed": "Ancient Indians predicted eclipses with mathematical precision", "niche": "Vedic Astrology & Cosmic Science"},
    {"name": "Lunar Eclipse Season", "month": 10, "day": 28, "topic_seed": "Why ancient texts banned eating during eclipses — science confirms", "niche": "Vedic Astrology & Cosmic Science"},
]

# How many days before an event to generate seasonal content
SEASONAL_LEAD_DAYS = 3


# ─────────────────────────────────────────────────────────────────────────────
# Virality Scoring for Topics
# ─────────────────────────────────────────────────────────────────────────────

def score_topic_virality(topic: str, pillar: str, trend_score: float = 0.0) -> float:
    """
    Scores a topic candidate for viral potential.
    Used to rank all candidates and pick the BEST one for video production.
    
    Factors:
    - Curiosity keywords (+2 each)
    - Shock/attention words (+3 each)
    - Pillar bonus (trends get recency boost)
    - Length optimization
    - Trend strength (for trend_fusion pillar)
    """
    text = topic.lower()
    score = 0.0

    # Curiosity keywords
    curiosity = ["mystery", "secret", "hidden", "unknown", "raaz", "kaise", "kyun",
                 "banned", "classified", "disappeared", "impossible"]
    score += sum(2.0 for w in curiosity if w in text)

    # Shock / attention words
    shock = ["shocking", "dangerous", "terrifying", "nuclear", "warning",
             "scientists", "NASA", "government", "proof", "evidence"]
    score += sum(3.0 for w in shock if w in text)

    # Pillar-specific bonuses
    pillar_bonus = {
        "evergreen": 2.0,       # Solid baseline
        "trend_fusion": 5.0,    # Timeliness bonus
        "seasonal": 4.0,        # Cultural relevance bonus
        "experimental": 1.0,    # Risky but creative
    }
    score += pillar_bonus.get(pillar, 1.0)

    # Trend strength bonus (for trend-fused topics)
    if trend_score > 0:
        score += trend_score * 0.5

    # Length penalty (too short = vague, too long = unfocused)
    words = len(topic.split())
    if 5 <= words <= 18:
        score += 2.0
    elif words < 4:
        score -= 3.0

    return round(max(score, 0), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Topic Generators (one per pillar)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_evergreen_topic(bank: TopicBank) -> dict:
    """
    Pillar 1: Generates an evergreen topic from the topic bank.
    Picks a subject + unused angle and uses Gemini to create a specific topic.
    """
    subject, niche, angle = bank.get_available_subject()
    if not subject:
        return None

    prompt = (
        f"You are a viral YouTube Shorts researcher.\n\n"
        f"Subject: \"{subject}\"\n"
        f"Angle: {angle}\n"
        f"Niche: {niche}\n\n"
        f"Generate ONE specific, shocking YouTube Short topic about '{subject}' "
        f"viewed through the '{angle}' lens.\n\n"
        f"RULES:\n"
        f"- Must be specific (name a fact, event, or claim)\n"
        f"- Must trigger curiosity\n"
        f"- Max 18 words\n"
        f"- Must be about Indian mythology, history, or mysteries\n"
        f"Return ONLY the topic string."
    )

    try:
        topic = _call_with_fallback(prompt)
        topic = topic.replace('"', '').strip()
    except Exception:
        topic = f"The {angle} truth about {subject} that nobody talks about"

    return {
        "topic": topic,
        "niche": niche,
        "pillar": "evergreen",
        "subject": subject,
        "angle": angle,
        "virality_score": score_topic_virality(topic, "evergreen"),
    }


def _generate_trend_topic(niche: str) -> dict:
    """
    Pillar 2: Fetches a real trend and fuses it with the channel niche.
    """
    trends = get_top_trends(n=5)
    if not trends:
        return None

    # Pick a high-scoring trend
    trend = trends[0]  # Already sorted by virality

    fused_topic = generate_fused_topic(niche, trend["title"], trend.get("summary", ""))

    return {
        "topic": fused_topic,
        "niche": niche,
        "pillar": "trend_fusion",
        "original_trend": trend["title"],
        "trend_category": trend.get("category", "trending"),
        "virality_score": score_topic_virality(fused_topic, "trend_fusion", trend.get("virality_score", 0)),
    }


def _generate_seasonal_topic() -> dict:
    """
    Pillar 3: Checks if any seasonal event is approaching and generates
    a relevant topic. Returns None if no event is near.
    """
    today = datetime.utcnow()

    for event in SEASONAL_EVENTS:
        try:
            event_date = datetime(today.year, event["month"], event["day"])
            # Check both before and on the day
            diff = (event_date - today).days
            if 0 <= diff <= SEASONAL_LEAD_DAYS:
                topic_seed = event["topic_seed"]
                niche = event["niche"]

                # Enhance with Gemini
                try:
                    prompt = (
                        f"A major event is coming: {event['name']} (in {diff} days).\n"
                        f"Base topic: \"{topic_seed}\"\n\n"
                        f"Rewrite this into a viral, curiosity-driven YouTube Short topic.\n"
                        f"Make it shocking and specific. Max 18 words.\n"
                        f"Return ONLY the topic string."
                    )
                    topic = _call_with_fallback(prompt).replace('"', '').strip()
                except Exception:
                    topic = topic_seed

                return {
                    "topic": topic,
                    "niche": niche,
                    "pillar": "seasonal",
                    "event": event["name"],
                    "days_until": diff,
                    "virality_score": score_topic_virality(topic, "seasonal"),
                }
        except ValueError:
            continue

    return None


def _generate_experimental_topic() -> dict:
    """
    Pillar 4: Wild card — Gemini generates something unexpected.
    Designed to test new content angles the algorithm might favor.
    """
    experimental_prompts = [
        "What's the most controversial unsolved mystery in Indian history?",
        "Name one ancient Indian invention that would shock a modern scientist.",
        "What's the strangest paranormal event documented in India?",
        "What ancient Indian text contains information that sounds like science fiction?",
        "What's the most dangerous archaeological site in India and why?",
    ]

    prompt_seed = random.choice(experimental_prompts)

    try:
        prompt = (
            f"You are a viral content strategist.\n\n"
            f"Question: {prompt_seed}\n\n"
            f"Turn the answer into a viral YouTube Short topic.\n"
            f"Must be specific, shocking, and curiosity-driven.\n"
            f"Max 18 words. Return ONLY the topic string."
        )
        topic = _call_with_fallback(prompt).replace('"', '').strip()
    except Exception:
        topic = "The one ancient Indian secret that modern science cannot explain"

    return {
        "topic": topic,
        "niche": "Ancient Mysteries",
        "pillar": "experimental",
        "virality_score": score_topic_virality(topic, "experimental"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def plan_today(num_candidates: int = 5) -> list:
    """
    Main entry point: Generates multiple topic candidates across all 4 pillars
    based on the content mix ratio, scores them, and returns them sorted.
    
    The caller (main.py) picks the BEST candidate and produces ONE video.
    
    Args:
        num_candidates: Total number of topic candidates to generate
    
    Returns:
        List of topic dicts sorted by virality_score (best first).
        Each dict has: topic, niche, pillar, virality_score, + pillar-specific metadata
    """
    print("\n   Planning today's content across 4 pillars...")
    print("   " + "=" * 50)

    bank = TopicBank()
    candidates = []

    # Determine how many candidates per pillar based on mix ratios
    # For 5 candidates: 2-3 evergreen, 1-2 trend, 0-1 seasonal, 0-1 experimental
    pillar_counts = {}
    remaining = num_candidates
    for pillar, ratio in sorted(CONTENT_MIX.items(), key=lambda x: x[1], reverse=True):
        count = max(1, round(num_candidates * ratio))
        count = min(count, remaining)
        pillar_counts[pillar] = count
        remaining -= count
        if remaining <= 0:
            break

    # Generate Evergreen candidates
    for _ in range(pillar_counts.get("evergreen", 2)):
        try:
            result = _generate_evergreen_topic(bank)
            if result:
                candidates.append(result)
                print(f"   [EVERGREEN] {result['topic'][:60]}... (score: {result['virality_score']})")
        except Exception as e:
            print(f"   Warning: Evergreen generation failed: {e}")

    # Generate Trend Fusion candidates
    for _ in range(pillar_counts.get("trend_fusion", 1)):
        try:
            niche = random.choice(["Indian Mythology", "Ancient Mysteries", "Temple Secrets", "Spiritual Science"])
            result = _generate_trend_topic(niche)
            if result:
                candidates.append(result)
                print(f"   [TREND]     {result['topic'][:60]}... (score: {result['virality_score']})")
        except Exception as e:
            print(f"   Warning: Trend fusion failed: {e}")

    # Generate Seasonal candidate (only if event is near)
    if pillar_counts.get("seasonal", 0) > 0:
        try:
            result = _generate_seasonal_topic()
            if result:
                candidates.append(result)
                print(f"   [SEASONAL]  {result['topic'][:60]}... (score: {result['virality_score']})")
            else:
                # No seasonal event near — fill with evergreen instead
                fallback = _generate_evergreen_topic(bank)
                if fallback:
                    candidates.append(fallback)
                    print(f"   [EVERGREEN] (no seasonal event) {fallback['topic'][:50]}... (score: {fallback['virality_score']})")
        except Exception as e:
            print(f"   Warning: Seasonal generation failed: {e}")

    # Generate Experimental candidate
    if pillar_counts.get("experimental", 0) > 0:
        try:
            result = _generate_experimental_topic()
            if result:
                candidates.append(result)
                print(f"   [EXPERIMENT]{result['topic'][:60]}... (score: {result['virality_score']})")
        except Exception as e:
            print(f"   Warning: Experimental generation failed: {e}")

    # Sort all candidates by virality score
    candidates.sort(key=lambda c: c.get("virality_score", 0), reverse=True)

    print(f"\n   Generated {len(candidates)} topic candidates")
    if candidates:
        best = candidates[0]
        print(f"   Best candidate: [{best['pillar'].upper()}] \"{best['topic'][:60]}...\" "
              f"(score: {best['virality_score']})")
    print("   " + "=" * 50)

    return candidates


def get_topic_bank() -> TopicBank:
    """Returns a TopicBank instance for use by other modules."""
    return TopicBank()


# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    candidates = plan_today(num_candidates=5)
    print(f"\nAll candidates ranked:")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. [{c['pillar']}] {c['topic'][:70]} — score: {c['virality_score']}")
