#!/usr/bin/env python3
"""bilan.py - how did a published video actually do? Numbers for the post-publication review.

    python3 bilan.py VIDEO_ID_OR_URL
    python3 bilan.py VIDEO_ID_OR_URL --json
    python3 bilan.py VIDEO_ID_OR_URL --public      # no OAuth: public numbers only (yt-dlp)
    python3 bilan.py VIDEO_ID --vue vue_<projet - final>.txt   # drops and peaks tied to what was said
    python3 bilan.py --csv retention.csv --duree 581 [--vue vue.txt]   # Studio export, no OAuth needed
    python3 bilan.py --csv retention.csv --duree 581 --id pokemon-ia --age 7
    python3 bilan.py --csv retention.csv --duree 581 --unite-position secondes --unite-retention ratio
    python3 bilan.py VIDEO_ID --age 7            # numbers at the same age for every video (days 0-6 only)
    python3 bilan.py VIDEO_ID --id pokemon-ia    # also keeps a dated copy in videos/<id>/bilans/

Retention curve analysis (API curve or Studio CSV): every DROP (the audience falls by 10 % or more of
itself within 10 seconds, after the first 30 s; the fall back after a peak does not count) and every PEAK (the curve rises: people rewind and
rewatch), with the time in m:ss and, with --vue (timeline_overview.py output of the final edit,
montage/02_ANALYSE/vue_<projet - final>.txt), the sentence said at that moment. Plus the intro (0:15),
the premise (1:00) and the gaming benchmarks (0:30 at 70 % or more, 45-55 % watched, CTR 5-10 %).

With OAuth (YouTube Analytics, your own channel only), from the publication date to today:
views, watch time, average view duration and percentage, subscribers gained, likes, comments,
shares, views on the release day and the next one (days 0-1) and on days 0-6, traffic sources, the retention curve
(kept at 30 s, 25 %, 50 %, 75 %) and, when the API exposes them, impressions and click-through rate.

What the API does NOT give: the Test & Compare winner, and on many accounts the impressions and
CTR. Those come from YouTube Studio; the review asks the user for them.

PERIODS. YouTube Analytics counts in whole days of the Pacific time zone (America/Los_Angeles), not in
hours from the release: "days 0-1" is the release day (often partial) and the next one, never "48 hours".
The release date is converted to a Pacific date before counting. --age N stops every query at day N-1,
so two videos are compared at the same age whatever the day the review is run.

Analytics lag about 2 days behind: a review before day 3 is mostly empty. Prints at the end a row
ready for ~/.claude/youtube/apprentissages.md, with [à compléter] where Studio is needed.

Needs: pip install google-api-python-client google-auth-oauthlib, and the OAuth client file at
~/.claude/youtube_client_secrets.json (see the bilan-video skill). The first run opens a browser.
"""
import hashlib, json, os, re, shutil, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "youtube" / "execution"))

CORE = ["views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
        "subscribersGained", "subscribersLost", "likes", "comments", "shares"]
# the impressions / CTR metric names have changed over time and are not exposed on every account:
# each pair is tried in turn, and a failure only means "copy them from Studio"
CTR_CANDIDATES = [("videoThumbnailImpressions", "videoThumbnailImpressionsClickRate"),
                  ("impressions", "impressionClickThroughRate")]

def video_id(s):
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/live/|/video/)([\w-]{11})", s)
    return m.group(1) if m else (s if re.fullmatch(r"[\w-]{11}", s) else None)

def iso_duration(s):
    """'PT1H2M3S' -> 3723 seconds."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m: return None
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se

def pacific(dt):
    """UTC datetime -> date in the Pacific time zone (YouTube Analytics days). zoneinfo when available
    (on Windows it needs the tzdata package), else the US rule: summer time from the 2nd Sunday of March
    to the 1st Sunday of November, at 2:00 local."""
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("America/Los_Angeles")).date()
    except Exception:
        y = dt.year
        sunday = lambda m, n: date(y, m, 1) + timedelta(days=(6 - date(y, m, 1).weekday()) % 7 + 7 * (n - 1))
        start = datetime.combine(sunday(3, 2), datetime.min.time(), timezone.utc) + timedelta(hours=10)   # 2:00 PST
        end = datetime.combine(sunday(11, 1), datetime.min.time(), timezone.utc) + timedelta(hours=9)     # 2:00 PDT
        return (dt - timedelta(hours=7 if start <= dt < end else 8)).date()


def retention_at(curve, ratio):
    """curve: [(elapsedVideoTimeRatio, audienceWatchRatio)], linear interpolation at ratio."""
    pts = sorted(curve)
    if not pts or ratio is None: return None
    if ratio <= pts[0][0]: return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= ratio <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (ratio - x0) / (x1 - x0)
    return pts[-1][1]

# gaming benchmarks (youtube-seo-skills, deeployCO, MIT): a reference, not a law; compare to the channel first
BENCH = {"retention_30s": [(70, "bon"), (60, "moyen"), (0, "à retravailler : accroche ou promesse du titre")],
         "averageViewPercentage": [(55, "excellent"), (45, "bon (repère gaming 45-55 %)"), (35, "à retravailler"),
                                   (0, "bas pour du gaming (repère de niche, pas une règle de YouTube)")],
         "ctr": [(10, "très haut (peu d'impressions ?)"), (5, "dans la plage gaming 5-10 %"), (2, "bas pour du gaming"),
                 (0, "très bas : titre ou miniature")]}


def bench(key, v):
    if v is None or key not in BENCH: return None
    return next(lab for lim, lab in BENCH[key] if v >= lim)


def mmss(t):
    t = int(round(t)); return f"{t // 60}:{t % 60:02d}"


def analyse_curve(curve, duration):
    """curve [(ratio, audience)] -> drops, peaks, intro and premise levels (audience in %)."""
    if not curve or not duration: return None
    pts = sorted((x * duration, y * 100) for x, y in curve)
    drops, peaks = [], []
    for i, (t0, a0) in enumerate(pts):
        if t0 < 30: continue  # the intro's natural slope is judged apart (0:15, 0:30)
        win = [(t, a) for t, a in pts[i + 1:] if t - t0 <= 10]
        if not win: continue
        t1, a1 = min(win, key=lambda p: p[1])
        if a0 > 0 and (a0 - a1) / a0 >= 0.10:
            drops.append({"t": round(t0, 1), "jusqu_a": round(t1, 1), "de": round(a0, 1), "a": round(a1, 1)})
        t2, a2 = max(win, key=lambda p: p[1])
        if a2 - a0 >= 2:
            peaks.append({"t": round(t0, 1), "jusqu_a": round(t2, 1), "de": round(a0, 1), "a": round(a2, 1)})
    def merge(xs, key):
        out = []
        for x in xs:
            if out and x["t"] <= out[-1]["jusqu_a"] + 1:
                if key(x) > key(out[-1]): out[-1] = dict(x, t=out[-1]["t"])
                else: out[-1]["jusqu_a"] = max(out[-1]["jusqu_a"], x["jusqu_a"])
            else: out.append(dict(x))
        return out
    peaks = merge(peaks, lambda d: d["a"] - d["de"])
    # the fall back after a rewatch peak is not a drop: people simply stop rewinding
    after_peak = lambda d: any(p["t"] <= d["t"] <= p["jusqu_a"] + 10 and d["a"] >= p["de"] - 2 for p in peaks)
    drops = [d for d in merge(drops, lambda d: d["de"] - d["a"]) if not after_peak(d)]
    drops = sorted(drops, key=lambda d: -(d["de"] - d["a"]))[:6]
    peaks = sorted(peaks, key=lambda d: -(d["a"] - d["de"]))[:4]
    lo, hi = pts[0][0], pts[-1][0]
    at = lambda s: round(retention_at([(t / duration, a) for t, a in pts], s / duration), 1) if lo - 1 <= s <= hi + 1 else None
    return {"intro_15s": at(15), "premisse_60s": at(60), "chutes": sorted(drops, key=lambda d: d["t"]),
            "pics": sorted(peaks, key=lambda d: d["t"]), "mesure_de": round(lo, 1), "mesure_a": round(hi, 1),
            "couverture": round((hi - lo) / duration * 100)}


def read_vue(path):
    """timeline_overview.py output: '  12.3 NOIR      sentence' -> [(seconds, sentence)]."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s+(\S+)\s+(.*)", line)
        if m: rows.append((float(m.group(1)), m.group(3).strip()))
    return rows


def said_at(vue, t):
    before = [s for s in vue if s[0] <= t + 0.5]
    return before[-1][1] if before else ""


UNITS = ("pourcentage", "ratio", "secondes")


def position_unit(header, values, duration):
    """Unit of the position column: from its header first ("%", "ratio", "(s)", "sec"), then from its values
    (m:ss -> seconds, all <= 1 -> ratio, above 100 -> seconds). Ambiguous (values between 1 and 100, no header
    hint): None, and the caller asks for --unite-position."""
    h = header.lower()
    if re.search(r"%|pourcent|percent", h): return "pourcentage"
    if re.search(r"ratio|fraction", h): return "ratio"
    if re.search(r"\(s\)|\bsec|seconde|second", h): return "secondes"
    if any(":" in v for v in values): return "secondes"
    nums = [float(v.replace(",", ".")) for v in values if re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", v)]
    if not nums: return None
    if max(nums) <= 1: return "ratio"
    if max(nums) > 100: return "secondes"
    return None


def read_studio_csv(path, duration, unite=None, unite_retention=None):
    """Studio retention export -> ([(position ratio 0-1, audience ratio without upper cap)], info). The position unit is read from the header
    or the values (see position_unit), or forced with unite; seconds are divided by the REAL duration of the
    video (never by the last point: a partial export would be stretched over the whole video). info gives the
    units and the part of the video the export covers."""
    import csv
    if duration <= 0: raise ValueError("durée réelle strictement positive requise")
    text = Path(path).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(text.splitlines(), delimiter=";" if text.count(";") > text.count(",") else ","))
    head_i = next((i for i, r in enumerate(rows) if any(re.search(r"position|temps|time", c, re.I) for c in r)), None)
    if head_i is None: raise ValueError("colonne de position introuvable dans le CSV")
    head = [c.lower() for c in rows[head_i]]
    pos = next(i for i, c in enumerate(head) if re.search(r"position|temps|time", c))
    ret = next((i for i, c in enumerate(head) if re.search(r"absolu", c)), None)
    if ret is None: ret = next((i for i, c in enumerate(head) if re.search(r"r[ée]tention|audience", c) and i != pos), None)
    if ret is None: raise ValueError("colonne de rétention introuvable dans le CSV")
    body = [r for r in rows[head_i + 1:] if len(r) > max(pos, ret) and r[pos].strip() and r[ret].strip()]
    unit = unite or position_unit(rows[head_i][pos], [r[pos].strip() for r in body], duration)
    if unit not in UNITS:
        raise ValueError(f"unité de la colonne « {rows[head_i][pos]} » impossible à lire (valeurs entre 1 et 100 : "
                         "pourcentage ou secondes ?) : relance avec --unite-position pourcentage|ratio|secondes")
    def position(v):
        if ":" in v:
            parts = [float(x.replace(",", ".")) for x in v.split(":")]
            v = sum(x * 60 ** i for i, x in enumerate(reversed(parts)))
        else:
            v = float(v.replace("%", "").replace(",", ".").strip())
        return {"pourcentage": v / 100, "ratio": v, "secondes": v / duration}[unit]
    num = lambda x: float(x.replace("%", "").replace(",", ".").strip())
    data = []
    for r in body:
        try: data.append((position(r[pos]), num(r[ret])))
        except ValueError: continue
    if not data: raise ValueError("aucune ligne chiffrée dans le CSV")
    if max(p for p, _ in data) > 1.02:
        raise ValueError(f"positions au-delà de la fin de la vidéo ({unit}, durée {duration:g} s) : durée ou unité fausse")
    h = head[ret]
    ret_unit = unite_retention
    if ret_unit is None:
        if re.search(r"%|pourcent|percent", h): ret_unit = "pourcentage"
        elif re.search(r"ratio|fraction", h): ret_unit = "ratio"
        elif any("%" in r[ret] for r in body): ret_unit = "pourcentage"
    if ret_unit not in ("pourcentage", "ratio"):
        raise ValueError(f"unité de rétention « {rows[head_i][ret]} » ambiguë : relance avec "
                         "--unite-retention pourcentage|ratio (un ratio peut dépasser 2 lors de relectures)")
    pct_ret = ret_unit == "pourcentage"
    curve = [(p, a / (100 if pct_ret else 1)) for p, a in data]
    lo, hi = min(p for p, _ in curve), max(p for p, _ in curve)
    info = {"unite_position": unit, "unite_retention": "pourcentage" if pct_ret else "ratio",
            "couverture": f"{round(lo * 100)} % à {round(hi * 100)} % de la vidéo"}
    if hi - lo < 0.9:
        info["alerte"] = (f"export partiel : la courbe couvre {info['couverture']} ; rien n'est conclu en dehors "
                          "(0:15 et 1:00 manquent s'ils sont hors de cette plage)")
    return curve, info


def first_days(daily, published, n):
    """Sum of views over days 0 to n-1 (Pacific days, day 0 = release day, often partial), None if not enough days yet."""
    if not daily or not published: return None
    end = published + timedelta(days=n - 1)
    if max(d for d, _ in daily) < end: return None
    return int(sum(v for d, v in daily if published <= d <= end))

def pct(x, scale=100):
    return None if x is None else round(x * scale, 1)

def row(r):
    def f(v, suffix=""): return "[à compléter]" if v is None else f"{v}{suffix}"
    return (f"| {r.get('published') or '?'} | {r.get('title', '?')} | [levier gagnant] | "
            f"{f(r.get('ctr'), ' %')} | {f(r.get('retention_30s'), ' %')} | {f(r.get('averageViewPercentage'), ' %')} | "
            f"{f(r.get('views_7d'))} | {f(r.get('subscribersGained'))} | [référence] | [constat] ; [hypothèse, à vérifier] |")

def query(svc, vid, start, end, metrics, dimensions=None, extra_filter=""):
    kw = dict(ids="channel==MINE", startDate=start, endDate=end, metrics=",".join(metrics),
              filters=f"video=={vid}{extra_filter}")
    if dimensions: kw["dimensions"] = dimensions
    if dimensions == "day": kw["sort"] = "day"
    resp = svc.reports().query(**kw).execute()
    heads = [h["name"] for h in resp.get("columnHeaders", [])]
    return [dict(zip(heads, x)) for x in resp.get("rows", [])]

def private(vid, age=None):
    try:
        from googleapiclient.discovery import build
        from utils.youtube_auth import get_oauth_credentials
    except ImportError as e:
        return None, {"error": f"dépendances manquantes ({e})",
                      "fix": "pip install google-api-python-client google-auth-oauthlib"}
    creds, err = get_oauth_credentials()
    if err: return None, err
    yt = build("youtube", "v3", credentials=creds)
    an = build("youtubeAnalytics", "v2", credentials=creds)
    items = yt.videos().list(part="snippet,contentDetails,statistics", id=vid).execute().get("items", [])
    if not items:
        return None, {"error": f"vidéo {vid} introuvable sur le compte connecté (vidéo privée d'un autre compte ?)"}
    it = items[0]
    pub = pacific(datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00")))
    today = pacific(datetime.now(timezone.utc))
    r = {"id": vid, "title": it["snippet"]["title"], "published": pub.isoformat(),
         "duration": iso_duration(it["contentDetails"].get("duration")),
         "age_days": (today - pub).days, "notes": []}
    end_d = today
    if age:
        end_d = min(today, pub + timedelta(days=age - 1))
        r["periode"] = f"jours 0 à {age - 1} (jours de YouTube, heure du Pacifique)"
        if pub + timedelta(days=age - 1) > today - timedelta(days=2):
            r["notes"].append(f"--age {age} : la vidéo n'a pas encore {age} jours de données complètes (Analytics a environ 2 jours de retard)")
    else:
        r["periode"] = f"jours 0 à {(today - pub).days} (de la sortie à aujourd'hui, heure du Pacifique)"
    r["date_bilan"], r["fin_periode"] = date.today().isoformat(), end_d.isoformat()
    start, end = pub.isoformat(), end_d.isoformat()
    try:
        core = query(an, vid, start, end, CORE)
        if core: r.update({k: (round(v, 1) if isinstance(v, float) else v) for k, v in core[0].items()})
        else: r["notes"].append("aucune donnée Analytics pour l'instant (décalage d'environ 2 jours)")
    except Exception as e:
        r["notes"].append(f"métriques principales indisponibles : {e}")
    try:
        daily = [(date.fromisoformat(x["day"]), x["views"]) for x in query(an, vid, start, end, ["views"], "day")]
        r["views_d0_1"], r["views_7d"] = first_days(daily, pub, 2), first_days(daily, pub, 7)
    except Exception as e:
        r["notes"].append(f"vues par jour indisponibles : {e}")
    try:
        curve = [(x["elapsedVideoTimeRatio"], x["audienceWatchRatio"])
                 for x in query(an, vid, start, end, ["audienceWatchRatio"], "elapsedVideoTimeRatio",
                                ";audienceType==ORGANIC")]
        if curve:
            r["curve"] = curve
            r["curve_units"] = {"position": "ratio", "audience": "ratio"}
            r["curve_source"] = {"type": "youtube_analytics", "metric": "audienceWatchRatio",
                                 "dimension": "elapsedVideoTimeRatio", "audienceType": "ORGANIC",
                                 "startDate": start, "endDate": end}
            d = r.get("duration")
            r["retention_30s"] = pct(retention_at(curve, 30 / d if d else None))
            for p in (25, 50, 75): r[f"retention_{p}"] = pct(retention_at(curve, p / 100))
    except Exception as e:
        r["notes"].append(f"courbe de rétention indisponible : {e}")
    try:
        r["traffic_sources"] = {x["insightTrafficSourceType"]: x["views"]
                                for x in query(an, vid, start, end, ["views"], "insightTrafficSourceType")}
    except Exception as e:
        r["notes"].append(f"sources de trafic indisponibles : {e}")
    for imp, ctr in CTR_CANDIDATES:
        try:
            x = query(an, vid, start, end, [imp, ctr])
            if x:
                r["impressions"] = x[0].get(imp)
                c = x[0].get(ctr)
                r["ctr"] = None if c is None else round(c * 100 if c <= 1 else c, 1)
            break
        except Exception:
            continue
    if r.get("ctr") is None:
        r["notes"].append("impressions et taux de clics non exposés par l'API sur ce compte : les recopier depuis Studio")
    return r, None

def public(vid):
    exe = shutil.which("yt-dlp")
    cmd = ([exe] if exe else [sys.executable, "-m", "yt_dlp"]) + ["--skip-download", "--no-warnings", "-j",
                                                                    f"https://www.youtube.com/watch?v={vid}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
        info = json.loads(out.stdout)
    except Exception as e:
        return None, {"error": f"yt-dlp a échoué : {e.__class__.__name__}"}
    pub = info.get("upload_date")
    pub = datetime.strptime(pub, "%Y%m%d").date() if pub else None
    return {"id": vid, "title": info.get("title"), "published": pub.isoformat() if pub else None,
            "duration": info.get("duration"), "age_days": (date.today() - pub).days if pub else None,
            "views": info.get("view_count"), "likes": info.get("like_count"),
            "comments": info.get("comment_count"),
            "notes": ["mode public : ni rétention, ni durée moyenne, ni taux de clics (il faut l'accès OAuth)"]}, None

def show(r):
    print(f"\n  {r['title']}  ({r['id']})")
    print(f"    publiée le {r.get('published')}, il y a {r.get('age_days')} j, durée {r.get('duration')} s")
    if r.get("periode"): print(f"    période : {r['periode']}")
    labels = [("views", "vues"), ("views_d0_1", "vues jours 0-1"), ("views_7d", "vues jours 0-6"),
              ("averageViewDuration", "durée moyenne (s)"), ("averageViewPercentage", "% moyen regardé"),
              ("retention_30s", "rétention à 30 s (%)"), ("retention_25", "rétention à 25 % (%)"),
              ("retention_50", "rétention à 50 % (%)"), ("retention_75", "rétention à 75 % (%)"),
              ("impressions", "impressions"), ("ctr", "taux de clics (%)"),
              ("subscribersGained", "abonnés gagnés"), ("subscribersLost", "abonnés perdus"),
              ("likes", "j'aime"), ("comments", "commentaires"), ("shares", "partages")]
    for k, lab in labels:
        if r.get(k) is not None: print(f"    {lab:<24} {r[k]}")
    if r.get("traffic_sources"):
        tot = sum(r["traffic_sources"].values()) or 1
        print("    sources : " + ", ".join(f"{k} {v * 100 // tot} %" for k, v in
                                       sorted(r["traffic_sources"].items(), key=lambda x: -x[1])[:5]))
    for n in r.get("notes", []): print(f"    ! {n}")
    show_curve(r)
    print("\n  ligne pour apprentissages.md :\n  " + row(r) + "\n")


def show_curve(r):
    marks = [(k, lab) for k, lab in (("retention_30s", "rétention à 30 s"), ("averageViewPercentage", "% regardé"), ("ctr", "taux de clics"))
             if r.get(k) is not None]
    if marks:
        print("\n  repères gaming (à comparer d'abord aux vidéos précédentes de la chaîne)")
        for k, lab in marks: print(f"    {lab:<18} {r[k]} % : {bench(k, r[k])}")
    c = r.get("analyse")
    if not c: return
    if r.get("csv_info"):
        i = r["csv_info"]
        print(f"\n  CSV : position en {i['unite_position']}, rétention en {i['unite_retention']}, couverture {i['couverture']}")
        if i.get("alerte"): print(f"    ! {i['alerte']}")
    fmt = lambda v: "hors de la courbe" if v is None else f"{v} %"
    print(f"\n  courbe : {fmt(c['intro_15s'])} à 0:15 (accroche), {fmt(c['premisse_60s'])} à 1:00 (promesse ; repère ≥ 60 %)")
    vue = r.get("_vue") or []
    for title, xs, sign in (("chutes (10 % ou plus du public perdu en moins de 10 s)", c["chutes"], "-"),
                            ("pics (le public revient en arrière : moments forts)", c["pics"], "+")):
        print(f"  {title}")
        if not xs: print("    aucune" if sign == "-" else "    aucun")
        for x in xs:
            what = said_at(vue, x["t"]) if vue else ""
            print(f"    {mmss(x['t'])}-{mmss(x['jusqu_a'])}  {x['de']} % -> {x['a']} %" + (f"   « {what[:90]} »" if what else ""))
    if not vue:
        print("    (avec --vue vue_<projet - final>.txt : la phrase dite à chaque moment)")

def main():
    a = sys.argv[1:]
    val = lambda n: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else None
    vue = read_vue(val("--vue")) if val("--vue") else []
    try:
        age = int(val("--age")) if val("--age") else None
        if age is not None and age <= 0: raise ValueError()
    except ValueError:
        sys.exit("--age demande un nombre de jours strictement positif")
    collected = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if val("--csv"):
        d = val("--duree") or ""
        dur = sum(float(x) * 60 ** i for i, x in enumerate(reversed(d.split(":")))) if re.fullmatch(r"[\d.:]+", d) else 0
        if not dur: sys.exit("--csv demande --duree <secondes ou m:ss> (durée réelle de la vidéo publiée)")
        try:
            curve, info = read_studio_csv(val("--csv"), dur, val("--unite-position"), val("--unite-retention"))
        except (ValueError, OSError) as e:
            sys.exit(f"CSV : {e}")
        source = Path(val("--csv"))
        r = {"title": source.name, "id": "csv", "duration": dur, "curve": curve,
             "curve_units": {"position": "ratio", "audience": "ratio"},
             "curve_source": {"type": "studio_csv", "file": source.name,
                              "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                              "raw_csv": source.read_text(encoding="utf-8-sig"), **info},
             "collected_at": collected, "requested_age": age,
             "periode": "période de l'export Studio, à vérifier dans Studio",
             "analyse": analyse_curve(curve, dur), "csv_info": info, "_vue": vue}
        if val("--id"):
            print(f"  bilan gardé : {keep(val('--id'), {k: v for k, v in r.items() if k != '_vue'})}", file=sys.stderr)
        if "--json" in a: print(json.dumps({k: v for k, v in r.items() if k != "_vue"}, indent=1, ensure_ascii=False))
        else: show_curve(r)
        return
    skip = {val(n) for n in ("--vue", "--csv", "--duree", "--unite-position", "--unite-retention", "--age", "--id")}
    if "--public" in a and age is not None:
        sys.exit("--public fournit un cumul actuel : --age nécessite YouTube Analytics")
    ids = [video_id(x) for x in a if not x.startswith("--") and x not in skip]
    if not ids or None in ids: print(__doc__); sys.exit(1)
    out = []
    for vid in ids:
        r, err = public(vid) if "--public" in a else private(vid, age)
        if err:
            print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
            if "--public" not in a: print("  astuce : --public donne au moins les chiffres publics", file=sys.stderr)
            sys.exit(1)
        if r.get("curve"): r["analyse"] = analyse_curve(r["curve"], r.get("duration"))
        r["requested_age"], r["collected_at"] = age, collected
        r["_vue"] = vue
        out.append(r)
    clean = [{k: v for k, v in r.items() if k != "_vue"} for r in out]
    if val("--id"):
        for c in clean: print(f"  bilan gardé : {keep(val('--id'), c)}", file=sys.stderr)
    if "--json" in a:
        print(json.dumps(clean if len(clean) > 1 else clean[0], indent=1, ensure_ascii=False))
    else:
        for r in out: show(r)


def keep(vid_id, r):
    """A distinct copy per collection instant and requested window, never overwritten.
    The actual video age stays separate from requested_age."""
    sys.path.insert(0, str(HERE.parent.parent / "nouvelle-video" / "scripts"))
    try:
        import repo
        base = repo.root() / "videos" / vid_id
    except (Exception, SystemExit):
        base = Path("videos") / vid_id
    d = base / "bilans"
    d.mkdir(parents=True, exist_ok=True)
    r = dict(r)
    r.setdefault("collected_at", datetime.now(timezone.utc).isoformat(timespec="microseconds"))
    stamp = datetime.fromisoformat(r["collected_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
    window = f"J{r['requested_age']}" if r.get("requested_age") is not None else "cumul"
    stem = f"{stamp.strftime('%Y-%m-%dT%H%M%S.%fZ')}-{window}"
    for version in range(10000):
        p = d / f"{stem}{'-' + str(version) if version else ''}.json"
        try:
            with p.open("x", encoding="utf-8") as f:
                json.dump(r, f, indent=1, ensure_ascii=False)
            return p
        except FileExistsError:
            continue
    raise RuntimeError("trop de bilans au même instant : aucun fichier écrasé")

if __name__ == "__main__":
    main()
