import os
import asyncio
import edge_tts
from mutagen.mp3 import MP3

class AudioEngine:
    def __init__(self, voice="hi-IN-MadhurNeural"):
        self.voice = voice
        self.output_dir = os.path.join(os.getcwd(), "assets", "audio_clips")
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_audio(self, text, output_filename, retries=3):
        """
        Generates MP3 with retry logic. Strips metadata like [BOOM] or (pause)
        before sending to edge-tts.
        """
        import re
        output_path = os.path.join(self.output_dir, output_filename)
        
        # ── CLEAN TEXT ────────────────────────────────────────────────────────
        # 1. Remove ANY brackets or parentheses metadata
        clean_text = re.sub(r'\[.*?\]', '', text)
        clean_text = re.sub(r'\(.*?\)', '', clean_text)
        # 2. Final cleanup of extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        for attempt in range(retries):
            try:
                # Elite Master Sync: Pitch -5Hz, Rate +22% (Authoritative & Snappy)
                communicate = edge_tts.Communicate(clean_text, self.voice, rate="+22%", pitch="-5Hz")
                await communicate.save(output_path)
                return output_path
            
            except Exception as e:
                print(f"      ⚠️ Audio Error (Attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise e

    def get_audio_duration(self, file_path):
        try:
            audio = MP3(file_path)
            return audio.info.length
        except Exception as e:
            print(f"❌ Error reading audio length: {e}")
            return 0.0

    async def process_script(self, script_data):
        print(f"🎙️ Starting Audio Generation for {len(script_data)} scenes...")
        
        for scene in script_data:
            scene_id = scene['id']
            text = scene.get('voiceover_text', scene.get('text', ''))
            filename = f"voice_{scene_id}.mp3"
            
            try:
                # Generate Audio
                file_path = await self.generate_audio(text, filename)
                
                # Get Duration
                duration = self.get_audio_duration(file_path)
                
                # Update Scene Data
                scene['audio_path'] = file_path
                scene['duration'] = duration
                
                print(f"   ✅ Scene {scene_id}: {duration:.2f}s generated.")
                
                # CRITICAL: Sleep for 1 second to be polite to the API
                # This prevents the "Connection Timeout" error
                await asyncio.sleep(1) 
                
            except Exception as e:
                print(f"   ❌ Skipping Scene {scene_id} due to audio error.")
                continue
            
        return script_data