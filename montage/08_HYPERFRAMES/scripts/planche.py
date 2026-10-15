"""Planche de contrôle : une image par (composition, seconde), posée sur gris, assemblée en une seule image.
usage : python scripts/planche.py sortie.png chapitre@1.5 manche@3 [--vars fichier.json]…
        (composition = fichier de compositions/ sans .html, ou chemin .html ; variables : comp@t@vars.json)"""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out, specs = sys.argv[1], sys.argv[2:]
tmp = Path(tempfile.mkdtemp(prefix="planche-"))
tiles = []
for i, spec in enumerate(specs):
    parts = spec.split("@")
    comp, t = parts[0], float(parts[1])
    path = comp if comp.endswith(".html") else f"compositions/{comp}.html"
    seq = tmp / f"s{i}"
    cmd = ["npx", "hyperframes", "render", ".", "-c", path, "--format", "png-sequence", "-f", "4", "-o", str(seq), "--quiet"]
    if len(parts) > 2:
        cmd += ["--variables-file", parts[2]]
    subprocess.run(cmd, cwd=ROOT, check=True, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    frames = sorted(seq.glob("*.png"))
    src = frames[min(len(frames) - 1, int(round(t * 4)))]
    tile = tmp / f"t{i}.png"
    subprocess.run(["magick", str(src), "-background", "#5a6470", "-flatten", "-resize", "640x", "-gravity", "north", "-fill", "yellow",
                    "-pointsize", "18", "-annotate", "+0+4", f"{Path(comp).stem} @{t}s", str(tile)], check=True)
    tiles.append(str(tile))
subprocess.run(["magick", "montage", *tiles, "-tile", "3x", "-geometry", "+4+4", "-background", "#111", out], check=True)
shutil.rmtree(tmp, ignore_errors=True)
print(out)
