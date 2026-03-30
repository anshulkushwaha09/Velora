import os
import argparse
import asyncio
import shutil
from modules.brain import ContentBrain
from modules.audio import AudioEngine
from modules.asset_manager import AssetManager
from modules.composer import Composer

def clean_cache():
    print("🧹 Cleaning up temporary files...")
    folders_to_clean = [
        os.path.join(os.getcwd(), "assets", "audio_clips"),
        os.path.join(os.getcwd(), "assets", "video_clips"),
        os.path.join(os.getcwd(), "assets", "temp")
    ]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
    print("✨ Workspace clean!")

async def main():
    parser = argparse.ArgumentParser(description="Velora Elite v9.0 Shorts Automation")
    parser.add_argument("--dry-run", action="store_true", help="Run without uploading to YouTube")
    parser.add_argument("--topic", type=str, help="Manually specify a topic")
    args = parser.parse_args()

    print("🚀 STARTING AUTOMATION...")
    if args.dry_run:
        print("🧪 DRY-RUN MODE — video will be saved locally, not uploaded.")

    # 1. BRAIN: Generate Topic & Script
    brain = ContentBrain()
    
    if args.topic:
        topic, niche = args.topic, "Manual"
    else:
        topic, niche = brain.get_trending_topic()
        
    script = brain.generate_script(topic)
    if not script:
        print("❌ Script generation failed. Terminating.")
        return

    # 2. AUDIO: Generate Voiceover
    audio_engine = AudioEngine()
    script_with_audio = await audio_engine.process_script(script)

    # 3. ASSETS: Gather Video Clips
    asset_manager = AssetManager()
    assets_map = asset_manager.get_videos(script_with_audio)

    # 4. COMPOSER: Render All Scenes
    composer = Composer()
    final_scene_paths = composer.render_all_scenes(script_with_audio, assets_map)

    # 5. STITCH: Final Video
    if final_scene_paths:
        final_video_path = composer.concatenate_with_transitions(final_scene_paths)
        
        if final_video_path:
            print(f"✅ FINAL VIDEO SAVED: {final_video_path}")
            if not args.dry_run:
                # 6. UPLOADER (Future implementation)
                print("📤 Uploading to YouTube... (TBD)")
            else:
                print("✅ DRY RUN COMPLETE!")
            
            # 7. CLEANUP (Only on success)
            clean_cache()
        else:
            print("❌ Stitching failed. Temporary files preserved for debugging.")
    else:
        print("❌ No scenes rendered. Terminating.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Automation stopped by user.")
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")