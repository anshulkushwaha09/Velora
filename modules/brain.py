import os
import json
import time
import re
import random
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from modules.viral_engine import apply_trend_pattern, get_best_style

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

# Model fallback chain - using models verified as available in this environment
FALLBACK_MODELS = [
    "gemini-2.0-flash",      # Standard 2.0
    "gemini-2.0-flash-lite", # Lightweight 2.0
    "gemini-2.5-flash",      # Next-gen Flash
    "gemini-2.5-flash-lite", # Next-gen Flash Lite
    "gemini-2.5-pro",       # Next-gen Pro (high quality)
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
                    print(f"      ⚠️ Quota hit on {model} (Key #{i+1}). Waiting 2s...")
                    time.sleep(2) # Small delay to avoid rapid-fire quota burning
                elif "404" in err_str or "not found" in err_str.lower() or "503" in err_str:
                    print(f"      ⚠️ Model {model} unavailable or overloaded.")
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
        },
        "PSYCHOLOGICAL_MIRROR": {
            "hook": "PERSONALIZED CLAIM (Why this matters to YOU)",
            "focus": "Connecting ancient Vedic psychology, birth nakshatras, or karma theory to the viewer's current life struggles and personality.",
            "keywords": "personalized, karma, identity, subconscious, ancient psychology"
        },
        "GLITCH_IN_HISTORY": {
            "hook": "OUT-OF-PLACE ARTIFACT (The glitch in the timeline)",
            "focus": "Ooparts (Out-of-place artifacts) found in India — ancient batteries, rockets, or surgical tools that shouldn't exist.",
            "keywords": "glitch, oopart, impossible artifact, anomaly, forbidden archeology"
        },
        "THE_VOID_EXPERIMENT": {
            "hook": "EXISTENTIAL CLAIM (Simulation vs Reality)",
            "focus": "The physics of 'Maya', ancient meditation experiments, and sound frequencies that can manipulate physical reality.",
            "keywords": "simulation, frequency, maya, vibration, consciousness"
        },
        "BANNED_GEOGRAPHY": {
            "hook": "RESTRICTED ACCESS CLAIM (Why is this pixelated?)",
            "focus": "Hidden portals, satellite-pixelated temples, and underground cities in the Himalayas that governments keep secret.",
            "keywords": "restricted, classified, hidden portal, underground city, secret map"
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
        "Ancient Indian Scientists & Inventions",
        "Restricted Archaeological Sites",
        "Vedic Psychology & Mind Control",
        "Forbidden Manuscripts",
        "Lost DNA Secrets",
        "Ancient Bio-Weaponry"
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
        UPGRADED: Applies viral trend patterns for curiosity-framed topics.
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

        raw_topic = _call_with_fallback(prompt)

        # ── PART 4: SMART TOPIC ENGINE ────────────────────────────────────
        # Wrap the raw Gemini topic in a curiosity-maximizing trend pattern
        topic = apply_trend_pattern(raw_topic)
        print(f"🎯 Style: {style_key} | Raw: {raw_topic} | Final: {topic}")

        # Save to history & return with niche
        history.append(f"[{style_key}] [{current_niche}] {topic}")
        self._save_history(history)

        return topic, current_niche

    # ── PART 1: STYLE DEFINITIONS ──────────────────────────────────────
    # Each style modifies hook tone, narrative pacing, and curiosity density.
    SCRIPT_STYLES = {
        "default": {
            "hook_directive": "Start with a bold, shocking statement. Absolutely NO questions. Must trigger curiosity or pride instantly.",
            "pacing_directive": "Maintain steady tension throughout. Each segment builds on the last.",
            "curiosity_directive": "Add 1 curiosity trigger every 2–3 segments.",
        },
        "curiosity": {
            "hook_directive": "Start with an IMPOSSIBLE-sounding fact that makes the viewer think 'wait, WHAT?'. Use phrases like 'Yeh jagah exist karti hai...' or 'Ek aisi cheez hai jo science explain nahi kar sakti'.",
            "pacing_directive": "Slow-build. Each segment must add ONE new mystery layer. Delay the reveal until segment 8–9. Viewer must feel like they're going deeper into a rabbit hole.",
            "curiosity_directive": "Every 2 segments MUST introduce a new unanswered question. Stack curiosity like layers — never resolve one mystery without opening another.",
        },
        "shock": {
            "hook_directive": "Hit HARD in the first 2 seconds with an outrageous claim: 'Yeh 5000 saal pehle BAN kiya gaya tha' or 'NASA ne ise classify kiya hai'. The viewer must feel URGENCY.",
            "pacing_directive": "RAPID-FIRE pacing. Short punchy sentences. No breathing room. Every segment is a mini-explosion of information.",
            "curiosity_directive": "Use SHOCK markers every segment: 'aur sabse scary baat', 'lekin yeh toh kuch nahi', 'asli shock abhi aayega'. Keep adrenaline HIGH.",
        },
        "story": {
            "hook_directive": "Start with a character or event: 'Ek raja tha jisne...' or '1947 mein ek archaeologist ne...' — pull them into a NARRATIVE, not a fact dump.",
            "pacing_directive": "Classic story arc: setup → rising tension → climax → twist. Make the viewer FEEL like they're watching a movie trailer. Use emotional beats.",
            "curiosity_directive": "Plant 1 'mystery seed' in the setup, water it through the middle, and reveal it at the climax. Ending must reframe the entire story.",
        },
        # v3.0: New styles for trend fusion, controversy, and seasonal pillars
        "trend_fusion": {
            "hook_directive": "Start by referencing a CURRENT world event or trend, then IMMEDIATELY connect it to ancient India: 'Aaj NASA ne jo discover kiya... woh 5000 saal pehle Vedas mein likha tha'. Make it feel like ancient India PREDICTED modern discoveries.",
            "pacing_directive": "Alternate between modern trend facts and ancient parallels. Create a ping-pong effect: modern -> ancient -> modern -> ancient. Build toward the revelation that ancients ALREADY KNEW.",
            "curiosity_directive": "Stack 'HOW DID THEY KNOW?' moments. Every comparison must make the viewer question the timeline of knowledge. End with an open question about what else ancients predicted.",
        },
        "controversy": {
            "hook_directive": "Present a DIVISIVE claim: 'Science says X, but ancient texts say Y - aur proof DONO ke paas hai'. The viewer must feel compelled to PICK A SIDE.",
            "pacing_directive": "Debate-style pacing: present one side -> counter-argument -> escalate -> present shocking evidence -> leave it unresolved. Viewer must feel the TENSION between two worldviews.",
            "curiosity_directive": "Use polarizing language: 'believers say...', 'scientists disagree...', 'but NOBODY can explain this one fact'. Every segment must deepen the divide.",
        },
        "seasonal": {
            "hook_directive": "Start with something EVERYONE knows about the festival/event, then IMMEDIATELY subvert it: 'Har saal Diwali manate ho... par ASLI reason koi nahi jaanta'. Make the familiar feel UNFAMILIAR.",
            "pacing_directive": "Start with the widely known narrative, then peel back layers of hidden meaning. Each segment reveals a deeper, more surprising layer. Climax should be a 'WHAT?! I never knew this' moment.",
            "curiosity_directive": "Use 'you thought you knew' triggers: 'actually...', 'asli raaz yeh hai ki...', 'par textbooks mein yeh nahi padhate'. Make common knowledge feel incomplete.",
        },
    }

    def generate_script(self, topic, style: str = "default"):
        """
        Generates an ELITE v12.0 viral script with HIGH-RETENTION rules.
        UPGRADED: Accepts 'style' parameter (curiosity/shock/story/default)
        to vary hook tone, pacing, and curiosity density.
        Enforces: Visual Intelligence (camera motion + lighting + realism),
        no static/text-only/cartoon visuals.
        """
        # Resolve style config (fall back to default for unknown styles)
        style_cfg = self.SCRIPT_STYLES.get(style, self.SCRIPT_STYLES["default"])

        print(f"📝 Writing ELITE v12.0 VIRAL script for: {topic} [style={style}]...")
        prompt = f"""
You are an elite YouTube Shorts scriptwriter specializing in HIGH-RETENTION Indian mythology, mystery, and hidden history content.

Topic: {topic}
Style: {style.upper()}

🎯 CORE RULES:
1. HOOK (0–2 sec): {style_cfg['hook_directive']}
2. CONTINUOUS STORY FLOW: Entire voiceover must be ONE smooth flowing paragraph. Use natural Hinglish connectors ("aur", "lekin", "phir", "shayad").
3. PAYOFF RULE (MANDATORY): You MUST explicitly reveal the name of the city, temple, or mystery. No vague placeholders.
4. SNAP-CAPTION STYLE (v11.3): You MUST generate 10–12 short segments.
   - voiceover_text: 6–8 words MAX per segment.
   - caption_text: 6–10 words MAX per segment.
   - **HIGHLIGHTING**: Wrap 1-2 "Power Words" in `**double asterisks**` (Yellow). Keep others plain (White).
   - *Example*: "The secret of **ANCIENT CITIES** was finally found."
5. LANGUAGE STYLE: Use conversational Hinglish (Hindi + simple English). Avoid robotic tone. Avoid repeating words like "ancient", "hidden", "mysterious" more than once.
6. LENGTH: 30–35 seconds ONLY (Target 32s). Keep it extremely tight.
7. LOOP ENDING: Ending must connect back to the beginning to make it feel like a cycle.
8. COMMENT BAIT (ELITE RULE): The final scene MUST include a polarizing or curious question to trigger comments.

🧠 PACING RULES (STYLE-SPECIFIC):
- Pacing: {style_cfg['pacing_directive']}
- Curiosity: {style_cfg['curiosity_directive']}

🧠 ANTI-PATTERN RULES (CRITICAL):
- Hook must NOT be a question. Use statements, claims, or revelations.
- Every 2–3 segments must add NEW curiosity (not repeat old info).
- Include 1 mid-video twist that reframes what came before.
- Use Hinglish naturally — don't force it. Mix organically.
- Avoid repetitive filler words: "ancient", "hidden", "secret" (use max once each).
- Reveal actual place/event name clearly. No vagueness.
- Ending must loop to the beginning.
- Final line must trigger comments.
- Viewer curiosity must INCREASE every 3 seconds.

Structure: Hook (Pattern Interrupt) → Curiosity → Insight (MANDATORY REVEAL) → Twist → Comment Bait → Loop Ending.

🎬 VISUAL DIRECTIONS (CRITICAL — CINEMATIC QUALITY):
Provide 2 cinematic visual prompts per segment (10–12 segments total).

⚠️ VISUAL RULES (MANDATORY):
- Every visual MUST include camera motion (dolly, pan, zoom, tracking shot, drone, handheld)
- Every visual MUST include lighting description (torch light, golden hour, moonlit, dramatic shadows, cinematic fog)
- Every visual MUST feel photorealistic and cinematic
- BANNED: static visuals, text-only scenes, cartoon/anime style, stock photo feel
- Examples of GOOD visuals:
  "camera slowly moving inside ancient temple corridor, torch light flickering, dust particles in air"
  "aerial drone shot of misty Himalayan valley at dawn, golden light cutting through fog"
  "handheld camera POV walking through dark underground tunnel, flashlight beam scanning walls"

📦 OUTPUT FORMAT (STRICT JSON — return ONLY this):
[
  {{
    "id": 1,
    "voiceover_text": "Chunk of the continuous story...",
    "caption_text": "Dynamic caption with **HIGHLIGHTS**...",
    "visual_search_1": "cinematic visual with camera motion and lighting",
    "visual_search_2": "backup cinematic visual with different angle",
    "visual_style": "zoom in / out / fast / slow pan"
  }}
]

Return ONLY the JSON array. No explanation. No preamble.
"""
        raw_text = _call_with_fallback(prompt)
        clean_text = raw_text.replace('```json', '').replace('```', '').strip()

        try:
            script = json.loads(clean_text)
            # Tag the script with its generation style for performance tracking
            if isinstance(script, list) and script:
                script[0]["_generation_style"] = style
            return script
        except json.JSONDecodeError as e:
            print(f"❌ JSON Error: {e}. Attempting recovery...")
            match = re.search(r'\[.*\]', clean_text, re.DOTALL)
            if match:
                try:
                    recovered = json.loads(match.group())
                    if isinstance(recovered, list) and recovered:
                        recovered[0]["_generation_style"] = style
                    return recovered
                except:
                    pass
            return None

    def generate_multiple_scripts(self, topic: str, pillar: str = "evergreen") -> list:
        """
        v3.0: Generates 3 script variants with style selection based on content pillar.
        
        Pillar-to-style mapping:
          evergreen    -> curiosity, shock, story
          trend_fusion -> trend_fusion, curiosity, controversy
          seasonal     -> seasonal, curiosity, story
          experimental -> shock, controversy, curiosity
        """
        # Style subsets per pillar — each produces 3 variants
        pillar_styles = {
            "evergreen":    ["curiosity", "shock", "story"],
            "trend_fusion": ["trend_fusion", "curiosity", "controversy"],
            "seasonal":     ["seasonal", "curiosity", "story"],
            "experimental": ["shock", "controversy", "curiosity"],
        }
        styles = pillar_styles.get(pillar, pillar_styles["evergreen"])

        print(f"\nGenerating 3 script variants for: {topic} [pillar={pillar}]")
        print(f"   Styles: {styles}")

        scripts = []
        for style in styles:
            script = self.generate_script(topic, style=style)
            if script:
                scripts.append(script)
                print(f"   [{style.upper()}] variant generated ({len(script)} segments)")
            else:
                print(f"   [{style.upper()}] variant failed, skipping")

        if not scripts:
            print("   All styled variants failed. Trying default...")
            fallback = self.generate_script(topic, style="default")
            if fallback:
                scripts.append(fallback)

        print(f"   {len(scripts)} variants ready for scoring\n")
        return scripts

    def generate_title(self, topic: str) -> str:
        """
        Generates a viral, curiosity-driven YouTube Shorts title.
        """
        print(f"🎬 Generating viral title for: {topic}...")
        prompt = (
            f"You are a viral YouTube Shorts growth expert.\n"
            f"Topic: \"{topic}\"\n\n"
            f"🎯 YOUR TASK: Create ONE high-engagement, curiosity-driven title for a YouTube Short.\n"
            f"RULES:\n"
            f"1. LENGTH: Under 75 characters (so we can add #Shorts after).\n"
            f"2. FORMAT: No markdown bolding (**). No quotes around the title.\n"
            f"3. HOOK: Start with a power word or a shocking claim. Use curiosity gaps.\n"
            f"4. EMOJIS: Include 1-2 relevant emojis for visual pop.\n"
            f"5. No #Shorts: Do NOT include the hashtag in the title itself.\n"
            f"Return ONLY the title string. No explanation."
        )

        try:
            title = _call_with_fallback(prompt)
            # Cleanup any unwanted characters
            title = title.replace('"', '').replace('**', '').strip()
            return title
        except Exception as e:
            print(f"   ⚠️ Title generation failed ({e}), using safe fallback.")
            return topic[:60]

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
    from modules.viral_engine import score_script, pick_best_script

    brain = ContentBrain()
    topic, niche = brain.get_trending_topic()

    # Test multi-script generation + scoring
    scripts = brain.generate_multiple_scripts(topic)
    if scripts:
        best = pick_best_script(scripts)
        desc = brain.generate_description(topic, best)
        print("\n📋 Description preview:\n")
        print(desc)

        test_output = os.path.join(os.getcwd(), "assets", "temp", "script_test.json")
        os.makedirs(os.path.dirname(test_output), exist_ok=True)
        with open(test_output, "w", encoding="utf-8") as f:
            json.dump({"topic": topic, "scripts": len(scripts), "best_script": best}, f, indent=4, ensure_ascii=False)
            print(f"\n✅ Test script saved to {test_output}")
    else:
        print("❌ No scripts generated.")
