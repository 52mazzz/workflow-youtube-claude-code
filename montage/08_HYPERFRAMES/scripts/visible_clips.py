"""Plans vidéo visibles (rushs .mkv / scènes) d'un projet CapCut entre deux secondes.
usage : python visible_clips.py "<projet>" a b [a b ...]
Affiche : début-fin timeline, piste, fichier, début source (s), échelle/position."""
import json, os, sys
from pathlib import Path

root = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
d = json.loads((root / sys.argv[1] / "draft_content.json").read_text(encoding="utf-8"))
mats = {m["id"]: m for m in d["materials"]["videos"]}
ranges = [(float(a), float(b)) for a, b in zip(sys.argv[2::2], sys.argv[3::2])]
for a, b in ranges:
    print(f"== {a:.2f} - {b:.2f}")
    rows = []
    for ti, t in enumerate(d["tracks"]):
        if t["type"] != "video":
            continue
        for s in t["segments"]:
            st = s["target_timerange"]["start"] / 1e6
            en = st + s["target_timerange"]["duration"] / 1e6
            if en <= a or st >= b:
                continue
            m = mats.get(s["material_id"])
            if not m or not m.get("path"):
                continue
            name = Path(m["path"]).name
            if name.endswith(".mov"):
                continue  # overlays / sous-titres
            src = (s.get("source_timerange") or {}).get("start", 0) / 1e6
            sc = s["clip"]["scale"]["x"]
            rows.append((st, ti, f"{st:8.2f}-{en:8.2f}  piste {ti:2d}  {name:40s} src {src:8.2f}  x{sc:.2f}"))
    for r in sorted(rows):
        print(r[2])
