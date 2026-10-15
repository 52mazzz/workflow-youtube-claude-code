"""Transitions calées sur les vraies coupes d'image du projet CapCut.   python scripts/transitions.py <id>

Seulement entre deux moments qui n'ont rien à voir (changement de partie, de lieu, vainqueur), jamais sur les plans
rapides du début, ~12 pour 10 min, en variant (retours du 2026-10-03) :
  « glisse_gauche » / « glisse_droite » / « glisse_haut » / « glisse_bas » (haut et bas ajoutés le 2026-10-06 pour varier) :
     l'image sortante pousse l'entrante, mouvement adouci (accélère puis ralentit), sans flou, whoosh ; rendu par FFmpeg
     à partir des deux plans visibles de part et d'autre de la coupe ;
  « flash » : éclair blanc + déclic d'appareil photo (son CapCut « click (camera shutter sound single shot) ») ;
  « obturateur » : volets noirs + déclic ;
  une coupe nette n'a besoin d'aucune entrée. Plus de montée (riser) avant une coupe : refusé.
video.json → "transitions": [[seconde approximative, type, "pourquoi"]] ; chaque moment est recalé sur le changement
de plan visible le plus proche (±0,8 s), plans de jeu de plan.json compris.
Sortie : videos/<id>/transitions.json (éléments pour export_capcut.py).
"""
import json
import sys
from pathlib import Path
from commun import ANALYSE, draft, est_rush, rush as chemin_rush, video, write_json
from verifie_plan import fin_accroche, plein_ecran

_lum = ANALYSE / "luminance_rushs.json"
LUM = json.loads(_lum.read_text(encoding="utf-8")) if _lum.exists() else {}

SENS = ["droite", "gauche", "haut", "bas"]  # les sauts de scène automatiques tournent sur les quatre sens
DUR = {"obturateur": 0.5, "flash": 0.42, **{f"glisse_{s}": 0.5 for s in SENS}}
CUT_AT = {"obturateur": 0.5, "flash": 1 / 3, **{f"glisse_{s}": 0.5 for s in SENS}}  # position de la coupe


def segments(cfg) -> list:
    """Plans visibles : (début, fin, niveau, fichier, seconde source au début) — piste principale et plans de jeu de plan.json."""
    d = draft(cfg["projet"])
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    segs = []
    for level, t in enumerate(d["tracks"]):
        if t["type"] != "video":
            continue
        for s in t["segments"]:
            path = vids.get(s["material_id"], {}).get("path", "")
            if est_rush(path):  # jamais nos propres rendus (scènes, transitions) si on relance après une pose
                a = s["target_timerange"]["start"] / 1e6
                segs.append((a, a + s["target_timerange"]["duration"] / 1e6, level, path, s["source_timerange"]["start"] / 1e6))
    plan = cfg["dir"] / "plan.json"
    if plan.exists():
        data = json.loads(plan.read_text(encoding="utf-8-sig"))
        for p in data.get("plans", []):  # pas encore posés : au-dessus de la piste principale
            segs.append((p["at"], p["at"] + p["dur"], 100, chemin_rush(p["rush"], data.get("rush_dir")).as_posix(), p["src"]))
    return segs


def visible(segs, t):
    on = [s for s in segs if s[0] <= t < s[1]]
    return max(on, key=lambda s: s[2]) if on else None


def cuts(segs) -> list:
    points = sorted({round(x, 3) for a, b, *_ in segs for x in (a, b)})
    return [p for p in points if visible(segs, p - 0.02) != visible(segs, p + 0.02)]


def sauts(cfg, segs, deja, ecart=8.0, espace=6.0) -> list:
    """Sauts de scène dans le jeu (retours du 2026-10-03 : « inventaire puis combat, pas naturel ») : deux clips
    principaux qui se suivent viennent de moments éloignés (> `ecart` s dans le rush, ou deux rushs), image du jeu
    visible des deux côtés → glissement, en tournant sur les quatre sens, à `espace` s au moins de toute autre transition.
    Jamais dans l'accroche (plans rapides, « À venir » : chaque coupe y saute d'un moment à l'autre, c'est voulu), ni à
    0,5 s d'un plein écran (scène, insert, frise, carte en plein écran), ni dans une fenêtre de déclics (2026-10-08)."""
    d = draft(cfg["projet"])
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    out = []
    plan = cfg["dir"] / "plan.json"
    elements = json.loads(plan.read_text(encoding="utf-8-sig")).get("elements", []) if plan.exists() else []
    scenes = [(a - 0.5, b + 0.5) for a, b, _ in plein_ecran(elements)] + [(a, b) for a, b in cfg.get("declics", [])]
    scenes.append((-1.0, fin_accroche(elements)))
    for s1, s2 in zip(main["segments"], main["segments"][1:]):
        if any(a <= s2["target_timerange"]["start"] / 1e6 <= b for a, b in scenes):
            continue
        cut = s2["target_timerange"]["start"] / 1e6
        p1, p2 = vids[s1["material_id"]]["path"], vids[s2["material_id"]]["path"]
        fin1 = (s1["source_timerange"]["start"] + s1["source_timerange"]["duration"]) / 1e6
        loin = p1 != p2 or abs(s2["source_timerange"]["start"] / 1e6 - fin1) > ecart
        a, b = visible(segs, cut - 0.02), visible(segs, cut + 0.02)
        # image de la piste principale des deux côtés, et pas un rush « voix seule » (écran noir, luminance ≈ 16)
        jeu = a and b and a[2] == 0 and b[2] == 0 and min(LUM.get(p1, 99), LUM.get(p2, 99)) > 25
        if loin and jeu and all(abs(cut - t) >= espace for t in deja + [o[0] for o in out]):
            sens = SENS[:2] if cfg.get("format") == "vertical" else SENS  # Short : haut / bas empilent deux carrés (gojo-ia, 2026-10-13)
            out.append([round(cut, 3), f"glisse_{sens[(len(out) + 1) % len(sens)]}", "saut de scène"])
    return out


def main(vid: str) -> None:
    cfg = video(vid)
    segs = segments(cfg)
    cs = cuts(segs)
    els = []
    liste = list(cfg["transitions"])
    if cfg.get("transitions_sauts", True):
        liste = sorted(liste + sauts(cfg, segs, [t for t, *_ in liste]))
    for n, (t0, kind, why) in enumerate(liste, 1):
        near = min(cs, key=lambda c: abs(c - t0))
        cut = near if abs(near - t0) <= 0.8 else t0
        el = {"id": f"tr{n:02d}-transition", "type": kind, "at": round(cut - DUR[kind] * CUT_AT[kind], 3),
              "dur": DUR[kind], "coupe": round(cut, 3), "note": why}
        if kind.startswith("glisse"):
            a, b = visible(segs, cut - 0.02), visible(segs, cut + 0.02)
            el["vars"] = {"sens": kind.split("_")[1],
                          "A": [a[3], round(a[4] + cut - a[0], 3)], "B": [b[3], round(b[4] + cut - b[0], 3)]}
        els.append(el)
        print(f"{kind:<14} {t0:7.2f} → coupe {cut:7.2f}  {why}")
    write_json(cfg["dir"] / "transitions.json", {"elements": els})


if __name__ == "__main__":
    main(sys.argv[1])
