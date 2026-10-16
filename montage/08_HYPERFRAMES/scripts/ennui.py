"""Passages ennuyeux à l'écran, à habiller d'une vignette (règle du 2026-10-10, sukuna-ia).
usage : python scripts/ennui.py <id> [fichier.mp4]   → 02_ANALYSE/ennui_<id>.txt, code 1 s'il y a des passages

Après le rendu (étape 8, avec revue.py). Un passage est signalé quand, hors scène plein écran :
  - l'image bouge à peine pendant au moins 2 s (écran de texte, menu, plan fixe), ou
  - rien ne s'ajoute à l'image pendant au moins 6 s : aucun élément (l'étiquette en bas à gauche et les sous-titres ne
    comptent pas), aucun zoom de lecture ni punch.
Pour chaque passage, le script donne ce qui est dit. Je propose alors une `vignette` (image dans une case propre,
entrée sur le mot, sortie, bruitages) de ce qui est nommé : logo d'une œuvre, d'un jeu ou d'un outil, personnage,
objet, capture. Il choisit l'image sur une planche numérotée. Rien d'étranger à ce qui est dit, jamais pour un compteur.
"""
import re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ANALYSE, HF, read_json, remap, video  # noqa: E402

FIXE, VIDE = 2.0, 6.0
SCENES = {"partage", "progression", "frise", "insert", "scene_fenetre", "scene_vs", "scene_vainqueur", "scene_outro",
          "scene_fond", "scene_mots", "scene_description", "barres"}
DISCRETS = {"pastille", "soustitre", "etiquette"}  # toujours là ou trop discrets : ne meublent pas l'écran


def mm(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def fixes(mp4: Path, fin: float) -> list[tuple[float, float]]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-an", "-vf",
                          f"scale=320:-2,freezedetect=n=0.01:d={FIXE}", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    a = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    b = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", err)] + [fin]
    return list(zip(a, b))


def moins(intervalle, caches):
    """Parties d'un intervalle qui ne sont couvertes par aucun des caches."""
    morceaux = [intervalle]
    for c0, c1 in caches:
        suite = []
        for a, b in morceaux:
            if c1 <= a or c0 >= b:
                suite.append((a, b))
                continue
            if c0 > a:
                suite.append((a, c0))
            if c1 < b:
                suite.append((c1, b))
        morceaux = suite
    return morceaux


def main(vid: str, mp4=None) -> int:
    cfg = video(vid)
    plan = read_json(HF / "videos" / vid / "plan.json")
    out = Path(cfg["out"])
    mp4 = Path(mp4) if mp4 else out / f"{vid} - final.mp4"
    fin = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                               capture_output=True, text=True).stdout or 0)
    mots = [(remap(w["startMs"] / 1000, cfg.get("coupes", [])), w["text"].strip())
            for w in read_json(ANALYSE / "transcriptions" / cfg["transcription"])]
    els = plan["elements"]
    pleins = [(e["at"], e["at"] + e["dur"]) for e in els if e["type"] in SCENES]
    pleins += [(e["at"], e["at"] + min(float(e.get("vars", {}).get("plein", 2.5)), e["dur"])) for e in els if e["type"] == "carte"]
    zooms = [(z[0], z[0] + z[1]) for z in cfg.get("zooms", {}).get("punch", [])]
    meubles = [(e["at"], e["at"] + e["dur"]) for e in els if e["type"] not in DISCRETS | SCENES] + zooms + pleins

    passages = []
    for a, b in fixes(mp4, fin):
        passages += [(x, y, "image presque immobile") for x, y in moins((a, b), pleins) if y - x >= FIXE]
    for x, y in moins((0.0, fin), sorted(meubles)):
        if y - x >= VIDE:
            passages.append((x, y, "rien ne s'ajoute à l'image"))
    passages.sort()
    joints = []
    for a, b, quoi in passages:  # deux passages qui se touchent (un zoom lent coupe une image figée) n'en font qu'un
        if joints and a - joints[-1][1] < 1.0 and joints[-1][2] == quoi:
            joints[-1] = (joints[-1][0], max(b, joints[-1][1]), quoi)
        else:
            joints.append((a, b, quoi))
    passages = joints

    lignes = [f"Passages ennuyeux de « {vid} » ({mp4.name}) : {len(passages)} (vignette à proposer, voir l'en-tête du script)", ""]
    for a, b, quoi in passages:
        dit = " ".join(m for t, m in mots if a - 0.2 <= t < b)
        lignes.append(f"{mm(a)} → {mm(b)} ({b - a:.1f} s)  {quoi}")
        lignes.append(f"    dit : « {dit or '(rien)'} »")
    rapport = ANALYSE / f"ennui_{vid}.txt"
    rapport.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    print(f"→ {rapport}")
    return 1 if passages else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
