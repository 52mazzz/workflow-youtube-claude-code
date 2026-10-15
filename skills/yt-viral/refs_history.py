#!/usr/bin/env python3
"""refs_history.py - keep every reference collection, and read what holds over time.

    python3 refs_history.py save refs.json --slug minecraft-shaders
    python3 refs_history.py show                 # last 8 weeks
    python3 refs_history.py show --weeks 12 --json

`save` copies a `swipe.py --json` output to the history folder as <date>-<slug>.json.
`show` reads the collections of the last N weeks and prints:
  - the channels already collected, when, and how their median moved (no need to collect a
    channel again if it was done a few days ago);
  - the title formulas that came back among outliers in several collections (a structure that
    holds across weeks is stronger evidence than one good week);
  - the strongest outliers seen so far, with the date they were first seen.

History folder: ~/.claude/youtube/references/ (or $YT_REFS_DIR). `python setup.py --save` copies it
back into the repo so every machine gets it.
"""
import json, os, re, sys
from datetime import datetime, timedelta
from pathlib import Path

def base():
    return Path(os.environ.get("YT_REFS_DIR") or Path.home() / ".claude" / "youtube" / "references")

def opt(a, name, default=None):
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default

def load(path):
    try: return json.load(open(path, encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError): return None

def save(a):
    src = next((x for x in a if not x.startswith("--") and x != opt(a, "--slug")), None)
    if not src or not os.path.exists(src): sys.exit("usage: refs_history.py save refs.json --slug sujet")
    data = load(src)
    if not isinstance(data, dict) or "outliers" not in data:
        sys.exit(f"{src} n'est pas une sortie `swipe.py --json`")
    slug = re.sub(r"[^\w-]+", "-", (opt(a, "--slug") or "veille").lower()).strip("-") or "veille"
    date = data.get("collected_at") or datetime.now().strftime("%Y-%m-%d")
    d = base(); d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{date}-{slug}.json"
    dest.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {dest} ({len(data['outliers'])} outliers, {len(data.get('channels', []))} channels)")

def show(a):
    weeks = float(opt(a, "--weeks", 8))
    today = os.environ.get("SWIPE_NOW")
    today = datetime.strptime(today, "%Y-%m-%d") if today else datetime.now()
    since = today - timedelta(weeks=weeks)
    files = sorted(base().glob("*.json")) if base().exists() else []
    cols = []
    for f in files:
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.json$", f.name)
        if not m: continue
        when = datetime.strptime(m.group(1), "%Y-%m-%d")
        if when < since: continue
        data = load(f)
        if isinstance(data, dict): cols.append((m.group(1), m.group(2), data))
    if not cols:
        msg = f"aucune collection dans {base()} sur les {weeks:g} dernières semaines"
        print(json.dumps({"collections": [], "message": msg}) if "--json" in a else f"\n  {msg}\n")
        return

    channels = {}
    for date, slug, d in cols:
        for c in d.get("channels", []):
            key = c.get("channel_id") or c.get("channel")
            channels.setdefault(key, {"channel": c.get("channel"), "handle": c.get("handle", ""), "seen": []})
            channels[key]["seen"].append((date, c.get("median")))
    for c in channels.values():
        c["seen"].sort()
        c["last"] = c["seen"][-1][0]
        c["days_since"] = (today - datetime.strptime(c["last"], "%Y-%m-%d")).days

    formulas = {}
    for date, slug, d in cols:
        for f in {o.get("formula") for o in d.get("outliers", []) if o.get("formula") not in (None, "Unclassified")}:
            formulas.setdefault(f, set()).add(date)
    lasting = sorted(((f, sorted(ds)) for f, ds in formulas.items() if len(ds) >= 2), key=lambda x: -len(x[1]))

    best = {}
    for date, slug, d in cols:
        for o in d.get("outliers", []):
            key = o.get("id") or o.get("url") or o.get("title")
            if key not in best:
                best[key] = dict(o, first_seen=date, collections=1)
            else:
                first, n = best[key]["first_seen"], best[key]["collections"] + 1
                best[key] = dict(o, first_seen=first, collections=n)  # latest views win
    top = sorted(best.values(), key=lambda o: -(o.get("multiple") or 0))[:15]

    if "--json" in a:
        print(json.dumps({"collections": [{"date": d, "slug": s, "outliers": len(x.get("outliers", []))} for d, s, x in cols],
                          "channels": sorted(channels.values(), key=lambda c: c["days_since"]),
                          "lasting_formulas": [{"formula": f, "dates": ds} for f, ds in lasting],
                          "top_outliers": top}, indent=1, ensure_ascii=False))
        return
    print(f"\n  {len(cols)} collection(s) depuis le {since:%Y-%m-%d} : " + ", ".join(f"{d} {s}" for d, s, _ in cols))
    print("\n  chaînes déjà collectées (dernière fois, médiane)")
    for c in sorted(channels.values(), key=lambda c: c["days_since"]):
        meds = " -> ".join(f"{m:,}" for _, m in c["seen"] if m is not None)
        fresh = "à jour" if c["days_since"] < 7 else "à recollecter"
        print(f"    {c['channel'][:28]:<28} {c['last']}  il y a {c['days_since']:>3} j  ({fresh})  médiane {meds}")
    print("\n  formules qui reviennent parmi les outliers dans plusieurs collections")
    for f, ds in lasting: print(f"    {len(ds)}x  {f}  ({', '.join(ds)})")
    if not lasting: print("    aucune pour l'instant : une seule semaine de recul ne prouve pas qu'une structure tient")
    print("\n  meilleurs outliers vus sur la période")
    for o in top:
        print(f"    {o.get('multiple', 0):5.2f}x  {o.get('channel', '')[:20]:<20} {o.get('title', '')[:58]}   (vu le {o['first_seen']}, {o['collections']} fois)")
    print()

def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("save", "show"): print(__doc__); sys.exit(1)
    (save if a[0] == "save" else show)(a[1:])

if __name__ == "__main__":
    main()
