"""Zooms des plans de jeu.                                            python scripts/zooms.py <id>

Direction « duel lisible et nerveux » (2026-10-07, mesures des chaînes qui performent : analyse-2026-10-07.md) :
  - zooms rapides légers (1,08 à 1,15), 3 à 5 par minute, calés sur un mot ou un événement, jamais deux de suite ;
  - un zoom de lecture fort (1,5 à 3) environ une fois par minute sur un texte, un bouton, un chiffre du jeu, tenu
    pendant la phrase (on en sort par une coupe) ;
  - cadrés sur la chose (fx, fy = position dans l'image, 0..1 depuis le haut gauche, relevée sur une planche
    timeline_frames.py) ;
  - respiration (2026-10-08) sur chaque séquence de jeu de 5 s ou plus : 1 → 1,08 en 7 s puis retour très doux ; un zoom
    rapide part de l'échelle en cours. Règles appliquées par cadrage.plan_zooms (rendu.py et bridge), testées dans
    tests/test_montage_regles.py.
Écartés ici, avec une ligne d'explication : un zoom sous un plein écran (invisible, son tick sonnerait dans le vide), un
zoom à moins de 2 s du précédent (jamais deux de suite). Avertissement si l'échelle sort des deux familles.
video.json → "zooms": {"punch": [[seconde, durée, échelle, fx, fy, "pourquoi"]], "slow": {scale, periode, min_dur}}
Sortie : 06_CAPCUT/<id>/zooms.json (rendu.py ; option CapCut : capcut_bridge.py zooms "<projet>" zooms.json)
"""
import json, sys
from cadrage import LENT
from commun import draft, video, write_json
from verifie_plan import plein_ecran, sous_plein_ecran

ECART = 2.0


def coupes_image(cfg) -> list:
    """Débuts des plans de la piste principale (secondes de la timeline)."""
    d = draft(cfg["projet"])
    main = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    return [s["target_timerange"]["start"] / 1e6 for s in main["segments"]]


def choisir(punch, elements) -> list:
    """Zooms gardés, dans l'ordre ; affiche ceux qui sont écartés et pourquoi."""
    full, out = plein_ecran(elements), []
    for z in sorted(punch, key=lambda z: z[0]):
        at, s = float(z[0]), float(z[2])
        cache = sous_plein_ecran(at, full)
        if cache:
            print(f"  zoom {at:.2f} s écarté : sous le plein écran {cache}")
            continue
        if out and at - out[-1][0] < ECART:
            print(f"  zoom {at:.2f} s écarté : {at - out[-1][0]:.1f} s après le précédent (jamais deux de suite)")
            continue
        if not (1.08 - 1e-6 <= s <= 1.15 + 1e-6 or 1.5 - 1e-6 <= s <= 3.0 + 1e-6):
            print(f"  zoom {at:.2f} s : échelle {s} hors des familles 1,08–1,15 (léger) et 1,5–3 (lecture)")
        out.append(z)
    return out


def debuts_de_phrase(cfg) -> list[float]:
    """Début de chaque phrase (mot qui suit un . ? ! ou une pause de 0,8 s : les petites pauses de Whisper ne comptent pas,
    elles feraient sauter l'image au milieu d'une phrase), en temps de la timeline : la respiration
    y revient nettement à 1 (retour du 2026-10-08)."""
    from commun import ANALYSE, read_json, remap
    mots = read_json(ANALYSE / "transcriptions" / cfg.get("transcription", ""), []) if cfg.get("transcription") else []
    out, prev = [], None
    for w in mots:
        t = remap(w["startMs"] / 1000 - 0.12, cfg.get("coupes", []))
        if prev is not None and (prev["text"].strip()[-1:] in ".?!" or w["startMs"] - prev["endMs"] >= 800):
            out.append(round(t, 3))
        prev = w
    return out


def main(vid: str) -> None:
    cfg = video(vid)
    z = cfg.get("zooms", {})
    plan = cfg["dir"] / "plan.json"
    elements = json.loads(plan.read_text(encoding="utf-8-sig")).get("elements", []) if plan.exists() else []
    punch = []
    for at, dur, s, fx, fy, why in choisir(z.get("punch", []), elements):
        dx, dy = 2 * fx - 1, 1 - 2 * fy  # recentre la chose sans montrer les bords (décalage max = s - 1)
        punch.append({"at": at, "dur": dur, "scale": s, "x": round(max(-(s - 1), min(s - 1, -dx * s)), 3),
                      "y": round(max(-(s - 1), min(s - 1, -dy * s)), 3), "note": why,
                      "net": z.get("retour") == "net", **({"rampe": z["rampe"]} if "rampe" in z else {})})  # rampe : montée calée sur le son ; « retour net » (2026-10-16)
    # « suivis » [[seconde, durée, échelle, [[t, fx, fy], …], pourquoi]] : zoom qui suit un objet qui bouge (le beurre
    # déplacé dans l'inventaire, rick-morty-ia 2026-10-16) ; t en secondes de la timeline, cadrage interpolé entre les points
    for at, dur, s, pts, why in z.get("suivis", []):
        cl = lambda fx, fy: (round(max(-(s - 1), min(s - 1, -(2 * fx - 1) * s)), 3), round(max(-(s - 1), min(s - 1, -(1 - 2 * fy) * s)), 3))
        chemin = [[t, *cl(fx, fy)] for t, fx, fy in pts]
        # un zoom de cadrage vit dans un seul plan : le suivi est découpé aux coupes d'image qu'il traverse, la montée
        # seulement au premier morceau, les suivants déjà pleins (la coupe cache le raccord)
        bornes = [at] + [c for c in coupes_image(cfg) if at < c < at + dur] + [at + dur]
        for k, (a_, b_) in enumerate(zip(bornes, bornes[1:])):
            x0, y0 = cl(*[float(__import__("numpy").interp(a_, [p[0] for p in pts], [p[i] for p in pts])) for i in (1, 2)])
            punch.append({"at": round(a_, 3), "dur": round(b_ - a_, 3), "scale": s, "x": x0, "y": y0, "note": why, "net": True,
                          "rampe": (z.get("rampe", 0.17) if k == 0 else 1 / 60), "chemin": chemin})
    # « avancees » [[seconde, durée, échelle, fx, fy, pourquoi]] : avancée lente vers un objet d'inventaire et son infobulle,
    # sur toute la durée, puis sortie nette (référence LAirHisson, rick-morty-ia 2026-10-16)
    for at, dur, s, fx, fy, why in z.get("avancees", []):
        dx, dy = 2 * fx - 1, 1 - 2 * fy
        punch.append({"at": at, "dur": dur, "scale": s, "x": round(max(-(s - 1), min(s - 1, -dx * s)), 3),
                      "y": round(max(-(s - 1), min(s - 1, -dy * s)), 3), "note": why, "net": True, "lent": True})
    slow = {k: v for k, v in {**LENT, **z.get("slow", {})}.items() if k in LENT}
    if slow.get("mode") not in ("vague", "unique"):  # « unique » : une poussée par plan, sans retour à chaque phrase
        slow["remises"] = debuts_de_phrase(cfg)
    write_json(cfg["out"] / "zooms.json", {"reset": True, "punch": punch, "slow": slow})
    print(f"{len(punch)} zooms rapides -> {cfg['out'] / 'zooms.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
