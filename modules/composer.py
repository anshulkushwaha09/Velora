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

# Font size (px). At 56px bold, ~30 chars fit within 1080px.
FONT_SIZE = 56

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
    NOTE: we do NOT join lines with '\n' here — each line is a separate
    drawtext call to avoid ffmpeg-python double-escaping the backslash.
    """
    text = text.replace("\\", "\\\\")   # Must be first
    text = text.replace("'",  "\u2019") # Curly apostrophe — avoids shell quoting issues
    text = text.replace(":",  "\\:")
    text = text.replace("%",  "%%")
    return text


class Composer:
    def __init__(self):
        self.temp_dir    = os.path.join(os.getcwd(), "assets", "temp")
        self.final_dir   = os.path.join(os.getcwd(), "assets", "final")
        self.avatar_path = os.path.join(os.getcwd(), "assets", "avatar", "avatars.mp4")
        self.font_path   = os.path.join(os.getcwd(), "assets", "fonts", "Montserrat-Bold.ttf")

        os.makedirs(self.temp_dir,  exist_ok=True)
        os.makedirs(self.final_dir, exist_ok=True)
        self.transitions = ['fade', 'diagbr', 'diagtl']

    # ── internal ──────────────────────────────────────────────────────────────

    def _font_opts(self) -> dict:
        """Base drawtext options shared by every layer."""
        opts = {"fontsize": FONT_SIZE}
        if os.path.exists(self.font_path):
            opts["fontfile"] = self.font_path.replace("\\", "/")
        return opts

    def _add_caption(self, video_stream, text: str):
        """
        Burns styled, 3-D coloured captions into *video_stream*.
        """
        lines = _wrap_text(text, max_chars=MAX_CHARS_PER_LINE)
        n = len(lines)
        line_h = FONT_SIZE + LINE_SPACING

        def y_expr(i: int) -> str:
            offset = i * line_h - (n * line_h) // 2
            sign   = "+" if offset >= 0 else "-"
            return f"(h*0.72){sign}{abs(offset)}"

        base = self._font_opts()

        for i, line in enumerate(lines):
            safe = _escape_drawtext(line)
            color = CAPTION_COLORS[i % len(CAPTION_COLORS)]
            y     = y_expr(i)

            for d in range(DEPTH_LAYERS, 0, -1):
                video_stream = video_stream.filter(
                    "drawtext",
                    **base,
                    text=safe,
                    fontcolor="0x1a0a00@0.85",
                    borderw=3,
                    bordercolor="black",
                    x=f"(w-text_w)/2+{d * 2}",
                    y=f"({y})+{d * 2}",
                )

            video_stream = video_stream.filter(
                "drawtext",
                **base,
                text=safe,
                fontcolor=color,
                borderw=4,
                bordercolor="black",
                shadowcolor="black@0.6",
                shadowx=2,
                shadowy=2,
                x="(w-text_w)/2",
                y=y,
            )

        return video_stream

    # ── public ────────────────────────────────────────────────────────────────

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
        ass_path = os.path.join(self.temp_dir, f"scene_{scene_id}.ass")
        header = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Elite,EliteSerif,64,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,2,2,50,50,480,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        def _apply_style(match):
            word = match.group(1)
            # Gold color & 20% scale bump for power words
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
        import re
        scene_id       = scene.get('id', 'Unknown')
        audio_path     = scene.get('audio_path', '')
        total_duration = scene.get('duration', 0)
        caption_text   = scene.get('caption_text', scene.get('text', ''))
        output_path    = os.path.join(self.temp_dir, f"scene_{scene_id}.mp4")

        try:
            if not audio_path or not os.path.exists(audio_path):
                print(f"   ❌ Scene {scene_id}: Audio file missing or invalid path.")
                return None

            input_audio = ffmpeg.input(audio_path)

            if is_avatar:
                print(f"   ⚙️ Processing Scene {scene_id}: 🤖 Avatar Mode (Cropped)")
                video_stream = (
                    ffmpeg.input(video_pair[0], stream_loop=-1)
                    .trim(duration=total_duration + 0.5)
                    .setpts('PTS-STARTPTS')
                    .filter('crop', 'iw', 'ih-150', 0, 0)
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase')
                    .filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    # Elite Pattern Interrupt: Slow 1.5x zoom
                    .filter('zoompan', z='min(zoom+0.0015,1.5)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
            else:
                print(f"   ⚙️ Processing Scene {scene_id}: 🎞️ A/B Split Mode")
                path_a, path_b = video_pair
                duration_a = total_duration / 2
                duration_b = (total_duration / 2) + 0.5

                stream_a = (
                    ffmpeg.input(path_a, stream_loop=-1)
                    .trim(duration=duration_a).setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    # Segment A Zoom
                    .filter('zoompan', z='min(zoom+0.0015,1.5)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
                stream_b = (
                    ffmpeg.input(path_b, stream_loop=-1)
                    .trim(duration=duration_b).setpts('PTS-STARTPTS')
                    .filter('scale', 1080, 1920, force_original_aspect_ratio='increase').filter('crop', 1080, 1920)
                    .filter('fps', fps=30, round='up')
                    # Segment B Zoom (reset)
                    .filter('zoompan', z='min(zoom+0.0015,1.5)', d=1, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
                )
                video_stream = ffmpeg.concat(stream_a, stream_b, v=1, a=0)

            if caption_text:
                ass_path = self._generate_ass_subtitles(caption_text, total_duration, scene_id)
                rel_ass_path = os.path.relpath(ass_path, os.getcwd()).replace("\\", "/")
                video_stream = video_stream.filter('subtitles', rel_ass_path, fontsdir="assets/fonts")

            runner = ffmpeg.output(
                video_stream, input_audio, output_path,
                vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None
            )
            runner.run(overwrite_output=True, quiet=True)
            return output_path

        except ffmpeg.Error as e:
            print(f"❌ Render Fail Scene {scene_id}: {e.stderr.decode('utf8') if e.stderr else str(e)}")
            return None

    def render_all_scenes(self, script_data, video_pairs):
        rendered_paths = []
        for i, scene in enumerate(script_data):
            current_pair = video_pairs[i]
            if current_pair is None:
                continue
            output_path = self.process_scene(scene, current_pair)
            if output_path:
                rendered_paths.append(output_path)
        return rendered_paths

    def concatenate_with_transitions(self, video_paths, output_filename="final_short.mp4"):
        print("🎬 Stitching final video...")
        output_path = os.path.join(self.final_dir, output_filename)

        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                print("⚠️ Could not delete old file — it may be open in a player.")

        if not video_paths:
            return None

        # ── INITIAL CLIP ─────────────────────────────────────────────────────
        input1      = ffmpeg.input(video_paths[0])
        # Force consistent audio format/sample rate before processing
        v_stream    = input1.video.filter('format', 'yuv420p').filter('scale', 1080, 1920)
        a_stream    = input1.audio.filter('aresample', 44100).filter('aformat', channel_layouts='stereo')
        
        current_dur = self.get_duration(video_paths[0])

        for i in range(1, len(video_paths)):
            next_clip = ffmpeg.input(video_paths[i])
            next_dur  = self.get_duration(video_paths[i])
            trans_dur = 0.5
            
            # ── PRECISION OFFSETS ─────────────────────────────────────────────
            # Subtract a small safety margin (0.05s) to ensure the offset 
            # is always strictly within the stream, even with rounding errors.
            offset = max(0, current_dur - trans_dur - 0.05)
            
            effect = random.choice(self.transitions)
            print(f"   ✨ Transition {i}: '{effect}' at {offset:.2f}s")

            # Validate next clip has video/audio
            next_v = next_clip.video.filter('format', 'yuv420p').filter('scale', 1080, 1920)
            next_a = next_clip.audio.filter('aresample', 44100).filter('aformat', channel_layouts='stereo')

            v_stream = ffmpeg.filter(
                [v_stream, next_v], 'xfade',
                transition=effect, duration=trans_dur, offset=offset
            )
            a_stream = ffmpeg.filter(
                [a_stream, next_a], 'acrossfade', d=trans_dur
            )
            
            # Update running duration: segment_a + segment_b - overlap
            current_dur = (current_dur + next_dur) - trans_dur

        try:
            runner = ffmpeg.output(
                v_stream, a_stream, output_path,
                vcodec='libx264', acodec='aac',
                pix_fmt='yuv420p', movflags='faststart', preset='medium'
            )
            runner.run(overwrite_output=True, quiet=False)
            print(f"✅ FINAL VIDEO SAVED: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            err_log = e.stderr.decode('utf8') if e.stderr else str(e)
            print(f"❌ Stitching Error: {err_log}")
            return None