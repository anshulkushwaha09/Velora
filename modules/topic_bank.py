"""
topic_bank.py — Persistent Topic Memory + Infinite Expansion Engine (Parts 3 & 4)

The brain behind topic exhaustion prevention:
- Tracks every subject the channel has covered
- Rotates through 12 'angles' per subject (scientific, forbidden, etc.)
- Enforces cooldown periods so subjects don't repeat too soon
- Auto-expands high-performing subjects into subtopic trees
- Seeds itself with ~50 core Indian mythology subjects on first run

Schema (topic_bank.json):
{
    "subjects": {
        "Mount Kailash": {
            "niche": "Temple Secrets",
            "used_angles": ["scientific", "forbidden"],
            "unused_angles": ["psychological", "warfare", ...],
            "subtopics": ["magnetic anomalies", "failed expeditions"],
            "times_used": 2,
            "last_used": "2026-04-20",
            "cooldown_days": 45,
            "avg_score": 12.5
        }
    },
    "stats": {
        "total_generated": 0,
        "last_seeded": "2026-04-26"
    }
}
"""

import os
import json
import random
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Expansion Angles — 12 unique lenses for any subject
# ─────────────────────────────────────────────────────────────────────────────

EXPANSION_ANGLES = [
    "scientific",        # Modern science perspective
    "historical",        # Chronological / archaeological
    "psychological",     # Human behavior, fear, belief systems
    "forbidden",         # Banned, restricted, taboo
    "government secrecy", # Classified, military, cover-ups
    "paranormal",        # Ghosts, curses, unexplained
    "geographical",      # Location-based mystery, maps, coordinates
    "modern relevance",  # How it connects to today's world
    "symbolic meaning",  # Hidden symbolism, coded messages
    "warfare",           # Weapons, battles, strategy
    "spiritual",         # Meditation, energy, cosmic connection
    "technological",     # Advanced tech, engineering marvels
]

# ─────────────────────────────────────────────────────────────────────────────
# Seed Subjects — auto-populated on first run (~50 core topics)
# ─────────────────────────────────────────────────────────────────────────────

SEED_SUBJECTS = {
    # Mythology & Epics
    "Mahabharata": "Indian Mythology",
    "Ramayana": "Indian Mythology",
    "Bhagavad Gita": "Spiritual Science",
    "Kurukshetra War": "Ancient Indian Weapons & Warfare",
    "Brahmastra": "Ancient Indian Weapons & Warfare",
    "Vimana": "Ancient Mysteries",
    "Pushpak Viman": "Ancient Mysteries",
    "Samudra Manthan": "Indian Mythology",
    "Dashavatar": "Indian Mythology",
    "Lanka": "Lost Cities & Civilizations",

    # Temples & Sacred Sites
    "Konark Sun Temple": "Temple Secrets",
    "Kailasa Temple Ellora": "Temple Secrets",
    "Brihadeeswarar Temple": "Temple Secrets",
    "Padmanabhaswamy Temple": "Temple Secrets",
    "Jagannath Puri Temple": "Temple Secrets",
    "Kedarnath Temple": "Temple Secrets",
    "Somnath Temple": "Temple Secrets",
    "Meenakshi Temple": "Temple Secrets",
    "Ram Setu": "Ancient Mysteries",

    # Mountains & Geography
    "Mount Kailash": "Ancient Mysteries",
    "Roopkund Lake": "Cursed Places & Paranormal India",
    "Kuldhara Village": "Cursed Places & Paranormal India",
    "Bhangarh Fort": "Cursed Places & Paranormal India",
    "Magnetic Hill Ladakh": "Ancient Mysteries",
    "Dwaraka Underwater City": "Lost Cities & Civilizations",

    # Ancient Science & Tech
    "Wootz Steel": "Ancient Indian Scientists & Inventions",
    "Sushruta Surgery": "Ancient Indian Scientists & Inventions",
    "Aryabhata": "Vedic Astrology & Cosmic Science",
    "Iron Pillar Delhi": "Ancient Mysteries",
    "Nalanda University": "Untold History",
    "Takshashila University": "Untold History",
    "Vedic Mathematics": "Ancient Indian Scientists & Inventions",
    "Ayurveda Origins": "Spiritual Science",

    # Texts & Knowledge
    "Vedas": "Forbidden Manuscripts",
    "Upanishads": "Spiritual Science",
    "Arthashastra": "Untold History",
    "Yoga Sutras": "Spiritual Science",
    "Surya Siddhanta": "Vedic Astrology & Cosmic Science",
    "Sthapatya Veda": "Ancient Indian Scientists & Inventions",

    # Rulers & Historical Figures
    "Ashoka the Great": "Untold History",
    "Chandragupta Maurya": "Untold History",
    "Prithviraj Chauhan": "Untold History",
    "Rani Padmini": "Untold History",
    "Shivaji Maharaj": "Untold History",

    # Civilizations
    "Indus Valley Civilization": "Lost Cities & Civilizations",
    "Mohenjo-daro": "Lost Cities & Civilizations",
    "Harappa": "Lost Cities & Civilizations",
    "Lothal Ancient Port": "Lost Cities & Civilizations",
    "Sanchi Stupa": "Temple Secrets",

    # Spiritual & Paranormal
    "Chakra System": "Vedic Psychology & Mind Control",
    "Kundalini Energy": "Spiritual Science",
    "Third Eye Pineal Gland": "Vedic Psychology & Mind Control",
    "Akashic Records": "Spiritual Science",
    "Sound Healing Om": "Spiritual Science",
}

# ─────────────────────────────────────────────────────────────────────────────
# Topic Bank Class
# ─────────────────────────────────────────────────────────────────────────────

BANK_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "topic_bank.json")


class TopicBank:
    """
    Persistent topic memory with angle rotation, cooldowns, and expansion.
    Prevents topic exhaustion by ensuring every subject is covered from
    12 different angles before being repeated.
    """

    def __init__(self):
        self.data = self._load()
        # Auto-seed on first run
        if not self.data.get("subjects"):
            self._seed()

    def _load(self) -> dict:
        """Load topic bank from disk."""
        if os.path.exists(BANK_FILE):
            try:
                with open(BANK_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"subjects": {}, "stats": {"total_generated": 0}}

    def _save(self):
        """Persist topic bank to disk."""
        try:
            with open(BANK_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"   Warning: Could not save topic bank: {e}")

    def _seed(self):
        """Seeds the bank with core Indian mythology/history subjects."""
        print("   Seeding topic bank with core subjects...")
        subjects = {}
        for name, niche in SEED_SUBJECTS.items():
            subjects[name] = {
                "niche": niche,
                "used_angles": [],
                "unused_angles": list(EXPANSION_ANGLES),  # All angles available
                "subtopics": [],
                "times_used": 0,
                "last_used": None,
                "cooldown_days": 45,
                "avg_score": 0.0,
            }
        self.data["subjects"] = subjects
        self.data["stats"] = {
            "total_generated": 0,
            "last_seeded": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        self._save()
        print(f"   Seeded {len(subjects)} subjects with {len(EXPANSION_ANGLES)} angles each "
              f"= {len(subjects) * len(EXPANSION_ANGLES)} unique topic slots")

    def get_available_subject(self) -> tuple:
        """
        Returns (subject_name, niche, angle) for a subject that:
        1. Is NOT on cooldown
        2. Has unused angles remaining
        3. Prioritizes subjects with the most unused angles
        
        Returns (None, None, None) if exhausted (shouldn't happen with expansion).
        """
        today = datetime.utcnow()
        candidates = []

        for name, data in self.data["subjects"].items():
            # Check cooldown
            last_used = data.get("last_used")
            if last_used:
                last_date = datetime.strptime(last_used, "%Y-%m-%d")
                cooldown = timedelta(days=data.get("cooldown_days", 45))
                if today - last_date < cooldown:
                    continue

            # Check if angles remain
            unused = data.get("unused_angles", [])
            if not unused:
                continue

            # Score: more unused angles = higher priority (fresher subject)
            priority = len(unused)
            candidates.append((priority, name, data))

        if not candidates:
            # Emergency: reset a random subject's angles
            print("   Warning: All subjects on cooldown or exhausted. Resetting oldest...")
            self._reset_oldest_subject()
            return self.get_available_subject()

        # Weighted random pick — prefer subjects with more unused angles
        # but add randomness so it's not purely sequential
        candidates.sort(key=lambda x: x[0], reverse=True)
        # Pick from top 10 candidates randomly
        top = candidates[:min(10, len(candidates))]
        _, chosen_name, chosen_data = random.choice(top)

        # Pick a random unused angle
        angle = random.choice(chosen_data["unused_angles"])

        return chosen_name, chosen_data["niche"], angle

    def register_usage(self, subject: str, angle: str, score: float = 0.0):
        """
        Marks a subject+angle as used. Updates last_used timestamp.
        Called after successful video production.
        """
        if subject not in self.data["subjects"]:
            # Auto-register new subjects discovered via trends or expansion
            self.data["subjects"][subject] = {
                "niche": "Ancient Mysteries",
                "used_angles": [],
                "unused_angles": list(EXPANSION_ANGLES),
                "subtopics": [],
                "times_used": 0,
                "last_used": None,
                "cooldown_days": 45,
                "avg_score": 0.0,
            }

        subj = self.data["subjects"][subject]
        
        # Move angle from unused to used
        if angle in subj["unused_angles"]:
            subj["unused_angles"].remove(angle)
        if angle not in subj["used_angles"]:
            subj["used_angles"].append(angle)

        # Update metadata
        subj["times_used"] = subj.get("times_used", 0) + 1
        subj["last_used"] = datetime.utcnow().strftime("%Y-%m-%d")

        # Running average score
        old_avg = subj.get("avg_score", 0.0)
        n = subj["times_used"]
        subj["avg_score"] = round(((old_avg * (n - 1)) + score) / n, 1)

        self.data["stats"]["total_generated"] = self.data["stats"].get("total_generated", 0) + 1
        self._save()

    def expand_subject(self, subject: str, subtopics: list = None):
        """
        Part 4: Infinite Expansion — adds subtopics to a subject.
        Each subtopic becomes its own subject in the bank with all 12 angles fresh.
        
        If subtopics not provided, uses Gemini to generate them.
        """
        if subtopics:
            new_topics = subtopics
        else:
            new_topics = self._generate_subtopics(subject)

        if not new_topics:
            return

        niche = self.data["subjects"].get(subject, {}).get("niche", "Ancient Mysteries")
        added = 0

        for sub in new_topics:
            sub = sub.strip()
            if sub and sub not in self.data["subjects"]:
                self.data["subjects"][sub] = {
                    "niche": niche,
                    "used_angles": [],
                    "unused_angles": list(EXPANSION_ANGLES),
                    "subtopics": [],
                    "times_used": 0,
                    "last_used": None,
                    "cooldown_days": 45,
                    "avg_score": 0.0,
                }
                added += 1

                # Also register as subtopic of parent
                if subject in self.data["subjects"]:
                    parent_subs = self.data["subjects"][subject].get("subtopics", [])
                    if sub not in parent_subs:
                        parent_subs.append(sub)
                        self.data["subjects"][subject]["subtopics"] = parent_subs

        if added > 0:
            self._save()
            print(f"   Expanded '{subject}' with {added} new subtopics → "
                  f"{added * len(EXPANSION_ANGLES)} new topic slots")

    def _generate_subtopics(self, subject: str) -> list:
        """Uses Gemini to generate subtopics for a subject."""
        try:
            from modules.brain import _call_with_fallback
            
            prompt = (
                f"You are a content strategist for Indian mythology and ancient mystery content.\n\n"
                f"Core subject: \"{subject}\"\n\n"
                f"Generate 5-7 specific SUBTOPICS that could each be a separate YouTube Short.\n"
                f"Each subtopic must be a specific aspect, event, mystery, or angle — NOT a restatement.\n\n"
                f"Example for 'Mount Kailash':\n"
                f"- Magnetic anomalies detected by satellites\n"
                f"- Failed Russian expedition of 1999\n"
                f"- Underground cave network theories\n"
                f"- Shiva's meditation chamber legend\n"
                f"- Why China banned climbing attempts\n\n"
                f"Return ONLY a JSON array of strings. No explanation.\n"
                f'Example: ["subtopic 1", "subtopic 2", ...]'
            )
            
            result = _call_with_fallback(prompt)
            result = result.replace("```json", "").replace("```", "").strip()
            subtopics = json.loads(result)
            return subtopics if isinstance(subtopics, list) else []

        except Exception as e:
            print(f"   Warning: Subtopic generation failed for '{subject}': {e}")
            return []

    def _reset_oldest_subject(self):
        """Resets the oldest-used subject's angles as emergency fallback."""
        oldest_name = None
        oldest_date = datetime.utcnow()

        for name, data in self.data["subjects"].items():
            last = data.get("last_used")
            if last:
                d = datetime.strptime(last, "%Y-%m-%d")
                if d < oldest_date:
                    oldest_date = d
                    oldest_name = name

        if oldest_name:
            subj = self.data["subjects"][oldest_name]
            subj["unused_angles"] = list(EXPANSION_ANGLES)
            subj["used_angles"] = []
            subj["last_used"] = None
            self._save()
            print(f"   Reset angles for '{oldest_name}' (last used: {oldest_date.strftime('%Y-%m-%d')})")

    def get_high_performers(self, min_score: float = 10.0, n: int = 5) -> list:
        """Returns top N subjects by average score for expansion priority."""
        scored = []
        for name, data in self.data["subjects"].items():
            avg = data.get("avg_score", 0)
            if avg >= min_score:
                scored.append((avg, name))
        scored.sort(reverse=True)
        return [name for _, name in scored[:n]]

    def get_stats(self) -> dict:
        """Returns topic bank coverage statistics."""
        total_subjects = len(self.data["subjects"])
        total_slots = 0
        used_slots = 0
        on_cooldown = 0
        today = datetime.utcnow()

        for data in self.data["subjects"].values():
            total_slots += len(EXPANSION_ANGLES)
            used_slots += len(data.get("used_angles", []))
            last = data.get("last_used")
            if last:
                d = datetime.strptime(last, "%Y-%m-%d")
                if today - d < timedelta(days=data.get("cooldown_days", 45)):
                    on_cooldown += 1

        return {
            "total_subjects": total_subjects,
            "total_slots": total_slots,
            "used_slots": used_slots,
            "remaining_slots": total_slots - used_slots,
            "coverage_pct": round((used_slots / total_slots * 100) if total_slots else 0, 1),
            "on_cooldown": on_cooldown,
            "available": total_subjects - on_cooldown,
            "total_generated": self.data["stats"].get("total_generated", 0),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bank = TopicBank()
    stats = bank.get_stats()
    print(f"\nTopic Bank Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    subject, niche, angle = bank.get_available_subject()
    print(f"\nNext topic: {subject} [{niche}] — angle: {angle}")
