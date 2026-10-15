"""Rend une preview vidéo d'une plage de timeline CapCut, sans ouvrir CapCut.

Lit un draft_content.json : le son vient de la piste principale, l'image de la piste
la plus haute qui a un clip à cet instant (les plans d'illustration recouvrent la voix).
Les clips combinés / effets / textes ne sont pas rendus : c'est un contrôle des coupes.

Usage : python scripts/capcut_preview.py <draft_content.json> <debut_s> <fin_s> <sortie.mp4>
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import h264  # noqa: E402

W, H, FPS = 960, 540, 30


def main() -> None:
    draft_path, t0, t1, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4])
    d = json.loads(Path(draft_path).read_text(encoding="utf-8"))
    videos = {m["id"]: m for m in d["materials"]["videos"]}
    tracks = [t for t in d["tracks"] if t["type"] == "video"]

    def clips(track):
        for s in track["segments"]:
            tr, src = s["target_timerange"], s["source_timerange"]
            yield (tr["start"] / 1e6, (tr["start"] + tr["duration"]) / 1e6, src["start"] / 1e6,
                   videos[s["material_id"]].get("path", ""))

    layers = [list(clips(t)) for t in tracks]
    cuts = sorted({t0, t1, *(x for layer in layers for c in layer for x in c[:2] if t0 < x < t1)})

    def at(layer, t):
        return next((c for c in layer if c[0] <= t < c[1] and c[3]), None)

    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            if b - a < 0.02:
                continue
            mid = (a + b) / 2
            audio = at(layers[0], mid)
            image = next((c for layer in reversed(layers) if (c := at(layer, mid))), None)
            part = Path(tmp) / f"{i:05d}.ts"
            dur = b - a
            args = ["ffmpeg", "-v", "error", "-y"]
            if image:
                args += ["-ss", f"{image[2] + a - image[0]:.3f}", "-t", f"{dur:.3f}", "-i", image[3]]
            else:
                args += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"color=black:s={W}x{H}:r={FPS}"]
            if audio:
                args += ["-ss", f"{audio[2] + a - audio[0]:.3f}", "-t", f"{dur:.3f}", "-i", audio[3]]
            else:
                args += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
            args += ["-map", "0:v:0", "-map", "1:a:0", "-vf", f"scale={W}:{H},fps={FPS}",
                     *h264(26, "veryfast"), "-c:a", "aac", "-ar", "48000",
                     "-ac", "2", "-shortest", "-f", "mpegts", str(part)]
            subprocess.run(args, check=True)
            parts.append(part)
        listing = Path(tmp) / "list.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                        "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(out)


if __name__ == "__main__":
    main()
