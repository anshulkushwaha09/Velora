"""
main.py — Velora v3.0 Hybrid Viral Engine

Single-video execution flow:
  1. Content planner generates topic candidates across 4 pillars (text only)
  2. Best topic selected by virality scoring
  3. 3 script variants generated for winning topic (text only)
  4. Best script selected by heuristic scoring
  5. Retention injection + comment bait (text only)
  6. Audio + Assets + Render (ONCE, for the single winning video)
  7. Upload + performance logging + topic bank expansion

Steps 1-5 are FREE (text/Gemini only). Steps 6-7 use Pexels/FFmpeg ONCE.
"""

import asyncio
import argparse
import os
import shutil
import json
from dotenv import load_dotenv
from modules.brain import ContentBrain
from modules.asset_manager import AssetManager
from modules.audio import AudioEngine
from modules.composer import Composer
from modules.content_planner import plan_today, get_topic_bank
from modules.viral_engine import (
    pick_best_script,
    score_script,
    inject_pattern_interrupt,
    append_comment_bait_to_script,
    generate_viral_title,
    log_performance,
    get_best_style,
    get_best_topic_type,
)

# Load .env on startup
load_dotenv()


def clean_cache():
    """
    Safely deletes temporary files.
    Includes a Safety Lock to prevent deleting anything outside the project.
    """
    print("Cleaning up temporary files...")
    
    folders_to_clean = [
        os.path.join(os.getcwd(), "assets", "audio_clips"),
        os.path.join(os.getcwd(), "assets", "video_clips"),
        os.path.join(os.getcwd(), "assets", "temp")
    ]

    for folder in folders_to_clean:
        if not os.path.exists(folder):
            continue
        if "assets" not in folder:
            print(f"   SECURITY ALERT: Skipping {folder} because it looks unsafe!")
            continue

        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"   Failed to delete {file_path}. Reason: {e}")
    
    print("Workspace clean!")


async def produce_video(brain, topic_data, dry_run):
    """
    v3.0: Full production pipeline for a SINGLE video.
    Takes a topic_data dict from content_planner and produces one video.
    
    Steps: Multi-script -> Score -> Pick best -> Retention inject ->
           Audio -> Assets -> Render -> Upload -> Log -> Expand
    """
    topic = topic_data["topic"]
    niche = topic_data.get("niche", "Ancient Mysteries")
    pillar = topic_data.get("pillar", "evergreen")
    subject = topic_data.get("subject", "")
    angle = topic_data.get("angle", "")

    print(f"\n{'='*60}")
    print(f"PRODUCING VIDEO: {topic}")
    print(f"Pillar: {pillar.upper()} | Niche: {niche}")
    print(f"{'='*60}")

    # ── STEP 1: GENERATE 3 SCRIPT VARIANTS (text only, cheap) ───────
    scripts = brain.generate_multiple_scripts(topic, pillar=pillar)

    if not scripts:
        print("Script generation failed for all styles.")
        return False

    # ── STEP 2: SCORE & PICK BEST SCRIPT (text only, free) ──────────
    best_script = pick_best_script(scripts)
    best_score = score_script(best_script)

    if not best_script:
        print("No viable script produced.")
        return False

    winning_style = best_script[0].get("_generation_style", "default") if best_script else "default"

    # ── STEP 3: RETENTION INJECTION (text only, free) ───────────────
    best_script = inject_pattern_interrupt(best_script)

    # ── STEP 4: COMMENT BAIT (text only, free) ─────────────────────
    best_script = append_comment_bait_to_script(best_script, topic)

    # ── SAVE FINAL SCRIPT FOR INSPECTION ───────────────────────────
    temp_script_path = os.path.join(os.getcwd(), "assets", "temp", "final_script.json")
    os.makedirs(os.path.dirname(temp_script_path), exist_ok=True)
    with open(temp_script_path, "w", encoding="utf-8") as f:
        json.dump({
            "topic": topic,
            "pillar": pillar,
            "style": winning_style,
            "score": best_score,
            "script": best_script
        }, f, indent=4, ensure_ascii=False)
    print(f"Final script saved to {temp_script_path}")

    # ══════════════════════════════════════════════════════════════════
    # FROM HERE: Expensive operations (Audio, Pexels, FFmpeg) — ONE video only
    # ══════════════════════════════════════════════════════════════════

    # ── STEP 5: AUDIO GENERATION ───────────────────────────────────
    audio_engine = AudioEngine()
    try:
        best_script = await audio_engine.process_script(best_script)
    except Exception as e:
        print(f"Audio Error: {e}")
        return False

    # ── STEP 6: ASSET DOWNLOAD (Pexels — single video) ────────────
    asset_manager = AssetManager()
    assets_map = asset_manager.get_videos(best_script, niche=niche)

    # ── STEP 7: RENDER SCENES ─────────────────────────────────────
    print(f"Starting Render for {len(best_script)} scenes...")

    for scene in best_script:
        ap = scene.get('audio_path')
        if not ap or not os.path.exists(ap):
            print(f"Critical Error: Audio missing for scene {scene.get('id')} at {ap}")
            return False

    composer = Composer()
    final_scene_paths = composer.render_all_scenes(best_script, assets_map)

    # ── STEP 8: STITCH WITH TRANSITIONS ───────────────────────────
    final_video_path = None
    if final_scene_paths:
        try:
            final_video_path = composer.concatenate_with_transitions(
                final_scene_paths,
                output_filename="final_short.mp4"
            )
            
            if final_video_path:
                print("Generation successful. Cleaning up...")
                await asyncio.sleep(2)
                clean_cache()
            else:
                print("Stitching failed. Keeping temporary files for inspection.")
        except Exception as e:
            print(f"Critical Error during stitching: {e}")
    else:
        print("Failed to generate any valid scenes.")
        return False

    if not final_video_path:
        return False

    # ── STEP 9: TITLE & UPLOAD ────────────────────────────────────
    if dry_run:
        print(f"\nDONE! Your masterpiece is ready.")
        print(f"   Location: {final_video_path}")
    else:
        try:
            from modules.youtube_uploader import upload_video

            viral_title = generate_viral_title(topic, pillar=pillar)
            video_title = f"{viral_title} #Shorts"
            video_description = brain.generate_description(topic, best_script)

            video_url = upload_video(
                final_video_path,
                title=video_title,
                description=video_description
            )

            # ── STEP 10: PERFORMANCE LOGGING ─────────────────────
            video_id = video_url.split("/")[-1] if video_url else "unknown"
            log_performance({
                "video_id": video_id,
                "topic": topic,
                "style": winning_style,
                "pillar": pillar,
                "topic_category": topic_data.get("trend_category", ""),
                "subject": subject,
                "angle": angle,
                "script_score": best_score,
                "title": video_title,
            })

        except Exception as e:
            print(f"YouTube Upload Error: {e}")
            print(f"   The video was still saved at: {final_video_path}")

    # ── STEP 11: TOPIC BANK EXPANSION ─────────────────────────────
    # Register usage and expand high-performing subjects
    if subject and pillar == "evergreen":
        bank = get_topic_bank()
        bank.register_usage(subject, angle, score=best_score)
        
        # If score is high, auto-expand this subject for future content
        if best_score >= 10:
            print(f"   High-scoring topic! Expanding '{subject}' for future content...")
            bank.expand_subject(subject)

    return True


async def main(dry_run: bool = False, script_path: str = None):
    print("STARTING VELORA VIRAL ENGINE v3.0...")
    if dry_run:
        print("DRY-RUN MODE -- videos will be saved locally, not uploaded.\n")

    brain = ContentBrain()

    # ── MANUAL SCRIPT MODE (backward compatible) ───────────────────
    if script_path and os.path.exists(script_path):
        print(f"Loading manual script: {script_path}...")
        topic = "Elite Mystery"
        script = None
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "script" in data:
                    script = data["script"]
                    topic = data.get("topic", topic)
                else:
                    script = data
        except Exception as e:
            print(f"Error loading manual script: {e}")
            return

        if not script:
            print("Script loading failed.")
            return

        audio_engine = AudioEngine()
        try:
            script = await audio_engine.process_script(script)
        except Exception as e:
            print(f"Audio Error: {e}")
            return

        asset_manager = AssetManager()
        assets_map = asset_manager.get_videos(script)

        for scene in script:
            ap = scene.get('audio_path')
            if not ap or not os.path.exists(ap):
                print(f"Critical Error: Audio missing for scene {scene.get('id')} at {ap}")
                return

        composer = Composer()
        final_scene_paths = composer.render_all_scenes(script, assets_map)

        final_video_path = None
        if final_scene_paths:
            try:
                final_video_path = composer.concatenate_with_transitions(final_scene_paths)
                if final_video_path:
                    print("Generation successful. Cleaning up...")
                    await asyncio.sleep(2)
                    clean_cache()
            except Exception as e:
                print(f"Critical Error during stitching: {e}")

        if not final_video_path:
            return

        if dry_run:
            print(f"\nDONE! Your masterpiece is ready.")
            print(f"   Location: {final_video_path}")
        else:
            try:
                from modules.youtube_uploader import upload_video
                video_title = f"{brain.generate_title(topic)} #Shorts"
                video_description = brain.generate_description(topic, script)
                upload_video(final_video_path, title=video_title, description=video_description)
            except Exception as e:
                print(f"YouTube Upload Error: {e}")
                print(f"   The video was still saved at: {final_video_path}")
        return

    # ══════════════════════════════════════════════════════════════════
    # v3.0: SINGLE-VIDEO FLOW — Many candidates, ONE winner, ONE video
    # ══════════════════════════════════════════════════════════════════

    # Self-learning: Check what performed best historically
    preferred_style = get_best_style()
    preferred_pillar = get_best_topic_type()
    print(f"Self-learning: Best style = '{preferred_style}' | Best pillar = '{preferred_pillar}'")

    # ── PHASE 1: GENERATE TOPIC CANDIDATES (all text, no Pexels) ──
    print(f"\n{'='*60}")
    print("PHASE 1: TOPIC CANDIDATE GENERATION (text only)")
    print(f"{'='*60}")

    candidates = plan_today(num_candidates=5)

    if not candidates:
        print("No topic candidates generated. Aborting.")
        return

    # ── PHASE 2: PICK THE BEST TOPIC ──────────────────────────────
    best_topic = candidates[0]  # Already sorted by virality score
    print(f"\n{'='*60}")
    print("PHASE 2: WINNER SELECTED")
    print(f"  Topic:  {best_topic['topic']}")
    print(f"  Pillar: {best_topic['pillar']}")
    print(f"  Score:  {best_topic['virality_score']}")
    print(f"{'='*60}")

    # ── PHASE 3: PRODUCE SINGLE VIDEO ─────────────────────────────
    try:
        result = await produce_video(brain, best_topic, dry_run)
        if result:
            print(f"\n{'='*60}")
            print("VIDEO PRODUCED SUCCESSFULLY")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("VIDEO PRODUCTION FAILED")
            print(f"{'='*60}")
    except Exception as e:
        print(f"Pipeline error: {e}")

    # ── PHASE 4: REPORT TOPIC BANK STATS ──────────────────────────
    bank = get_topic_bank()
    stats = bank.get_stats()
    print(f"\n--- Topic Bank Status ---")
    print(f"   Subjects: {stats['total_subjects']} | "
          f"Used slots: {stats['used_slots']}/{stats['total_slots']} "
          f"({stats['coverage_pct']}%) | "
          f"Available now: {stats['available']} | "
          f"On cooldown: {stats['on_cooldown']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Velora Viral Engine v3.0 -- AI YouTube Shorts Generator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the video locally without uploading to YouTube."
    )
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Path to an optional local script.json file to use instead of generating a new one."
    )
    args = parser.parse_args()

    asyncio.run(main(dry_run=args.dry_run, script_path=args.script))
