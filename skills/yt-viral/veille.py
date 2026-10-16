#!/usr/bin/env python3
"""veille.py - the whole weekly watch in one command: collect, rank, second pass, compare, summarise.

    python veille.py collecte --mode legere --requete "claude fable 5.1 jeu" --requete "ia mod minecraft" ...
    python veille.py collecte --mode complete [--requete "..."]
    python veille.py creneau "jeu d'horreur fait par une ia" "ia pokemon"     # is the idea free in French?
    python veille.py grille idees.json [--md]                                 # score the ideas
    python veille.py tendance "mod dragon minecraft" "pokemon ia"           # Google Trends (YouTube search), 5 years
    python veille.py chaines                                                  # the channels followed

`collecte` writes into --dossier (default ./veille, kept out of git) and prints the path of
veille-resume.md, the only file to read afterwards (a few dozen lines instead of thousands):

  1. the user's own channel (ma-chaine.json, next to the folder), to avoid repeating a subject;
  2. the followed channels of chaines.json: all of them in a full watch, in a light one only those
     that hold a recent top outlier or were discovered in the last 4 weeks; a channel collected in
     the last 6 days is not collected again (cache);
  3. the searches: every base query of veille-requetes.json plus --requete in a full watch, only the
     --requete in a light one (at least 4, fresh: new models, new games, trends);
  4. ranking with swipe.py (multiple of each channel's own median, --min-views floor, Shorts apart);
  5. SECOND PASS: channels found by the searches with too few videos for a median, but with a
     strong video (>= --min-views), get their /videos tab collected and everything is ranked again.
     This is where the unknown channels come from;
  6. chaines.json is updated: medians and dates, and every new channel with an outlier >= 3x is
     added as "découverte";
  7. DYNAMICS: videos already seen in an earlier collection (config/youtube/references/) are
     compared: views per day since then against their lifetime average -> monte / ralentit / plafonne;
  8. the collection is archived (refs_history.py, slug veille or veille-complete).

All yt-dlp calls run 4 at a time. Public data only, never a logged-in account. Nothing is invented:
a channel or a search that fails is listed as failed in the summary.

`creneau` searches each concept on YouTube (French phrasing) and counts the French videos already
made (title language guessed from French words): "libre" when none has 10,000 views or more,
"partiel" when one to two do, "pris" beyond. A guess on titles, to confirm by eye. "libre" only means
"no strong French reference found in these 20 results": it is printed that way, never as "free".

`tendance` asks Google Trends (YouTube search, France, 5 years, weekly) and classifies each term:
saisonnier (same month peaks every year: the next peak date is given), tendance (rising, little
history), en déclin, permanent. Google Trends often refuses automated calls (429): the command
says so and nothing is guessed.

`grille` reads a JSON list of ideas, fills the demand (YouTube autocomplete, suggest.py), the
French gap (creneau) and the season (tendance) when they are missing, and prints the ideas ranked
by a transparent score out of 13 (see GRILLE below). Fields written by Claude: titre, type,
intention (divertissement, comparatif, tutoriel, actualité: shown, not scored), multiple, vues
(best proof) or, for a crossed idea, morceaux [{role, source, multiple, vues}] (proof = weakest piece), faisabilite 1-3, urgence 0-2, apprentissages -1..1, and optionally creneau,
creneau_concept, demande_seeds, pic (AAAA-MM-JJ or MM-JJ, a known date: Halloween, a game release)
or tendance_mot, sondage (true: the option that won the channel's Community poll: demand 2). A peak within 60 days adds 1 to urgence (max 2). Season and intention from
youtube-seo-skills (deeployCO, MIT).

Files: chaines.json and veille-requetes.json in ~/.claude/youtube/ (config/youtube/ of the repo,
or $YT_CONFIG_DIR); history in ~/.claude/youtube/references/ (or $YT_REFS_DIR); yt-dlp from $YTDLP,
else yt-dlp on the PATH, else `python -m yt_dlp`.
"""
import json, math, os, re, shlex, shutil, subprocess, sys, tempfile, threading, unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SWIPE = HERE / "swipe.py"
OWN = ("letsar555", "tsar rouge555")
OWN_URL = "https://www.youtube.com/@letsar555/videos"
GRILLE = """preuve 0-3 (log2 du multiple / 2, divisé par 2 sous 10 000 vues ; idée croisée : son morceau le plus faible) + faisabilité 1-3 + créneau FR
(libre 2, partiel 1, pris 0) + urgence 0-2 (+1 si un pic saisonnier tombe dans les 60 jours) + demande 0-2
(autocomplétion YouTube) + apprentissages -1..1 = /13. Une donnée non mesurée (créneau, demande) vaut 0 : elle
ne peut pas faire monter une idée ; le maximum possible et la confiance (élevée, moyenne, faible) s'affichent"""
CRENEAU_TXT = {"libre": "aucune référence FR forte trouvée", "partiel": "1-2 références FR fortes", "pris": "déjà fait en FR"}


# ---------------------------------------------------------------- places and tools

def config_dir():
    return Path(os.environ.get("YT_CONFIG_DIR") or Path.home() / ".claude" / "youtube")


def refs_dir():
    return Path(os.environ.get("YT_REFS_DIR") or config_dir() / "references")


def today():
    fixed = os.environ.get("SWIPE_NOW")
    return datetime.strptime(fixed, "%Y-%m-%d").date() if fixed else date.today()


def ytdlp():
    if os.environ.get("YTDLP"):
        return shlex.split(os.environ["YTDLP"])
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def slugify(s, n=40):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:n] or "x"


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(p, data):
    Path(p).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def opt(a, name, default=None, many=False):
    vals = [a[i + 1] for i, x in enumerate(a) if x == name and i + 1 < len(a)]
    return vals if many else (vals[-1] if vals else default)


# ---------------------------------------------------------------- collection

def fetch(job):
    """job = (kind, target, path, n). Runs yt-dlp, writes the JSON; returns (job, error or None)."""
    kind, target, path, n = job
    if Path(path).exists() and Path(path).stat().st_size > 50:
        return job, None  # already collected today (resumed run)
    args = ["--flat-playlist", "-J", "--no-warnings", "--ignore-errors"]
    if kind == "search":
        url = f"ytsearch{n}:{target}"
    else:
        url = target.rstrip("/")
        if not re.search(r"/(videos|streams|shorts)$", url):
            url += "/videos"
        args += ["--playlist-end", str(n), "--extractor-args", "youtubetab:approximate_date"]
    try:
        p = subprocess.run(ytdlp() + args + [url], capture_output=True, text=True, encoding="utf-8", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        return job, e.__class__.__name__
    out = p.stdout.strip()
    try:
        data = json.loads(out) if out else None
    except ValueError:
        data = None
    if not data or not data.get("entries"):
        err = (p.stderr.strip().splitlines() or ["réponse vide"])[-1][:160]
        return job, err
    Path(path).write_text(out, encoding="utf-8")
    return job, None


def run_jobs(jobs):
    with ThreadPoolExecutor(max_workers=4) as ex:
        return [r for r in ex.map(fetch, jobs)]


def swipe(files, min_views, extra=()):
    cmd = [sys.executable, str(SWIPE), *map(str, files), "--min", "1.5", "--no-shorts", "--max-age", "365",
           "--min-age", "5", "--min-views", str(min_views), "--json", *extra]
    for o in OWN:
        cmd += ["--exclude", o]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf8"))
    if p.returncode != 0:
        sys.exit(f"swipe.py a échoué : {p.stderr.strip() or p.stdout.strip()[:300]}")
    return json.loads(p.stdout)


def channel_url(c):
    if c.get("url"):
        return c["url"]
    if c.get("channel_id"):
        return f"https://www.youtube.com/channel/{c['channel_id']}"
    h = c.get("handle") or ""
    return f"https://www.youtube.com/{h if h.startswith('@') else '@' + h}" if h else ""


def channel_key(c):
    return c.get("channel_id") or (c.get("channel") or c.get("nom") or "").lower()


def recent_history(weeks=6, before=None):
    """[(date, slug, data)] of the archived collections of the last weeks, oldest first."""
    since = today() - timedelta(weeks=weeks)
    out = []
    for f in sorted(refs_dir().glob("*.json")) if refs_dir().exists() else []:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.json$", f.name)
        if not m:
            continue
        d = date.fromisoformat(m.group(1))
        if d < since or (before and d >= before):
            continue
        data = load_json(f, None)
        if isinstance(data, dict):
            out.append((d, m.group(2), data))
    return out


def dynamics(now_outliers, history):
    """Videos seen before: views per day since then vs their lifetime average then."""
    seen = {}
    for d, _, data in history:
        for o in data.get("outliers", []):
            if o.get("id") and o.get("views") and o.get("age_days"):
                seen[o["id"]] = (d, o)  # latest earlier sighting wins
    rows = []
    for o in now_outliers:
        if o.get("id") not in seen:
            continue
        d, old = seen[o["id"]]
        days = (today() - d).days
        if days < 3:
            continue
        recent = max(0, o["views"] - old["views"]) / days
        avg = old["views"] / max(1, old["age_days"])
        ratio = recent / avg if avg else 0
        state = "monte" if ratio >= 0.6 else "ralentit" if ratio >= 0.2 else "plafonne"
        rows.append({"id": o["id"], "title": o["title"], "channel": o["channel"], "since": d.isoformat(),
                     "views_then": old["views"], "views_now": o["views"], "recent_per_day": int(recent),
                     "avg_per_day_then": int(avg), "state": state})
    order = {"monte": 0, "ralentit": 1, "plafonne": 2}
    return sorted(rows, key=lambda r: (order[r["state"]], -r["recent_per_day"]))


def collecte(a):
    mode = opt(a, "--mode", "legere")
    if mode not in ("legere", "complete"):
        sys.exit("--mode legere ou --mode complete")
    folder = Path(opt(a, "--dossier", "veille"))
    folder.mkdir(parents=True, exist_ok=True)
    min_views = int(opt(a, "--min-views", 10000))
    extra_q = opt(a, "--requete", many=True)
    cfg = config_dir()
    chaines = load_json(cfg / "chaines.json", {"chaines": []})
    base_q = load_json(cfg / "veille-requetes.json", {})
    t = today()

    if mode == "legere" and len(extra_q) < 4:
        print(f"attention : veille légère avec {len(extra_q)} recherche(s) fraîche(s) ; il en faut au moins 4 (--requete)")

    # 1-3. what to collect
    history = recent_history(weeks=4, before=t)
    hot = set()
    for _, _, data in history:
        for o in sorted(data.get("outliers", []), key=lambda o: -(o.get("multiple") or 0))[:15]:
            hot.add((o.get("channel") or "").lower())
    jobs = [("channel", OWN_URL, str(folder.parent / "ma-chaine.json"), 40)]
    skipped_cache = []
    for c in chaines.get("chaines", []):
        url = channel_url(c)
        if not url:
            continue
        last = c.get("derniere_collecte")
        fresh = last and (t - date.fromisoformat(last)).days < 7
        recent_find = c.get("source") == "découverte" and c.get("ajoutee") and \
            (t - date.fromisoformat(c["ajoutee"])).days <= 28
        wanted = mode == "complete" or (c.get("nom") or "").lower() in hot or recent_find
        if not wanted:
            continue
        if fresh:
            skipped_cache.append(c.get("nom"))
            continue
        jobs.append(("channel", url, str(folder / f"c-{slugify(c.get('nom') or url)}.json"), 25))
    queries = (base_q.get("fr", []) + base_q.get("en", []) + base_q.get("hors_niche", []) if mode == "complete" else []) + extra_q
    for q in dict.fromkeys(queries):
        jobs.append(("search", q, str(folder / f"s-{slugify(q)}.json"), 25))
    print(f"veille {mode} : {sum(1 for j in jobs if j[0] == 'channel') - 1} chaîne(s), "
          f"{sum(1 for j in jobs if j[0] == 'search')} recherche(s), {len(skipped_cache)} chaîne(s) déjà à jour")
    failed = [(j[1], e) for j, e in run_jobs(jobs) if e]

    # 4-5. ranking, then second pass on the thin channels with a strong video
    files = sorted(folder.glob("*.json"))
    if not files:
        sys.exit("aucune donnée collectée (yt-dlp bloqué ?) : voir les erreurs ci-dessus ; ne pas inventer de multiple")
    first = swipe(files, min_views)
    cap = 25 if mode == "complete" else 10
    known = {channel_key(c) for c in chaines.get("chaines", [])}
    cands = [c for c in first.get("thin_candidates", [])
             if c["best_views"] >= min_views and c.get("url") and channel_key(c) not in known
             and (c.get("channel") or "").lower() not in OWN][:cap]
    second = [("channel", c["url"], str(folder / f"c-{slugify(c['channel'])}.json"), 25) for c in cands]
    if second:
        print(f"deuxième passage : {len(second)} chaîne(s) trouvée(s) par les recherches")
        failed += [(j[1], e) for j, e in run_jobs(second) if e]
    final = swipe(sorted(folder.glob("*.json")), min_views) if second else first
    write_json(folder.parent / "refs.json", final)

    # 6. followed channels
    by_key = {channel_key(c): c for c in chaines.get("chaines", [])}
    best = {}
    for o in final["outliers"]:
        best[o["channel"].lower()] = max(best.get(o["channel"].lower(), 0), o["multiple"])
    added = []
    for ch in final.get("channels", []):
        k = channel_key(ch)
        entry = by_key.get(k) or next((c for c in chaines["chaines"] if (c.get("nom") or "").lower() == ch["channel"].lower()), None)
        top = best.get(ch["channel"].lower(), 0)
        if entry is None:
            if top < 3:
                continue
            entry = {"nom": ch["channel"], "channel_id": ch.get("channel_id", ""), "handle": ch.get("handle", ""),
                     "url": channel_url(ch), "source": "découverte", "ajoutee": t.isoformat()}
            chaines["chaines"].append(entry)
            by_key[k] = entry
            added.append(ch["channel"])
        entry.update({"derniere_collecte": t.isoformat(), "mediane": ch["median"], "meilleur_multiple": top})
    chaines["chaines"].sort(key=lambda c: (c.get("source") != "référence", (c.get("nom") or "").lower()))
    write_json(cfg / "chaines.json", chaines)

    # 7. dynamics, 8. archive
    dyn = dynamics(final["outliers"], history)
    slug = "veille-complete" if mode == "complete" else "veille"
    refs_dir().mkdir(parents=True, exist_ok=True)
    write_json(refs_dir() / f"{final.get('collected_at', t.isoformat())}-{slug}.json", final)

    resume = summary(mode, final, dyn, added, failed, skipped_cache, len(second), min_views)
    (folder / "veille-resume.md").write_text(resume, encoding="utf-8")
    print(folder / "veille-resume.md")


def num(x):
    return f"{x:,}".replace(",", " ") if isinstance(x, (int, float)) else "?"


def summary(mode, final, dyn, added, failed, cached, n_second, min_views):
    o = final["outliers"]
    L = [f"# Veille {'complète' if mode == 'complete' else 'légère'} du {final.get('collected_at')}", "",
         f"{len(final.get('channels', []))} chaînes classées, {len(o)} outliers à 1,5× leur médiane ou plus "
         f"(au moins {num(min_views)} vues, Shorts à part, vidéos de 5 à 365 jours) ; {n_second} chaîne(s) ajoutée(s) "
         f"par le deuxième passage. Ce sont des vues, pas de la rétention ni des volumes de recherche.", "",
         "## Meilleurs outliers", "",
         "| × médiane | vues | médiane (sur n vidéos) | âge | vues/j | chaîne | titre | formule |", "|---|---|---|---|---|---|---|---|"]
    for r in o[:20]:
        age = f"{r['age_days']} j" if r.get("age_days") else "?"
        title = r["title"][:70].replace("|", "/")
        n = r.get("median_n")
        med = f"{num(r['median'])} (n={n}{', fragile' if r.get('fragile') else ''})" if n else num(r["median"])
        L.append(f"| {r['multiple']:.1f} | {num(r['views'])} | {med} | {age} | {num(r.get('views_per_day'))} | "
                 f"{r['channel']} | [{title}]({r['url']}) | {r['formula']} |")
    rising = sorted([r for r in o if r.get("age_days") and r["age_days"] <= 30], key=lambda r: -(r.get("views_per_day") or 0))[:8]
    if rising:
        L += ["", "## Ce qui monte (moins de 30 jours, vues par jour)", ""]
        L += [f"- {num(r['views_per_day'])} /j · {r['multiple']:.1f}× · {r['channel']} · {r['title'][:80]}" for r in rising]
    L += ["", "## Dynamique (vidéos déjà vues dans une veille précédente)", ""]
    L += [f"- **{r['state']}** : {num(r['recent_per_day'])} vues/j depuis le {r['since']} (moyenne alors {num(r['avg_per_day_then'])}/j) · "
          f"{r['channel']} · {r['title'][:70]}" for r in dyn[:12]] or ["- rien à comparer (première veille ou aucun outlier revu)"]
    weak = final.get("weak_signals", [])
    L += ["", f"## Signaux faibles (petites chaînes à 10× ou plus, sous {num(min_views)} vues : à surveiller, pas des preuves)", ""]
    L += [f"- {r['multiple']:.0f}× · {num(r['views'])} vues · {r['channel']} · {r['title'][:80]}" for r in weak[:8]] or ["- aucun"]
    flops = final.get("flops", [])
    L += ["", "## Contre-exemples (flops : 0,5× la médiane de leur chaîne ou moins, 5 à 180 jours)", ""]
    L += [f"- {r['multiple']:.2f}× · {num(r['views'])} vues (médiane {num(r['median'])}) · {r['channel']} · {r['title'][:80]} · {r['formula']}"
          for r in flops[:10]] or ["- aucun (il faut au moins 8 vidéos collectées par chaîne)"]
    if flops and o:
        fo, ff = {}, {}
        for r in o: fo[r["formula"]] = fo.get(r["formula"], 0) + 1
        for r in flops: ff[r["formula"]] = ff.get(r["formula"], 0) + 1
        worse = [f for f, n in ff.items() if n >= 2 and n / len(flops) > 2 * fo.get(f, 0) / len(o)]
        if worse:
            L += ["", "Formules surreprésentées parmi les flops (à éviter ou à justifier) : " + ", ".join(worse)]
    L += ["", "## Chaînes ajoutées à chaines.json (découverte)", "", ", ".join(added) or "aucune"]
    formulas = {}
    for r in o:
        formulas[r["formula"]] = formulas.get(r["formula"], 0) + 1
    L += ["", "## Formules de titre parmi les outliers", ""]
    L += [f"- {n} × {f}" for f, n in sorted(formulas.items(), key=lambda x: -x[1])[:8]]
    if cached:
        L += ["", f"Chaînes non recollectées (déjà collectées il y a moins de 7 jours) : {', '.join(c for c in cached if c)}"]
    if failed:
        L += ["", "## Échecs (rien n'a été inventé à leur place)", ""] + [f"- {t} : {e}" for t, e in failed]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- French gap

FR_WORDS = re.compile(r"\b(j'ai|je|le|la|les|une?|des|du|pour|avec|qui|est|sur|dans|mon|ma|mes|contre|fait|faire|"
                      r"cr[ée]e|jeu|vid[ée]o|meilleur|vraiment|c'est|ia)\b|[éèêàùç]", re.I)
EN_WORDS = re.compile(r"\b(the|i|my|with|vs|make|made|from|scratch|game|best|this|is|of|and|to)\b", re.I)


def is_french(title):
    return len(FR_WORDS.findall(title)) >= 2 and len(FR_WORDS.findall(title)) > len(EN_WORDS.findall(title))


def creneau_one(concept):
    path = Path(tempfile.gettempdir()) / f"creneau-{slugify(concept)}-{os.getpid()}-{threading.get_ident()}.json"
    job, err = fetch(("search", concept, str(path), 20))
    if err:
        return {"concept": concept, "erreur": err}
    data = load_json(path, {})
    path.unlink(missing_ok=True)
    vids = [e for e in data.get("entries", []) if e and e.get("title")
            and (e.get("channel") or "").lower() not in OWN]
    fr = sorted([e for e in vids if is_french(e["title"])], key=lambda e: -(e.get("view_count") or 0))
    big = [e for e in fr if (e.get("view_count") or 0) >= 10000]
    verdict = "libre" if not big else "partiel" if len(big) <= 2 else "pris"
    return {"concept": concept, "resultats": len(vids), "videos_fr": len(fr), "fr_10k": len(big), "verdict": verdict,
            "exemples": [{"titre": e["title"], "chaine": e.get("channel"), "vues": e.get("view_count")} for e in fr[:3]]}


def creneau(a):
    concepts = [x for x in a if not x.startswith("--")]
    if not concepts:
        sys.exit("usage : veille.py creneau \"concept en français\" ...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(creneau_one, concepts))
    if "--json" in a:
        print(json.dumps(res, indent=1, ensure_ascii=False)); return
    for r in res:
        if r.get("erreur"):
            print(f"\n  {r['concept']} : recherche impossible ({r['erreur']})"); continue
        print(f"\n  {r['concept']} : {CRENEAU_TXT[r['verdict']]} ({r['verdict']}) — {r['videos_fr']} vidéo(s) en français "
              f"sur les {r['resultats']} premiers résultats de cette recherche, {r['fr_10k']} à 10 000 vues ou plus")
        for e in r["exemples"]:
            print(f"      {num(e['vues'] or 0):>9}  {(e['chaine'] or '')[:22]:<22} {e['titre'][:70]}")
    print("\n  (langue devinée sur les titres : à confirmer à l'œil ; une seule recherche de 20 résultats ne prouve pas "
          "l'absence de concurrence, d'autres formulations peuvent trouver des vidéos)\n")


# ---------------------------------------------------------------- Google Trends

def trends_points(term):
    """[(date, value)] weekly interest on YouTube search, France, 5 years; raises on refusal."""
    import http.cookiejar, urllib.parse, urllib.request
    if os.environ.get("TRENDS_FIXTURE"):  # tests
        data = json.loads(Path(os.environ["TRENDS_FIXTURE"]).read_text(encoding="utf-8"))
        return [(date.fromisoformat(d), v) for d, v in data.get(term, [])]
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", "Mozilla/5.0"), ("Accept-Language", "fr-FR,fr;q=0.9")]
    op.open("https://trends.google.com/trends/explore?geo=FR&gprop=youtube", timeout=20).read()
    req = {"comparisonItem": [{"keyword": term, "geo": "FR", "time": "today 5-y"}], "category": 0, "property": "youtube"}
    q = urllib.parse.urlencode({"hl": "fr", "tz": "-120", "req": json.dumps(req)})
    body = op.open(f"https://trends.google.com/trends/api/explore?{q}", timeout=20).read().decode("utf-8")
    widget = next(w for w in json.loads(body[body.index("{"):])["widgets"] if w.get("id") == "TIMESERIES")
    q = urllib.parse.urlencode({"hl": "fr", "tz": "-120", "req": json.dumps(widget["request"]), "token": widget["token"]})
    body = op.open(f"https://trends.google.com/trends/api/widgetdata/multiline?{q}", timeout=20).read().decode("utf-8")
    rows = json.loads(body[body.index("{"):])["default"]["timelineData"]
    return [(datetime.fromtimestamp(int(r["time"]), timezone.utc).date(), (r.get("value") or [0])[0]) for r in rows]


def analyse_trend(points, t=None):
    """Classify a weekly series: saisonnier / tendance / en déclin / permanent, next peak for a season."""
    t = t or today()
    pts = [(d, v) for d, v in points if v is not None]
    if len(pts) < 20 or not any(v for _, v in pts):
        return {"classe": "trop peu de données", "pic": None}
    by_month = {}
    for d, v in pts:
        by_month.setdefault(d.month, []).append(v)
    means = {m: sum(vs) / len(vs) for m, vs in by_month.items()}
    overall = sum(v for _, v in pts) / len(pts)
    peak_m = max(means, key=means.get)
    years = sorted({d.year for d, _ in pts})
    yearly_peak = []
    for y in years[:-1] if len(years) > 2 else years:
        ys = [(d, v) for d, v in pts if d.year == y]
        if ys:
            yearly_peak.append(max(ys, key=lambda x: x[1])[0].month)
    same_month = sum(1 for m in yearly_peak if abs(m - peak_m) <= 1 or abs(m - peak_m) == 11)
    last = [v for d, v in pts if (t - d).days <= 365]
    prev = [v for d, v in pts if 365 < (t - d).days <= 730]
    growth = (sum(last) / len(last)) / ((sum(prev) / len(prev)) or 1) if last and prev else None
    seasonal = means[peak_m] >= 1.6 * overall and len(yearly_peak) >= 2 and same_month >= max(2, len(yearly_peak) - 1)
    if seasonal:
        nxt = date(t.year, peak_m, 15)
        if nxt < t - timedelta(days=15):
            nxt = date(t.year + 1, peak_m, 15)
        classe = "saisonnier"
    else:
        nxt = None
        classe = "tendance" if growth and growth >= 1.5 else "en déclin" if growth is not None and growth <= 0.6 else "permanent"
    return {"classe": classe, "mois_du_pic": peak_m, "pic": nxt.isoformat() if nxt else None,
            "croissance_1_an": round(growth, 2) if growth else None, "force_du_pic": round(means[peak_m] / (overall or 1), 2)}


def tendance(a):
    terms = [x for x in a if not x.startswith("--")]
    if not terms:
        sys.exit("usage : veille.py tendance \"terme\" ...")
    res = []
    for term in terms:
        try:
            r = dict(analyse_trend(trends_points(term)), terme=term)
        except Exception as e:
            r = {"terme": term, "erreur": f"Google Trends indisponible ({e.__class__.__name__}) : pas de saisonnalité, rien n'est deviné"}
        res.append(r)
    if "--json" in a:
        print(json.dumps(res, indent=1, ensure_ascii=False)); return
    for r in res:
        if r.get("erreur"):
            print(f"  {r['terme']} : {r['erreur']}"); continue
        extra = f", prochain pic vers le {r['pic']}" if r.get("pic") else ""
        print(f"  {r['terme']} : {r['classe']}{extra} (croissance sur un an : {r.get('croissance_1_an')}, "
              f"pic à {r.get('force_du_pic')}× la moyenne)")


# ---------------------------------------------------------------- idea grid

def demand(seeds):
    """0-2 from YouTube autocomplete: how many suggestions come back for the seeds."""
    if not seeds:
        return None, []
    sys.path.insert(0, str(HERE.parent / "youtube-titles-ab"))
    try:
        import suggest  # noqa: E402
    except ImportError:
        return None, []
    if os.environ.get("SWIPE_OFFLINE"):
        return None, []
    got = {}
    for s in seeds:
        try:
            got[s] = suggest.fetch(s, "fr", "FR")
        except Exception:
            pass
    if not got:
        return None, []
    ranked = suggest.rank(got)
    n = len(ranked)
    return (2 if n >= 12 else 1 if n >= 4 else 0), [s for s, _, _ in ranked[:3]]


def proof(multiple, views):
    if not multiple or multiple <= 1:
        return 0.0
    p = min(3.0, math.log2(multiple) / 2)
    return round(p / 2 if (views or 0) < 10000 else p, 2)


def idea_proof(i):
    """(points, multiple shown, measured?) : a crossed idea (morceaux) is worth its weakest piece."""
    pieces = i.get("morceaux")
    if not pieces:
        return proof(i.get("multiple"), i.get("vues")), i.get("multiple", "?"), bool(i.get("multiple"))
    weakest = min(pieces, key=lambda x: proof(x.get("multiple"), x.get("vues")))
    return (proof(weakest.get("multiple"), weakest.get("vues")), f"croisée, min {weakest.get('multiple', '?')}",
            all(x.get("multiple") for x in pieces))


def grille(a):
    files = [x for x in a if not x.startswith("--")]
    if not files:
        sys.exit("usage : veille.py grille idees.json [--md]")
    ideas = load_json(files[0], None)
    if not isinstance(ideas, list):
        sys.exit(f"{files[0]} doit contenir une liste d'idées (voir le mode d'emploi en tête du script)")
    gaps = {}
    need = [i.get("creneau_concept") for i in ideas if not i.get("creneau") and i.get("creneau_concept")]
    if need and not os.environ.get("SWIPE_OFFLINE"):
        with ThreadPoolExecutor(max_workers=4) as ex:
            for r in ex.map(creneau_one, need):
                gaps[r["concept"]] = r.get("verdict")
    rows = []
    t = today()
    for i in ideas:
        gap = i.get("creneau") or gaps.get(i.get("creneau_concept"))
        pic = i.get("pic")
        if not pic and i.get("tendance_mot") and not os.environ.get("SWIPE_OFFLINE"):
            try:
                pic = analyse_trend(trends_points(i["tendance_mot"])).get("pic")
            except Exception:
                pic = None
        days = None
        if pic:
            d = date.fromisoformat(pic if len(pic) == 10 else f"{t.year}-{pic}")
            if d < t - timedelta(days=7):
                d = d.replace(year=d.year + 1)
            days = (d - t).days
        dem = 2 if i.get("sondage") else i.get("demande")   # the option the viewers voted for
        sugg = []
        if dem is None:
            dem, sugg = demand(i.get("demande_seeds") or [])
        gap = gap if gap in ("libre", "partiel", "pris") else None
        pts, shown, proven = idea_proof(i)
        unknown = [k for k, known in (("créneau", gap is not None), ("demande", dem is not None), ("preuve", proven))
                   if not known]
        parts = {"preuve": pts,
                 "faisabilite": max(1, min(3, int(i.get("faisabilite", 2)))),
                 "creneau": {"libre": 2, "partiel": 1, "pris": 0}.get(gap, 0),
                 "urgence": max(0, min(2, int(i.get("urgence", 0)) + (1 if days is not None and -7 <= days <= 60 else 0))),
                 "demande": dem if dem is not None else 0,
                 "apprentissages": max(-1, min(1, float(i.get("apprentissages", 0))))}
        total = round(sum(parts.values()), 2)
        best = total + (2 if gap is None else 0) + (2 if dem is None else 0) + (3 - pts if not proven else 0)
        rows.append(dict(i, **{"_parts": parts, "_total": total, "_multiple": shown, "_max_possible": round(best, 2), "_inconnues": unknown,
                               "_confiance": "élevée" if not unknown else "moyenne" if len(unknown) == 1 else "faible",
                               "_gap": gap or "?", "_pic_dans": days, "_demande_connue": dem is not None, "_suggestions": sugg}))
    rows.sort(key=lambda r: (-r["_total"], len(r["_inconnues"])))
    # a winner is recommended only when nothing unmeasured could change the first place
    top = rows[0] if rows else None
    open_ = [r for r in rows[1:] if r["_max_possible"] > top["_total"]] if top else []
    verdict = None
    if top and (top["_inconnues"] or open_):
        todo = sorted({f"{r.get('titre', '?')} ({', '.join(r['_inconnues'])})" for r in [top] + open_ if r["_inconnues"]})
        verdict = "classement non tranché : à mesurer avant de recommander un gagnant : " + " ; ".join(todo)
    if "--json" in a:
        print(json.dumps({"idees": rows, "non_tranche": verdict}, indent=1, ensure_ascii=False) if "--avec-verdict" in a
              else json.dumps(rows, indent=1, ensure_ascii=False)); return
    lines = ["| # | idée | type | intention | preuve | faisab. | créneau FR | urgence | demande | apprent. | **total /13** | confiance (max possible) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, r in enumerate(rows, 1):
        p = r["_parts"]
        pic = f" (pic dans {r['_pic_dans']} j)" if r.get("_pic_dans") is not None else ""
        lines.append(f"| {n} | {r.get('titre', '?')} | {r.get('type', '')} | {r.get('intention', '')} | {p['preuve']} ({r['_multiple']}×) | "
                     f"{p['faisabilite']} | {p['creneau']} ({CRENEAU_TXT.get(r['_gap'], 'non mesuré (?)')}) | {p['urgence']}{pic} | "
                     f"{p['demande']}{'' if r['_demande_connue'] else ' (?)'} | {p['apprentissages']:+g} | **{r['_total']}** | "
                     f"{r['_confiance']}" + (f" (jusqu'à {r['_max_possible']})" if r["_inconnues"] else "") + " |")
    lines += ["", f"Barème : {GRILLE}. (?) = donnée non mesurée, comptée 0 (une inconnue n'est pas un avantage).",
              "Créneau FR : « aucune référence FR forte trouvée » veut dire « pas dans les 20 résultats de cette recherche », pas « personne ne l'a fait »."]
    if verdict:
        lines += ["", f"**{verdict[0].upper() + verdict[1:]}.**"]
    print("\n".join(lines))


# ---------------------------------------------------------------- followed channels

def chaines_cmd(a):
    data = load_json(config_dir() / "chaines.json", {"chaines": []})
    t = today()
    for c in data["chaines"]:
        last = c.get("derniere_collecte")
        age = f"il y a {(t - date.fromisoformat(last)).days} j" if last else "jamais"
        print(f"  {c.get('source', '?'):<11} {c.get('nom', '?')[:30]:<30} collectée {age:<12} médiane {c.get('mediane', '?')}  "
              f"meilleur {c.get('meilleur_multiple', '?')}×")
    print(f"\n  {len(data['chaines'])} chaînes suivies ({config_dir() / 'chaines.json'})")


def main():
    a = sys.argv[1:]
    cmds = {"collecte": collecte, "creneau": creneau, "grille": grille, "tendance": tendance, "chaines": chaines_cmd}
    if not a or a[0] not in cmds:
        print(__doc__); sys.exit(1)
    cmds[a[0]](a[1:])


if __name__ == "__main__":
    main()
