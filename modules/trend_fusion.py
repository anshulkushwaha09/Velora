"""
trend_fusion.py — Trend + Niche Fusion Engine (Part 2)

Uses Gemini to intelligently fuse real-world trending topics with the
channel's core niche (Indian mythology, mysteries, hidden history).

The key insight: instead of covering a trend directly (which breaks brand),
we ASK: "How does this modern trend connect to an ancient mystery?"

Examples:
  Trend: "AI surveillance"  →  "Did ancient civilizations already have hidden surveillance?"
  Trend: "Mars water"       →  "Did Vedic texts predict life beyond Earth?"
  Trend: "Solar storm"      →  "Ancient Indian scriptures warned about cosmic destruction"
"""

import os
import json
import random

# Import the shared Gemini caller from brain module
# This reuses the existing API key rotation and fallback logic
from modules.brain import _call_with_fallback


# ─────────────────────────────────────────────────────────────────────────────
# Fusion Templates — used as fallback if Gemini is unavailable
# ─────────────────────────────────────────────────────────────────────────────

FUSION_TEMPLATES = [
    "Did ancient Indian texts predict {trend}?",
    "Scientists found {trend} — but Vedic scholars knew 5000 years ago",
    "{trend} is making headlines — but an ancient temple already had the answer",
    "The connection between {trend} and forgotten Indian science",
    "Why {trend} is proof that ancient civilizations were more advanced",
    "Modern {trend} was described in Mahabharata thousands of years ago",
    "{trend} — and what the Rishis already knew about it",
    "Government hides the link between {trend} and ancient Indian technology",
]


# ─────────────────────────────────────────────────────────────────────────────
# Core Fusion Function
# ─────────────────────────────────────────────────────────────────────────────

def generate_fused_topic(niche: str, trend_title: str, trend_summary: str = "") -> str:
    """
    Uses Gemini to fuse a real-world trend with the channel's niche.
    
    Args:
        niche: The channel niche context (e.g., "Indian Mythology")
        trend_title: The trending topic headline
        trend_summary: Optional short description of the trend
    
    Returns:
        A fused topic string that feels both timely AND on-brand.
    """
    context = trend_summary if trend_summary else trend_title

    prompt = (
        f"You are a viral content strategist for a YouTube Shorts channel about "
        f"Indian mythology, ancient mysteries, and hidden history.\n\n"
        f"A topic is trending globally right now:\n"
        f"TREND: \"{trend_title}\"\n"
        f"CONTEXT: {context}\n\n"
        f"Your channel niche: {niche}\n\n"
        f"YOUR TASK: Create ONE viral YouTube Short topic that FUSES this trend "
        f"with Indian mythology, ancient history, or spiritual science.\n\n"
        f"RULES:\n"
        f"1. The topic MUST feel connected to the trend (timely), but through the "
        f"lens of ancient India (on-brand).\n"
        f"2. Must create a curiosity gap — viewer thinks 'wait, how are these connected?'\n"
        f"3. Must be specific (name a text, temple, event, or concept).\n"
        f"4. Must NOT be generic news. Must feel like a DISCOVERY.\n"
        f"5. Max 20 words.\n"
        f"6. Use Hinglish naturally if it adds punch.\n\n"
        f"EXAMPLES of good fusion:\n"
        f"- Trend: 'AI surveillance' → 'Arthashashtra mein likha tha AI jaisa surveillance system'\n"
        f"- Trend: 'Mars water discovery' → 'Vedic texts predicted water on Mars 5000 years ago'\n"
        f"- Trend: 'Quantum entanglement' → 'Rishis already knew about quantum consciousness'\n\n"
        f"Return ONLY the fused topic string. No explanation."
    )

    try:
        topic = _call_with_fallback(prompt)
        # Clean up
        topic = topic.replace('"', '').replace("'", "").strip()
        if topic:
            return topic
    except Exception as e:
        print(f"   Warning: Gemini fusion failed ({e}), using template fallback")

    # Fallback: use local template
    template = random.choice(FUSION_TEMPLATES)
    return template.format(trend=trend_title[:50])


def batch_fuse_trends(niche: str, trends: list, max_fusions: int = 3) -> list:
    """
    Fuses multiple trends with the niche. Returns list of fused topic dicts.
    
    Args:
        niche: Channel niche
        trends: List of trend dicts (from trend_fetcher)
        max_fusions: Maximum number of fusions to generate (limits API calls)
    
    Returns:
        List of dicts: [{"original_trend": ..., "fused_topic": ..., "category": ...}, ...]
    """
    fused = []

    for trend in trends[:max_fusions]:
        title = trend.get("title", "")
        summary = trend.get("summary", "")
        category = trend.get("category", "trending")

        print(f"   Fusing trend: \"{title[:50]}...\"")
        fused_topic = generate_fused_topic(niche, title, summary)

        fused.append({
            "original_trend": title,
            "fused_topic": fused_topic,
            "category": category,
            "source": trend.get("source", "unknown"),
            "virality_score": trend.get("virality_score", 0),
            "pillar": "trend_fusion",
        })

    return fused


# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Test with mock trends
    mock_trends = [
        {"title": "NASA discovers high water content on Mars", "summary": "New rover data suggests water beneath surface", "category": "space", "virality_score": 8.0},
        {"title": "AI model passes Turing test", "summary": "A new AI system fooled human judges", "category": "technology", "virality_score": 7.5},
    ]
    
    results = batch_fuse_trends("Indian Mythology", mock_trends)
    for r in results:
        print(f"\n  Original: {r['original_trend']}")
        print(f"  Fused:    {r['fused_topic']}")
