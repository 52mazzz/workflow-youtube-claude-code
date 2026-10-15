"""Variété d'une vidéo par rapport aux précédentes : ouverture, musiques, transitions.   python scripts/variete.py <id>

Demande du 2026-10-06 (note manuscrite) : ouvertures, musiques et transitions plus variées, sans que l'utilisateur ait à
le surveiller. À lancer après avoir rempli video.json et plan.json (étape 3 du montage), puis avant l'export.

Compare videos/<id>/ aux montages précédents de 08_HYPERFRAMES/videos/ (les plus récents d'abord : « Publiée le » de
videos/<id>/suivi.md du dépôt, sinon "date" de video.json ; seulement ceux d'avant celui-ci) :
  - ouverture : video.json → "ouverture" (une recette d'OUVERTURES) ; la même que l'une des 2 dernières vidéos = à varier ;
  - musiques : un morceau déjà pris pour la même partie (le hook surtout) dans la vidéo d'avant, un morceau qui revient
    plus de 2 fois dans la vidéo ; liste des morceaux de musiques/perso/ pas utilisés récemment, et le signale quand la
    bibliothèque a moins de morceaux que de parties (le choix lui-même : musique.py choisir) ;
  - transitions : video.json "transitions" + transitions.json (sauts de scène automatiques) + cartes titre de plan.json ;
    un type qui fait plus de la moitié, moins de 3 types pour 6 transitions ou plus, le même type dominant que la vidéo
    d'avant ; liste des types pas encore utilisés.
Code de sortie 1 s'il y a quelque chose à varier (à corriger ou à justifier, comme controle.py), 0 sinon.
"""
import json, re, sys
from collections import Counter
from datetime import date
from pathlib import Path

HF = Path(__file__).resolve().parent.parent
VIDEOS = HF / "videos"
PERSO = HF.parent / "04_RESSOURCES" / "musiques" / "perso"
DEPOT_VIDEOS = HF.parent.parent / "videos"

OUVERTURES = {
    "resultat_partage": "les deux résultats en écran partagé, celui pas encore montré flouté (WOLF, Short glacon-ia)",
    "flash_plans": "plans rapides du résultat avec flash et clics d'appareil photo (pokemon-ia)",
    "avant_apres": "le jeu de base, puis le résultat (« Minecraft de base ressemble à ça », 0927)",
    "pire_moment": "le bug ou l'échec le plus drôle d'abord, puis « comment on en est arrivé là »",
    "question_ecran": "une question ou un pari à l'écran sur le résultat (« laquelle a codé ça ? »), réponse plus tard",
    "chiffre_choc": "un chiffre énorme en carte plein écran (« 22 créatures en 40 min »), puis le jeu",
    "trois_plans": "trois plans de plus en plus forts en 9 s, puis la mission (WOLF, vidéo des avatars)",
}
TRANSITIONS = ["glisse_gauche", "glisse_droite", "glisse_haut", "glisse_bas", "flash", "obturateur", "carte"]
ANCIENS = {"_exemple": "0927"}  # montages d'avant les ids courts


def lire(path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def date_de(d: Path) -> str:
    """« Publiée le » de suivi.md, sinon video.json → "date" (montages sans suivi : 0927, Shorts), sinon aujourd'hui
    (vidéo en cours de montage)."""
    suivi = DEPOT_VIDEOS / d.name / "suivi.md"
    if suivi.exists():
        m = re.search(r"Publiée le\s*:\s*(\d{4}-\d{2}-\d{2})", suivi.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return lire(d / "video.json").get("date") or date.today().isoformat()


def montage(d: Path) -> dict:
    cfg, plan = lire(d / "video.json"), lire(d / "plan.json")
    trans = [t[1] for t in cfg.get("transitions", [])]
    auto = lire(d / "transitions.json").get("elements", [])
    trans += [e["type"] for e in auto if e.get("note") == "saut de scène"]
    trans += ["carte" for e in plan.get("elements", []) if e.get("type") == "carte"]
    musiques = [(m[0], Path(m[3]).name) for m in cfg.get("musiques", [])]
    return {"id": ANCIENS.get(d.name, d.name), "ouverture": cfg.get("ouverture", ""), "musiques": musiques, "transitions": trans}


def precedents(vid: str) -> list:
    """Montages publiés ou faits avant celui-ci, le plus récent d'abord."""
    jour = date_de(VIDEOS / vid)
    dirs = [d for d in VIDEOS.iterdir() if d.is_dir() and d.name not in ("_modele", vid) and (d / "video.json").exists()
            and date_de(d) < jour]
    return [montage(d) for d in sorted(dirs, key=date_de, reverse=True)]


def rapport(cur: dict, avant: list) -> list:
    lignes, recents = [], avant[:2]
    # ouverture
    o = cur["ouverture"]
    deja = [p["ouverture"] for p in avant if p["ouverture"]]
    libres = [k for k in OUVERTURES if k not in deja[:3]]
    if not o:
        lignes.append(f"ouverture : non choisie (video.json → \"ouverture\"). Pas utilisées récemment : {', '.join(libres)}")
    elif o not in OUVERTURES:
        lignes.append(f"ouverture : « {o} » n'est pas dans le catalogue de variete.py (à y ajouter avec sa description)")
    elif o in [p["ouverture"] for p in recents]:
        qui = next(p["id"] for p in recents if p["ouverture"] == o)
        lignes.append(f"ouverture : « {o} » déjà prise par {qui}. Pas utilisées récemment : {', '.join(libres)}")
    # musiques
    if cur["musiques"]:
        if avant and avant[0]["musiques"]:
            prev = dict(avant[0]["musiques"])
            for part, f in cur["musiques"]:
                if prev.get(part) == f:
                    lignes.append(f"musique : « {f} » déjà sur la partie « {part} » dans {avant[0]['id']}")
        for f, n in Counter(f for _, f in cur["musiques"]).items():
            if n > 2:
                lignes.append(f"musique : « {f} » revient {n} fois dans cette vidéo")
        biblio = sorted(p.name for p in PERSO.glob("*.mp3")) if PERSO.exists() else []
        recents_f = {f for p in recents for _, f in p["musiques"]} | {f for _, f in cur["musiques"]}
        libres_m = [f for f in biblio if f not in recents_f]
        parties = len(cur["musiques"])
        if len(biblio) < parties:
            lignes.append(f"musique : {len(biblio)} morceaux dans musiques/perso/ pour {parties} parties : impossible de ne pas "
                          f"répéter ; chercher du neuf : python scripts/musique.py chercher <moment>")
        if libres_m:
            lignes.append(f"musique (info) : pas utilisés récemment : {', '.join(libres_m)}")
    # transitions
    t = cur["transitions"]
    if t:
        c = Counter(t)
        top, n = c.most_common(1)[0]
        if len(t) >= 4 and n / len(t) > 0.5:
            lignes.append(f"transitions : « {top} » fait {n} sur {len(t)}")
        if len(t) >= 6 and len(c) < 3:
            lignes.append(f"transitions : seulement {len(c)} types pour {len(t)} transitions ({', '.join(c)})")
        if avant and avant[0]["transitions"]:
            top_prev = Counter(avant[0]["transitions"]).most_common(1)[0][0]
            if top == top_prev and len(t) >= 4:
                lignes.append(f"transitions : « {top} » domine déjà {avant[0]['id']}")
        jamais = [k for k in TRANSITIONS if k not in c]
        if jamais and lignes and lignes[-1].startswith("transitions"):
            lignes.append(f"transitions (info) : pas utilisées ici : {', '.join(jamais)}")
    return lignes


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    vid = sys.argv[1]
    d = VIDEOS / vid
    if not (d / "video.json").exists():
        sys.exit(f"{d / 'video.json'} introuvable")
    cur, avant = montage(d), precedents(vid)
    print(f"{vid} comparée à : {', '.join(p['id'] for p in avant[:3]) or 'aucune vidéo précédente'}")
    lignes = rapport(cur, avant)
    print("\n".join(lignes) if lignes else "rien à varier")
    sys.exit(1 if any("(info)" not in l for l in lignes) else 0)


if __name__ == "__main__":
    main()
