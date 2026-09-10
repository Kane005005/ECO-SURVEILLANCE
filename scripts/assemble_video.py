#!/usr/bin/env python3
"""Assemblage de la vidéo de démo ECO-SURVEILLANCE MALI.

- Génère la page-titre et le générique de fin (Pillow, tons de la marque).
- Normalise chaque clip en 1280×720, 25 fps (H.264).
- Enchaîne avec des fondus (xfade) et exporte video/ECO_SURVEILLANCE_DEMO.mp4.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "video" / "scenes"
WORK = SCENES_DIR / "work"
FINAL = ROOT / "video" / "ECO_SURVEILLANCE_DEMO.mp4"
W, H, FPS = 1280, 720, 25
TRANS = 0.4
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

GREEN = (21, 128, 61)
BLUE = (37, 99, 235)
INK = (15, 23, 42)
MUTED = (148, 163, 184)
WHITE = (255, 255, 255)
LIGHT_GREEN = (34, 197, 94)
LIGHT_BLUE = (96, 165, 250)


def gradient(size, top, bottom):
    img = Image.new("RGB", size)
    w, h = size
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        ImageDraw.Draw(img).line([(0, y), (w, y)], fill=color)
    return img


def draw_logo(draw, cx, cy, r):
    box = [cx - r, cy - r, cx + r, cy + r]
    draw.ellipse(box, outline=GREEN, width=3)
    for i in range(4):
        draw.arc(
            [cx - r * (0.75 + i * 0.08), cy - r * (0.75 + i * 0.08),
             cx + r * (0.75 + i * 0.08), cy + r * (0.75 + i * 0.08)],
            start=45, end=135, fill=tuple(int(min(255, x * 1.4)) for x in GREEN), width=2,
        )
    draw.ellipse([cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45], outline=LIGHT_BLUE, width=2)
    draw.polygon([(cx - r * 0.5, cy), (cx - r * 0.1, cy + r * 0.35), (cx + r * 0.55, cy - r * 0.4)],
                 fill=None, outline=LIGHT_GREEN, width=3)
    draw.ellipse([cx - r * 0.12, cy - r * 0.12, cx + r * 0.12, cy + r * 0.12], fill=LIGHT_BLUE)


def make_card(path, title, subtitle, footer=None):
    img = gradient((W, H), (9, 14, 28), (5, 24, 16))
    draw = ImageDraw.Draw(img)

    for i, rad in enumerate(range(260, 340, 26)):
        color = (22, 101, 52, max(6, 26 - i * 6))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        x = int(W * 0.82) - rad
        y = int(H * 0.18) - rad
        d.ellipse([x, y, x + rad * 2, y + rad * 2], fill=color)
        img = Image.alpha_composite(img.convert("RGBA"), overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

    draw_logo(draw, W // 2, 190, 70)

    ft = ImageFont.truetype(FONT_B, 72)
    sub_t = ImageFont.truetype(FONT, 30)
    foot_t = ImageFont.truetype(FONT, 22)
    small_t = ImageFont.truetype(FONT, 24)

    def center_text(y, text, font, fill):
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)

    center_text(320, "ECO-SURVEILLANCE", ft, LIGHT_GREEN)
    center_text(408, "MALI", ft, LIGHT_BLUE)
    center_text(500, subtitle, sub_t, MUTED)
    draw.rectangle([(W // 2 - 120, 574), (W // 2 + 120, 576)], fill=GREEN)
    if footer:
        center_text(600, footer, small_t, (100, 116, 139))
    img.save(path)
    print("carte:", path)


def make_outro(path):
    img = gradient((W, H), (5, 12, 22), (2, 12, 8))
    draw = ImageDraw.Draw(img)
    draw_logo(draw, W // 2, 240, 60)
    ft = ImageFont.truetype(FONT_B, 60)
    st = ImageFont.truetype(FONT, 30)
    sm = ImageFont.truetype(FONT, 22)

    def center_text(y, text, font, fill):
        w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)

    center_text(360, "ECO-SURVEILLANCE MALI", ft, LIGHT_GREEN)
    center_text(470, "Merci de votre attention", st, MUTED)
    center_text(560, "surveiller · alerter · agir", sm, LIGHT_BLUE)
    img.save(path)
    print("carte:", path)


def run(cmd):
    print("+", " ".join(str(c) for c in cmd)[:160])
    subprocess.run(cmd, check=True)


def ffprobe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def normalize(src, dst, start=0.0, t=None):
    cmd = ["ffmpeg", "-y"]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(src),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                   "setsar=1,pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                   f"fps={FPS},format=yuv420p"]
    if t is not None:
        cmd += ["-t", f"{t:.3f}"]
    cmd += ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            str(dst)]
    run(cmd)


def card_to_clip(card_path, dst, duration):
    vf = ("scale=1280:720,format=yuv420p,"
          f"zoompan=z='min(zoom+0.0007,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={FPS}")
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-t",
         f"{duration}", "-i", str(card_path), "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", str(dst)])


def build_filter(items):
    n = len(items)
    durs = [ffprobe_duration(p) for p in items]
    labels = []
    for i, p in enumerate(items):
        labels.append(f"{i:03d}")
    # fade in on first
    parts = [f"[0:v]fade=t=in:st=0:d=0.8[f0]"]
    prev = "[f0]"
    s = durs[0]
    for i in range(1, n):
        off = s - TRANS
        out = f"[x{i}]"
        parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={TRANS}:offset={off:.3f}{out}")
        prev = out
        s += durs[i] - TRANS
    parts.append(f"{prev}fade=t=out:st={s - 1.0:.3f}:d=1.0[v]")
    return ";".join(parts), s


def main():
    if not (SCENES_DIR / "manifest.json").exists():
        sys.exit("Manifest absent — lancez d'abord scripts/video_demo.py")
    manifest = json.loads((SCENES_DIR / "manifest.json").read_text())
    WORK.mkdir(exist_ok=True)

    intro_png = WORK / "intro.png"
    outro_png = WORK / "outro.png"
    make_card(intro_png, "ECO-SURVEILLANCE", "Plateforme intelligente de surveillance environnementale",
              footer="Démonstration")
    make_outro(outro_png)

    intro_clip = WORK / "000_intro.mp4"
    card_to_clip(intro_png, intro_clip, 4.0)

    items = [intro_clip]
    for entry in manifest:
        video = Path(entry["video"])
        if not video.exists():
            print("VIDEO MANQUANTE:", entry["slug"])
            continue
        dst = WORK / f"{len(items):03d}_{entry['slug']}.mp4"
        raw = ffprobe_duration(video)
        want = min(entry.get("duration", 5.0), max(0.8, raw - 1.0))
        start = raw - want
        print(f"{entry['slug']}: clip {raw:.1f}s -> fenêtre {want:.1f}s (start {start:.1f}s)")
        normalize(video, dst, start=start, t=want)
        items.append(dst)

    outro_clip = WORK / f"{len(items):03d}_outro.mp4"
    card_to_clip(outro_png, outro_clip, 3.0)
    items.append(outro_clip)

    flt, total = build_filter(items)
    print("Durée totale estimée:", round(total, 2), "s")
    cmd = ["ffmpeg", "-y"]
    for p in items:
        cmd += ["-i", str(p)]
    cmd += ["-f", "lavfi", "-t", f"{total+1}", "-i",
            "anullsrc=r=44100:cl=stereo", "-filter_complex", flt,
            "-map", "[v]", "-map", f"{len(items)}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "160k", "-shortest",
            "-movflags", "+faststart", str(FINAL)]
    run(cmd)
    print("FINAL:", FINAL, round(total, 1), "s")


if __name__ == "__main__":
    main()