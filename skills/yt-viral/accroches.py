#!/usr/bin/env python3
"""accroches.py - how the best reference videos open: their first 30 seconds, measured.

    python accroches.py URL1 URL2 URL3 [--secondes 30] [--json]
    python accroches.py --refs refs.json --top 5            # the 5 best outliers of the watch

For each video, from its subtitles (French first, else English; manual or automatic) fetched with
yt-dlp (public, no download of the video):
  - the transcript of the first N seconds, with timestamps (to read, not to copy);
  - words spoken in the first 15 s (pace);
  - when the MISSION / PROMISE is first said ("today", "aujourd'hui", "je vais", "I'm going to",
    "in this video", "challenge", "défi", "from scratch", "de zéro"...): how fast the viewer knows
    what they will get;
  - when the first NUMBER is said (a constraint, a stake: "60 minutes", "1 prompt");
  - early asks (subscribe, like) in the first 30 s, and greeting intros ("hey guys", "salut",
    "welcome back"): the classic leaks at 0:30;
Then the medians over all videos. Method from youtube-seo-skills (competitor hook extraction,
deeployCO, MIT). It measures words, not images: say so when presenting it.
"""
import json, os, re, shlex, shutil, statistics, subprocess, sys, tempfile
from pathlib import Path

PROMISE = re.compile(r"\b(today|aujourd'?hui|i'?m going to|i am going to|je vais|on va|in this video|dans cette vid[ée]o|"
                     r"challenge|d[ée]fi|from scratch|de z[ée]ro|let'?s see|on va voir|who wins|qui gagne|"
                     r"(?:i |we )?want to (?:make|build|create)|voyons (?:lequel|laquelle|si|qui)|"
                     r"je veux (?:faire|cr[ée]er|fabriquer)|j'ai demand[ée])\b", re.I)
NUMBER = re.compile(r"\b(\d+|one|two|three|ten|hundred|un|une|deux|trois|dix|cent)\b\s+\w+", re.I)
ASK = re.compile(r"\b(subscrib\w*|abonne\w*|like the video|laisse[rz]? un like|lâche[rz]? un like|hit the bell|cloche)\b", re.I)
GREET = re.compile(r"\b(hey guys|hi guys|what'?s up guys|welcome back|salut (?:à tous|tout le monde|les gars)|bienvenue)\b", re.I)


def ytdlp():
    if os.environ.get("YTDLP"):
        return shlex.split(os.environ["YTDLP"])
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def ts(s):
    h, m, rest = ("0:" + s if s.count(":") == 1 else s).split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))


def parse_vtt(text):
    """[(start_seconds, text)], with the rolling duplicates of automatic captions removed."""
    cues, seen = [], ""
    for block in re.split(r"\n\s*\n", text):
        m = re.search(r"(\d+:\d{2}(?::\d{2})?[.,]\d{3})\s+-->", block)
        if not m:
            continue
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in block.splitlines()[block.splitlines().index(
            next(l for l in block.splitlines() if "-->" in l)) + 1:]]
        txt = " ".join(l for l in lines if l)
        if not txt:
            continue
        new = txt[len(seen):].strip() if txt.startswith(seen) and seen else txt
        if new and new != seen and not seen.endswith(new):
            cues.append((ts(m.group(1)), new))
        seen = txt
    return cues


def fetch_subs(url, folder):
    # Two passes, never an automatic translation: asking for "fr" on an English video makes YouTube
    # translate on the fly, which answers 429 and makes yt-dlp drop the whole video, English included.
    # 1. subtitles written by the channel (fr, en); 2. automatic captions in the video's own language.
    base = ytdlp() + ["--skip-download", "--no-warnings", "--sub-format", "vtt",
                      "-o", str(Path(folder) / "%(id)s.%(ext)s")]
    for opts in (["--write-subs", "--sub-langs", "fr,en"], ["--write-auto-subs", "--sub-langs", ".*-orig"]):
        try:
            subprocess.run(base + opts + [url], capture_output=True, text=True, encoding="utf-8", timeout=120)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if any(Path(folder).glob("*.vtt")):
            break
    # French first, then English; a plain language file before an "-orig" automatic one
    files = sorted(Path(folder).glob("*.vtt"), key=lambda p: (0 if ".fr" in p.name else 1, "orig" in p.name, p.name))
    return files[0] if files else None


def analyse(cues, secs=30):
    head = [(t, x) for t, x in cues if t < secs]
    first = lambda rx: next((round(t, 1) for t, x in head if rx.search(x)), None)
    words15 = sum(len(x.split()) for t, x in head if t < 15)
    promise = first(PROMISE)
    return {"mots_15s": words15, "promesse_a": promise,
            "promesse_statut": "détectée" if promise is not None else "promesse non détectée, à vérifier",
            "premier_nombre_a": first(NUMBER),
            "demande_avant_30s": first(ASK), "salutation_a": first(GREET),
            "transcription": [f"{int(t) // 60}:{int(t) % 60:02d}  {x}" for t, x in head]}


def urls_from_refs(path, top):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [o["url"] for o in data.get("outliers", [])[:top] if o.get("url")]


def main():
    a = sys.argv[1:]
    val = lambda n, d=None: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else d
    secs = float(val("--secondes", 30))
    skip = {val(n) for n in ("--secondes", "--refs", "--top")}
    urls = [x for x in a if not x.startswith("--") and x not in skip]
    if val("--refs"):
        urls += urls_from_refs(val("--refs"), int(val("--top", 5)))
    if not urls:
        print(__doc__); sys.exit(1)
    res = []
    for u in urls:
        with tempfile.TemporaryDirectory() as tmp:
            f = fetch_subs(u, tmp)
            if not f:
                res.append({"url": u, "erreur": "pas de sous-titres récupérables (yt-dlp bloqué ou vidéo sans sous-titres)"}); continue
            r = dict(analyse(parse_vtt(f.read_text(encoding="utf-8", errors="replace")), secs), url=u, sous_titres=f.name)
            res.append(r)
    ok = [r for r in res if not r.get("erreur")]
    med = lambda k: statistics.median([r[k] for r in ok if r.get(k) is not None]) if any(r.get(k) is not None for r in ok) else None
    summary = {"videos": len(ok), "mots_15s_median": med("mots_15s"), "promesse_median_s": med("promesse_a"),
               "promesses_detectees": sum(r["promesse_a"] is not None for r in ok),
               "promesses_a_verifier": sum(r["promesse_a"] is None for r in ok),
               "nombre_median_s": med("premier_nombre_a"), "demandes_avant_30s": sum(1 for r in ok if r.get("demande_avant_30s") is not None),
               "salutations": sum(1 for r in ok if r.get("salutation_a") is not None)}
    if "--json" in a:
        print(json.dumps({"videos": res, "resume": summary}, indent=1, ensure_ascii=False)); return
    for r in res:
        print(f"\n  {r['url']}")
        if r.get("erreur"):
            print(f"    {r['erreur']}"); continue
        fmt = lambda v: f"{v} s" if v is not None else "non détecté, à vérifier"
        promise_text = fmt(r['promesse_a']) if r['promesse_a'] is not None else r['promesse_statut']
        print(f"    {r['mots_15s']} mots en 15 s ; mission/promesse : {promise_text} ; premier chiffre à {fmt(r['premier_nombre_a'])}"
              + (f" ; demande d'abonnement à {r['demande_avant_30s']} s" if r.get("demande_avant_30s") is not None else "")
              + (f" ; salutation à {r['salutation_a']} s" if r.get("salutation_a") is not None else ""))
        for line in r["transcription"]:
            print(f"      {line}")
    print(f"\n  sur {summary['videos']} vidéo(s) : {summary['mots_15s_median']} mots en 15 s (médiane), promesse à "
          f"{summary['promesse_median_s']} s, premier chiffre à {summary['nombre_median_s']} s ; {summary['demandes_avant_30s']} "
          f"demande(s) d'abonnement et {summary['salutations']} salutation(s) avant 30 s.")
    print(f"  Promesse : médiane sur {summary['promesses_detectees']} détection(s), {summary['promesses_a_verifier']} à vérifier manuellement.")
    print("  Comptage indicatif par début de sous-titre, sans mesure du débit audio ni preuve de rétention ; l'image se regarde à part.\n")


if __name__ == "__main__":
    main()
