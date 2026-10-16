"""Cadrage des plans de jeu (zooms) : fonctions pures, communes au rendu direct (rendu.py) et à la pose CapCut (bridge).

Règles (retours du 2026-10-08 sur le test de la direction « duel lisible et nerveux ») :
  - une **séquence** = plans qui se suivent sur la même piste, du même rush, à un moment voisin (moins de 1 s sautée :
    des pauses coupées, la même image) ; l'échelle continue d'une coupe à l'autre, sans revenir à 1 à chaque coupe ;
  - **respiration** sur chaque séquence d'au moins `min_dur` s, mode « pousse » par défaut (retour du 2026-10-08 sur le
    Short site-ennui : « un zoom lent, synchronisé avec la voix, puis l'image revient nettement à son état original, pas de
    dézoom lent ») : 1 → `scale` en une demi-période, linéaire, tenu à `scale`, et **retour net à 1 (en une image) au début
    de chaque phrase** (`remises` : secondes de la timeline, écrites par zooms.py d'après la transcription) ; mode
    « vague » (ancien) : s(t) = 1 + (scale − 1)·(1 − cos 2πt/T)/2, retour très doux ; mode « unique » (retour du
    2026-10-13 sur gojo-ia : « zoom, revient, re-zoom » se voyait trop) : la poussée seule, tenue jusqu'au plan suivant ; dans les deux cas elle repart de 1 à
    un vrai changement de plan, que la coupe cache (une poussée de 1,07 étalée sur 30 s était invisible, image immobile
    83 %) ;
  - un **zoom rapide** multiplie l'échelle en cours (jamais « lent, retour à 1, rapide »), entrée adoucie en 0,2 s
    (zoom léger) à 0,45 s (zoom de lecture de 2× et plus : un saut de 0,1 d'échelle par image se voit),
    tenu jusqu'à la coupe si elle arrive dans les 3 s, sinon retour adouci (0,35 s) ; un zoom à moins de 0,25 s de la
    fin de son plan passe au plan suivant de la séquence, sinon il est écarté.
Unités de position : celles de CapCut (x, y en demi-largeur / demi-hauteur du cadre, y vers le haut) ; un décalage de
(s − 1) montre exactement le bord de l'image agrandie s fois.
"""
from __future__ import annotations

import numpy as np
import math

RAMPE, SORTIE, TENU, BORD = 0.2, 0.35, 3.0, 0.25
PAS = 0.5           # écart des points de la respiration (interpolation linéaire : erreur < 0,0002 d'échelle)
LENT = {"scale": 1.08, "periode": 14.0, "min_dur": 5.0, "mode": "pousse", "remises": []}
ECART_REMISE = 0.6  # deux remises à moins de 0,6 s : la seconde est ignorée (pas de saccade sur des phrases très courtes)


def lisse(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def sequences(segs: list[dict]) -> list[list[dict]]:
    """segs : [{"id", "start", "length", "path", "level", "src"?}] (s) → séquences dans l'ordre (niveau, temps)."""
    out = []
    for s in sorted(segs, key=lambda s: (s["level"], s["start"])):
        last = out[-1][-1] if out else None
        if (last and last["level"] == s["level"] and last["path"] == s["path"]
                and abs(last["start"] + last["length"] - s["start"]) < 0.05
                and abs(s.get("src", 0.0) - (last.get("src", 0.0) + last["length"])) <= 1.0):
            out[-1].append(s)
        else:
            out.append([s])
    return out


def remises_de(slow: dict | None, debut: float, fin: float) -> list[float]:
    """Remises à 1 (débuts de phrase) dans ]debut, fin[, en temps de la timeline, espacées d'au moins ECART_REMISE."""
    out, last = [], debut
    for r in sorted(float(x) for x in (slow or {}).get("remises", [])):
        if debut + ECART_REMISE <= r < fin - 0.05 and r - last >= ECART_REMISE:
            out.append(r)
            last = r
    return out


def respiration(t_rel: float, duree: float, slow: dict | None, debut: float = 0.0) -> float:
    """Échelle de la respiration à t_rel s du début d'une séquence de `duree` s qui commence à `debut` (timeline)."""
    if not slow or duree < float(slow.get("min_dur", LENT["min_dur"])):
        return 1.0
    a = float(slow.get("scale", LENT["scale"])) - 1.0
    T = float(slow.get("periode", LENT["periode"]))
    if slow.get("mode", LENT["mode"]) == "vague":
        return 1.0 + a * (1 - math.cos(2 * math.pi * max(0.0, t_rel) / T)) / 2
    t = debut + max(0.0, t_rel)
    depart = max([debut] + [r for r in remises_de(slow, debut, debut + duree) if r <= t + 1e-9])
    return 1.0 + a * min(1.0, (t - depart) / (T / 2))


def plan_zooms(segs: list[dict], punch: list[dict], slow: dict | None) -> dict:
    """Points de cadrage par plan. punch : [{"at", "dur", "scale", "x"?, "y"?}] (temps de la timeline).
    Rend {id: {"points": [{"t" (s depuis le début du plan), "scale", "x", "y"}], "ease": bool}} ; un plan sans
    mouvement n'y figure pas. Les points sont assez serrés pour une interpolation linéaire (rendu FFmpeg) ; "ease"
    signale un zoom rapide (courbe adoucie dans CapCut)."""
    seqs = sequences(segs)
    seq_of = {s["id"]: (q[0]["start"], q[-1]["start"] + q[-1]["length"]) for q in seqs for s in q}
    suivant = {q[i]["id"]: q[i + 1] for q in seqs for i in range(len(q) - 1)}
    par_plan = {}
    for p in sorted(punch, key=lambda p: p["at"]):
        hit = [s for s in segs if s["start"] <= p["at"] < s["start"] + s["length"]]
        if not hit:
            print(f"  zoom {p['at']:.1f} s : aucun plan de jeu, écarté")
            continue
        s = max(hit, key=lambda h: h["level"])
        if s["start"] + s["length"] - p["at"] < BORD:
            n = suivant.get(s["id"])
            if n is None:
                print(f"  zoom {p['at']:.1f} s : à moins de {BORD} s d'une coupe, écarté")
                continue
            p = {**p, "at": n["start"]}
            s = n
        par_plan.setdefault(s["id"], []).append(p)

    out = {}
    for s in segs:
        sid, st, ln = s["id"], s["start"], s["length"]
        t0, t1 = seq_of[sid]
        end = max(0.0, ln - 0.04)
        zs = par_plan.get(sid, [])
        envs = []                                     # (a, plein, b, fin, échelle, x, y) en temps du plan
        for p in zs:
            a = max(p["at"] - st, 0.0)
            b = min(a + p["dur"], end)
            if b - a < 0.1:
                continue
            ramp = (b - a) if p.get("lent") else float(p["rampe"]) if p.get("rampe") else min(RAMPE + 0.25 * min(1.0, float(p['scale']) - 1.0), (b - a) / 3)
            fin = min(end, b + 1 / 60) if p.get("net") else end if end - b <= TENU else b + SORTIE  # net : retour en une image
            chemin = [(t - st, x, y) for t, x, y in p.get("chemin", [])]   # suivi d'un objet : (temps du plan, x, y)
            envs.append((a, a + ramp, b, fin, float(p["scale"]), float(p.get("x", 0.0)), float(p.get("y", 0.0)), chemin))

        def valeur(t):
            k, x, y = 1.0, 0.0, 0.0
            for a, plein, b, fin, sc, px, py, chemin in envs:
                if t < a or t > fin:
                    continue
                if chemin:                                                 # position interpolée sur la trajectoire
                    ts_ = [c[0] for c in chemin]
                    px, py = float(np.interp(t, ts_, [c[1] for c in chemin])), float(np.interp(t, ts_, [c[2] for c in chemin]))
                w = lisse((t - a) / (plein - a)) if t < plein else 1.0 if t <= b or fin == end else 1 - lisse((t - b) / (fin - b))
                k *= 1 + (sc - 1) * w
                x, y = px * w, py * w
            return respiration(st + t - t0, t1 - t0, slow, t0) * k, x, y

        ts = {0.0, end}
        n = int(end / PAS)
        ts.update(i * PAS for i in range(1, n + 1) if i * PAS < end)
        if t1 - t0 >= float((slow or {}).get("min_dur", LENT["min_dur"])):   # retour net : la valeur d'avant, une image plus tôt
            for r in remises_de(slow, t0, t1):
                if 1 / 60 < r - st < end:
                    ts.update({r - st - 1 / 60, r - st})
        for a, plein, b, fin, sc_, px_, py_, chemin in envs:
            if chemin:                                                     # suivi : 12 points par seconde sur tout le zoom
                n = max(1, round((b - a) * 12))
                ts.update(min(end, a + (b - a) * k / n) for k in range(n + 1))
                ts.update(c[0] for c in chemin if a <= c[0] <= b)
            for x0, x1 in ((a, plein), (b, fin) if fin != end else (b, b)):   # montées et sorties : un point par image
                # au-delà de 0,5 s (avancée lente d'inventaire), 12 points par seconde suffisent : un point par image
                # donnait une expression de plus de 100 Ko et FFmpeg manquait de mémoire (rick-morty-ia, 2026-10-16)
                n = max(1, round((x1 - x0) * (60 if x1 - x0 <= 0.5 else 12)))
                ts.update(min(end, x0 + (x1 - x0) * k / n) for k in range(n + 1))
            ts.add(min(end, b))
        pts = []
        for t in sorted(ts):
            sc, x, y = valeur(t)
            pts.append({"t": round(t, 4), "scale": round(sc, 5), "x": round(x, 4), "y": round(y, 4)})
        if any(abs(p["scale"] - 1) > 1e-6 or p["x"] or p["y"] for p in pts):
            out[sid] = {"points": pts, "ease": bool(envs)}
    return out


def echelle(points: list[dict], t: float) -> tuple[float, float, float]:
    """(échelle, x, y) à t s du début du plan, interpolation linéaire entre les points."""
    if not points:
        return 1.0, 0.0, 0.0
    if t <= points[0]["t"]:
        p = points[0]
        return p["scale"], p.get("x", 0.0), p.get("y", 0.0)
    for a, b in zip(points, points[1:]):
        if t <= b["t"]:
            u = (t - a["t"]) / max(1e-9, b["t"] - a["t"])
            return tuple(a.get(k, 0.0) + (b.get(k, 0.0) - a.get(k, 0.0)) * u for k in ("scale", "x", "y"))
    p = points[-1]
    return p["scale"], p.get("x", 0.0), p.get("y", 0.0)
