"""Reporte les temps d'une vidéo (plan.json, video.json) d'une ancienne timeline vers la nouvelle après un dérush
corrigé (prises retirées, blancs raccourcis) : chaque instant est ramené à sa position dans le rush (segments de
l'ancien projet), puis retrouvé dans le nouveau projet. Un instant tombé dans un passage retiré va au début du clip
suivant. Les durées suivent (fin recalée de la même façon).

Usage : python scripts/recale.py <id> "<ancien projet>" "<nouveau projet>"   (écrit plan.json et video.json, copies .avant-recale)
"""
import json
import shutil
import sys
from pathlib import Path
from commun import draft, video


def segs(project):
    if project.endswith(".tsv"):  # relevé de capcut_timeline_audio.py (état posé par Claude, même si le projet a été retouché)
        import csv
        rows = csv.DictReader(open(project, encoding="utf-8"), delimiter="\t")
        return [(float(r["debut_timeline"]), float(r["duree"]), Path(r["source"]).name, float(r["source_debut"])) for r in rows]
    d = draft(project)
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    return [(s["target_timerange"]["start"] / 1e6, s["target_timerange"]["duration"] / 1e6,
             Path(vids[s["material_id"]]["path"]).name, s["source_timerange"]["start"] / 1e6) for s in main["segments"]]


def make_map(old, new):
    def f(t):
        seg = next((s for s in old if s[0] <= t < s[0] + s[1]), old[-1] if t >= old[-1][0] else old[0])
        name, src = seg[2], seg[3] + min(max(t - seg[0], 0), seg[1])
        same = [s for s in new if s[2] == name]
        hit = next((s for s in same if s[3] - 0.02 <= src <= s[3] + s[1] + 0.02), None)
        if hit:
            return round(hit[0] + src - hit[3], 3)
        after = [s for s in same if s[3] > src]  # passage retiré : début du clip suivant de ce rush
        if after:
            return round(min(after, key=lambda s: s[3])[0], 3)
        return round(t, 3)
    return f


def main(vid, old_p, new_p):
    cfg = video(vid)
    m = make_map(segs(old_p), segs(new_p))
    span = lambda at, dur: (m(at), max(0.1, round(m(at + dur - 0.01) + 0.01 - m(at), 3)))  # noqa: E731

    pf = cfg["dir"] / "plan.json"
    shutil.copy2(pf, pf.with_suffix(".avant-recale.json"))
    plan = json.loads(pf.read_text(encoding="utf-8"))
    for p in plan.get("plans", []) + plan.get("elements", []):
        p["at"], p["dur"] = span(p["at"], p["dur"])
    pf.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    vf = cfg["dir"] / "video.json"
    shutil.copy2(vf, vf.with_suffix(".avant-recale.json"))
    v = json.loads(vf.read_text(encoding="utf-8"))
    v["projet"] = new_p
    v["musiques"] = [[n, m(a), m(b), *rest] for n, a, b, *rest in v.get("musiques", [])]
    v["sfx"] = [[m(t), *rest] for t, *rest in v.get("sfx", [])]
    v["transitions"] = [[m(t), *rest] for t, *rest in v.get("transitions", [])]
    v["sous_titres"]["phrases"] = [[m(t), *rest] for t, *rest in v["sous_titres"].get("phrases", [])]
    v["zooms"]["punch"] = [[m(t), *rest] for t, *rest in v["zooms"].get("punch", [])]
    vf.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"recalé : {pf.name}, {vf.name} ({old_p} → {new_p})")


if __name__ == "__main__":
    main(*sys.argv[1:4])
