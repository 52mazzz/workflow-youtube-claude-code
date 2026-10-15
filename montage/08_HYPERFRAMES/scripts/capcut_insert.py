"""Applique un dérushage (liste de coupes JSON) à un projet CapCut.

- Sauvegarde d'abord draft_content.json en draft_content.avant_claude_<date>.json.
- Supprime de la piste principale le clip brut indiqué par "remplace_a_partir_de" (et tout ce qui suit),
  puis ajoute les clips dans l'ordre, collés les uns aux autres.
- Les "broll" d'un groupe vont sur une 2e piste vidéo, son coupé, et remplissent la durée du groupe.
- Chaque clip est cloné depuis un clip existant du projet (mêmes réglages par défaut).

Refuse d'écrire si CapCut est ouvert (il écraserait le fichier en quittant).
Usage : python scripts/capcut_insert.py <projet_capcut> <liste.json> [--dry-run]
"""

import copy
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import rush as chemin_rush  # noqa: E402

DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
EXTRA_KINDS = ["speeds", "placeholder_infos", "canvases", "sound_channel_mappings", "material_colors", "vocal_separations"]


def new_id() -> str:
    return str(uuid.uuid4()).upper()


def capcut_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe"], capture_output=True, text=True).stdout
    return "CapCut.exe" in out


def media_duration_us(path: str) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return int(round(float(out) * 1e6))


class Project:
    def __init__(self, name: str):
        # nom d'un projet CapCut, ou chemin complet d'un dossier de projet (copie de test)
        self.dir = Path(name) if Path(name).is_dir() else DRAFTS / name
        self.content_path = self.dir / "draft_content.json"
        self.meta_path = self.dir / "draft_meta_info.json"
        self.d = json.loads(self.content_path.read_text(encoding="utf-8"))
        self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        self.fps = float(self.d.get("fps") or 30)
        self.main = next(t for t in self.d["tracks"] if t["type"] == "video")
        self.by_id = {m["id"]: m for m in self.d["materials"]["videos"]}
        self.library = {Path(v["file_Path"]).as_posix(): v for g in self.meta["draft_materials"] for v in g["value"]}
        # clip modèle : un clip "normal" de la piste principale, avec ses matériaux annexes
        self.template = next(s for s in reversed(self.main["segments"])
                             if self.by_id[s["material_id"]].get("path") and len(s["extra_material_refs"]) >= 6)

    def us(self, seconds: float) -> int:
        """Secondes -> microsecondes, calé sur la grille d'images du projet."""
        return int(round(round(seconds * self.fps) * 1e6 / self.fps))

    def find_material(self, mid: str):
        for kind, lst in self.d["materials"].items():
            if isinstance(lst, list):
                for m in lst:
                    if isinstance(m, dict) and m.get("id") == mid:
                        return kind, m
        return None, None

    def make_segment(self, path: str, src_start: float, src_end: float, target_start_us: int, muted=False, overlay=False):
        tpl = self.template
        video = copy.deepcopy(self.by_id[tpl["material_id"]])
        existing = next((m for m in self.d["materials"]["videos"] if m.get("path") == path), None)
        lib = self.library.get(path)
        video.update({
            "id": new_id(),
            "path": path,
            "material_name": Path(path).name,
            "duration": media_duration_us(path),
            "unique_id": existing["unique_id"] if existing else "",
            "local_material_id": lib["id"] if lib else "",
        })
        self.d["materials"]["videos"].append(video)

        refs = []
        for ref in tpl["extra_material_refs"]:
            kind, m = self.find_material(ref)
            if kind in EXTRA_KINDS:
                clone = copy.deepcopy(m)
                clone["id"] = new_id()
                self.d["materials"][kind].append(clone)
                refs.append(clone["id"])

        seg = copy.deepcopy(tpl)
        start_us, dur_us = self.us(src_start), self.us(src_end) - self.us(src_start)
        seg.update({
            "id": new_id(),
            "material_id": video["id"],
            "extra_material_refs": refs,
            "source_timerange": {"start": start_us, "duration": dur_us},
            "target_timerange": {"start": target_start_us, "duration": dur_us},
            "volume": 0.0 if muted else 1.0,
            "last_nonzero_volume": 1.0,
            "keyframe_refs": [],
        })
        if overlay:
            seg["render_index"] = seg["track_render_index"] = 1
        return seg


def main() -> None:
    project_name, edl_path = sys.argv[1], Path(sys.argv[2])
    dry = "--dry-run" in sys.argv
    p = Project(project_name)
    inside_capcut = DRAFTS in p.dir.resolve().parents
    if inside_capcut and capcut_running() and not dry:
        sys.exit("CapCut est ouvert : ferme-le complètement puis relance (sinon il écraserait les changements).")

    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    rush = edl.get("rush_dir")  # facultatif : sinon cherché dans tous les dossiers de rushs (commun.rush)

    segs = p.main["segments"]
    cut_at = next(i for i, s in enumerate(segs)
                  if Path(p.by_id[s["material_id"]].get("path", "")).name == edl["remplace_a_partir_de"])
    removed = segs[cut_at:]
    del segs[cut_at:]
    cursor = segs[-1]["target_timerange"]["start"] + segs[-1]["target_timerange"]["duration"] if segs else 0
    print(f"piste principale : {len(removed)} clip(s) retiré(s) à partir de {cursor / 1e6:.2f} s")

    overlay = {"id": new_id(), "type": "video", "flag": 0, "attribute": 0, "name": "", "is_default_name": True,
               "segments": []}
    for group in edl["groupes"]:
        g_start = cursor
        for name, a, b, _text in group["clips"]:
            seg = p.make_segment(chemin_rush(name, rush).as_posix(), a, b, cursor)
            segs.append(seg)
            cursor += seg["target_timerange"]["duration"]
        # plans d'illustration sur la 2e piste, son coupé, pour couvrir tout le groupe
        t = g_start
        brolls = group.get("broll", [])
        for i, item in enumerate(brolls):
            name, start = item[0], item[1]
            path = chemin_rush(name, rush).as_posix()
            available = media_duration_us(path) / 1e6 - start - 0.1
            remaining = (cursor - t) / 1e6
            if remaining <= 0.05:
                break
            wanted = item[2] if len(item) > 2 else remaining / (len(brolls) - i)
            length = min(available, remaining if i == len(brolls) - 1 else wanted)
            seg = p.make_segment(path, start, start + length, t, muted=True, overlay=True)
            overlay["segments"].append(seg)
            t += seg["target_timerange"]["duration"]
        print(f"  {group['titre']:<48} {g_start / 1e6:7.2f} s → {cursor / 1e6:7.2f} s"
              f"{'  (+ ' + str(len(brolls)) + ' plans)' if brolls else ''}")

    if overlay["segments"]:
        p.d["tracks"].append(overlay)
    p.d["duration"] = cursor  # la 2e piste reste toujours à l'intérieur de la piste principale
    p.meta["tm_duration"] = p.d["duration"]
    print(f"nouvelle durée : {p.d['duration'] / 1e6:.2f} s")

    if dry:
        print("(simulation : rien n'a été écrit)")
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(p.content_path, p.dir / f"draft_content.avant_claude_{stamp}.json")
    shutil.copy2(p.meta_path, p.dir / f"draft_meta_info.avant_claude_{stamp}.json")
    p.content_path.write_text(json.dumps(p.d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    p.meta_path.write_text(json.dumps(p.meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"écrit dans {p.content_path} (sauvegarde : draft_content.avant_claude_{stamp}.json)")


if __name__ == "__main__":
    main()
