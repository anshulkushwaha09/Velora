"""
viral_engine.py — Self-Optimizing Viral Intelligence Module (v3.0)

Houses all viral optimization logic:
- Script scoring & best-pick selection
- Performance memory & self-learning
- Smart topic trend patterns
- Retention injection / pattern interrupts
- Comment bait generation
- Pillar-aware title engine
- Content pillar performance tracking

This module is stateless (no class needed) — all functions are pure or file-backed.
"""

import os
import json
import random
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# SMART TOPIC ENGINE — Trend Patterns
# Replaces randomness with curiosity-framed topic templates.
# ─────────────────────────────────────────────────────────────────────────────

TREND_PATTERNS = [
    "Scientists shocked by {topic}",
    "Google Maps mystery in {topic}",
    "{topic} banned by authorities",
    "People disappeared in {topic}",
    "NASA satellites captured {topic}",
    "Ancient code hidden inside {topic}",
    "Military sealed off {topic} forever",
    "{topic} — what archaeologists found changes everything",
    "Why {topic} is erased from history books",
]


def apply_trend_pattern(raw_topic: str) -> str:
    """
    Wraps a raw Gemini topic inside a curiosity-maximizing trend pattern.
    This creates the 'curiosity gap' that drives CTR on Shorts.
    """
    pattern = random.choice(TREND_PATTERNS)
    return pattern.format(topic=raw_topic)


# ─────────────────────────────────────────────────────────────────────────────
# TITLE ENGINE — Pillar-Organized High-CTR Title Templates (v3.0)
# ─────────────────────────────────────────────────────────────────────────────

TITLE_FORMATS = {
    "evergreen": [
        "Nobody noticed THIS in {topic}",
        "This place hides a dark secret",
        "Scientists can't explain this",
        "Google Maps hides this location",
        "{topic} the truth they buried",
        "Why is {topic} BANNED?",
        "This changes EVERYTHING about {topic}",
        "The secret inside {topic} will shock you",
    ],
    "trend_fusion": [
        "This trend predicted by ancient India",
        "Modern science just proved {topic}",
        "Breaking: {topic} changes everything",
        "Ancient texts already knew about {topic}",
        "{topic} history is repeating itself",
    ],
    "seasonal": [
        "The REAL reason behind {topic}",
        "Nobody knows THIS about {topic}",
        "{topic} science behind the tradition",
        "What they never taught about {topic}",
    ],
    "experimental": [
        "This will blow your mind",
        "Is {topic} even real?",
        "The most dangerous secret in India",
        "You were NOT supposed to see this",
    ],
}


def generate_viral_title(topic: str, pillar: str = "evergreen") -> str:
    """
    Generates a high-CTR title using pillar-specific templates.
    Keeps it under 75 chars so #Shorts can be appended by main.py.
    """
    formats = TITLE_FORMATS.get(pillar, TITLE_FORMATS["evergreen"])
    template = random.choice(formats)
    title = template.format(topic=topic)

    # Enforce YouTube Shorts title limit (leave room for ' #Shorts')
    if len(title) > 75:
        title = title[:72] + "..."

    return title


# ─────────────────────────────────────────────────────────────────────────────
# SCRIPT SCORING ENGINE
# Scores scripts 0-20+ based on viral markers.
# Higher score = more likely to retain viewers and trigger engagement.
# ─────────────────────────────────────────────────────────────────────────────

def score_script(script: list) -> int:
    """
    Heuristic scorer for viral potential.
    Evaluates: shock words, curiosity density, narrative tension,
    loop structure, and optimal segment count.
    """
    if not script:
        return 0

    text = " ".join([s.get("voiceover_text", "") for s in script]).lower()

    score = 0

    # Shock / attention words (Hindi + English mix for Hinglish content)
    if any(word in text for word in ["shocking", "strange", "kya", "sach"]):
        score += 2

    # Curiosity density -- each curiosity word adds +1
    curiosity_words = ["kyun", "kaise", "raaz", "mystery", "unknown",
                       "secret", "hidden", "banned", "classified"]
    score += sum(1 for word in curiosity_words if word in text)

    # Narrative tension markers ("but" / "however" in Hinglish)
    if "lekin" in text or "par" in text or "magar" in text:
        score += 2

    # Loop structure bonus -- ending echoes the opening (retention loop)
    if script and len(script) >= 2:
        first_words = script[0].get("voiceover_text", "")[:20].lower()
        last_words = script[-1].get("voiceover_text", "")[:20].lower()
        if len(last_words) >= 10 and last_words[:10] in first_words:
            score += 3

    # Optimal length bonus (sweet spot for 30-35s Shorts)
    if 6 <= len(script) <= 14:
        score += 2

    # Penalty for too-short scripts (under-cooked content)
    if len(script) < 5:
        score -= 2

    # Bonus for comment-triggering words in the final segment
    if script:
        final_text = script[-1].get("voiceover_text", "").lower()
        if any(w in final_text for w in ["comment", "batao", "sochte", "likho"]):
            score += 2

    return max(score, 0)  # Floor at 0


def pick_best_script(scripts: list) -> list:
    """
    Returns the highest-scoring script from a list of script candidates.
    Logs all scores for transparency.
    """
    if not scripts:
        return []

    scored = [(score_script(s), i, s) for i, s in enumerate(scripts)]
    scored.sort(key=lambda x: x[0], reverse=True)

    for sc, idx, _ in scored:
        style_labels = ["curiosity", "shock", "story"]
        label = style_labels[idx] if idx < len(style_labels) else f"variant_{idx}"
        print(f"   Script [{label}]: score = {sc}")

    best_score, best_idx, best = scored[0]
    style_labels = ["curiosity", "shock", "story"]
    best_label = style_labels[best_idx] if best_idx < len(style_labels) else f"variant_{best_idx}"
    print(f"   Winner: [{best_label}] with score {best_score}")

    return best


# ─────────────────────────────────────────────────────────────────────────────
# RETENTION INJECTION -- Pattern Interrupt
# Inserts a mid-video curiosity spike to prevent drop-off.
# ─────────────────────────────────────────────────────────────────────────────

_INTERRUPT_VARIANTS = [
    {
        "voiceover_text": "Lekin asli sach abhi baaki hai...",
        "caption_text": "Par **ASLI RAAZ** abhi baaki hai",
        "visual_search_1": "sudden zoom face reaction dark lighting",
        "visual_search_2": "mysterious pause cinematic shadow",
        "visual_style": "fast cut"
    },
    {
        "voiceover_text": "Ruko... yeh toh shuruwat hai...",
        "caption_text": "Ruko... yeh toh **SHURUWAT** hai",
        "visual_search_1": "dramatic reveal dark cinematic close up",
        "visual_search_2": "suspense building torch light ancient",
        "visual_style": "zoom in"
    },
    {
        "voiceover_text": "Par sabse bada twist abhi aayega...",
        "caption_text": "Sabse bada **TWIST** abhi aayega",
        "visual_search_1": "plot twist cinematic dark reveal",
        "visual_search_2": "shocked expression dramatic lighting",
        "visual_style": "fast cut"
    },
]


def inject_pattern_interrupt(script: list) -> list:
    """
    Injects a retention-boosting 'pattern interrupt' at the midpoint
    of scripts longer than 5 segments. Prevents viewer drop-off at 50% mark.
    """
    if not script or len(script) <= 5:
        return script

    interrupt = random.choice(_INTERRUPT_VARIANTS).copy()
    interrupt["id"] = 999

    midpoint = len(script) // 2
    script.insert(midpoint, interrupt)

    print(f"   Pattern interrupt injected at position {midpoint}")
    return script


# ─────────────────────────────────────────────────────────────────────────────
# COMMENT BAIT -- Appended to Final Segment
# ─────────────────────────────────────────────────────────────────────────────

_COMMENT_BAIT_POOL = [
    "Sach kya hai - {topic} ya science?",
    "Tum kya sochte ho? Comment karo",
    "Agar yeh sach hai toh history galat hai?",
    "Real ya myth? Comment mein batao",
    "Kya tumhe lagta hai yeh possible hai?",
    "Type 'RAAZ' agar tum believe karte ho",
    "Comment 'SHIVA' if you want coordinates",
]


def generate_comment_bait(topic: str) -> str:
    """
    Returns a randomized, polarizing comment-triggering CTA.
    Designed to maximize comment count for algorithmic boost.
    """
    bait = random.choice(_COMMENT_BAIT_POOL)
    return bait.format(topic=topic)


def append_comment_bait_to_script(script: list, topic: str) -> list:
    """
    Appends the comment bait text to the final segment's voiceover and caption.
    Ensures every video ends with a direct engagement trigger.
    """
    if not script:
        return script

    bait = generate_comment_bait(topic)

    last = script[-1]
    last["voiceover_text"] = last.get("voiceover_text", "") + " " + bait
    last["caption_text"] = last.get("caption_text", "") + " " + bait

    print(f"   Comment bait appended: \"{bait[:50]}\"")
    return script


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE MEMORY & SELF-LEARNING LOOP (v3.0)
# Thread-safe JSON-backed performance logging with pillar tracking.
# ─────────────────────────────────────────────────────────────────────────────

PERFORMANCE_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "performance_log.json")


def _load_performance_log() -> list:
    """Safely loads the performance log, returns empty list if missing/corrupt."""
    if os.path.exists(PERFORMANCE_LOG_FILE):
        try:
            with open(PERFORMANCE_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_performance_log(data: list):
    """Writes the full performance log back to disk."""
    try:
        with open(PERFORMANCE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"   Warning: Failed to save performance log: {e}")


def log_performance(data: dict):
    """
    Appends a performance entry to performance_log.json.
    Called after each successful upload.
    
    v3.0: Now tracks pillar, topic_category, subject, angle for self-learning.
    """
    log = _load_performance_log()

    entry = {
        "video_id": data.get("video_id", "unknown"),
        "topic": data.get("topic", ""),
        "style": data.get("style", "default"),
        "pillar": data.get("pillar", "evergreen"),
        "topic_category": data.get("topic_category", ""),
        "subject": data.get("subject", ""),
        "angle": data.get("angle", ""),
        "script_score": data.get("script_score", 0),
        "views": data.get("views", 0),
        "likes": data.get("likes", 0),
        "watch_time": data.get("watch_time", 0),
        "title": data.get("title", ""),
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }

    log.append(entry)
    _save_performance_log(log)
    print(f"   Performance logged for video: {entry['video_id']}")


def get_best_style() -> str:
    """
    Analyzes performance_log.json to determine the best-performing script style.
    Scoring formula: score = views*0.5 + likes*0.3 + watch_time*0.2
    Returns the style with the highest average score.
    """
    log = _load_performance_log()

    if not log:
        return "curiosity"

    style_scores = {}

    for entry in log:
        style = entry.get("style", "default")
        views = entry.get("views", 0)
        likes = entry.get("likes", 0)
        watch_time = entry.get("watch_time", 0)

        perf_score = views * 0.5 + likes * 0.3 + watch_time * 0.2

        if style not in style_scores:
            style_scores[style] = []
        style_scores[style].append(perf_score)

    style_averages = {
        style: sum(scores) / len(scores)
        for style, scores in style_scores.items()
        if scores
    }

    if not style_averages:
        return "curiosity"

    best_style = max(style_averages, key=style_averages.get)
    print(f"   Self-learning: Best style = '{best_style}' "
          f"(avg: {style_averages[best_style]:.1f})")

    return best_style


def get_best_topic_type() -> str:
    """
    Analyzes which content pillar performs best.
    Returns: 'evergreen', 'trend_fusion', 'seasonal', or 'experimental'.
    Falls back to 'evergreen' if insufficient data.
    """
    log = _load_performance_log()
    if not log:
        return "evergreen"

    pillar_scores = {}
    for entry in log:
        pillar = entry.get("pillar", "evergreen")
        views = entry.get("views", 0)
        likes = entry.get("likes", 0)
        watch_time = entry.get("watch_time", 0)
        perf = views * 0.5 + likes * 0.3 + watch_time * 0.2

        if pillar not in pillar_scores:
            pillar_scores[pillar] = []
        pillar_scores[pillar].append(perf)

    averages = {
        p: sum(s) / len(s) for p, s in pillar_scores.items() if s
    }

    if not averages:
        return "evergreen"

    best = max(averages, key=averages.get)
    print(f"   Self-learning: Best pillar = '{best}' (avg: {averages[best]:.1f})")
    return best


def collect_performance_data():
    """
    Utility function to backfill real YouTube metrics into performance_log.json.
    Run separately (e.g., via cron) 24-48 hours after upload.
    """
    log = _load_performance_log()
    if not log:
        print("No performance entries to update.")
        return

    try:
        from modules.youtube_uploader import get_authenticated_service
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"Cannot connect to YouTube API: {e}")
        return

    pending = [entry for entry in log if entry.get("views", 0) == 0 and entry.get("video_id", "unknown") != "unknown"]

    if not pending:
        print("All entries already have metrics. Nothing to update.")
        return

    video_ids = [e["video_id"] for e in pending]

    try:
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            response = youtube.videos().list(
                part="statistics",
                id=",".join(batch)
            ).execute()

            stats_map = {}
            for item in response.get("items", []):
                vid = item["id"]
                stats = item.get("statistics", {})
                stats_map[vid] = {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                }

            for entry in log:
                vid = entry.get("video_id")
                if vid in stats_map:
                    entry["views"] = stats_map[vid]["views"]
                    entry["likes"] = stats_map[vid]["likes"]

        _save_performance_log(log)
        print(f"Updated metrics for {len(pending)} videos.")

    except Exception as e:
        print(f"Error fetching YouTube metrics: {e}")
