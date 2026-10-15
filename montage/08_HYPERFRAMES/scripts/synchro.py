"""Contrôle de synchro image / voix d'un montage (à lancer avant tout rendu, après verifie_plan.py).
usage : python scripts/synchro.py <id>   → 02_ANALYSE/synchro_<id>.txt, code 1 si un point est à corriger

Ce que le script vérifie tout seul :
  - trou court (0,02 à 0,35 s) de jeu entre deux plein écran (scène, plein écran d'une carte) : « une image de jeu, puis
    l'écran en gros, puis le jeu » ; un plein écran commence pile sur la coupe d'image et le suivant pile à sa fin ;
  - changement vert / rouge d'une pastille sans mot dit juste avant (moins de 1,5 s) ;
  - sous-titre (soustitre) dont un mot n'est pas calé sur celui de la transcription (écart de plus de 0,25 s).
Ce qu'il montre pour que je le juge (lecture obligatoire, un élément par ligne) : le mot dit à l'entrée de chaque carte,
pastille, flèche, réaction de Tsar, mot, titre, logos et zoom, avec l'écart en secondes. Règle : un élément qui nomme
quelque chose (carte « LA TRANCHE », logo d'une IA, titre) entre sur le mot qui le dit, au plus 0,3 s avant ; un
élément de réaction entre sur le mot qui réagit ; un état vert / rouge change après le mot qui le justifie."""
import sys
from commun import ANALYSE, read_json, remap, video, HF

SCENES = {"partage", "progression", "insert", "scene_fenetre", "scene_vs", "scene_vainqueur", "scene_outro",
          "scene_fond", "scene_mots", "scene_description", "barres"}
SUIVIS = {"carte", "pastille", "fleche", "reaction", "mot", "titre_jeu", "duel", "capture", "note", "a_venir", "vignette"}


def main(vid):
    cfg = video(vid)
    plan = read_json(HF / "videos" / vid / "plan.json")
    mots = [(remap(w["startMs"] / 1000 - 0.12, cfg.get("coupes", [])), w["text"].strip())
            for w in read_json(ANALYSE / "transcriptions" / cfg["transcription"])]
    els = sorted(plan["elements"], key=lambda e: e["at"])
    lignes, points = [], []

    def mot_pres(t):
        return min(mots, key=lambda m: abs(m[0] - t))

    # 1. plein écran : trous courts
    pleins = []
    for e in els:
        v = e.get("vars", {})
        if e["type"] in SCENES:
            pleins.append((e["at"], e["at"] + e["dur"], e["id"]))
        elif e["type"] == "carte":
            pleins.append((e["at"], e["at"] + min(float(v.get("plein", 2.5)), e["dur"]), e["id"]))
    pleins.sort()
    for (a1, b1, i1), (a2, b2, i2) in zip(pleins, pleins[1:]):
        if 0.02 < a2 - b1 < 0.35:
            points.append(f"{b1:7.2f}  trou de {a2 - b1:.2f} s de jeu entre {i1} et {i2} : coller le second sur la fin du premier")
    # 2. éléments qui nomment ou réagissent : mot dit à l'entrée
    lignes.append("élément (entrée) : mot le plus proche (écart = élément − mot)")
    for e in els:
        if e["type"] in SUIVIS:
            t, m = mot_pres(e["at"])
            lignes.append(f"{e['at']:7.2f}  {e['id']:28s} {e['type']:9s} « {m} » @{t:.2f}  écart {e['at'] - t:+.2f}")
    # 3. pastilles : changement d'état sur un mot
    for e in els:
        if e["type"] != "pastille":
            continue
        for rel, etat in e["vars"].get("etat", []):
            t = e["at"] + rel
            avant = [m for m in mots if t - 1.5 <= m[0] <= t]
            if not avant:
                points.append(f"{t:7.2f}  {e['id']} passe « {etat} » sans mot dit dans les 1,5 s qui précèdent")
    # 4. sous-titres : mots calés sur la transcription
    for e in els:
        if e["type"] != "soustitre":
            continue
        for w in e["vars"].get("mots", []):
            t = e["at"] + float(w["t"])
            t0, m = mot_pres(t)
            if abs(t0 - t) > 0.25:
                points.append(f"{t:7.2f}  {e['id']} : « {w['text']} » à {t:.2f} s, mot dit le plus proche « {m} » à {t0:.2f} s")
    sortie = ANALYSE / f"synchro_{vid}.txt"
    sortie.write_text("\n".join([f"Synchro de « {vid} » : {len(points)} point(s) à corriger", *points, "", *lignes]), encoding="utf-8")
    print(f"synchro : {len(points)} point(s) à corriger → {sortie}")
    for p in points:
        print("  " + p)
    return 1 if points else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
