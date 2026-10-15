#!/usr/bin/env python3
"""check_description.py - check a YouTube description and its tags before they are pasted.

    python3 check_description.py videos/<id>/description.md
    python3 check_description.py videos/<id>/description.md --duree 9:42 --mot-cle "claude chatgpt pokemon"

description.md holds a "## Description" section and a "## Tags" section, each with one fenced code
block (what gets pasted into Studio). Checked:
  - description: 5000 characters max, no < or > (YouTube refuses them), no emoji (channel rule),
    no [PLACEHOLDER] left, the first two lines (shown before "...more") carry the promise;
  - chapters: first at 0:00, at least 3, increasing, at least 10 s apart (otherwise YouTube ignores
    them all), inside the video length when --duree is given;
  - hashtags: 15 max (beyond that YouTube ignores all of them), only the first 3 show above the title;
  - tags: 500 characters max as YouTube counts them (a tag with a space counts 2 more for quotes),
    5 to 8 tags for this channel;
  - the main keyword (--mot-cle, else the first tag) in the first 150 characters (what search and
    the "...more" preview read), and the first tag being that keyword;
  - chapter labels that say nothing ("Intro", "Partie 2", "Fin") get a note;
  - entities: an optional "## Entités" section (one name per line or comma-separated: the AIs, the
    game, the versions, the tools) lists what the description must name; each missing one is reported.
    Method adapted from youtube-seo-skills (deeployCO, MIT).

Two levels: ERRORS (YouTube or channel rule, or a required check that could not run) make the script exit
with code 1; ADVICE (preview length, generic chapter labels, number of tags, first tag) does not block.
No chapters is an error (the channel always has them; --sans-chapitres for a video that really has none).
Without --duree the last chapter cannot be checked against the video length: advice.
"""
import re, sys, unicodedata

GENERIC = re.compile(r"^(intro(duction)?|outro|conclusion|d[ée]but|fin|partie \d+|part \d+|suite|la suite|r[ée]sum[ée])$", re.I)

def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def kw_words(kw):
    stop = {"le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "a", "au", "aux", "vs", "contre"}
    return [w for w in re.findall(r"[a-z0-9]+", fold(kw)) if w not in stop]

def missing_in(text, kw):
    t = fold(text)
    return [w for w in kw_words(kw) if not re.search(r"\b" + re.escape(w) + r"\b", t)]

def entities(md):
    m = re.search(r"^##\s+Entit[ée]s\b.*?$(.*?)(?=^##\s|\Z)", md, re.S | re.M | re.I)
    if not m: return []
    body = re.sub(r"```[^\n]*", "", m.group(1))
    return [e.strip(" -*\t") for e in re.split(r"[,\n]", body) if e.strip(" -*\t")]

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF️]")
CHAPTER = re.compile(r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+[-–—]?\s*(\S.*)$")

def secs(t):
    parts = [int(x) for x in t.split(":")]
    s = 0
    for p in parts: s = s * 60 + p
    return s

def section(md, name):
    m = re.search(r"^##\s+" + name + r"\b.*?$(.*?)(?=^##\s|\Z)", md, re.S | re.M | re.I)
    if not m: return None
    b = re.search(r"```[^\n]*\n(.*?)```", m.group(1), re.S)
    return b.group(1).rstrip("\n") if b else None

def check_description(text, duration=None):
    issues, notes = [], []
    n = len(text)
    if n > 5000: issues.append(f"{n} caractères : 5000 maximum")
    if "<" in text or ">" in text: issues.append("caractères < ou > : YouTube refuse la description")
    if EMOJI.search(text): issues.append("emoji présent : la chaîne n'en met pas dans les descriptions")
    left = re.findall(r"\[[^\]\n]{2,60}\]", text)
    if left: issues.append("crochets à remplir : " + ", ".join(sorted(set(left))[:6]))
    lines = [l for l in text.splitlines()]
    head = [l for l in lines if l.strip()][:2]
    if head and len(" ".join(head)) > 160:
        notes.append(f"les 2 premières lignes font {len(' '.join(head))} caractères : seules ~150 s'affichent avant « plus »")
    chapters = [(secs(m.group(1)), m.group(1), m.group(2)) for m in (CHAPTER.match(l) for l in lines) if m]
    if chapters:
        if chapters[0][0] != 0: issues.append(f"le premier chapitre est à {chapters[0][1]} : il doit être à 0:00")
        if len(chapters) < 3: issues.append(f"{len(chapters)} chapitre(s) : 3 minimum, sinon YouTube les ignore")
        for (a, ta, _), (b, tb, _) in zip(chapters, chapters[1:]):
            if b <= a: issues.append(f"chapitres dans le désordre : {ta} puis {tb}")
            elif b - a < 10: issues.append(f"chapitre de moins de 10 s ({ta} -> {tb}) : YouTube ignore alors tous les chapitres")
        if duration is not None:
            if chapters[-1][0] >= duration: issues.append(f"le dernier chapitre ({chapters[-1][1]}) dépasse la durée de la vidéo")
            elif duration - chapters[-1][0] < 10: issues.append("le dernier chapitre dure moins de 10 s")
        vague = [lab for _, _, lab in chapters if GENERIC.match(lab.strip())]
        if vague: notes.append("chapitres sans contenu (" + ", ".join(vague) + ") : dire ce qui s'y passe")
        notes.append(f"{len(chapters)} chapitres")
    else:
        issues.append("aucun chapitre : la chaîne en met toujours (0:00 en premier, 3 au moins) ; --sans-chapitres si la vidéo n'en a vraiment pas")
    tags = re.findall(r"(?<![\w#])#[\w-]+", text)
    if len(tags) > 15: issues.append(f"{len(tags)} hashtags : au-delà de 15 YouTube les ignore tous")
    elif len(tags) > 3: notes.append("seuls les 3 premiers hashtags s'affichent au-dessus du titre")
    return issues, notes, chapters

def check_tags(text):
    issues, notes = [], []
    tags = [t.strip() for t in re.split(r"[,\n]", text) if t.strip()]
    counted = sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)
    if counted > 500: issues.append(f"tags : {counted} caractères comptés par YouTube, 500 maximum")
    if not 5 <= len(tags) <= 8: notes.append(f"{len(tags)} tags (5 à 8 pour la chaîne)")
    long = [t for t in tags if len(t) > 30]
    if long: notes.append("tags longs (peu utiles) : " + ", ".join(long))
    dup = {t.lower() for t in tags if [x.lower() for x in tags].count(t.lower()) > 1}
    if dup: issues.append("tags en double : " + ", ".join(sorted(dup)))
    return issues, notes, tags, counted

def main():
    a = sys.argv[1:]
    files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--duree", "--mot-cle"))]
    tips = []
    if not files: print(__doc__); sys.exit(1)
    duration = secs(a[a.index("--duree") + 1]) if "--duree" in a else None
    kw = a[a.index("--mot-cle") + 1] if "--mot-cle" in a and a.index("--mot-cle") + 1 < len(a) else None
    md = unicodedata.normalize("NFC", open(files[0], encoding="utf-8-sig").read())
    desc, tags = section(md, "Description"), section(md, "Tags")
    total = 0
    if desc is None:
        print("  ERREUR : pas de section « ## Description » avec un bloc de code"); total += 1
    else:
        issues, notes, chapters = check_description(desc, duration)
        if "--sans-chapitres" in a:
            issues = [i for i in issues if not i.startswith("aucun chapitre")]
        if chapters and duration is None:
            tips.append("--duree absent : le dernier chapitre n'est pas comparé à la durée du montage final")
        tips += [n for n in notes if not re.fullmatch(r"\d+ chapitres", n)]
        print(f"\n  description : {len(desc)} caractères" + (f" ; {len(chapters)} chapitres" if chapters else ""))
        for i in issues: print(f"    ERREUR : {i}")
        total += len(issues)
    if tags is None:
        print("  ERREUR : pas de section « ## Tags » avec un bloc de code"); total += 1
    else:
        issues, notes, t, counted = check_tags(tags)
        if t and kw and missing_in(t[0], kw):
            notes.append(f"le premier tag (« {t[0]} ») n'est pas le mot-clé principal « {kw} »")
        tips += notes
        print(f"  tags : {len(t)}, {counted} caractères comptés")
        for i in issues: print(f"    ERREUR : {i}")
        total += len(issues)
        kw = kw or (t[0] if t else None)
    if desc is not None:
        extra = []
        if kw:
            miss = missing_in(desc[:150], kw)
            if miss: extra.append(f"mot-clé « {kw} » absent des 150 premiers caractères ({', '.join(miss)}) : c'est ce que lisent la recherche et l'aperçu")
        ents = entities(md)
        absent = [e for e in ents if fold(e) not in fold(desc)]
        if absent: extra.append("entités non citées dans la description : " + ", ".join(absent))
        elif ents: print(f"  entités : les {len(ents)} sont citées")
        for i in extra: print(f"    ERREUR : {i}")
        total += len(extra)
    for i in tips: print(f"    conseil : {i}")
    print(f"\n  {total} erreur(s) à corriger, {len(tips)} conseil(s)\n" if total else
          "\n  aucune erreur" + (f", {len(tips)} conseil(s) à regarder\n" if tips else ", tout est conforme\n"))
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main()
