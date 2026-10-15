"""Balayage serré d'un ou plusieurs rushs : une vignette toutes les P secondes, avec « rush@seconde » écrit dessus.
Pour retrouver un type de plan précis (face caméra, mob, dimension…).
usage : python scripts/rush_scan.py sortie.png P "motif_rush" [--cols 16] [--w 120]"""
import subprocess, sys, tempfile
from pathlib import Path
from commun import rushes

out, period, pattern = sys.argv[1], float(sys.argv[2]), sys.argv[3]
cols = int(sys.argv[sys.argv.index("--cols") + 1]) if "--cols" in sys.argv else 16
w = int(sys.argv[sys.argv.index("--w") + 1]) if "--w" in sys.argv else 120
tmp = Path(tempfile.mkdtemp(prefix="rushscan-"))
tiles = []
for r in rushes(pattern):  # .mkv, .mp4, .mov de Documents/TSAR/Videos/*/Rush
    seq = tmp / r.stem
    seq.mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(r), "-vf", f"fps=1/{period},scale={w}:-2",
                    "-q:v", "5", str(seq / "%05d.jpg")], check=True)
    for k, f in enumerate(sorted(seq.glob("*.jpg"))):
        lab = tmp / f"{r.stem}_{k:05d}.jpg"
        subprocess.run(["magick", str(f), "-fill", "yellow", "-undercolor", "#000A", "-pointsize", "10", "-gravity", "northwest",
                        "-annotate", "+1+1", f"{r.stem[11:]}@{k * period:.0f}", str(lab)], check=True)
        tiles.append(str(lab))
subprocess.run(["magick", "montage", *tiles, "-tile", f"{cols}x", "-geometry", "+1+1", "-background", "#111", out], check=True)
print(out, len(tiles), "vignettes")
