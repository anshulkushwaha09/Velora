import os
import asyncio
from modules.brain import ContentBrain
from modules.audio import AudioEngine
from modules.composer import Composer

async def test():
    brain = ContentBrain()
    audio = AudioEngine()
    composer = Composer()

    topic = "The Mystery of the Gold Idol"
    print(f"Testing Topic: {topic}")

    # 1. Generate Script
    script = brain.generate_script(topic)
    if not script:
        print("Failed to generate script")
        return

    # Look for a scene with star
    scene = script[0]
    print(f"Scene 0 Text: {scene['caption_text']}")
    
    # 2. Test Audio Speed
    audio_path = await audio.generate_audio(scene['voiceover_text'], "scene_test.mp3")
    duration = composer.get_duration(audio_path)
    print(f"Audio Duration: {duration}s")

    # 3. Test .ass Generations
    ass_path = composer._generate_ass_subtitles(scene['caption_text'], duration, "test")
    with open(ass_path, "r", encoding="utf-8") as f:
        ass_content = f.read()
    
    if "H00D7FF" in ass_content:
        print("✅ Gold Highlight DETECTED in .ass file!")
    else:
        print("❌ Gold Highlight NOT FOUND in .ass file.")
        print("ASS Content Head:")
        print("\n".join(ass_content.splitlines()[-3:]))

if __name__ == "__main__":
    asyncio.run(test())
