"""Reconstitue l'audio d'une timeline CapCut (lecture seule du projet) pour la transcrire.

Lit draft_content.json, prend chaque segment de la piste vidéo principale (source + plage)
et recolle l'audio correspondant, dans l'ordre de la timeline. Les clips sans fichier
(clips combinés) sont remplacés par du silence de même durée.

Sortie : 02_ANALYSE/audio_16k/capcut_<projet>.wav + 02_ANALYSE/capcut_<projet>_segments.tsv
Usage  : python scripts/capcut_timeline_audio.py <nom_du_projet_capcut>
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))


def main() -> None:
    project = sys.argv[1]
    draft = json.loads((DRAFTS / project / "draft_content.json").read_text(encoding="utf-8"))
    videos = {m["id"]: m for m in draft["materials"]["videos"]}
    track = next(t for t in draft["tracks"] if t["type"] == "video")

    work = ROOT / "02_ANALYSE" / "capcut_tmp"
    work.mkdir(parents=True, exist_ok=True)
    parts, rows = [], ["debut_timeline\tduree\tsource\tsource_debut\tsource_fin"]
    for i, seg in enumerate(track["segments"]):
        tr, src = seg["target_timerange"], seg["source_timerange"]
        path = videos[seg["material_id"]].get("path", "")
        dur = tr["duration"] / 1e6
        out = work / f"{i:04d}.wav"
        if path and Path(path).exists():
            start = src["start"] / 1e6
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", path,
                            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out)], check=True)
            rows.append(f"{tr['start']/1e6:.3f}\t{dur:.3f}\t{Path(path).name}\t{start:.3f}\t{start + dur:.3f}")
        else:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                            "-t", f"{dur:.3f}", "-c:a", "pcm_s16le", str(out)], check=True)
            rows.append(f"{tr['start']/1e6:.3f}\t{dur:.3f}\t(clip combiné)\t\t")
        parts.append(out)

    concat = work / "list.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    wav = ROOT / "02_ANALYSE" / "audio_16k" / f"capcut_{project}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:a", "pcm_s16le", str(wav)], check=True)
    (ROOT / "02_ANALYSE" / f"capcut_{project}_segments.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    for p in parts:
        p.unlink()
    concat.unlink()
    work.rmdir()
    print(wav)


if __name__ == "__main__":
    main()
