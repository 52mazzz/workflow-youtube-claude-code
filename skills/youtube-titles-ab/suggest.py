#!/usr/bin/env python3
"""suggest.py - what people actually type into YouTube search, in French, for free.

    python3 suggest.py "claude vs chatgpt"
    python3 suggest.py "ia minecraft" "minecraft mais" --expand
    python3 suggest.py "ia crée un jeu" --hl fr --gl FR --json

Reads YouTube's search autocomplete (the list under the search bar) for each seed. With --expand,
each seed is also tried with a-z after it ("ia minecraft a", "ia minecraft b"...), which surfaces
the long tail. Suggestions are scored by their rank in each list and by how many seeds returned
them: a phrase that comes back often and high is a phrase people type.

What it is: real wording, ordered by popularity. What it is not: search volume. Use it to pick
the words of a title, a tag or a description, not to promise traffic.
"""
import json, re, string, sys, time, urllib.parse, urllib.request

URL = "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl={hl}&gl={gl}&q={q}"

def parse(body):
    """Accepts the plain JSON list or the JSONP form YouTube sometimes returns."""
    body = body.strip()
    m = re.match(r"^[\w.]+\((.*)\)\s*;?$", body, re.S)
    if m: body = m.group(1)
    data = json.loads(body)
    items = data[1] if isinstance(data, list) and len(data) > 1 else []
    return [i[0] if isinstance(i, list) else i for i in items if i]

def fetch(q, hl, gl):
    req = urllib.request.Request(URL.format(hl=hl, gl=gl, q=urllib.parse.quote(q)),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return parse(r.read().decode("utf-8", "replace"))

def rank(results):
    """results: {seed: [suggestion, ...]} -> sorted [(suggestion, score, hits)]."""
    score, hits = {}, {}
    for seed, sugg in results.items():
        for pos, s in enumerate(sugg):
            s = s.strip().lower()
            score[s] = score.get(s, 0) + 1 / (pos + 1)
            hits[s] = hits.get(s, 0) + 1
    return sorted(((s, round(v, 2), hits[s]) for s, v in score.items()), key=lambda x: (-x[1], x[0]))

def main():
    a = sys.argv[1:]
    def opt(n, d):
        return a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
    hl, gl = opt("--hl", "fr"), opt("--gl", "FR")
    seeds = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--hl", "--gl"))]
    if not seeds: print(__doc__); sys.exit(1)
    queries = list(seeds)
    if "--expand" in a:
        queries += [f"{s} {c}" for s in seeds for c in string.ascii_lowercase]
    results, errors = {}, []
    for q in queries:
        try:
            results[q] = fetch(q, hl, gl)
        except Exception as e:
            errors.append(f"{q}: {e.__class__.__name__}")
            if len(errors) >= 3 and not results: break  # blocked network: stop early
        time.sleep(0.15)
    ranked = rank(results)
    if "--json" in a:
        print(json.dumps({"seeds": seeds, "hl": hl, "gl": gl, "suggestions":
                          [{"text": s, "score": v, "seeds": h} for s, v, h in ranked], "errors": errors},
                         indent=1, ensure_ascii=False))
        return
    print(f"\n  {len(ranked)} suggestions pour {len(results)} requête(s), hl={hl} gl={gl}\n")
    for s, v, h in ranked[:40]:
        print(f"    {v:5.2f}  {h:2d}x  {s}")
    if errors: print(f"\n  {len(errors)} requête(s) en échec, ex. {errors[0]}")
    print()

if __name__ == "__main__":
    main()
