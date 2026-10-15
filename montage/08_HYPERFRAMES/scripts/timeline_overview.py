"""Vue d'ensemble d'une timeline CapCut pour préparer le motion design.

Pour chaque phrase dite (transcription de la timeline) : temps, texte, et ce qu'on voit à l'écran
(NOIR = rush voix sur écran noir, JEU = rush avec image, +PLAN = plan posé au-dessus).
Usage : python scripts/timeline_overview.py <projet_capcut>
Prérequis : scripts/capcut_timeline_audio.py <projet> puis node scripts/transcribe.ts capcut_<projet>.wav
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
CACHE = ROOT / "02_ANALYSE" / "luminance_rushs.json"


def luminance(path: str, cache: dict) -> float:
    if path not in cache:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", "2", "-t", "4", "-i", path, "-an", "-vf",
                              "fps=1,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        vals = [float(l.split("YAVG=")[1]) for l in err.splitlines() if "YAVG=" in l]
        cache[path] = max(vals) if vals else 0.0
    return cache[path]


def main():
    project = sys.argv[1]
    d = json.loads((DRAFTS / project / "draft_content.json").read_text(encoding="utf-8"))
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    main_track = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    overlays = [s for t in d["tracks"] if t.get("flag") == 2 for s in t["segments"]]

    def visual(t: float) -> str:
        seg = next((s for s in main_track["segments"]
                    if s["target_timerange"]["start"] <= t * 1e6 < s["target_timerange"]["start"] + s["target_timerange"]["duration"]), None)
        path = vids[seg["material_id"]].get("path", "") if seg else ""
        kind = "NOIR" if path and luminance(path, cache) < 25 else ("JEU" if path else "?")
        if any(s["target_timerange"]["start"] <= t * 1e6 < s["target_timerange"]["start"] + s["target_timerange"]["duration"]
               for s in overlays):
            kind += "+PLAN"
        return kind

    words = json.loads((ROOT / "02_ANALYSE" / "transcriptions" / f"capcut_{project}.json").read_text(encoding="utf-8"))
    phrase, start, prev = [], None, None
    lines = []

    def flush():
        if phrase:
            lines.append(f"{start:6.1f} {visual(start + 0.2):9} {' '.join(phrase)}")

    for w in words:
        s, txt = w["startMs"] / 1000, w["text"].strip()
        if not txt:
            continue
        if phrase and (s - prev > 0.7 or phrase[-1].endswith((".", "?", "!"))):
            flush()
            phrase, start = [], None
        if start is None:
            start = s
        phrase.append(txt)
        prev = w["endMs"] / 1000
    flush()
    CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    out = ROOT / "02_ANALYSE" / f"vue_{project}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
