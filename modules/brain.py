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
    
    # Check for numbered keys (up to 10)
    for i in range(1, 11):
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
    # Narrow Focus: Dark Indian History & Mythology
    NICHES = [
        "Forgotten Secrets of Mahabharata & Ramayana",
        "Unknown Stories of Shiva, Vishnu & Ancient Gods",
        "Ancient Temple Mysteries of India",
        "Lost Civilizations: Saraswati River & Indus Valley",
        "Puranic Weapons, Strategies & Hidden Meanings",
        "Mythological Creatures & Their Symbolism",
        "Unsolved Mysteries of Indian History",
        "The Untold Truth Behind Indian Freedom Struggle",
        "Mysteries Around Netaji Subhash Chandra Bose",
        "Ancient Indian Inventions Ahead of Their Time",
    ]

    HISTORY_FILE = "topic_history.json"
    HISTORY_LIMIT = 100  # Remember last 100 topics (v1 was 30)

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
        Picks a unique topic every run by injecting:
          - Today's date + current hour  (breaks Gemini's cache)
          - A randomly chosen niche      (forces category variety)
          - Recent topic history         (explicit avoidance list)
        """
        niche    = random.choice(self.NICHES)
        now      = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        hour_str = now.strftime("%H:%M UTC")
        history  = self._load_history()

        avoid_block = ""
        if history:
            avoid_list = "\n".join(f"  - {t}" for t in history[-10:])
            avoid_block = (
                f"\n\nIMPORTANT — You MUST pick something NEW. "
                f"Do NOT suggest any of these recently used topics:\n{avoid_list}"
            )

        prompt = (
            f"Today is {date_str} at {hour_str}. "
            f"Give me 1 specific, viral, and highly engaging topic for a YouTube Short documentary "
            f"in the niche: **{niche}**. "
            f"It must be a surprising 'Did You Know' fact, an incredible true story, or a mind-blowing "
            f"recent discovery. Be very specific — not generic. "
            f"Return ONLY the topic name, nothing else."
            f"{avoid_block}"
        )

        topic = _call_with_fallback(prompt)
        print(f"🎯 Topic ({niche}): {topic}")

        # Save to history so next run avoids it
        history.append(topic)
        self._save_history(history)

        return topic, niche

    def generate_script(self, topic):
        """
        Generates a structured JSON script with visual cues.
        Enforces a Split Format: 
        - voiceover_text: Hinglish (Devanagari) for natural narration.
        - caption_text: Simple English for on-screen subtitles (fixes rendering issues).
        """
        print(f"📝 Writing script for: {topic}...")
        prompt = f"""
    You are the lead scriptwriter for a high-retention YouTube Shorts channel.
    Topic: {topic}

    ### GOAL:
    Create a script optimized for an Indian audience.
    We need TWO versions of the text for every scene:
    1. **voiceover_text (Hinglish):** This will be the audio. Use Conversational Hindi mixed with English words in **Devanagari script**.
    2. **caption_text (English):** This will be on-screen. Use **Simple English** only.

    ### 1. SCRIPT REQUIREMENTS (The Voiceover):
    - **Language:** Natural "Hinglish". Use words like "Actually", "Mind-blowing", "Result" within the Hindi flow. 
    - **Tone:** High energy, informal, and relatable. NO formal "Shuddh" Hindi.
    - **Speed:** Fast-paced.
    - **Perspective:** Strictly **3rd Person**.
    - **Structure:** 5-7 Scenes total (Keep it strictly between 60-70 seconds total duration).
    - **VIRAL HOOK (Scene 1):** Use a 'Negative Gap' or 'Curiosity Gap' hook. 
      *Examples*: "The one secret scholars won't tell you about Mahabharata...", "Why is this 1,000-year-old temple technology still impossible today?", "Actually, most people believe X, but the truth is shocking..."
    - **Flow:** Hook -> Context -> Shocking Fact -> Why it matters -> Outro -> Call to Action.
    - **MANDATORY FINAL SCENE:** Must be a Like & Subscribe request.

    ### 2. VISUAL REQUIREMENTS (Strictly No Vloggers):
    - For EVERY scene, provide TWO distinct search terms in **English**:
      - **visual_1:** Matches the start.
      - **visual_2:** Matches the end.
    - **STYLE CONSTRAINT:** Prioritize **Cinematic Landscapes**, **Ancient Architecture**, **Empty Temples**, **Abstract Energy**, or **Stone Textures**.
    - **KEYWORD RULE:** Every visual query MUST contain at least one concrete noun (e.g., "Temple", "Statue", "Jungle", "Stone"). Never use only abstract words like "Secret" or "History".
    - **EDUCATIONAL STYLE:** Documentary-style footage is OK (e.g., scholars studying, people in traditional prayer, museum artifacts).
    - **STRICTLY FORBIDDEN:** NO travel vloggers, NO selfies, NO people talking to the camera, NO modern tourists, NO "walking-vlog" shots. The video must feel like a premium documentary, NOT a travel blog.

    ### OUTPUT FORMAT (Strict JSON, no markdown, no extra text):
    [
        {{
            "id": 1,
            "voiceover_text": "क्या आप जानते हैं कि एक प्राचीन Indian Temple को सिर्फ एक पहाड़ काटकर बनाया गया था? Actually, ये बेहद shocking है!",
            "caption_text": "Did you know this ancient temple was carved from a single mountain?",
            "visual_1": "ellora kailash temple aerial view",
            "visual_2": "giant rock mountain architecture",
            "mood": "amazed" 
        }}
    ]
    """

        raw_text = _call_with_fallback(prompt)

        # Strip markdown code fences if the model wrapped the JSON
        clean_text = raw_text.replace('```json', '').replace('```', '').strip()

        try:
            script_data = json.loads(clean_text)
            return script_data
        except json.JSONDecodeError:
            print("❌ Error parsing JSON. Raw output:")
            print(clean_text)
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
            scene.get("text", "") for scene in (script_data or [])[:5]
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