#!/usr/bin/env python3
"""comments.py - read what viewers of the reference videos liked and what they ask for next.

    python3 comments.py URL [URL ...]                # 150 top comments per video, via yt-dlp
    python3 comments.py URL --max 300 --json
    python3 comments.py --from-file video.info.json  # an info.json already saved with comments

For each video: the most-liked comments (what landed), the comments that ask for something
("fais-le sur Roblox", "partie 2", "try it with Gemini") sorted by likes, and the games, AIs and
names viewers mention most. Requests with many likes are idea material; they are not proof of
demand on their own (a comment section is the most engaged 1% of viewers), so say that when you
use them.

Public data only, no account. Top-level comments only, replies are skipped.
"""
import json, re, shutil, subprocess, sys
from collections import Counter

REQUEST = re.compile(
    r"\b(fais|faites|refais|refaites|tu (peux|pourrais|devrais)|vous (pouvez|pourriez|devriez)|et si|"
    r"la prochaine|prochaine vid[ée]o|essaie|essayez|teste|testez|partie 2|part 2|la suite|une suite|"
    r"j'aimerais|on veut|do (it|this|one)|try|next (video|time)|make (one|a|it)|can you|could you|"
    r"please do|pls|we need)\b", re.I)
KNOWN = ["Minecraft", "Roblox", "Fortnite", "GTA", "Zelda", "Pokémon", "Pokemon", "Mario", "Terraria",
         "Among Us", "Geometry Dash", "Clash", "Brawl Stars", "Valorant", "Rocket League", "Doom", "Tetris",
         "Snake", "Flappy", "Claude", "ChatGPT", "GPT", "Gemini", "Grok", "DeepSeek", "Copilot", "Mistral",
         "Llama", "Midjourney", "Sora", "Veo", "Suno", "Cursor"]
STOPCAPS = {"Je", "J'ai", "Il", "Elle", "On", "Le", "La", "Les", "Un", "Une", "Et", "Mais", "Ce", "Cette",
            "C'est", "Moi", "Toi", "Vous", "Tu", "Si", "Bravo", "Merci", "Trop", "Très", "Super", "Ah",
            "Oh", "Lol", "Mdr", "Ptdr", "The", "I", "It", "This", "That", "You", "And", "But", "What",
            "Wow", "Bro", "Omg", "Ok", "Oui", "Non", "Pas", "En", "De", "Du", "Des", "Ça", "Ca", "Quand"}

def fetch(url, n):
    exe = shutil.which("yt-dlp")
    cmd = ([exe] if exe else [sys.executable, "-m", "yt_dlp"]) + [
        "--skip-download", "--no-warnings", "--write-comments", "-j",
        "--extractor-args", f"youtube:max_comments={n},{n},0,0;comment_sort=top", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
    except Exception as e:
        return None, f"{e.__class__.__name__}: {e}"
    line = next((l for l in r.stdout.splitlines() if l.startswith("{")), None)
    if not line: return None, (r.stderr.strip().splitlines() or ["no output"])[-1]
    return json.loads(line), None

def analyse(info, top=10):
    cs = [c for c in (info.get("comments") or []) if c.get("parent", "root") == "root" and c.get("text")]
    likes = lambda c: c.get("like_count") or 0
    best = sorted(cs, key=likes, reverse=True)[:top]
    asks = sorted((c for c in cs if REQUEST.search(c["text"])), key=likes, reverse=True)[:top]
    mentions = Counter()
    for c in cs:
        t = c["text"]
        for k in KNOWN:
            if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", t, re.I): mentions[k] += 1
        for w in set(re.findall(r"(?<![\w'])([A-ZÀ-Ý][\w'’-]{2,})", t)):
            if w not in STOPCAPS and w not in KNOWN and not w.isupper(): mentions[w] += 1
    short = lambda c: {"likes": likes(c), "text": re.sub(r"\s+", " ", c["text"]).strip()[:220]}
    return {"title": info.get("title"), "channel": info.get("channel"), "url": info.get("webpage_url"),
            "comments_read": len(cs), "top": [short(c) for c in best], "requests": [short(c) for c in asks],
            "mentions": [{"name": k, "count": n} for k, n in mentions.most_common(12) if n >= 2]}

def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    n = int(a[a.index("--max") + 1]) if "--max" in a else 150
    infos, errors = [], []
    if "--from-file" in a:
        for p in a[a.index("--from-file") + 1:]:
            if p.startswith("--"): break
            infos.append(json.load(open(p, encoding="utf-8")))
    else:
        urls = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--max")]
        if not urls: print(__doc__); sys.exit(1)
        for u in urls:
            info, err = fetch(u, n)
            if info: infos.append(info)
            else: errors.append({"url": u, "error": err})
    res = [analyse(i) for i in infos]
    if as_json:
        print(json.dumps({"videos": res, "errors": errors}, indent=1, ensure_ascii=False)); return
    for r in res:
        print(f"\n  {r['title']}  [{r['channel']}]  {r['comments_read']} commentaires lus")
        print("    les plus aimés")
        for c in r["top"][:5]: print(f"      {c['likes']:>6}  {c['text'][:110]}")
        print("    demandes")
        for c in r["requests"]: print(f"      {c['likes']:>6}  {c['text'][:110]}")
        if not r["requests"]: print("      aucune")
        if r["mentions"]: print("    cités : " + ", ".join(f"{m['name']} ({m['count']})" for m in r["mentions"]))
    for e in errors: print(f"\n  ! {e['url']} : {e['error']}")
    print()

if __name__ == "__main__":
    main()
