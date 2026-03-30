import os
import json
import time
import re
import random
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini clients from multiple potential environment variables
# Supports: GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
def _initialize_clients():
    keys = []
    # Check for the primary key
    primary = os.getenv("GEMINI_API_KEY")
    if primary:
        keys.append(primary)
    
    # Check for numbered keys (Expanded to 20 keys for scaling)
    for i in range(1, 21):
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if key and key not in keys:
            keys.append(key)
    
    if not keys:
        raise EnvironmentError(
            "No Gemini API keys found. Please add GEMINI_API_KEY_1, etc., to your .env file."
        )
    
    print(f"📡 Found {len(keys)} Gemini API keys for rotation.")
    return [genai.Client(api_key=k) for k in keys]

clients = _initialize_clients()

# Model fallback chain
FALLBACK_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]

def _call_with_fallback(prompt: str) -> str:
    """
    Attempts to call Gemini using a double-layered fallback:
    1. Tries all models on Client 1
    2. If all fail, switches to Client 2 and tries all models again
    3. Repeats until a success or all (Keys x Models) are exhausted.
    """
    last_error = None

    for i, client_inst in enumerate(clients):
        print(f"   🔑 Using API Key #{i+1}...")
        for model in FALLBACK_MODELS:
            try:
                print(f"      🤖 Trying model: {model}...")
                response = client_inst.models.generate_content(model=model, contents=prompt)
                return response.text.strip()

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"      ⚠️ Quota hit on {model} (Key #{i+1})")
                elif "404" in err_str or "not found" in err_str.lower():
                    print(f"      ⚠️ Model {model} unavailable.")
                else:
                    print(f"      ⚠️ Error on {model}: {e}")
                last_error = e

    raise RuntimeError(
        f"❌ All {len(clients)} API keys and all models hit quota limits.\n"
        f"Last error: {last_error}"
    )


class ContentBrain:
    # Specialized Narrative Styles for years of non-repeating content
    NARRATIVE_STYLES = {
        "FORBIDDEN_ARCHAEOLOGY": {
            "hook": "ATOMIC SCIENTIFIC CLAIM (Debunk modern science)",
            "focus": "Ancient engineering, structural impossibilities, and lost technologies that modern science cannot replicate.",
            "keywords": "precision, monolithic, unknown machinery, advanced metallurgy"
        },
        "DARK_FOLKLORE": {
            "hook": "ATOMIC TABOO CLAIM (Cursed/Forbidden secrets)",
            "focus": "Restricted areas, sunset bans, ancient curses, and the 'Fear of the Unknown' history of sacred sites.",
            "keywords": "cursed, restricted, forbidden, ritual, spiritual entity"
        },
        "MANTRA_SCIENCE": {
            "hook": "ATOMIC BIOLOGICAL CLAIM (Sound frequencies)",
            "focus": "Bio-acoustics, the physics of vibrations, resonance, and how ancient chants interact with human cells/DNA.",
            "keywords": "resonance, frequency, vibration, bio-acoustic, cellular memory"
        },
        "GENERAL_ELITE": {
            "hook": "ATOMIC HISTORICAL CLAIM (The 'Hidden Truth')",
            "focus": "A general 'Premium Documentary' style focused on the most mysterious and majestic aspects of Indian heritage.",
            "keywords": "hidden, secret, power, ancient wisdom, mystery"
        },
        "ALIEN_THEORY": {
            "hook": "ATOMIC EXTRATERRESTRIAL CLAIM (Ancient contact)",
            "focus": "Vimanas, nuclear war evidence in Mahabharata, Vedic flying machines, and ancient astronaut theories backed by text references.",
            "keywords": "vimana, nuclear, extraterrestrial, ancient contact, Vedic spacecraft"
        },
        "HIDDEN_KNOWLEDGE": {
            "hook": "ATOMIC SUPPRESSION CLAIM (They don't want you to know)",
            "focus": "Suppressed Vedic sciences, banned ancient texts, destroyed libraries, and knowledge deliberately erased from history.",
            "keywords": "suppressed, banned, erased, classified, hidden manuscript"
        },
        "REINCARNATION_FILES": {
            "hook": "ATOMIC PARANORMAL CLAIM (Scientifically documented)",
            "focus": "Verified past-life memory cases from India, karma science, and documented reincarnation stories that stumped researchers.",
            "keywords": "past life, reincarnation, karma, documented, verified memory"
        },
        "EPIC_BATTLES": {
            "hook": "ATOMIC WAR CLAIM (Ancient warfare reframed)",
            "focus": "Mahabharata and Ramayana battles retold with modern military framing — weapons, strategy, and scale that rivals any modern war.",
            "keywords": "Brahmastra, Divyastra, war, ancient weapon, celestial army"
        }
    }

    # Main Channel Niches — expanded for multi-year content variety
    NICHES = [
        "Indian Mythology",
        "Ancient Mysteries",
        "Temple Secrets",
        "Spiritual Science",
        "Untold History",
        "Lost Cities & Civilizations",
        "Ancient Indian Weapons & Warfare",
        "Vedic Astrology & Cosmic Science",
        "Cursed Places & Paranormal India",
        "Ancient Indian Scientists & Inventions"
    ]

    HISTORY_FILE = "topic_history.json"
    HISTORY_LIMIT = 200  # Remember last N topics to avoid repeats (scaled for 3 shorts/day)

    def _load_history(self) -> list:
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self, history: list):
        try:
            with open(self.HISTORY_FILE, "w") as f:
                json.dump(history[-self.HISTORY_LIMIT:], f, indent=2)
        except Exception:
            pass

    def get_trending_topic(self):
        """
        Rotates through Styles sequentially for perfect channel balance.
        """
        history   = self._load_history()
        style_keys = list(self.NARRATIVE_STYLES.keys())
        
        style_index = len(history) % len(style_keys)
        style_key   = style_keys[style_index]
        style       = self.NARRATIVE_STYLES[style_key]
        
        # Pick a random niche for cross-topic variety
        current_niche = random.choice(self.NICHES)
        
        now       = datetime.utcnow()
        date_str  = now.strftime("%Y-%m-%d")
        history   = self._load_history()

        # 🚫 STRICT BLACKLIST: Avoid the "Netaji" loop.
        blacklist = "\n- Netaji Subhash Chandra Bose\n- His disappearance or plane crash\n- Gumnami Baba"
        
        avoid_list = "\n".join(f"  - {t}" for t in history[-15:])
        
        prompt = (
            f"You are an ELITE viral researcher for {current_niche}.\n"
            f"Today is {date_str}. Narrative Style: **{style_key}**\n"
            f"Focus: {style['focus']}\n\n"
            f"🎯 YOUR TASK: Generate ONE highly specific, shocking, and ORIGINAL topic in the niche of {current_niche}.\n"
            f"STRICT RULE 1: The topic MUST be about Indian Mythology, History, or Mysteries.\n"
            f"STRICT RULE 2: DO NOT repeat anything from this history:\n{avoid_list}\n"
            f"STRICT RULE 3: DO NOT use any of these blacklisted topics:{blacklist}\n"
            f"Return ONLY the topic string (max 15 words)."
        )

        topic = _call_with_fallback(prompt)
        print(f"🎯 Style: {style_key} | Topic: {topic}")

        # Save to history & return with niche
        history.append(f"[{style_key}] [{current_niche}] {topic}")
        self._save_history(history)

        return topic, current_niche

    def generate_script(self, topic):
        """
        Generates a MASTER ELITE Hindi script with VIRAL retention rules (v9.0).
        """
        print(f"📝 Writing ELITE MASTER script for: {topic}...")
        prompt = f"""
    You are an ELITE viral YouTube Shorts script generator optimized for MAXIMUM RETENTION and REALISTIC STOCK FOOTAGE.
    Topic: {topic}

    ━━━━━━━━━━━━━━━━━━━━━━
    📊 CORE OBJECTIVE:
    Create a HIGH-RETENTION YouTube Short (28–34 seconds) that prevents viewer drop.

    ━━━━━━━━━━━━━━━━━━━━━━
    📏 STRICT TIMING RULES:
    - Total Duration: 28–34 seconds ONLY
    - Total Scenes: 12 ONLY
    - Each Scene: 2–2.5 seconds
    - Each voiceover: MAX 6 WORDS (natural flow, NOT robotic).
    ⚠️ IMPORTANT: 9 words takes too long (4+ seconds). Keep it to 5-6 words.

    ━━━━━━━━━━━━━━━━━━━━━━
    🧠 RETENTION STRUCTURE (follow EXACTLY):
    1. Scene 1  → SHOCK CLAIM (no intro, no question)
    2. Scene 2  → INSTANT PROOF (visual confirmation)
    3. Scenes 3–4  → FAST FACTS
    4. Scenes 5–8  → ESCALATION (bigger reveal)
    5. Scenes 9–10 → TWIST / NEW INFO
    6. Scenes 11–12 → LOOP BACK (connect to hook)

    ⚠️ CRITICAL RULES:
    - Proof MUST appear in Scene 2
    - NO slow explanation anywhere
    - EVERY scene must increase curiosity
    - Maintain CONTINUOUS STORY FLOW between scenes
    - Rapid-fire delivery: One key fact per scene.

    ━━━━━━━━━━━━━━━━━━━━━━
    🎬 STOCK VISUAL RULES:
    - visual_search_1: PRIMARY searchable keyword (e.g., "ancient temple aerial").
    - visual_search_2: SECONDARY backup keyword (e.g., "hindu stone carving").
    - visual_style: Aesthetic direction (e.g., "cinematic drone", "dramatic close up").
    - ⚠️ NO placeholder text. ONLY realistic, searchable stock keywords.

    ━━━━━━━━━━━━━━━━━━━━━━
    🎭 TONE & LANGUAGE:
    - Voiceover: Conversational PHONETIC HINGLISH (Hindi in Roman script).
    - ⚠️ PHONETIC RULE: Use "shehar", "banaya gaya", "pathar se" (natural spoken Hindi).
    - Subtitles: ALL-CAPS ENGLISH ONLY for 'caption_text'.
    - ⚠️ SUBTITLE RULE: Wrap 1-2 powerful words in **stars** (e.g., **ANCIENT SECRET**).

    OUTPUT FORMAT: Return ONLY a clean JSON array of 12 objects.
    [
      {{
        "id": 1,
        "voiceover_text": "...",
        "caption_text": "...",
        "visual_search_1": "...",
        "visual_search_2": "...",
        "visual_style": "..."
      }}
    ]
    """
        raw_text = _call_with_fallback(prompt)
        clean_text = raw_text.replace('```json', '').replace('```', '').strip()

        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            print("❌ JSON Error. Recovery attempt...")
            return None

    def generate_description(self, topic: str, script_data: list) -> str:
        """
        Generates a unique, dynamic YouTube description for each Short.

        Uses the actual script scenes so the description references real facts
        from the video — not a generic template.
        Falls back to a safe default if the API call fails.
        """
        print("✍️  Generating video description...")

        # Extract scene text to give Gemini real content to work with
        scene_texts = " | ".join(
            scene.get("voiceover_text", "") for scene in (script_data or [])[:5]
        )

        prompt = (
            f"You are writing a YouTube Short description for a video about: \"{topic}\"\n\n"
            f"The video covers these key points:\n{scene_texts}\n\n"
            f"Write a YouTube description following this EXACT format (no extra text):\n\n"
            f"Line 1: A single hook emoji + the topic as a punchy 1-line opener\n"
            f"Line 2: (blank)\n"
            f"Lines 3-4: A 2-sentence teaser that references a specific surprising fact "
            f"from the video WITHOUT giving away the ending. Make it curiosity-driven.\n"
            f"Line 5: (blank)\n"
            f"Line 6: ━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Line 7: 🔔 Subscribe for daily mind-blowing facts!\n"
            f"Line 8: (blank)\n"
            f"Line 9: ━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Line 10: 10 relevant hashtags starting with #Shorts\n"
            f"Line 11: (blank)\n"
            f"Line 12: 🔔 Like and Subscribe for daily amazing facts! 🚀"
        )

        try:
            description = _call_with_fallback(prompt)
            return description.strip()
        except Exception as e:
            print(f"   ⚠️ Description generation failed ({e}), using default.")
            # Safe fallback — still better than nothing
            return (
                f"🤯 {topic}\n\n"
                f"What if everything you thought you knew was wrong? "
                f"This Short uncovers a surprising truth that most people never learn.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔔 Subscribe for daily mind-blowing facts!\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"#Shorts #DidYouKnow #Facts #Science #MindBlowing "
                f"#Educational #Viral #FunFacts #Amazing #LearnSomethingNew"
            )


# --- TESTING THE MODULE ---
if __name__ == "__main__":
    brain = ContentBrain()
    topic = brain.get_trending_topic()
    script = brain.generate_script(topic)
    desc   = brain.generate_description(topic, script)
    print("\n📋 Description preview:\n")
    print(desc)

    with open("script.json", "w") as f:
        json.dump(script, f, indent=4)
        print("\n✅ Script saved to script.json")