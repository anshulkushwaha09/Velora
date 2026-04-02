import os
import re
import random
import ffmpeg


# ─────────────────────────────────────────────────────────────────────────────
# Caption helpers
# ─────────────────────────────────────────────────────────────────────────────

# Vibrant color palette for the main text — cycles per caption line
CAPTION_COLORS = [
    "#FFE500",   # Bright yellow
    "#00E5FF",   # Electric cyan
    "#FF6B00",   # Hot orange
    "#FF2D8B",   # Neon pink
]

# Number of 3-D depth layers drawn behind the main text
DEPTH_LAYERS = 5

# Font size (px). Elite v10.0 uses larger, bolder text for impact.
FONT_SIZE = 72

# Maximum characters per wrapped line. Keep enough margin so long words fit.
MAX_CHARS_PER_LINE = 24

# Vertical gap between caption lines (pixels)
LINE_SPACING = 14


def _wrap_text(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> list[str]:
    """
    Returns a list of strings, each no longer than max_chars.
    Uses word-boundary wrapping so words are never cut mid-character.
    """
    words = text.split()
    lines, current = [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        lines.append(current)
    return lines


def _escape_drawtext(text: str) -> str:
    """
    Escapes all characters that FFmpeg drawtext treats specially.
    """
    text = text.replace("\\", "\\\\")   # Must be first
    text = text.replace("'",  "\u2019") # Curly apostrophe
    text = text.replace(":",  "\\:")
    text = text.replace("%",  "%%")
    return text


class Composer:
    def __init__(self):
        self.temp_dir    = os.path.join(os.getcwd(), "assets", "temp").replace("\\", "/")
        self.final_dir   = os.path.join(os.getcwd(), "assets", "final").replace("\\", "/")
        self.avatar_path = os.path.join(os.getcwd(), "assets", "avatar", "avatars.mp4").replace("\\", "/")
        self.font_path   = os.path.join(os.getcwd(), "assets", "fonts", "Montserrat-Bold.ttf").replace("\\", "/")

        os.makedirs(self.temp_dir,  exist_ok=True)
        os.makedirs(self.final_dir, exist_ok=True)
        self.transitions = ['fade', 'diagbr', 'diagtl']

    def get_duration(self, filepath):
        try:
            probe = ffmpeg.probe(filepath)
            return float(probe['format']['duration'])
        except:
            return 0.0

    def _generate_ass_subtitles(self, text: str, duration: float, scene_id: int) -> str:
        """
        Generates an Advanced Substation Alpha (.ass) file for 'Elite' style captions.
        """
        ass_filename = f"scene_{scene_id}.ass"
        ass_path = os.path.join(self.temp_dir, ass_filename).replace("\\", "/")
        header = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Elite,Montserrat,72,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,3,2,50,50,400,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        def _apply_style(match):
            word = match.group(1)
            return f"{{\\c&H00D7FF&\\fscx120\\fscy120\\b1}}{word}{{\\r}}"

        styled_text = re.sub(r"\*\*(.*?)\*\*", _apply_style, text)
        lines = _wrap_text(styled_text, max_chars=26)
        ass_text = "\\N".join(lines)
        end_time = duration + 0.5

        def fmt_time(t):
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = t % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        header.append(f"Dialogue: 0,0:00:00.00,{fmt_time(end_time)},Elite,,0,0,0,,{ass_text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header))
        return ass_path

    def process_scene(self, scene, video_pair, is_avatar=False):
        scene_id       = scene.get('id', 'Unknown')
        audio_path     = os.path.normpath(scene.get('audio_path', ''))
        total_duration = scene.get('duration', 0)
        caption_text   = scene.get('caption_text', scene.get('text', ''))
        output_path    = os.path.normpath(os.path.join(self.temp_dir, f"scene_{scene_id}.mp4"))

        try:
            if not audio_path or not os.path.exists(audio_path):
                print(f"   ❌ Scene {scene_id}: Audio missing ({audio_path}).")
                if audio_path:
                    print(f"      Abs path checked: {os.path.abspath(audio_path)}")
                return None

            input_audio = ffmpeg.input(audio_path)

            if is_avatar:
                v_in = video_pair[0].replace("\\", "/")
                video_stream = (
                    ffmpeg.input(v_in, stream_loop=-1)
                    .trim(duration=total_duration + 0.5)
                    .setpts('PTS-STARTPTS')
                    .filter('crop', 'iw', 'ih-150', 0, 0)
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    .filter('zoompan', z='min(zoom+0.008,1.5)' if (int(scene_id) % 2 == 0) else 'max(1.5-0.008,1.0)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
            else:
                p_a = video_pair[0].replace("\\", "/")
                p_b = video_pair[1].replace("\\", "/")
                dur_a = total_duration / 2
                dur_b = (total_duration / 2) + 0.5

                s_a = (
                    ffmpeg.input(p_a, stream_loop=-1)
                    .trim(duration=dur_a).setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    .filter('zoompan', z='min(zoom+0.008,1.5)' if (int(scene_id) % 2 == 0) else 'max(1.5-0.008,1.0)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
                s_b = (
                    ffmpeg.input(p_b, stream_loop=-1)
                    .trim(duration=dur_b).setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    .filter('zoompan', z='min(zoom+0.008,1.5)' if (int(scene_id) % 2 == 0) else 'max(1.5-0.008,1.0)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
                video_stream = ffmpeg.concat(s_a, s_b, v=1, a=0)

            if caption_text:
                ass_p = self._generate_ass_subtitles(caption_text, total_duration, scene_id)
                # RELATIVE PATH IS SAFEST FOR WINDOWS SUBTITLES FILTER
                # Must use forward slashes and ensure it's relative to the CWD
                rel_ass = os.path.relpath(ass_p, os.getcwd()).replace("\\", "/")
                # On Windows, FFmpeg sometimes needs ':' escaped even in relative paths if they are long
                rel_ass = rel_ass.replace(":", "\\:")
                video_stream = video_stream.filter('subtitles', rel_ass)

            runner = ffmpeg.output(
                video_stream, input_audio, output_path,
                vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None
            )
            runner.run(overwrite_output=True, quiet=True)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"   ✅ Scene {scene_id} Rendered.")
                return output_path
            return None

        except ffmpeg.Error as e:
            err = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"   ❌ Render Fail Scene {scene_id}: {err}")
            return None

    def render_all_scenes(self, script_data, video_pairs):
        print(f"🎬 Starting Render for {len(script_data)} scenes...")
        paths = []
        for i, scene in enumerate(script_data):
            pair = video_pairs[i]
            if not pair:
                continue
            path = self.process_scene(scene, pair)
            if path:
                paths.append(path)
        return paths

    def concatenate_with_transitions(self, video_paths, output_filename="final_short.mp4"):
        print(f"🔄 Stitching {len(video_paths)} scenes...")
        out_p = os.path.join(self.final_dir, output_filename).replace("\\", "/")

        if os.path.exists(out_p):
            try: os.remove(out_p)
            except: pass

        if not video_paths:
            return None

        try:
            inp1     = ffmpeg.input(video_paths[0])
            v_s      = inp1.video.filter('format', 'yuv420p').filter('scale', 1080, 1920)
            a_s      = inp1.audio.filter('aresample', 44100).filter('aformat', channel_layouts='stereo')
            curr_dur = self.get_duration(video_paths[0])

            for i in range(1, len(video_paths)):
                nxt_p = video_paths[i]
                if not os.path.exists(nxt_p): continue

                nxt   = ffmpeg.input(nxt_p)
                nxt_d = self.get_duration(nxt_p)
                overlap = 0.5
                
                off = max(0, curr_dur - overlap - 0.05)
                eff = random.choice(self.transitions)
                
                nv = nxt.video.filter('format', 'yuv420p').filter('scale', 1080, 1920)
                na = nxt.audio.filter('aresample', 44100).filter('aformat', channel_layouts='stereo')

                v_s = ffmpeg.filter([v_s, nv], 'xfade', transition=eff, duration=overlap, offset=off)
                a_s = ffmpeg.filter([a_s, na], 'acrossfade', d=overlap)
                
                curr_dur = (curr_dur + nxt_d) - overlap

            r = ffmpeg.output(v_s, a_s, out_p, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', movflags='faststart', preset='medium')
            r.run(overwrite_output=True, quiet=True)
            return out_p

        except ffmpeg.Error as e:
            err = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"❌ Stitching Error: {err}")
            return None
        except Exception as e:
            print(f"❌ Stitching Exception: {e}")
            return None
