"""Planche d'images de rushs avec grille verticale (10 colonnes) pour choisir un recadrage 9:16.
usage : python rush_sheet.py out.png "rush.mkv@sec" ...  (nom du rush seul, cherché par commun.rush)"""
import subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import rush as chemin_rush  # noqa: E402
out, items = sys.argv[1], sys.argv[2:]
tmp = Path(tempfile.mkdtemp())
tiles = []
for i, it in enumerate(items):
    name, sec = it.rsplit("@", 1)
    p = tmp / f"{i}.png"
    grid = ",".join(f"drawbox=x={int(640 * k / 10)}:y=0:w=1:h=360:color=yellow@0.6" for k in range(1, 10))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", sec, "-i", str(chemin_rush(name)), "-frames:v", "1",
                    "-vf", f"scale=640:360,{grid},drawtext=text='{i + 1}':x=8:y=8:fontsize=28:fontcolor=white:box=1:boxcolor=black",
                    str(p)], check=True)
    tiles.append(p)
cols = 3
while len(tiles) % cols:
    tiles.append(tiles[-1])
args = sum((["-i", str(t)] for t in tiles), [])
n = len(tiles)
layout = "|".join(f"{(k % cols) * 640}_{(k // cols) * 360}" for k in range(n))
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex",
                f"xstack=inputs={n}:layout={layout}", "-frames:v", "1", out], check=True)
print(out)
