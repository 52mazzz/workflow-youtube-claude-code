#!/usr/bin/env python3
"""audit.py - the channel's monthly check-up: rhythm, theme drift, format mix, thumbnail grid.

    python audit.py                         # fetches the channel with yt-dlp (public data)
    python audit.py --chaine ma-chaine.json # or reads a listing already collected (veille.py writes one)
    python audit.py ... --json

Measured from the public listing of @letsar555 (titles, dates, durations, thumbnails):
  - rhythm: long videos per week over the last 8 weeks, median and spread of the days between two
    uploads, days since the last one, against the goal of preferences.md (1 per week);
  - format mix: long videos and Shorts;
  - themes: the game or subject of each title (Minecraft, Pokémon, horror...), the share of the
    main one (concentration) and whether the last 5 videos follow the same theme as the earlier
    ones (drift); the common thread "IA + création" (titles naming an AI or "IA");
  - the thumbnail grid of the last 12 long videos (grille_chaine.png, OpenCV) to look at with Read:
    does the channel look like one channel?
Writes config/youtube/audits/<date>.md (in the repo: the history of the channel) and prints its path.
Topical authority and session chains come from youtube-seo-skills (deeployCO, MIT), adapted.
"""
import json, os, re, shlex, shutil, statistics, subprocess, sys, unicodedata, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CHAINE = "https://www.youtube.com/@letsar555/videos"
THEMES = [("Minecraft", r"minecraft|shader|mod\b"), ("Pokémon", r"pok[eé]mon"), ("Roblox", r"roblox"),
          ("Mario", r"mario"), ("Zelda", r"zelda"), ("GTA", r"\bgta\b"), ("Fortnite", r"fortnite"),
          ("Horreur", r"horreur|horror|halloween|fnaf|backrooms"), ("Subway Surfers", r"subway"),
          ("Jeu créé par l'IA", r"\bjeu\b|game")]
AI = re.compile(r"\b(ia|ai|claude|chatgpt|gpt|gemini|grok|fable|opus|astra)\b", re.I)


def config_dir():
    return Path(os.environ.get("YT_CONFIG_DIR") or Path.home() / ".claude" / "youtube")


def today():
    fixed = os.environ.get("SWIPE_NOW")
    return datetime.strptime(fixed, "%Y-%m-%d").date() if fixed else date.today()


def ytdlp():
    if os.environ.get("YTDLP"):
        return shlex.split(os.environ["YTDLP"])
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def load_listing(path):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    p = subprocess.run(ytdlp() + ["--flat-playlist", "-J", "--playlist-end", "60", "--extractor-args",
                                  "youtubetab:approximate_date", CHAINE], capture_output=True, text=True, encoding="utf-8", timeout=180)
    if p.returncode != 0 or not p.stdout.strip():
        sys.exit("chaîne non récupérée (yt-dlp bloqué ?) : passe --chaine ma-chaine.json ; rien n'est inventé")
    return json.loads(p.stdout)


def videos(listing):
    out = []
    def walk(n):
        if isinstance(n, list):
            for x in n: walk(x)
        elif isinstance(n, dict):
            if n.get("entries") is not None:
                walk(n["entries"]); return
            if n.get("title"):
                ts = n.get("timestamp")
                d = datetime.fromtimestamp(ts, timezone.utc).date() if isinstance(ts, (int, float)) else (
                    datetime.strptime(n["upload_date"], "%Y%m%d").date() if re.fullmatch(r"\d{8}", str(n.get("upload_date") or "")) else None)
                dur = n.get("duration")
                short = "/shorts/" in (n.get("url") or "") or (isinstance(dur, (int, float)) and 0 < dur < 60)
                thumbs = n.get("thumbnails") or []
                th = sorted(thumbs, key=lambda t: t.get("width") or 0)[-1]["url"] if thumbs else (
                    f"https://i.ytimg.com/vi/{n['id']}/hqdefault.jpg" if n.get("id") else "")
                out.append({"titre": n["title"], "date": d, "duree": dur, "short": short, "vues": n.get("view_count"),
                            "miniature": th})
    walk(listing)
    return out


def theme(title):
    t = unicodedata.normalize("NFC", title.lower())
    return next((name for name, rx in THEMES if re.search(rx, t)), "Autre")


def audit(vids, goal_per_week=1.0):
    t = today()
    long = sorted([v for v in vids if not v["short"]], key=lambda v: v["date"] or date.min, reverse=True)
    shorts = [v for v in vids if v["short"]]
    dated = [v["date"] for v in long if v["date"]]
    gaps = [(a - b).days for a, b in zip(dated, dated[1:])]
    last8 = sum(1 for d in dated if (t - d).days <= 56)
    themes = [theme(v["titre"]) for v in long]
    counts = {}
    for th in themes: counts[th] = counts.get(th, 0) + 1
    main = max(counts, key=counts.get) if counts else None
    recent, older = themes[:5], themes[5:]
    rmain = max(set(recent), key=recent.count) if recent else None
    r = {"date": t.isoformat(), "longues": len(long), "shorts": len(shorts),
         "par_semaine_8s": round(last8 / 8, 2), "objectif_par_semaine": goal_per_week,
         "ecart_median_j": statistics.median(gaps) if gaps else None,
         "ecart_dispersion_j": round(statistics.pstdev(gaps), 1) if len(gaps) >= 2 else None,
         "depuis_derniere_j": (t - dated[0]).days if dated else None,
         "themes": dict(sorted(counts.items(), key=lambda x: -x[1])), "theme_principal": main,
         "concentration": round(counts[main] / len(themes), 2) if main else None,
         "derive": bool(older) and rmain is not None and rmain != max(set(older), key=older.count),
         "fil_ia": round(sum(1 for v in long if AI.search(v["titre"])) / len(long), 2) if long else None,
         "miniatures": [v["miniature"] for v in long[:12] if v["miniature"]]}
    points = []
    if r["par_semaine_8s"] < goal_per_week:
        points.append(f"rythme : {r['par_semaine_8s']} vidéo longue par semaine sur 8 semaines, objectif {goal_per_week:g}")
    if r["depuis_derniere_j"] is not None and r["depuis_derniere_j"] > 10:
        points.append(f"dernière vidéo longue il y a {r['depuis_derniere_j']} jours")
    if r["ecart_dispersion_j"] and r["ecart_dispersion_j"] > 4:
        points.append(f"rythme irrégulier (écart-type de {r['ecart_dispersion_j']} j entre deux vidéos) : un jour fixe aide le fil d'accueil")
    if r["derive"]:
        points.append(f"dérive de thème : les 5 dernières vidéos tournent autour de « {rmain} », les précédentes autour d'autre chose ; "
                      "relier les deux par une playlist et le fil conducteur (IA + création)")
    if r["fil_ia"] is not None and r["fil_ia"] < 0.8:
        points.append(f"fil conducteur : seulement {int(r['fil_ia'] * 100)} % des titres nomment une IA")
    if not shorts:
        points.append("aucun Short : la chaîne ne profite pas du fil Shorts (étape 10)")
    r["points"] = points
    return r


def grid(urls, out):
    try:
        import cv2, numpy as np
    except ImportError:
        return None
    tiles = []
    for u in urls[:12]:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=20).read() if not os.path.exists(u) else Path(u).read_bytes()
            im = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if im is not None: tiles.append(cv2.resize(im, (320, 180), interpolation=cv2.INTER_AREA))
        except Exception:
            continue
    if not tiles:
        return None
    cols, W, H, G = 4, 320, 180, 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * (H + G) + G, cols * (W + G) + G, 3), 15, np.uint8)
    for k, t in enumerate(tiles):
        y, x = G + (k // cols) * (H + G), G + (k % cols) * (W + G)
        sheet[y:y + H, x:x + W] = t
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    return str(out)


def report_md(r, grid_path):
    L = [f"# Audit de la chaîne du {r['date']}", "",
         f"- Vidéos longues : {r['longues']} ; Shorts : {r['shorts']}",
         f"- Rythme : {r['par_semaine_8s']} vidéo longue par semaine sur les 8 dernières semaines (objectif {r['objectif_par_semaine']:g}) ; "
         f"écart médian entre deux vidéos {r['ecart_median_j']} j (dispersion {r['ecart_dispersion_j']} j) ; dernière il y a {r['depuis_derniere_j']} j",
         f"- Thèmes : " + ", ".join(f"{k} {v}" for k, v in r["themes"].items())
         + (f" ; thème principal « {r['theme_principal']} » ({int(r['concentration'] * 100)} %)" if r["theme_principal"] else ""),
         f"- Fil conducteur IA : {int((r['fil_ia'] or 0) * 100)} % des titres nomment une IA",
         f"- Grille des miniatures : {grid_path or 'non générée (OpenCV absent ou miniatures non téléchargées)'}", "",
         "## Points à traiter", ""]
    L += [f"- {p}" for p in r["points"]] or ["- rien à signaler sur les chiffres publics"]
    L += ["", "## À vérifier à la main (Studio, page de la chaîne)", "",
          "- Playlists : celles de `chaine.md` existent, dans l'ordre d'enchaînement, et chaque nouvelle vidéo y est",
          "- Écran de fin de chaque vidéo : la vidéo suivante de la chaîne prévue dans `chaine.md`",
          "- Page « À propos », bande-annonce, vidéo à la une, sections : conformes à `chaine.md`",
          "- Sondage Communauté du mois : posté, résultat noté dans `chaine.md`"]
    return "\n".join(L) + "\n"


def main():
    a = sys.argv[1:]
    val = lambda n: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else None
    r = audit(videos(load_listing(val("--chaine"))))
    out_dir = config_dir() / "audits"
    g = grid(r["miniatures"], out_dir / f"{r['date']}-miniatures.png") if "--sans-grille" not in a else None
    if "--json" in a:
        print(json.dumps(dict(r, grille=g), indent=1, ensure_ascii=False, default=str)); return
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{r['date']}.md"
    path.write_text(report_md(r, g), encoding="utf-8")
    print(path.read_text(encoding="utf-8"))
    print(path)


if __name__ == "__main__":
    main()
