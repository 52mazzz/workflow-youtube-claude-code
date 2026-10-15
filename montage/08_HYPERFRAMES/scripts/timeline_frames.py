"""Planche des images de la timeline CapCut à des secondes données (plan de jeu visible le plus haut),
avec une grille pour viser les zooms. Lecture seule du projet.

Usage : python scripts/timeline_frames.py <projet> <sortie.png> <s1> <s2> ...
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import est_rush  # noqa: E402

DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))


def main() -> None:
    project, out, *times = sys.argv[1:]
    d = json.loads((DRAFTS / project / "draft_content.json").read_text(encoding="utf-8-sig"))
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    tmp = Path(tempfile.mkdtemp())
    tiles = []
    for k, ts in enumerate(times):
        t = float(ts) * 1e6
        best = None
        for s in (s for tr in d["tracks"] if tr["type"] == "video" for s in tr["segments"]):
            path = vids.get(s["material_id"], {}).get("path", "")
            st, du = s["target_timerange"]["start"], s["target_timerange"]["duration"]
            if est_rush(path) and st <= t < st + du:
                best = (path, (s["source_timerange"]["start"] + t - st) / 1e6)  # le dernier = le plus haut
        if not best:
            continue
        png = tmp / f"{k}.png"
        # grille : 8 colonnes x 6 lignes, pour lire la position de ce qu'on veut zoomer
        grid = "drawgrid=w=iw/8:h=ih/6:t=2:c=yellow@0.5"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{best[1]:.3f}", "-i", best[0], "-frames:v", "1",
                        "-vf", f"scale=640:360,{grid}", str(png)], check=True)
        lab = tmp / f"{k}_l.png"
        subprocess.run(["magick", str(png), "-gravity", "north", "-fill", "white", "-undercolor", "#000A",
                        "-pointsize", "22", "-annotate", "+0+4", f"{ts}s", str(lab)], check=True)
        tiles.append(str(lab))
    subprocess.run(["magick", "montage", *tiles, "-tile", "3x", "-geometry", "+4+4", "-background", "#111", out],
                   check=True)
    print(out)


if __name__ == "__main__":
    main()
