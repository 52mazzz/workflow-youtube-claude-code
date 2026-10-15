"""Index visuel des rushs : N vignettes par rush (réparties sur sa durée), une ligne par rush, nom en marge.
Pour repérer vite un type de plan (face caméra, jeu, écran noir…) sans ouvrir les vidéos.
usage : python scripts/rush_index.py sortie.png "2026-09-27*" [--n 4] [--depuis 0 --jusqua 999]"""
import subprocess, sys, tempfile
from pathlib import Path
from commun import rushes as trouver_rushes

out, pattern = sys.argv[1], sys.argv[2]
n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4
rushes = trouver_rushes(pattern)  # .mkv, .mp4, .mov de Documents/TSAR/Videos/*/Rush
tmp = Path(tempfile.mkdtemp(prefix="rushidx-"))
rows = []
for i, r in enumerate(rushes):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(r)],
                             capture_output=True, text=True).stdout)
    thumbs = []
    for k in range(n):
        t = d * (k + 0.5) / n
        p = tmp / f"{i}_{k}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(r), "-frames:v", "1", "-vf", "scale=192:108", str(p)])
        thumbs.append(str(p))
    row = tmp / f"row{i}.png"
    label = f"{r.stem[5:]}  {d:.0f}s"
    subprocess.run(["magick", *thumbs, "+append", "-gravity", "west", "-background", "#111", "-splice", "150x0",
                    "-fill", "yellow", "-pointsize", "15", "-annotate", "+4+0", label, str(row)], check=True)
    rows.append(str(row))
half = (len(rows) + 1) // 2
cols = [tmp / "c1.png", tmp / "c2.png"]
subprocess.run(["magick", *rows[:half], "-append", str(cols[0])], check=True)
subprocess.run(["magick", *(rows[half:] or rows[:1]), "-append", str(cols[1])], check=True)
subprocess.run(["magick", str(cols[0]), str(cols[1]), "-background", "#111", "+append", out], check=True)
print(out, len(rushes), "rushs")
