#!/usr/bin/env python3
"""selection.py - the reference videos that fit THIS video, picked for relevance before their score.

    python selection.py refs.json --sujet "\bpok[eé]mon" --format "\b(make|makes|build|recreat\w*|from scratch|de z[ée]ro)\b" \
        [--exclure "plays?|joue|nuzlocke"] [--par-chaine 2] [--top 10] [--min-views 10000] > refs-sujet.json

refs.json is the --json output of swipe.py (the whole watch: every subject, every format). A huge
multiple on the subject does not make a video a good model: "ChatGPT plays Pokemon" is about an AI
PLAYING, the video being made is about AIs CREATING a game. So the selection ranks by relevance
first, then by multiple:
  1. "sujet+format": the title matches --sujet AND --format (the same thing being made);
  2. "format": same format on another subject (an AI duel creating another game): the structure travels;
  3. "sujet": same subject, other format: kept as SECONDARY inspiration only (shown, marked).
--sujet and --format are regular expressions on the title (case and accents ignored), written by Claude
for the video (the game, the kind of creation). --exclure marks titles of another format that would match
(an AI that "plays", a "nuzlocke"): they can only be secondary. At most --par-chaine videos per channel (default 2), so
the models come from several creators; under 3 channels in the selection, the output says so.

The output keeps the swipe.py structure ("outliers", each with a "pertinence" field), so accroches.py
--refs, check_titles.py --refs and miniature.py --refs read it as is; "secondaires" holds class 3.
"""
import json, re, sys, unicodedata
from pathlib import Path


def fold(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def rx(pattern):
    return re.compile(fold(pattern), re.I) if pattern else None


def select(outliers, sujet, fmt, exclure=None, per_channel=2, top=10, min_views=10000):
    s, f, x = rx(sujet), rx(fmt), rx(exclure)
    classes = {"sujet+format": [], "format": [], "sujet": []}
    for o in outliers:
        t = fold(o.get("title"))
        if (o.get("views") or 0) < min_views:
            continue
        hs, hf = bool(s and s.search(t)), bool(f and f.search(t))
        if x and x.search(t):
            hf = False   # another format (an AI playing, a nuzlocke): at most a secondary inspiration
        key = "sujet+format" if hs and hf else "format" if hf else "sujet" if hs else None
        if key:
            classes[key].append(dict(o, pertinence=key))
    picked, count = [], {}
    def take(rows, limit):
        out = []
        for o in sorted(rows, key=lambda o: -(o.get("multiple") or 0)):
            ch = o.get("channel") or "?"
            if count.get(ch, 0) >= per_channel or len(out) >= limit:
                continue
            count[ch] = count.get(ch, 0) + 1
            out.append(o)
        return out
    picked = take(classes["sujet+format"], top)
    picked += take(classes["format"], top - len(picked))
    secondary = take(classes["sujet"], 5)
    channels = sorted({o.get("channel") or "?" for o in picked})
    notes = []
    if len([o for o in picked if o["pertinence"] == "sujet+format"]) < 3:
        notes.append("moins de 3 références sur le même sujet ET le même format : le format (autres jeux) sert de modèle principal")
    if len(channels) < 3:
        notes.append(f"seulement {len(channels)} chaîne(s) dans la sélection : élargir la collecte (collecte ciblée de youtube-titles-ab)")
    return {"outliers": picked, "secondaires": secondary, "chaines": channels, "notes": notes,
            "criteres": {"sujet": sujet, "format": fmt, "exclure": exclure, "par_chaine": per_channel, "min_views": min_views}}


def main():
    a = sys.argv[1:]
    val = lambda n, d=None: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
    files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    if not files or not Path(files[0]).exists() or not (val("--sujet") or val("--format")):
        print(__doc__); sys.exit(1)
    data = json.loads(Path(files[0]).read_text(encoding="utf-8-sig"))
    res = select(data.get("outliers", []), val("--sujet"), val("--format"), val("--exclure"),
                 int(val("--par-chaine", 2)), int(val("--top", 10)), int(val("--min-views", 10000)))
    res["collected_at"] = data.get("collected_at")
    if "--texte" in a:
        for o in res["outliers"]:
            print(f"  {o['pertinence']:<13} {o['multiple']:7.1f}x {o['views']:>9,}  {o['channel'][:20]:<20} {o['title'][:70]}")
        for o in res["secondaires"]:
            print(f"  (secondaire) {o['multiple']:7.1f}x {o['views']:>9,}  {o['channel'][:20]:<20} {o['title'][:70]}")
        for n in res["notes"]:
            print(f"  ! {n}")
        return
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
