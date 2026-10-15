#!/usr/bin/env python3
"""swipe.py - rank collected videos by how far each beat its OWN channel, then name the formula.

    python3 swipe.py collected.json
    python3 swipe.py veille/*.json --min 2.0 --no-shorts --max-age 180
    python3 swipe.py veille/*.json --exclude @letsar555 --json > refs.json
    python3 swipe.py veille/*.json --thumbs miniatures/ --top 8

Input: one or more files. Each file is either a list you collected - one object per video:

    [{"channel":"Some Channel","title":"...","views":412000,"url":"...","duration":613,
      "upload_date":"20260915"}, ...]

or the raw output of `yt-dlp --flat-playlist -J` (a channel page, a channel /videos tab or a
`ytsearchN:` query), read as is: no conversion step. Videos seen in several files are counted once.
Collect with `--extractor-args "youtubetab:approximate_date"` and yt-dlp adds an approximate upload
date to every entry ("3 weeks ago"), which is what --max-age and the views-per-day column use.

Raw view counts rank channel size, not ideas. A 400k video on a 2M-subscriber channel is a normal
Tuesday; a 400k video on a channel whose median is 30k is the thing worth studying. So every video
is scored as a MULTIPLE OF ITS OWN CHANNEL'S MEDIAN, which needs at least four videos per channel
to mean anything - the tool says so rather than quietly ranking on noise. Videos with no view
count (premieres, lives not started) are left out instead of counting as zero.

THE MEDIAN is computed on the channel's videos that are old enough to have finished most of their run
(--median-min-age, default 14 days; undated videos are excluded from both median and ranking): videos a few
days old still have few views and would drag the median down, making every older video look like an
outlier. At least 4 such videos are needed, else the channel is "thin". Each row gives the sample size
(median_n) and "fragile": true when it is under 8 - a multiple off 4 to 7 videos is a hint, not a fact.

Options:
    --min X          only show outliers at X times the channel median or better (default 1.5)
    --no-shorts      drop Shorts (/shorts/ URL or under 60 s); keep long and short formats apart
    --exclude NAME   leave a channel out of the ranking (repeatable; name, @handle or channel
                     id): the user's own channel, for instance, whose few videos make a
                     meaningless median
    --max-age DAYS   only show outliers published in the last DAYS days (the median still uses
                     dated video). Undated videos are excluded and counted in dropped_unknown_date;
                     collect dates before ranking to include them
    --median-min-age DAYS  videos younger than DAYS days are left out of the median (default 14)
    --min-age DAYS   hide outliers younger than DAYS days (default 0): a video a few days old has
                     not finished its run, and its multiple says little either way
    --min-views N    an outlier needs at least N views (default 0). A multiple on a tiny channel is noise:
                     4,000 views at 249x its median is not an idea that travelled. Those below the floor
                     but at 10x or more are kept apart as "weak signals" (a small channel catching on),
                     never mixed into the ranking
    --top N          how many outliers to print, date or download (default 25)
    --thumbs DIR     download the thumbnails of the top N outliers into DIR, to look at them
    --refs-selection FILE --thumbs DIR  download an existing selection in order, without reranking
    --json           machine-readable output: outliers (with age, views per day, thumbnail URL),
                     a per-channel summary, the weak signals, the FLOPS (videos at 0.5x their channel's
                     median or worse, 5 to 180 days old, on channels with 8+ videos: what does NOT
                     work, as counter-examples), the thin channels worth a second pass
                     (thin_candidates: url and best views, for veille.py) and the collection date

The formula comes from skills/yt-script/hooks.json, matched against the TITLE (English and French
patterns). It is a judgement about the words on screen, not a claim about why the video worked.
"""
import json, os, re, shutil, statistics, subprocess, sys, unicodedata
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
FORMULAS = json.load(open(os.path.join(HERE, "..", "yt-script", "hooks.json"), encoding="utf-8"))["hooks"]

def classify(title):
    scored = []
    for f in FORMULAS:
        n = sum(1 for p in f["match"] if re.search(p, title, re.I))
        if n: scored.append((n, f["name"]))
    scored.sort(reverse=True)
    return scored[0][1] if scored else "Unclassified"

def video_id(v):
    vid = v.get("id") or ""
    if re.fullmatch(r"[\w-]{11}", vid): return vid
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/live/)([\w-]{11})", v.get("url") or v.get("webpage_url") or "")
    return m.group(1) if m else ""

def walk(node, parent):
    """Yield video dicts from a hand-made list or yt-dlp JSON (nested tabs included)."""
    if isinstance(node, list):
        for x in node: yield from walk(x, parent)
        return
    if not isinstance(node, dict): return
    if "entries" in node or "videos" in node:
        here = {"channel": node.get("channel") or node.get("uploader") or parent.get("channel"),
                "channel_id": node.get("channel_id") or parent.get("channel_id"),
                "uploader_id": node.get("uploader_id") or parent.get("uploader_id")}
        # a search result page is not a channel: its entries carry their own channel
        if str(node.get("extractor_key", "")).lower().startswith("youtubesearch") or \
           str(node.get("id", "")).startswith("ytsearch"):
            here = {}
        yield from walk(node.get("entries") or node.get("videos") or [], here)
        return
    v = dict(node)
    v["channel"] = v.get("channel") or v.get("uploader") or parent.get("channel")
    v["channel_id"] = v.get("channel_id") or parent.get("channel_id")
    v["uploader_id"] = v.get("uploader_id") or parent.get("uploader_id")
    yield v

def views_of(v):
    x = v.get("views", v.get("view_count"))
    try: return None if x is None else float(x)
    except (TypeError, ValueError): return None

def is_short(v):
    url = v.get("url") or v.get("webpage_url") or ""
    d = v.get("duration")
    return "/shorts/" in url or (isinstance(d, (int, float)) and 0 < d < 60)

def is_upcoming(v):
    return v.get("live_status") in ("is_upcoming", "is_live")

def published(v):
    """Upload time as an aware datetime, from timestamp or upload_date, else None."""
    ts = v.get("timestamp") or v.get("release_timestamp")
    if isinstance(ts, (int, float)) and ts > 0:
        return datetime.fromtimestamp(ts, timezone.utc)
    d = str(v.get("upload_date") or "")
    if re.fullmatch(r"\d{8}", d):
        return datetime.strptime(d, "%Y%m%d").replace(tzinfo=timezone.utc)
    return None

def now():
    fixed = os.environ.get("SWIPE_NOW")  # tests pin the clock
    if fixed: return datetime.strptime(fixed, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def norm(s): return unicodedata.normalize("NFC", (s or "").strip()).lower().lstrip("@")

def thumb_url(v, vid):
    th = v.get("thumbnails") or []
    if th: return sorted(th, key=lambda t: (t.get("width") or 0))[-1].get("url", "")
    return v.get("thumbnail") or (f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "")

def download(url, path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r, open(path, "wb") as f: f.write(r.read())
        return True
    except Exception as e:
        print(f"    thumbnail failed ({e.__class__.__name__}): {url}", file=sys.stderr)
        return False

def fetch_dates(urls):
    """Ask yt-dlp for the exact upload date of a few videos. Returns {id: 'YYYYMMDD'}."""
    if os.environ.get("SWIPE_OFFLINE"): return {}  # tests: never touch the network
    exe = shutil.which("yt-dlp")
    cmd = [exe] if exe else [sys.executable, "-m", "yt_dlp"]
    try:
        out = subprocess.run(cmd + ["--skip-download", "--no-warnings", "--ignore-errors",
                                    "--print", "%(id)s %(upload_date)s", *urls],
                             capture_output=True, text=True, encoding="utf-8", timeout=30 + 10 * len(urls))
    except Exception as e:
        print(f"  dates not fetched ({e.__class__.__name__}): install yt-dlp or collect with "
              "--extractor-args \"youtubetab:approximate_date\"", file=sys.stderr)
        return {}
    got = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and re.fullmatch(r"\d{8}", parts[1]): got[parts[0]] = parts[1]
    return got

def opt(a, name, default=None, many=False):
    vals = [a[i + 1] for i, x in enumerate(a) if x == name and i + 1 < len(a)]
    return vals if many else (vals[-1] if vals else default)

def main():
    a = sys.argv[1:]
    if "--refs-selection" in a:
        source = opt(a, "--refs-selection")
        thumbs = opt(a, "--thumbs")
        if not source or not thumbs: sys.exit("--refs-selection demande un fichier et --thumbs DIR")
        try:
            with open(source, encoding="utf-8-sig") as f: selection = json.load(f)
            rows = selection["outliers"]
            if not rows: raise ValueError("sélection vide")
        except (OSError, ValueError, KeyError, TypeError) as e:
            sys.exit(f"sélection inutilisable : {e}")
        failures = download_thumbnails(rows[:int(opt(a, '--top', len(rows)))], thumbs)
        selection["thumbnail_selection_source"] = source
        if "--json" in a: print(json.dumps(selection, ensure_ascii=False, indent=1))
        else: print(f"{len(rows)} références sélectionnées, ordre conservé ; {failures} échec(s) de miniature")
        sys.exit(1 if failures else 0)
    flags_with_value = {"--min", "--exclude", "--top", "--thumbs", "--max-age", "--min-age", "--min-views", "--median-min-age"}
    as_json, no_shorts = "--json" in a, "--no-shorts" in a
    lo = float(opt(a, "--min", 1.5))
    top = int(opt(a, "--top", 25))
    thumbs = opt(a, "--thumbs")
    max_age = opt(a, "--max-age"); max_age = float(max_age) if max_age else None
    min_age = float(opt(a, "--min-age", 0))
    min_views = float(opt(a, "--min-views", 0))
    med_min_age = float(opt(a, "--median-min-age", 14))
    clock = now()
    excluded = {norm(x) for x in opt(a, "--exclude", many=True)}
    files, skip = [], False
    for x in a:
        if skip: skip = False; continue
        if x in flags_with_value: skip = True; continue
        if not x.startswith("--"): files.append(x)
    missing = [f for f in files if not os.path.exists(f)]
    if not files or missing:
        print(__doc__)
        if missing: print("  not found: " + ", ".join(missing))
        sys.exit(1)

    seen, rows, empty, no_views, shorts = set(), [], [], 0, 0
    for f in files:
        try: data = json.load(open(f, encoding="utf-8"))
        except (ValueError, UnicodeDecodeError): data = None
        found = list(walk(data, {})) if data else []
        if not found: empty.append(os.path.basename(f)); continue
        for v in found:
            vid = video_id(v)
            key = vid or (v.get("url") or "") or (v.get("title") or "")
            if key in seen: continue
            seen.add(key)
            if views_of(v) is None or is_upcoming(v): no_views += 1; continue
            if no_shorts and is_short(v): shorts += 1; continue
            if excluded & {norm(v.get(k)) for k in ("channel", "channel_id", "uploader_id")}: continue
            v["_id"] = vid
            rows.append(v)

    by, names = {}, {}
    for r in rows:
        k = r.get("channel_id") or norm(r.get("channel")) or "?"
        by.setdefault(k, []).append(r)
        names.setdefault(k, r.get("channel") or k)
    out, thin, thin_cand, channels, flops = [], [], [], [], []
    def old_enough(v):
        p = published(v)
        return p is not None and (clock - p).days >= med_min_age
    unknown = sum(published(v) is None for v in rows)
    for k, vids in by.items():
        base = [v for v in vids if old_enough(v)]   # the videos the median is computed on
        if len(base) < 4:
            thin.append((names[k], len(base)))
            best = max(vids, key=views_of)
            cid, handle = best.get("channel_id") or "", best.get("uploader_id") or ""
            url = best.get("channel_url") or best.get("uploader_url") or (
                f"https://www.youtube.com/channel/{cid}" if cid else
                f"https://www.youtube.com/{handle}" if handle.startswith("@") else "")
            thin_cand.append({"channel": names[k], "channel_id": cid, "handle": handle, "url": url,
                              "videos": len(vids), "median_usable": len(base),
                              "undated_videos": sum(published(v) is None for v in vids),
                              "best_views": int(views_of(best)), "best_title": best.get("title", "")})
            continue
        med = statistics.median([views_of(v) for v in base])
        n, fragile = len(base), len(base) < 8
        channels.append({"channel": names[k], "channel_id": vids[0].get("channel_id") or "",
                         "handle": vids[0].get("uploader_id") or "", "videos": len(vids), "median": int(med),
                         "median_n": n, "fragile": fragile,
                         "dated_videos": sum(published(v) is not None for v in vids),
                         "undated_videos": sum(published(v) is None for v in vids)})
        for v in vids:
            if published(v) is None: continue
            m = views_of(v) / med if med else 0
            if n >= 8 and med and m <= 0.5:
                pub = published(v)
                flops.append({"channel": names[k], "title": v.get("title", ""), "views": int(views_of(v)), "median": int(med),
                              "multiple": round(m, 2), "formula": classify(v.get("title", "")),
                              "url": v.get("webpage_url") or v.get("url") or "", "published": pub})
            vid = v["_id"]
            pub = published(v)
            out.append({"channel": names[k], "title": v.get("title", ""), "views": int(views_of(v)),
                        "median": int(med), "median_n": n, "fragile": fragile, "multiple": round(m, 2),
                        "formula": classify(v.get("title", "")),
                        "url": v.get("webpage_url") or v.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else ""),
                        "id": vid, "duration": v.get("duration"), "thumbnail": thumb_url(v, vid),
                        "published": pub.strftime("%Y-%m-%d") if pub else None})
    out = [r for r in out if r["multiple"] >= lo]
    weak = [r for r in out if r["views"] < min_views and r["multiple"] >= 10]
    out = [r for r in out if r["views"] >= min_views]
    out.sort(key=lambda r: -r["multiple"])
    weak.sort(key=lambda r: -r["multiple"])
    thin_cand.sort(key=lambda c: -c["best_views"])

    today = now()
    for r in out:
        if r["published"]:
            age = max(1, (today - datetime.strptime(r["published"], "%Y-%m-%d").replace(tzinfo=timezone.utc)).days)
            r["age_days"], r["views_per_day"] = age, int(r["views"] / age)
        else:
            r["age_days"] = r["views_per_day"] = None
    kept = []
    for f in flops:
        age = (today - f.pop("published")).days if f.get("published") else None
        if age is not None and 5 <= age <= 180:
            kept.append(dict(f, age_days=age))
    flops = sorted(kept, key=lambda f: f["multiple"])[:20]
    too_old = sum(1 for r in out if max_age is not None and r["age_days"] and r["age_days"] > max_age)
    too_young = sum(1 for r in out if min_age and r["age_days"] and r["age_days"] < min_age)
    out = [r for r in out if not (max_age is not None and r["age_days"] and r["age_days"] > max_age)
           and not (min_age and r["age_days"] and r["age_days"] < min_age)]

    if thumbs:
        download_thumbnails(out[:top], thumbs)

    if as_json:
        print(json.dumps({"collected_at": today.strftime("%Y-%m-%d"), "min_multiple": lo,
                          "min_views": int(min_views), "outliers": out, "weak_signals": weak[:15], "flops": flops,
                          "channels": channels, "skipped_thin_channels": thin, "thin_candidates": thin_cand,
                          "empty_files": empty, "dropped_no_views": no_views, "dropped_shorts": shorts,
                          "dropped_unknown_date": unknown, "usable_dated_videos": len(rows) - unknown,
                          "dropped_too_old": too_old, "dropped_too_young": too_young},
                         indent=1, ensure_ascii=False))
        return
    print(f"\n  {len(rows)} videos across {len(by)} channels, outliers at {lo}x or better\n")
    for r in out[:top]:
        age = f"{r['age_days']}d, {r['views_per_day']:,}/day" if r["age_days"] else "date ?"
        print(f"    {r['multiple']:5.2f}x  {r['views']:>9,}  vs {r['median']:>9,} median of {r['median_n']}"
              + (" (fragile)" if r["fragile"] else "") + f"   {r['channel'][:22]:<22} {r['title'][:60]}")
        print(f"            {r['formula']}   {age}   {r['url']}")
    if not out: print("    nothing cleared the threshold - collect more per channel or lower --min")
    if thin:
        print(f"\n  skipped {len(thin)} channel(s) with under 4 videos at least {med_min_age:g} days old - a median off one or")
        print( "  two videos is not a median: " + ", ".join(f"{c} ({n})" for c, n in thin[:6]))
    if empty: print("\n  empty or unreadable file(s), skipped: " + ", ".join(empty))
    if weak:
        print(f"\n  weak signals (under {min_views:,.0f} views, at 10x or more on a small channel), not ranked:")
        for r in weak[:6]:
            print(f"    {r['multiple']:6.1f}x  {r['views']:>7,}  {r['channel'][:22]:<22} {r['title'][:60]}")
    if no_views: print(f"  {no_views} video(s) without a view count left out (premiere, live)")
    if unknown: print(f"  {unknown} vidéo(s) sans date exclue(s) des médianes et du classement ; {len(rows) - unknown} vidéos datées utilisables")
    if shorts: print(f"  {shorts} Short(s) left out (--no-shorts)")
    if too_old: print(f"  {too_old} outlier(s) older than {max_age:g} days left out (--max-age)")
    if too_young: print(f"  {too_young} outlier(s) younger than {min_age:g} days left out (--min-age)")
    counts = {}
    for r in out: counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    if counts:
        print("\n  formulas among the outliers")
        for f, n in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {n:2d}x  {f}")
    print()

def download_thumbnails(rows, folder):
    """Download the supplied rows in their existing order, without another ranking."""
    os.makedirs(folder, exist_ok=True)
    failures = 0
    for i, r in enumerate(rows, 1):
        url = thumb_url(r, video_id(r))
        safe = re.sub(r"[^\w-]+", "_", r.get("channel") or "reference")[:30]
        vid = video_id(r) or str(i)
        p = os.path.join(folder, f"{i:02d}-{safe}-{vid}.jpg")
        if url and download(url, p): r["thumbnail_file"] = p
        else: failures += 1
    return failures

if __name__ == "__main__":
    main()
