"""Comble les passages où l'écran reste noir (rush voix seule, rien par-dessus).   python scripts/combler.py <id>

Pour chaque trou, le plan de jeu visible juste avant continue dans son rush (suite directe), posé au-dessus de la
piste principale. Rush « noir » = luminance moyenne ≤ 20 (02_ANALYSE/luminance_rushs.json, écrit par timeline_overview.py).
Sortie : 06_CAPCUT/<id>/plan_comblement.json → capcut_bridge.py place "<projet>" plan_comblement.json
"""
import subprocess, sys
from pathlib import Path
from commun import ANALYSE, draft, est_rush, read_json, video, write_json


def duration(path: str) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)


def main(vid: str) -> None:
    cfg = video(vid)
    lum = {Path(k).name: v for k, v in read_json(ANALYSE / "luminance_rushs.json", {}).items()}
    d = draft(cfg["projet"])
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    shots, cover = [], []
    for level, t in enumerate(d["tracks"]):
        if t["type"] != "video":
            continue
        for s in t["segments"]:
            p = vids.get(s["material_id"], {}).get("path", "")
            a = s["target_timerange"]["start"] / 1e6
            b = a + s["target_timerange"]["duration"] / 1e6
            rush = est_rush(p)
            if (p.lower().endswith(".mp4") and not rush) or (rush and lum.get(Path(p).name, 99) > 20):
                cover.append((a, b))
                if rush:
                    shots.append((a, b, level, p, s["source_timerange"]["start"] / 1e6))
    cover.sort()
    gaps, t0 = [], 0.0
    for a, b in cover:
        if a > t0 + 0.2:
            gaps.append((t0, a))
        t0 = max(t0, b)
    items = []
    for a, b in gaps:
        before = [s for s in shots if abs(s[1] - a) < 0.05]
        if not before:
            print(f"trou {a:.2f}–{b:.2f} : aucun plan juste avant, laissé tel quel")
            continue
        _, end, _, path, src0 = max(before, key=lambda s: s[2])
        src = src0 + (end - max(s[0] for s in before if s[3] == path))
        need = b - a
        if src + need > duration(path) - 0.1:
            src = max(0.0, duration(path) - need - 0.1)
        items.append({"file": path, "at": round(a, 3), "dur": round(need, 3), "src": round(src, 3), "layer": 1, "mute": True})
        print(f"trou {a:.2f}–{b:.2f} ({need:.2f} s) ← suite de {Path(path).name} depuis {src:.2f} s")
    write_json(cfg["out"] / "plan_comblement.json", {"items": items})


if __name__ == "__main__":
    main(sys.argv[1])
