"""Vérifie le plan d'une vidéo avant tout rendu.      python scripts/verifie_plan.py <id> [--force]

Lancé aussi en tête d'export_capcut.py (arrêt sur erreur, --force pour passer outre). Rien ne doit arriver à l'écran
par accident (2026-10-08, « je veux pas devoir réitérer ») :
  Erreurs : type inconnu ; variable inconnue (faute de frappe : elle serait ignorée en silence) ; variable obligatoire
  absente (sinon l'élément affiche la valeur d'exemple du kit : les points de pokemon-ia, le logo Claude…) ; image
  introuvable ; deux éléments au même endroit au même moment ; un élément après la fin de la timeline.
  Avertissements : durées hors des règles de la direction, zooms trop proches ou hors des deux familles d'échelle,
  transition manuelle dans l'accroche ou sous un plein écran, mot-clé sur un élément central, repère de test
  (étiquette, carte réduite, minuteur, accéléré) laissé par-dessus une scène plein écran.
Les règles d'écran (pleins écrans, fin de l'accroche, emplacement de chaque type) servent aussi à transitions.py,
zooms.py et revue.py.
"""
from __future__ import annotations

import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_compositions import SPECS  # noqa: E402

HF = Path(__file__).resolve().parent.parent
F = 1 / 60

# types rendus hors du kit (FFmpeg) et leurs variables
HORS_KIT = {"partage": {"A", "B", "nomA", "nomB", "flou", "cxA", "cxB"}, **{f"glisse_{s}": {"sens", "A", "B"} for s in ("gauche", "droite", "haut", "bas")}}
OPAQUES = {k for k, (_, transparent, _) in SPECS.items() if not transparent} | {"partage"}
PERSISTANTS = {"pastille", "carte", "minuteur", "accelere"}       # repères tenus longtemps : au-dessus des autres
FLASHS = {"flash", "obturateur"}
# variables à donner explicitement (sinon : valeur d'exemple du kit à l'écran)
REQUIS = {
    "partage": ["A", "B", "nomA", "nomB"], "carte": ["texte", "plein"], "pastille": ["texte"],
    "progression": ["tests", "actuel", "nomA", "nomB", "logoA", "logoB"], "frise": ["objets", "actuel"], "capture": ["image"], "insert": ["image"],
    "duel": ["nomA", "nomB", "logoA", "logoB"], "minuteur": ["de"], "accelere": ["texte"], "note": ["nom", "logo", "note", "points"],
    "fleche": ["texte", "x", "y"], "mot": ["texte"], "score": ["avantA", "avantB", "point", "nomA", "nomB"], "reaction": ["humeur"],
    "etiquette": ["texte"], "scene_mots": ["items"], "annotation": ["texte"], "point": ["texte"], "scene_fenetre": ["titre", "lignes"],
}
# durées conseillées par la direction (s) : (min, max)
DUREES = {"reaction": (1.5, 2.2), "insert": (0.5, 1.0), "accelere": (1.0, 10.0), "mot": (0.8, 1.5), "a_venir": (2.0, 3.5),
          "titre_jeu": (0.8, 2.0), "duel": (1.5, 3.5)}
CENTRE = {"capture", "duel", "titre_jeu", "note", "scene_vs", "barres", "manche", "abonnement"}


def variables_kit() -> dict:
    """Variables lues par chaque élément du kit (tsar.js) : celles de SPECS plus celles que le kit lit sans les déclarer
    (ex. tsarDe de scene_fenetre)."""
    src = (HF / "kit" / "tsar.js").read_text(encoding="utf-8")
    out = {k: {x["id"] for x in spec[2]} for k, spec in SPECS.items()}
    for m in re.finditer(r"\n  B\.(\w+) = (.*?)(?=\n  B\.\w+ = |\n  // ─|$)", src, re.S):
        corps = m.group(2)
        lus = set(re.findall(r"\bv\.(\w+)", corps)) | set(re.findall(r'\bv\["(\w+)"\]', corps))
        for base in re.findall(r'\bv\["(\w+)" \+ k\]', corps):
            lus |= {base + "A", base + "B"}
        out.setdefault(m.group(1), set()).update(lus)
    return out


def js(v, k, defaut=None):
    x = v.get(k, defaut)
    return json.loads(x) if isinstance(x, str) and x[:1] in "[{" else x


def plein_ecran(elements) -> list:
    """Fenêtres où l'image est entièrement couverte : [(début, fin, id)]. La carte l'est pendant `plein`."""
    out = []
    for e in elements:
        a, d = float(e["at"]), float(e["dur"])
        if e["type"] in OPAQUES or e["type"].startswith("scene_"):
            out.append((a, a + d, e["id"]))
        elif e["type"] == "carte":
            out.append((a, a + min(d, float(e.get("vars", {}).get("plein", 2.5)) + 10 * F), e["id"]))
    return sorted(out)


def fin_accroche(elements, defaut=15.0) -> float:
    """Fin de l'accroche : fin du dernier élément d'accroche (partage, titre, duel, minuteur, À venir) des 20 premières s."""
    fins = [float(e["at"]) + float(e["dur"]) for e in elements
            if e["type"] in ("partage", "titre_jeu", "duel", "minuteur", "a_venir") and float(e["at"]) < 20]
    return max(fins) if fins else defaut


def sous_plein_ecran(t, fenetres, sauf=None) -> str | None:
    for a, b, i in fenetres:
        if i != sauf and a - 1e-6 <= t < b - 1e-6:
            return i
    return None


def zones_verticales(e) -> list:
    """Comme zones(), pour un Short (1080×1920) : mêmes emplacements que le kit (tsar.js, vertical())."""
    v, a, d, t = e.get("vars", {}), float(e["at"]), float(e["dur"]), e["type"]
    if t == "pastille":
        return [(a, a + d, (50, 150, 962, 265), "coin")]
    if t == "carte":
        p = a + min(d, float(v.get("plein", 2.5)) + 30 * F)
        return [(p, a + d, (760, 280, 1030, 440), "coin")] if p < a + d else []
    if t == "minuteur":
        pos, S = v.get("position", "haut-gauche"), float(v.get("taille", 420 if v.get("position") == "centre" else 200))
        r = {"centre": (540 - S / 2, 960 - S / 2, 540 + S / 2, 960 + S / 2), "haut-droite": (1024 - S, 270, 1024, 270 + S)}.get(pos, (50, 270, 50 + S, 270 + S))
        return [(a, a + d, r, "centre" if pos == "centre" else "coin")]
    if t == "accelere":
        return [(a, a + d, (410, 270, 670, 380), "coin")]
    if t == "a_venir":
        return [(a, a + d, (50, 150, 812, 300), "coin")]
    if t == "mot":
        return [(a, a + d, (110, 1200, 970, 1365), "mot")]
    if t == "reaction":
        x = float(v.get("x", 700))
        x = x if 0 < x <= 980 else 700                      # Tsar dans son cadre de 420 px (tsar.js, mascotCadre)
        return [(a, a + d, (x - 214, 1490 - 428, x + 214, 1490), "coin")]
    if t == "fleche":
        X, Y, cote = float(v.get("x", 0.5)) * 1080, float(v.get("y", 0.5)) * 1920, v.get("cote", "gauche")
        off = {"gauche": (-220, -220), "droite": (220, -220), "haut": (0, -280), "bas": (0, 260)}.get(cote, (-220, -220))
        lx, ly = max(320, min(760, X + off[0])), max(200, min(1400, Y + off[1]))
        return [(a, a + d, (min(lx - 300, X), min(ly - 50, Y), max(lx + 300, X), max(ly + 50, Y)), "coin")]
    if t in CENTRE:
        return [(a, a + d, (60, 420, 1020, 1500), "centre")]
    return []


def zones(e, taille=(1920, 1080)) -> list:
    """[(début, fin, (x0, y0, x1, y1), famille)] : où l'élément se voit (pixels 1920×1080). famille : coin | centre."""
    if taille[1] > taille[0]:
        return zones_verticales(e)
    v, a, d, t = e.get("vars", {}), float(e["at"]), float(e["dur"]), e["type"]
    if t == "pastille":
        return [(a, a + d, (40, 900, 1140, 1040), "coin")]
    if t == "carte":
        p = a + min(d, float(v.get("plein", 2.5)) + 30 * F)
        return [(p, a + d, (1380, 30, 1890, 270), "coin")] if p < a + d else []
    if t == "minuteur":
        pos, S = v.get("position", "haut-gauche"), float(v.get("taille", 420 if v.get("position") == "centre" else 220))
        r = {"centre": (960 - S / 2, 540 - S / 2, 960 + S / 2, 540 + S / 2), "haut-droite": (1864 - S, 48, 1864, 48 + S)}.get(pos, (56, 48, 56 + S, 48 + S))
        return [(a, a + d, r, "centre" if pos == "centre" else "coin")]
    if t == "accelere":
        return [(a, a + d, (740, 40, 1180, 150), "coin")]
    if t == "a_venir":
        return [(a, a + d, (40, 40, 900, 200), "coin")]
    if t == "mot":
        return [(a, a + d, (110, 770, 1810, 940), "mot")]
    if t == "reaction":
        x, S = float(v.get("x", 1600)), float(v.get("taille", 500))
        return [(a, a + d, (x - S / 2, 1080 - S, x + S / 2, 1080), "coin")]
    if t == "fleche":
        X, Y, cote = float(v.get("x", 0.5)) * 1920, float(v.get("y", 0.5)) * 1080, v.get("cote", "gauche")
        off = {"gauche": (-360, -150), "droite": (360, -150), "haut": (0, -260), "bas": (0, 230)}.get(cote, (-360, -150))
        lx, ly = max(160, min(1760, X + off[0])), max(90, min(1000, Y + off[1]))
        return [(a, a + d, (min(lx - 330, X), min(ly - 50, Y), max(lx + 330, X), max(ly + 50, Y)), "coin")]
    if t in CENTRE:
        return [(a, a + d, (310, 90, 1610, 990), "centre")]
    return []


def _croise(r1, r2) -> bool:
    return r1[0] < r2[2] and r2[0] < r1[2] and r1[1] < r2[3] and r2[1] < r1[3]


def verifier(elements, cfg=None, fin=None) -> tuple[list, list]:
    """Rend (erreurs, avertissements), chaque point = (seconde, texte)."""
    err, warn = [], []
    full = plein_ecran(elements)
    kit = variables_kit()
    for e in elements:
        t, v, eid, a, d = e["type"], e.get("vars", {}), e["id"], float(e["at"]), float(e["dur"])
        if t not in SPECS and t not in HORS_KIT:
            err.append((a, f"{eid} : type « {t} » inconnu"))
            continue
        connues = HORS_KIT.get(t) or kit.get(t, set())
        for k in v:
            if k not in connues and not k.startswith("_"):
                err.append((a, f"{eid} : variable « {k} » inconnue pour {t} (attendu : {', '.join(sorted(connues))})"))
        seul = t == "duel" and str(v.get("seul", False)).lower() == "true"  # une IA seule (logo sur son mot) : pas de B
        for k in REQUIS.get(t, []):
            if seul and k.endswith("B"):
                continue
            if k not in v or v[k] in ("", None, []):
                err.append((a, f"{eid} : variable « {k} » à donner (sinon {t} affiche sa valeur d'exemple)"))
        if t == "capture" and "zone" not in v and not js(v, "zones"):
            err.append((a, f"{eid} : capture sans « zone » ni « zones » (surlignage d'exemple)"))
        if t == "titre_jeu" and not v.get("image") and not v.get("texte"):
            err.append((a, f"{eid} : titre_jeu sans image ni texte (affiche « MINECRAFT »)"))
        for k in ("image",):
            if v.get(k) and not (HF / v[k]).exists():
                err.append((a, f"{eid} : image introuvable : {v[k]}"))
        for k in ("logo", "logoA", "logoB"):
            if v.get(k) and not (HF / "assets" / "logos" / f"{v[k]}.svg").exists():
                err.append((a, f"{eid} : logo introuvable : assets/logos/{v[k]}.svg"))
        if t in DUREES and not DUREES[t][0] - 1e-6 <= d <= DUREES[t][1] + 1e-6 and not (t == "duel" and str(e["vars"].get("seul", False)).lower() == "true"):
            warn.append((a, f"{eid} : {d:.2f} s (règle : {DUREES[t][0]} à {DUREES[t][1]} s)"))
        if t == "carte" and not 1.0 <= float(v.get("plein", 2.5)) <= 1.5:
            warn.append((a, f"{eid} : plein écran {v.get('plein', 2.5)} s (règle : 1 à 1,5 s)"))
        if t == "pastille":
            for x, _ in js(v, "etat", []):
                if not 0 <= float(x) < d:
                    err.append((a, f"{eid} : état à {x} s hors de l'élément ({d:.2f} s)"))
        if t == "capture":
            for z in js(v, "zones", []):
                if not 0 <= float(z[0]) < d:
                    err.append((a, f"{eid} : zone à {z[0]} s hors de l'élément ({d:.2f} s)"))
        if t == "note" and len(js(v, "points", [])) > 3:
            warn.append((a, f"{eid} : plus de 3 points (illisible)"))
        if t == "progression" and int(v.get("actuel", 0)) >= len(js(v, "tests", [])):
            err.append((a, f"{eid} : « actuel » = {v.get('actuel')} hors de la liste des tests"))
        if fin is not None and a + d > fin + 0.05:
            err.append((a, f"{eid} : finit à {a + d:.2f} s, après la fin de la timeline ({fin:.2f} s)"))
        if t in PERSISTANTS:   # un repère de test (étiquette, carte réduite…) n'a rien à faire sur une scène plein écran
            for fa, fb, fid in full:
                fe = next(x for x in elements if x["id"] == fid)
                if fid != eid and fe["type"] not in ("scene_fond",) and min(a + d, fb) - max(a, fa) > 0.3:
                    warn.append((max(a, fa), f"{eid} reste par-dessus le plein écran {fid} ({max(a, fa):.2f}–{min(a + d, fb):.2f} s)"))
    # deux éléments au même endroit au même moment
    from commun import taille
    zs = [(z, e["id"]) for e in elements for z in zones(e, taille(cfg))]
    for i, ((a1, b1, r1, f1), id1) in enumerate(zs):
        for (a2, b2, r2, f2), id2 in zs[i + 1:]:
            debut, fin_ = max(a1, a2), min(b1, b2)
            if fin_ - debut < 0.1 or id1 == id2 or not _croise(r1, r2):
                continue
            if f1 == f2 and f1 in ("coin", "centre"):
                err.append((debut, f"{id1} et {id2} au même endroit de {debut:.2f} à {fin_:.2f} s"))
            elif "mot" in (f1, f2) and "centre" in (f1, f2):
                warn.append((debut, f"{id1} et {id2} se recouvrent de {debut:.2f} à {fin_:.2f} s (mot-clé sur un élément central)"))
    if cfg:
        acc = fin_accroche(elements)
        pz = sorted(cfg.get("zooms", {}).get("punch", []), key=lambda z: z[0])
        for z, z2 in zip(pz, pz[1:]):
            if z2[0] - z[0] < 2.0:
                warn.append((z2[0], f"zoom à {z2[0]} s : {z2[0] - z[0]:.1f} s après le précédent (jamais deux de suite : écarté)"))
        for z in pz:
            s = float(z[2])
            if not (1.08 - 1e-6 <= s <= 1.15 + 1e-6 or 1.5 - 1e-6 <= s <= 3.0 + 1e-6):
                warn.append((z[0], f"zoom à {z[0]} s : échelle {s} hors des familles 1,08–1,15 (léger) et 1,5–3 (lecture)"))
            cache = sous_plein_ecran(float(z[0]), full)
            if cache:
                warn.append((z[0], f"zoom à {z[0]} s sous le plein écran {cache} : invisible, écarté"))
        for tr in cfg.get("transitions", []):  # une transition à l'entrée ou à la sortie d'une scène est voulue
            cache = next((i for a, b, i in full if a + 0.3 < float(tr[0]) < b - 0.3), None)
            if cache:
                warn.append((tr[0], f"transition {tr[1]} à {tr[0]} s sous le plein écran {cache}"))
            elif float(tr[0]) < acc:
                warn.append((tr[0], f"transition {tr[1]} à {tr[0]} s dans l'accroche (fin à {acc:.1f} s : plans rapides, pas de transition)"))
    return sorted(err), sorted(warn)


def lire_elements(plan_files) -> list:
    els = []
    for pf in plan_files:
        p = Path(pf)
        if p.exists():
            els += json.loads(p.read_text(encoding="utf-8-sig")).get("elements", [])
    return els


def fin_timeline(cfg) -> float | None:
    try:
        from commun import draft
        d = draft(cfg["projet"])
        return max(s["target_timerange"]["start"] + s["target_timerange"]["duration"]
                   for t in d["tracks"] if t["type"] == "video" for s in t["segments"]) / 1e6
    except Exception:  # projet absent (vidéo d'exemple, autre PC) : pas de contrôle de fin
        return None


def rapport(err, warn) -> str:
    mm = lambda s: f"{int(float(s) // 60)}:{float(s) % 60:05.2f}"  # noqa: E731
    out = [f"ERREUR  {mm(t)}  {x}" for t, x in err] + [f"attention {mm(t)}  {x}" for t, x in warn]
    out.append(f"{len(err)} erreur(s), {len(warn)} avertissement(s)")
    return "\n".join(out)


def main(vid: str) -> int:
    from commun import video
    cfg = video(vid)
    els = lire_elements([cfg["dir"] / "plan.json", cfg["dir"] / "transitions.json"])
    err, warn = verifier(els, cfg, fin_timeline(cfg))
    print(rapport(err, warn))
    return 1 if err and "--force" not in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
