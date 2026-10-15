"""Dessine la forme d'onde d'une portion de voix avec les mots transcrits et une grille temporelle.
Outil d'analyse pour choisir des points de coupe et caler les animations sur la voix.

Usage : python scripts/waveform.py <rush> <debut_s> <fin_s> [sortie.png]
  <rush> : nom sans extension, ex. 2026-09-26_12-03-47
Sortie par défaut : 02_ANALYSE/formes_onde/<rush>_<debut>-<fin>.png
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOICE = ROOT / "02_ANALYSE" / "voix"
TRANSCRIPTS = ROOT / "02_ANALYSE" / "transcriptions"
OUT_DIR = ROOT / "02_ANALYSE" / "formes_onde"
WIDTH, WAVE_H, LABEL_H = 1600, 220, 90
FONT = "Arial"


def main() -> None:
    rush, start, end = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(sys.argv[4]) if len(sys.argv) > 4 else OUT_DIR / f"{rush}_{start:g}-{end:g}.png"
    wave = out.with_suffix(".wave.png")
    dur = end - start
    px = WIDTH / dur

    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", str(VOICE / f"{rush}.wav"),
         "-filter_complex",
         f"[0]aformat=channel_layouts=mono,showwavespic=s={WIDTH}x{WAVE_H}:colors=0x4FC3F7:scale=sqrt[w];"
         f"color=c=0x111111:s={WIDTH}x{WAVE_H}[bg];[bg][w]overlay",
         "-frames:v", "1", str(wave)],
        check=True,
    )

    draw: list[str] = []
    # grille : trait fin tous les 0,1 s, trait fort + étiquette toutes les 0,5 s
    t = round(start * 10) / 10
    while t <= end:
        x = (t - start) * px
        major = abs(t * 2 - round(t * 2)) < 1e-6
        color = "#777" if major else "#333"
        draw += ["-stroke", color, "-draw", f"line {x:.1f},0 {x:.1f},{WAVE_H}"]
        if major:
            draw += ["-stroke", "none", "-fill", "#aaa", "-pointsize", "13",
                     "-draw", f"text {x + 2:.1f},{WAVE_H + 14} '{t:.1f}'"]
        t = round(t + 0.1, 2)

    transcript = TRANSCRIPTS / f"{rush}.json"
    if transcript.exists():
        row = 0
        for word in json.loads(transcript.read_text(encoding="utf-8")):
            s = word["startMs"] / 1000
            if not (start <= s <= end):
                continue
            x = (s - start) * px
            y = WAVE_H + 34 + (row % 3) * 18
            text = word["text"].strip().replace("'", "’")
            draw += ["-stroke", "#FFB74D", "-draw", f"line {x:.1f},0 {x:.1f},{WAVE_H}",
                     "-stroke", "none", "-fill", "#FFB74D", "-pointsize", "15",
                     "-draw", f"text {x + 2:.1f},{y} '{text}'"]
            row += 1

    subprocess.run(
        ["magick", str(wave), "-background", "#111111", "-gravity", "north",
         "-extent", f"{WIDTH}x{WAVE_H + LABEL_H}", "-gravity", "northwest", "-font", FONT,
         "-strokewidth", "1", *draw, str(out)],
        check=True,
    )
    wave.unlink()
    print(out)


if __name__ == "__main__":
    main()
