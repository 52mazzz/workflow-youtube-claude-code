"""Un élément du kit en fichier vidéo, pour le poser à la main dans CapCut (les éléments du kit sont en HTML).

    python scripts/calque.py etiquette --var texte=CLAUDE --var couleur=#E07A5A --var icone=burst -o 06_CAPCUT/x/claude.mov
    python scripts/calque.py flash -o flash.mov                  # vertical 1080 x 1920 (défaut), 60 i/s
    python scripts/calque.py reaction --var humeur=doute --var x=540 --dur 2.5 -o doute.mov
    python scripts/calque.py scene_vainqueur --var nom=CLAUDE --var detail="plus jouable" -o verdict.mp4
    python scripts/calque.py --liste                             # types et variables

Éléments transparents → MOV qtrle (alpha), comme l'export des vidéos longues : CapCut les garde transparents ;
scènes (`scene_*`) → MP4 plein cadre. `--horizontal` pour 1920 x 1080. Variables : `--var cle=valeur` (JSON si
possible : `--var x=540`, sinon texte ; les listes et objets se passent en JSON). `--dur` change la durée.
Hyperframes : la version épinglée dans package.json, lancée depuis le cache de npx (pas de téléchargement si elle y est).
TSAR_GPU=1 pour le rendu sur carte graphique (non par défaut)."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HF = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_compositions import SPECS, page  # noqa: E402


def hyperframes():
    pin = re.search(r"hyperframes@([\d.]+)", (HF / "package.json").read_text(encoding="utf-8")).group(1)
    for d in Path(os.path.expandvars(r"%LOCALAPPDATA%\npm-cache\_npx")).glob("*/node_modules/hyperframes"):
        try:
            if json.loads((d / "package.json").read_text(encoding="utf-8"))["version"] == pin:
                return ["node", str(d / "bin" / "hyperframes.mjs")]
        except (OSError, ValueError, KeyError):
            continue
    return ["npx", "--yes", f"hyperframes@{pin}"]


def main(argv):
    if "--liste" in argv or not argv:
        for kind, (dur, transparent, variables) in SPECS.items():
            print(f"{kind:18s} {dur:5.1f} s  {'MOV transparent' if transparent else 'MP4 plein cadre'}")
            for v in variables:
                print(f"    --var {v['id']}={v['default']}")
        return
    kind = argv[0]
    if kind not in SPECS:
        sys.exit(f"type inconnu : {kind} (python scripts/calque.py --liste)")
    dur0, transparent, variables = SPECS[kind]
    dur, out, vertical, v = dur0, None, "--horizontal" not in argv, {}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--dur":
            dur = float(argv[i + 1]); i += 1
        elif a == "-o":
            out = Path(argv[i + 1]); i += 1
        elif a == "--var":
            k, _, raw = argv[i + 1].partition("="); i += 1
            try:
                v[k] = json.loads(raw)
            except ValueError:
                v[k] = raw
        i += 1
    if not out:
        sys.exit("-o <fichier> manquant")
    ids = {x["id"] for x in variables}
    inconnues = set(v) - ids
    if inconnues:
        sys.exit(f"variable(s) inconnue(s) pour {kind} : {', '.join(sorted(inconnues))} (attendues : {', '.join(sorted(ids))})")
    # une liste ou un objet passé en JSON est redonné en texte JSON, comme le défaut des variables « J »
    v = {k: (json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) and next(d for d in variables if d["id"] == k)["type"] == "string" else x)
         for k, x in v.items()}
    w, h = (1080, 1920) if vertical else (1920, 1080)
    build = HF / "build" / "calques"
    build.mkdir(parents=True, exist_ok=True)
    nom = re.sub(r"[^\w-]", "_", Path(out).stem)   # un nom par fichier de sortie : deux rendus en parallèle ne se marchent pas dessus
    src = build / f"{kind}-{nom}.html"
    src.write_text(page(kind, dur, transparent, variables, w, h), encoding="utf-8")
    vf = build / f"{kind}-{nom}.vars.json"
    vf.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    out = out if out.is_absolute() else Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    gpu = os.environ.get("TSAR_GPU", "0") == "1"
    cmd = hyperframes() + ["render", ".", "-c", src.relative_to(HF).as_posix(), "-f", "60", "--quiet",
                           "--variables-file", str(vf), "-w", "2"] + (["--browser-gpu"] if gpu else [])
    shell = cmd[0] == "npx"
    if transparent:
        tmp = build / f"{kind}-{nom}.mov"
        r = subprocess.run(cmd + ["--format", "mov", "-o", str(tmp)], cwd=HF, shell=shell)
        if r.returncode:
            sys.exit("rendu échoué")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-r", "60", "-c:v", "qtrle", "-pix_fmt", "argb", str(out)], check=True)
        tmp.unlink()
    else:
        r = subprocess.run(cmd + ["--format", "mp4", "--crf", "16", "-o", str(out)], cwd=HF, shell=shell)
        if r.returncode:
            sys.exit("rendu échoué")
    print(f"{kind} {w}x{h} {dur:.2f}s → {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
