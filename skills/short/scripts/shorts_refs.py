#!/usr/bin/env python3
"""shorts_refs.py - les Shorts des chaînes suivies, classés par multiple de la médiane de leurs propres Shorts.

    python shorts_refs.py                      # chaînes de référence + LAirHisson, 30 Shorts chacune
    python shorts_refs.py --toutes             # les 80 chaînes de config/youtube/chaines.json
    python shorts_refs.py --ajoute @handle     # une chaîne de plus (répétable)
    python shorts_refs.py --frais              # ignore le résumé de moins de 14 jours

Même idée que swipe.py (le multiple de la médiane de la chaîne, pas les vues brutes), mais pour l'onglet
Shorts : yt-dlp ne donne pas de date sur cet onglet, donc pas de filtre d'âge ni de vues par jour ; un
Short récent a moins de vues qu'un ancien, le multiple est un indice, pas une preuve. Moins de 8 Shorts
avec des vues : « fragile », moins de 4 : la chaîne est écartée.

Écrit config/youtube/references/<AAAA-MM-JJ>-shorts.json (résumé court : médiane et meilleurs Shorts de
chaque chaîne) et l'imprime. Réutilise un résumé de moins de 14 jours.
"""
import json, os, re, shutil, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHAINES = ROOT / "config" / "youtube" / "chaines.json"
REFS = ROOT / "config" / "youtube" / "references"
STYLE = {"@LAirHisson"}          # référence de style des Shorts (montage-capcut, préférences)
N = 30


def ytdlp():
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def fetch(c):
    url = c["url"].rstrip("/") + "/shorts"
    try:
        p = subprocess.run(ytdlp() + ["--flat-playlist", "-J", "--no-warnings", "--ignore-errors",
                                      "--playlist-end", str(N), url],
                           capture_output=True, text=True, encoding="utf-8", timeout=180)
        d = json.loads(p.stdout) if p.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return c, []
    entries = [e for e in ((d or {}).get("entries") or []) if e]
    if entries and entries[0].get("entries"):          # onglets imbriqués
        entries = [x for t in entries for x in t["entries"] if x]
    return c, entries


def summarise(c, entries):
    vues = [e["view_count"] for e in entries if e.get("view_count") is not None]
    if len(vues) < 4:
        return None
    med = statistics.median(vues)
    top = sorted((e for e in entries if e.get("view_count")), key=lambda e: -e["view_count"])[:5]
    return {"nom": c["nom"], "handle": c.get("handle"), "n": len(vues), "fragile": len(vues) < 8,
            "mediane": med,
            "meilleurs": [{"titre": e.get("title"), "vues": e["view_count"],
                           "multiple": round(e["view_count"] / med, 1) if med else None,
                           "url": e.get("url") or f"https://www.youtube.com/shorts/{e.get('id')}"} for e in top]}


def recent():
    for f in sorted(REFS.glob("*-shorts.json"), reverse=True):
        try:
            d = datetime.strptime(f.name[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if (date.today() - d).days < 14:
            return f
    return None


def main(a):
    if not ("--frais" in a or "--toutes" in a or "--ajoute" in a) and recent():
        out = json.loads(recent().read_text(encoding="utf-8"))
        print(f"résumé de {recent().name} (moins de 14 jours, --frais pour refaire)")
    else:
        chaines = json.loads(CHAINES.read_text(encoding="utf-8"))["chaines"]
        ajoutes = {a[i + 1].lower() for i, x in enumerate(a) if x == "--ajoute" and i + 1 < len(a)}
        choix = [c for c in chaines if "--toutes" in a or c.get("source") == "référence"
                 or c.get("handle") in STYLE or (c.get("handle") or "").lower() in ajoutes]
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = list(ex.map(fetch, choix))
        ok = [s for s in (summarise(c, e) for c, e in res) if s]
        sans = [c["nom"] for (c, e), s in zip(res, [summarise(c, e) for c, e in res]) if not s]
        out = {"date": str(date.today()), "chaines": ok, "sans_shorts_exploitables": sans,
               "limite": "pas de date sur l'onglet Shorts : multiple de la médiane des 30 derniers Shorts, indice seulement"}
        REFS.mkdir(parents=True, exist_ok=True)
        (REFS / f"{date.today()}-shorts.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                                                          encoding="utf-8")
    for s in sorted(out["chaines"], key=lambda s: -(s["meilleurs"][0]["multiple"] or 0)):
        print(f"\n{s['nom']} : médiane {int(s['mediane']):,} vues sur {s['n']} Shorts".replace(",", " ")
              + (" (fragile)" if s["fragile"] else ""))
        for m in s["meilleurs"][:3]:
            print(f"  {m['multiple']}x  {m['vues']:>9,}  {m['titre']}".replace(",", " "))
    if out.get("sans_shorts_exploitables"):
        print("\nSans Shorts exploitables :", ", ".join(out["sans_shorts_exploitables"]))
    print("\nLimite :", out["limite"])


if __name__ == "__main__":
    main(sys.argv[1:])
