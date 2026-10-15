#!/usr/bin/env python3
"""check_titles.py - vérifie des titres YouTube (et leurs paires miniature) avant de les livrer.

    python3 check_titles.py titres.txt
    python3 check_titles.py titres.txt --refs refs.json --own ma-chaine.json --mot-cle "claude chatgpt pokemon"
    python3 check_titles.py shorts.txt --shorts      # titres de Shorts : sans surfaces (pas de Test & Compare)

titres.txt : une variante par ligne, « titre », « titre | TEXTE MINIATURE » ou
« titre | TEXTE MINIATURE | accueil » (ou « recherche ») : la surface que la paire vise.

Surfaces (méthode youtube-seo-skills, deeployCO, MIT) : une paire « accueil » (fil d'accueil, suggestions)
met l'émotion ou l'action en tête ; une paire « recherche » met le mot-clé principal (--mot-cle) dans
les 40 premiers caractères, ce que vérifie le script. Le jeu doit contenir au moins une paire de chaque.

Vérifie, pour chaque titre : longueur (100 max, 40 à 60 idéal), ce que montre le fil mobile
(40 premiers caractères), ponctuation interdite par la chaîne (deux-points, tiret isolé, points de
suspension), majuscules (2 mots max, sigles comme IA exclus), emojis (aucun), numéros de version
après un nom d'IA, adjectifs vagues. Pour la paire : texte miniature de 3 à 4 mots, mots répétés
entre le titre et la miniature. Pour le jeu : deux variantes qui commencent par les mêmes mots.

--refs : sortie --json de swipe.py (ou fichier texte, un titre par ligne). Donne pour chaque
titre la référence la plus proche, et signale une copie quasi mot pour mot.
--own : les titres de la chaîne (JSON yt-dlp ou texte) ; signale un titre déjà utilisé.
Les longueurs sont comptées après normalisation Unicode (NFC), comme un humain les compte.

Deux niveaux : les ERREURS (règle de la chaîne ou de YouTube, contrôle obligatoire impossible) font
sortir le script avec le code 1 ; les CONSEILS (longueur hors de 40-60, adjectif vague, mot répété,
attaques semblables, sujet hors de l'aperçu mobile d'une paire « accueil ») s'affichent sans bloquer.
Erreurs : plus de 100 caractères, deux-points, points de suspension, tiret, plus de 2 mots en
majuscules, emoji, numéro de version, texte miniature de plus de 4 mots, surface inconnue, paire
« recherche » sans --mot-cle ou sans le mot-clé dans les 40 premiers caractères, quasi copie d'une
référence, titre trop proche d'un titre de la chaîne, surfaces absentes ou toutes identiques dans
un jeu de plusieurs paires (sauf --shorts).
"""
import difflib, json, os, re, sys, unicodedata

ACRONYMS = {"IA", "AI", "GPT", "PC", "PS5", "FPS", "RPG", "MMO", "PNJ", "NPC", "TNT", "XP", "HD",
            "4K", "3D", "2D", "USA", "UK", "FR", "YT", "OP", "PvP", "PVP", "IRL", "GTA", "LOL"}
VAGUE = {"incroyable", "incroyables", "fou", "folle", "fous", "folles", "ultime", "ultimes",
         "énorme", "énormes", "dingue", "dingues", "insane", "hallucinant", "hallucinante",
         "choquant", "choquante", "épique", "légendaire", "extraordinaire", "magique", "parfait",
         "parfaite", "meilleur", "trop"}
STOP = set("""le la les l un une des de du d à au aux et ou en dans sur pour par avec sans mais qui que
quoi ce cet cette ces se sa son ses leur leurs mon ma mes ton ta tes je j il elle on nous vous ils
elles est sont a ai ont fait faire plus pas ne n y""".split())
AI_NAMES = r"(Claude|ChatGPT|GPT|Gemini|Grok|Copilot|Mistral|Llama|DeepSeek|Opus|Sonnet|Fable|Haiku|Astra)"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")

def nfc(s): return unicodedata.normalize("NFC", s.strip())

def words(s): return re.findall(r"[\w']+", s.lower())

def content_words(s):
    return {w.split("'")[-1] for w in words(s)} - STOP - {""}

def load_titles(path):
    if not path: return []
    raw = open(path, encoding="utf-8-sig").read()
    try: data = json.loads(raw)
    except ValueError:
        if str(path).lower().endswith(".json"): raise ValueError(f"JSON illisible : {path}")
        return [(nfc(l), "") for l in raw.splitlines() if l.strip()]
    out = []
    def walk(n):
        if isinstance(n, list):
            for x in n: walk(x)
        elif isinstance(n, dict):
            for k in ("outliers", "entries", "videos"):
                if k in n: walk(n[k]); return
            if n.get("title"):
                label = n.get("channel") or ""
                if n.get("multiple"): label += f", {n['multiple']}x"
                out.append((nfc(n["title"]), label))
    walk(data)
    return out

def check(title, thumb):
    """(errors, advice) for one title and its thumbnail text."""
    err, tip = [], []
    if not title.strip(): err.append("contrôle impossible : titre vide")
    n = len(title)
    if n > 100: err.append(f"{n} caractères : au-delà de 100, YouTube refuse")
    elif n > 60: tip.append(f"{n} caractères : au-delà de 60, vérifier que l'essentiel tient dans les 40 premiers")
    elif n < 30: tip.append(f"{n} caractères : court, vérifier qu'il reste explicite (qui, quoi, où)")
    if ":" in title: err.append("deux-points interdit par la chaîne")
    if "…" in title or "..." in title: err.append("points de suspension interdits par la chaîne")
    if re.search(r"(^|\s)[-–—](\s|$)|[–—]", title): err.append("tiret interdit par la chaîne (le trait d'union dans un mot reste permis)")
    caps = [w for w in re.findall(r"[^\W\d_][\w'’]*", title) if len(w) >= 2 and w.isupper() and w not in ACRONYMS]
    if len(caps) > 2: err.append(f"{len(caps)} mots en majuscules ({', '.join(caps)}) : 2 maximum")
    if EMOJI.search(title): err.append("emoji : la chaîne n'en met nulle part")
    v = re.search(AI_NAMES + r"\s*(\d[\d.,]*\w*|o\d\w*)", title, re.I)
    if v: err.append(f"« {v.group(0)} » : numéro de version dans le titre (le mettre en description)")
    if re.search(r"\b(Opus|Sonnet|Fable|Haiku|Astra)\b", title, re.I):
        tip.append("nom de modèle plutôt que de marque : préférer « Claude » ou « ChatGPT »")
    vague = [w for w in words(title) if w in VAGUE]
    if vague: tip.append("adjectif vague : " + ", ".join(vague) + " (préférer un chiffre ou un nom propre)")
    if thumb:
        tw = len(thumb.split())
        if tw > 4: err.append(f"texte miniature de {tw} mots : 4 maximum")
        shared = content_words(title) & content_words(thumb)
        if shared: tip.append("mot(s) répété(s) titre/miniature : " + ", ".join(sorted(shared)) + " (permis seulement pour le mot-sujet, à signaler)")
    return err, tip

def closest(title, pool):
    best, label, score = "", "", 0.0
    t = title.lower()
    for ref, lab in pool:
        s = difflib.SequenceMatcher(None, t, ref.lower()).ratio()
        if s > score: best, label, score = ref, lab, s
    return best, label, score

def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()

def keyword_in_head(title, kw, n=40):
    """Every content word of the keyword in the first n characters (accents and case ignored)."""
    head = fold(title[:n])
    missing = [w for w in content_words(fold(kw)) if not re.search(r"\b" + re.escape(w) + r"\b", head)]
    return missing

def main():
    a = sys.argv[1:]
    def opt(name):
        if name not in a: return None
        if a.index(name) + 1 >= len(a) or a[a.index(name) + 1].startswith("--"):
            sys.exit(f"contrôle impossible : {name} demande une valeur")
        return a[a.index(name) + 1]
    try:
        refs, own = load_titles(opt("--refs")), load_titles(opt("--own"))
        for name, pool in (("--refs", refs), ("--own", own)):
            if name in a and not pool: raise ValueError(f"aucun titre chargé pour {name}")
    except (OSError, ValueError) as e:
        sys.exit(f"contrôle impossible : {e}")
    kw = opt("--mot-cle")
    files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in ("--refs", "--own", "--mot-cle"))]
    if not files or not os.path.exists(files[0]): print(__doc__); sys.exit(1)
    rows = []
    for l in open(files[0], encoding="utf-8-sig").read().splitlines():
        if not l.strip() or l.lstrip().startswith("#"): continue
        parts = [x for x in l.split("|")]
        title, thumb = parts[0], parts[1] if len(parts) > 1 else ""
        surf = fold(parts[2]).strip() if len(parts) > 2 else ""
        rows.append((nfc(title), nfc(thumb), surf))
    if not rows: sys.exit("contrôle impossible : aucun titre à vérifier dans le fichier")
    if not refs:
        print("\n  aucune référence chargée (--refs) : impossible de dire sur quelle vidéo de référence chaque titre s'appuie")
    errors = advice = 0
    def report(errs, tips, indent="    "):
        nonlocal errors, advice
        for i in errs: print(f"{indent}ERREUR : {i}")
        for i in tips: print(f"{indent}conseil : {i}")
        errors += len(errs); advice += len(tips)
    for title, thumb, surf in rows:
        errs, tips = check(title, thumb)
        if surf and surf not in ("accueil", "recherche"):
            errs.append(f"surface « {surf} » inconnue : accueil ou recherche")
        miss = keyword_in_head(title, kw) if kw else None
        if surf == "recherche":
            if not kw: errs.append("paire « recherche » sans --mot-cle : le mot-clé en tête n'a pas été vérifié")
            elif miss: errs.append("paire « recherche » : mot-clé absent des 40 premiers caractères (" + ", ".join(miss) + ")")
        elif kw and miss:
            tips.append(f"aperçu mobile « {title[:40]} » : le sujet ({', '.join(miss)}) n'y est pas ; la miniature doit le montrer")
        print(f"\n  {title}" + (f"   | miniature : {thumb}" if thumb else "") + (f"   [{surf}]" if surf else ""))
        print(f"    {len(title)} caractères   mobile : « {title[:40]} »")
        if refs:
            ref, lab, sc = closest(title, refs)
            print(f"    référence la plus proche ({sc:.0%}) : {ref}" + (f"  [{lab}]" if lab else ""))
            if sc >= 0.8: errs.append("quasi copie d'un titre de référence : garder la structure, changer les mots")
        if own:
            mine, _, sc = closest(title, own)
            if sc >= 0.75: errs.append(f"trop proche d'un titre déjà publié sur la chaîne : {mine}")
        report(errs, tips)
        if not errs and not tips: print("    ok")
    surfs = {s for _, _, s in rows if s}
    if "--shorts" in a:
        pass   # titres de Shorts : pas de Test & Compare, donc pas de surfaces
    elif len(rows) > 1 and not surfs:
        report(["aucune surface indiquée : ajouter « | accueil » ou « | recherche » en 3e colonne, au moins une paire de chaque"], [], "\n  ")
    elif len(rows) > 1 and surfs and surfs != {"accueil", "recherche"}:
        report([f"toutes les paires visent « {surfs.pop()} » : il en faut au moins une pour l'accueil et une pour la recherche"], [], "\n  ")
    starts = {}
    for title, _, _ in rows:
        starts.setdefault(" ".join(words(title)[:2]), []).append(title)
    for k, ts in starts.items():
        if len(ts) > 1 and k:
            report([], [f"{len(ts)} variantes commencent par « {k} » : varier les attaques"], "\n  ")
    print(f"\n  {errors} erreur(s) à corriger, {advice} conseil(s)\n" if errors else
          f"\n  aucune erreur sur les contrôles effectués" + (f", {advice} conseil(s) à regarder\n" if advice else "\n"))
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
