#!/usr/bin/env python3
"""hookscore.py - score a YouTube hook before you waste a take on it.

Five properties, 0-100 each, and a verdict that is 60% the mean and 40% the weakest one. The
weakest-link weighting is deliberate: a hook with four strong properties and one dead one is a hook
that leaks at the dead one, and averaging hides that.

    python3 hookscore.py videos/<id>/script.md    # every "**Version X**" opening of a script, + minutage
    python3 hookscore.py hooks.txt                # one hook per line, ranked
    python3 hookscore.py --hook "one line"        # score a single hook
    python3 hookscore.py --json ...               # machine-readable
    python3 hookscore.py --calibrer               # our published openings against their 30 s retention
    python3 hookscore.py --profil solo ...        # Short à une seule IA (défi, contrainte, 3 s)
    python3 hookscore.py --profil generique ...   # ancien scoreur (adresse « vous » + menace)
    python3 hookscore.py --titre "..." ...        # le titre à confirmer (par défaut, celui de suivi.md à côté d'un script.md)

CURIOSITY EST UNE FORME (2026-10-08). Une vraie question (+ si elle porte sur une chose nommée : « lequel me donne
un vrai Dismantle ? » plutôt que « lequel va réussir ? »), « on va voir lequel… » compris, une promesse pour plus tard
(« à la fin », « jusqu'au domaine »), une tension (« mais »). Une suite de mots interrogatifs n'est plus une question.
SPECIFICITY compte les noms distincts (le jeu, le personnage, la technique, les deux modèles), même en tête de phrase,
et deux chiffres au plus.

TITRE ET PREMIERE IMAGE (ALERTES). Les noms du titre doivent être dits avant 6 s (moitié au moins), sinon le clic
n'est pas confirmé (règle 1 de hooks.json) ; le créneau 0-3 s d'un script a un [ON SCREEN] qui montre un résultat.

PROFIL PAR DEFAUT = LA CHAINE. Les accroches de duel d'IA ne s'adressent pas au spectateur et ne le
menacent pas : ADDRESS et STAKES les notaient ~25 et plafonnaient tout a 35. Elles sont remplacees par
DEFI (la mission est posee dans la premiere phrase, deux concurrents) et ENJEU (la regle du duel).

PROFIL SOLO (2026-10-08) = SHORT A UNE SEULE IA. Le duel n'y a pas de sens : DEFI compte l'IA nommée et l'ordre
qu'elle reçoit (« Claude, fais-moi… ») ou le défi en question (« Claude peut-il… ? ») ; ENJEU, la contrainte (une
seule phrase, dix minutes, aucune retouche) et ce qui peut rater ; BREVITY, l'accroche dite en 3 s (10 mots). Pas
encore mesuré sur de vrais Shorts : même prudence que plus bas.

BREVITY EN TEMPS. Une accroche d'une phrase garde la bande de 9 a 24 mots. Une ouverture de plusieurs
phrases (les 15 premieres secondes d'un script) est mesuree au debit de minutage.py : la premiere
phrase, celle de la mission, tient en 4 s, le tout en 15 s.

ALERTES. Salutation, presentation de la chaine, demande d'abonnement, « tu » au spectateur, titre non confirme,
premiere image : signales, sans effet sur la note (regles de config/youtube/preferences.md et voice.md).
Le script entier (tableau colle a jour, beats, voix) se relit avec relecture.py.

WHAT THIS CAN AND CANNOT TELL YOU. Measured against 74 real short-form hooks (first 15 seconds of
auto-captions, top-8 and bottom-8 by views across five channels): it separates deliberately bad
hooks from real ones well, and it separates a creator's own hits from their own misses barely at
all. calibration.json holds our own published openings and their retention at 30 s (one line per
J+7 bilan) : under 8 videos it is a guard, not a calibration. Treat a low score as a reason to look
again, never a high score as a promise.
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from minutage import RATE, SLOT, said, analyse  # noqa: E402

FORMULAS = json.load(open(os.path.join(HERE, "hooks.json"), encoding="utf-8"))["hooks"]
CALIBRATION = os.path.join(HERE, "calibration.json")

FILLER = {"basically","actually","literally","just","really","very","so","kind","sort","like",
          "guys","hey","welcome","today","video","subscribe","channel",
          # French
          "bon","bah","ben","alors","donc","genre","vraiment","juste","voilà","salut","bienvenue",
          "aujourd'hui","vidéo","abonnez","abonnez-vous","chaîne","gars"}
VAGUE = {"amazing","incredible","insane","crazy","huge","massive","game","changer","secret",
         "powerful","ultimate","best","revolutionary","mind","blowing","unbelievable",
         # French
         "incroyable","incroyables","fou","folle","dingue","ouf","énorme","ultime","meilleur",
         "meilleure","révolutionnaire","hallucinant","hallucinante","choquant","épique","magique"}
# French hooks write their numbers in letters: « un seul prompt », « deux IA », « 2IA »
CONCRETE = re.compile(r"\b(\d[\d,.]*\s?(%|k|m|x|s|m|h|€)?|\$\d|\d+\s?(second|minute|hour|day|week|month|year)s?"
                      r"|\d+\s?(seconde|minute|heure|jour|semaine|mois|an|année|fois|bloc|ligne)s?"
                      r"|\d+ ?ia|une? seule?|(?<!les )deux|trois|quatre|cinq|six|sept|huit|neuf|dix|vingt|cent|mille)\b",
                      re.I)
YOU = re.compile(r"\b(you|your|you're|youre|yourself|vous|votre|vos|tu|ton|ta|tes|toi)\b", re.I)
STAKE = re.compile(r"\b(lose|lost|wasting|waste|quit|fail|broke|cost|risk|before|stop|never|die|dying|dead"
                   r"|perdre|perdu|perd|gâcher|rater|rate|raté|échoue|échouer|échec|coûte|risque|avant|arrêter"
                   r"|jamais|mourir|mort|détruit|casse|cassé|plante|bug|impossible)\b", re.I)
# CURIOSITE = la forme, pas un compte de mots (une suite de « pourquoi comment qui » notait 100) :
# une vraie question, si possible sur une chose nommée, une promesse pour plus tard, une tension.
INTERROG = re.compile(r"\b(lequel|laquelle|lesquels|qui|quel|quelle|quels|quelles|comment|pourquoi|combien"
                      r"|est-ce que|est-ce qu|jusqu'où|où|which|who|how|why|what)\b|\w-t-(il|elle|on)\b"
                      r"|\w-(il|elle|ils|elles|on)\s*\?", re.I)
# « on va voir lequel… » : une question dite sans point d'interrogation
INDIRECT = re.compile(r"\b(on va voir|voyons|je veux savoir|savoir|découvrir|to see|find out)\s+(si|s'il|lequel|laquelle"
                      r"|qui|comment|ce que|ce qu|quel|quelle|jusqu'où|who|which|if|whether|how)\b", re.I)
TEASER = re.compile(r"\b(à la fin|à venir|jusqu'(au|à|aux)|le dernier|la dernière|plus tard|ensuite|attendez"
                    r"|until|by the end|wait)\b", re.I)
TENSION = re.compile(r"\b(mais|sauf|presque|personne|pourtant|sauf que|but|except|almost|nobody)\b", re.I)
# a hook that names its winner has closed its own question (« Claude gagne. »; a question is fine)
SPOILER = re.compile(r"\b(a gagné|gagne|remporte|l'emporte|le gagnant,? c'est|wins|won)\b", re.I)

def words(t): return re.findall(r"[\w'’%$.]+", t.lower())

def sentences(t): return [s for s in re.split(r"(?<=[.!?…])\s+", t.strip()) if s]

# mots qui ouvrent une phrase sans être un nom : la majuscule y vient de la ponctuation
COMMUNS = set("""je j'ai j' tu il elle on nous vous ils elles le la les l' un une des du de d' dans et ou mais donc
or ni car ce c' cet cette ces ça ca qui que qu' quoi quel quelle lequel laquelle pourquoi comment combien où
si avec sans pour par sur sous à au aux en y pas plus moins aucun aucune chaque tout toute tous toutes même
voici voilà alors puis ensuite enfin bon bah ben oui non est-ce deux trois quatre cinq six sept huit neuf dix
premier première dernier dernière d'un d'une jusqu'au jusqu'à ia vs ok i the a an this that what which who
why how in on at my your we they it today""".split())

def name_set(t):
    """distinct named things (game, character, model): capitalised words, except a sentence's ordinary first word"""
    found = {}
    for s in sentences(t):
        for i, x in enumerate(s.split()):
            x = x.strip(".,;:!?«»\"()…").replace("’", "'")
            if not x[:1].isupper() or x.lower() in COMMUNS or x.isupper() and len(x) <= 2:
                continue
            if i == 0 and (x.lower().split("'")[0] + "'" in COMMUNS):
                continue
            found.setdefault(x.lower(), x)
    return set(found.values())

def names(t): return len(name_set(t))

def specificity(t):
    w = words(t)
    if not w: return 0
    # two numbers say it; « un seul… une seule… deux… » on top is a list, and a list of numbers names nothing
    nums = min(2, len(CONCRETE.findall(t)))
    vague = sum(1 for x in w if x in VAGUE)
    filler = sum(1 for x in w if x in FILLER)
    s = 34 + nums * 22 - vague * 16 - filler * 5
    # this channel's specifics are names: the game, the character, the power, the two models
    s += min(32, 8 * names(t))
    return max(0, min(100, s))

def address(t):
    n = len(YOU.findall(t))
    first = 30 if YOU.search(" ".join(t.split()[:6])) else 0
    return max(0, min(100, 26 + n * 20 + first))

def stakes(t):
    n = len(STAKE.findall(t))
    return max(0, min(100, 22 + n * 26 + (14 if CONCRETE.search(t) else 0)))

def curiosity(t):
    ss = sentences(t)
    qs = [s for s in ss if s.rstrip().endswith("?")] + [s for s in ss if INDIRECT.search(s) and not s.rstrip().endswith("?")]
    s = 24
    if qs:
        s += 18
        s += 12 if any(INTERROG.search(q) or INDIRECT.search(q) for q in qs) else 0
        # « Lequel me donne un vrai Dismantle ? » keeps more than « Lequel va réussir ? »
        s += 10 if any(names(q) or CONCRETE.search(q) for q in qs) else 0
    s += 20 if TEASER.search(t) else 0
    s += 10 if TENSION.search(t) else 0
    # a hook that resolves itself has no gap left
    s -= 18 if re.search(r"\b(because|so that|which means|parce que|du coup|ce qui veut dire)\b", t, re.I) else 0
    s -= 18 if any(SPOILER.search(x) and not x.rstrip().endswith("?") for x in ss) else 0
    # three question words in a row are a list, not a question
    s -= max(0, len(INTERROG.findall(t)) - 3) * 12
    return max(0, min(100, s))

def brevity(t):
    n = len(words(t))
    if n == 0: return 0
    ss = sentences(t)
    if len(ss) < 2:
        # 9-24 words is the band a spoken hook lands in at ~150wpm inside 10 seconds
        if 9 <= n <= 24: return 100
        if n < 9:  return max(30, 100 - (9 - n) * 11)
        return max(10, 100 - (n - 24) * 7)
    # an opening of several sentences: the mission in 4 s, the whole thing in 15 s, at the channel's pace
    first = len(words(ss[0]))
    s = 100 - max(0, first - round(4 * RATE)) * 6 - max(0, n - round(15 * RATE)) * 4 - max(0, 9 - n) * 11
    return max(10, min(100, s))

# Profil « chaine » (défaut) : accroche de duel d'IA, sans adresse directe ni menace (voir
# skills/nouvelle-video/references/accroches-script.md). Profil « generique » : le scoreur d'origine.
MISSION = re.compile(r"\b(j'ai (demandé|donné|laissé|mis|lancé|fait)|je (vais )?(demande|teste|lance|donne|fais)"
                     r"|demand\w*|défi|mission|cod(e|es|er|ent|é|ée|és|ait|aient|era|eront)|programm\w*"
                     r"|(re)?cré(e|é|ée|és|ées|er|ent|ait|aient|era|eront)|construi\w*|fabriqu\w*"
                     r"|refai\w*|refont|refaire|invent\w*|transform\w*|affront\w*|développ\w*)\b", re.I)
# « contre » seul n'est pas un duel (« un site contre l'ennui ») : il faut un adversaire
DUEL = re.compile(r"\b(vs|versus|contre (l'|une |les )?(ias?|claude|chatgpt|gemini|grok|astra|moi)|les deux|deux (ia|jeux|modèles|intelligences)|\d ?ia|lequel|laquelle"
                  r"|face à face|duel|d'un côté)\b", re.I)
PAIR = re.compile(r"\b[A-Z][\w.]*(?: [A-Z0-9][\w.]*)? (et|contre|vs\.?|ou) [A-Z][\w.]*")
RULE = re.compile(r"\b(sans|aucun|aucune|un seul|une seule|seulement|minimum|maximum|limite|chrono|temps imparti"
                  r"|doivent|règle|gagnant|perdant|vainqueur|zéro|de zéro|même demande|même consigne|même prompt"
                  r"|le même|exactement le même|\d+ (prompt|demande|essai|correction)s?"
                  r"|ne touche à rien|je ne touche|interdit|pas le droit|pas de)\b", re.I)

def bourrage(t):
    """penalty for the scorer's own keywords beyond 3 or a third of the words: a real sentence stays under"""
    n = len(words(t))
    hits = (len(MISSION.findall(t)) + len(RULE.findall(t)) + len(DUEL.findall(t))
            + sum(1 for x in words(t) if x in VAGUE))
    return max(0, round((hits - max(3, n / 3)) * 15))

def defi(t):
    ss = sentences(t)
    s = 20 + (35 if MISSION.search(t) else 0) + (15 if ss and MISSION.search(ss[0]) else 0)
    s += 20 if (DUEL.search(t) or PAIR.search(t)) else 0
    s += 10 if words(t) and words(t)[0] not in FILLER else 0
    return max(0, min(100, s - bourrage(t)))

def enjeu(t):
    # three rules are already more than a viewer holds in 15 s
    n = min(3, len(set(m.group(0).lower() for m in RULE.finditer(t))))
    return max(0, min(100, 24 + n * 22 + (14 if CONCRETE.search(t) else 0) - bourrage(t)))

# Profil « solo » : Short à une seule IA (20 à 52 s, accroche dite en 0-3 s). Pas de second concurrent ni de règle
# de duel : le défi est « qui tente quoi » (une IA nommée + un ordre ou une question « peut-elle… ? »), l'enjeu est la
# contrainte (une seule phrase, dix minutes, aucune retouche) et ce qui peut rater ; la brièveté tient en 3 s.
IA = re.compile(r"\b(claude|opus|sonnet|chatgpt|gpt[\w.-]*|astra|gemini|grok|copilot|mistral|deepseek|llama"
                r"|l'ia|une ia)\b", re.I)
IA_FAMILLE = {"opus": "claude", "sonnet": "claude", "astra": "chatgpt", "une ia": "l'ia"}
# l'ordre donné à l'IA (« Claude, fais-moi un site ») ou le défi posé en question (« Claude peut-il guérir mon ennui ? »)
ORDRE = re.compile(r"\b(fais|crée|code|construis|dessine|invente|génère|écris|programme|refais|fabrique|imagine)"
                   r"-(moi|nous|lui|le|la|les)\b", re.I)
DEFI_Q = re.compile(r"\b(peut-(il|elle|on)|pourra-t-(il|elle|on)|arrive(ra)?-t-(il|elle|on)|réussi(t|ra)-t-(il|elle|on)"
                    r"|sait-(il|elle)|capable de|est-ce qu'(il|elle|on|une ia|l'ia) (peut|va|arrive|réussit|sait)"
                    r"|est-ce que (claude|chatgpt|l'ia|une ia) (peut|va|arrive|réussit|sait))\b", re.I)
BUDGET = re.compile(r"\b(\d+|une?|deux|trois|cinq|dix|quinze|vingt|trente|soixante) (secondes?|minutes?|heures?"
                    r"|phrases?|prompts?|essais?|mots?|lignes?)\b", re.I)
ISSUE = re.compile(r"\b(réussi\w*|rate\w*|raté|échou\w*|y arrive\w*|tenir|tient|marche\w*|plante\w*|casse\w*"
                   r"|survi\w*)\b|\?", re.I)

def ias(t):
    """distinct AIs named (Claude Opus = Claude, Astra = ChatGPT)"""
    return {IA_FAMILLE.get(x.group(0).lower(), x.group(0).lower()) for x in IA.finditer(t)}

def defi_solo(t):
    ss = sentences(t)
    mission = lambda x: MISSION.search(x) or ORDRE.search(x) or DEFI_Q.search(x)
    s = 20 + (35 if mission(t) else 0) + (15 if ss and mission(ss[0]) else 0)
    s += 20 if ias(t) else 0                       # qui tente : l'IA est dite (le pendant du duel)
    s += 10 if words(t) and words(t)[0] not in FILLER else 0
    return max(0, min(100, s - bourrage(t)))

def enjeu_solo(t):
    # la contrainte (une seule phrase, dix minutes, aucune retouche) et ce qui peut rater
    rules = {m.group(0).lower() for m in RULE.finditer(t)} | {m.group(0).lower() for m in BUDGET.finditer(t)}
    n = min(3, len(rules))
    return max(0, min(100, 24 + n * 22 + (14 if CONCRETE.search(t) else 0) + (16 if ISSUE.search(t) else 0)
                       - bourrage(t)))

def brevity_short(t):
    # dite en 0-3 s : 10 mots à 200 mots/min ; moins de 5 mots ne pose rien
    n = len(words(t))
    if n == 0: return 0
    return max(10, min(100, 100 - max(0, n - round(3 * RATE)) * 8 - max(0, 5 - n) * 12))

PROFILS = {
  "chaine":    [("SPECIFICITY", specificity), ("DEFI", defi), ("ENJEU", enjeu),
                ("CURIOSITY", curiosity), ("BREVITY", brevity)],
  "solo":      [("SPECIFICITY", specificity), ("DEFI", defi_solo), ("ENJEU", enjeu_solo),
                ("CURIOSITY", curiosity), ("BREVITY", brevity_short)],
  "generique": [("SPECIFICITY", specificity), ("ADDRESS", address), ("STAKES", stakes),
                ("CURIOSITY", curiosity), ("BREVITY", brevity)],
}
PROPS = PROFILS["chaine"]

ALERTES = [
 (re.compile(r"\b(salut|bienvenue|coucou|hello)\b", re.I), "salutation avant d'avoir donné quelque chose"),
 (re.compile(r"\b(ma chaîne|sur la chaîne|cette chaîne|je m'appelle)\b", re.I), "présentation de la chaîne"),
 (re.compile(r"\babonn\w*", re.I), "demande d'abonnement dans l'accroche"),
 (re.compile(r"\b(tu|toi|ton|ta|tes|t'as)\b", re.I), "« tu » adressé au spectateur (la chaîne vouvoie)"),
]

def classify(t):
    best, hits = None, 0
    for f in FORMULAS:
        n = sum(1 for p in f["match"] if re.search(p, t, re.I))
        if n > hits: best, hits = f, n
    return (best["name"] if best else "Unclassified"), hits

def score(t):
    t = t.replace("’", "'")
    parts = {n: fn(t) for n, fn in PROPS}
    vals = list(parts.values())
    verdict = round(0.6 * (sum(vals) / len(vals)) + 0.4 * min(vals))
    name, hits = classify(t)
    return parts, verdict, name, hits

def alertes(t):
    t = t.replace("’", "'")
    out = [msg for rx, msg in ALERTES if rx.search(t)]
    if PROPS is PROFILS["chaine"] and len(ias(t)) == 1 and not (DUEL.search(t) or PAIR.search(t)):
        out.append("une seule IA, pas de duel : un Short à une seule IA se note avec --profil solo")
    return out

def band(v): return "STRONG" if v >= 72 else "WORKABLE" if v >= 55 else "WEAK"

def report(r):
    t, parts = r["hook"], r["properties"]
    print(f"\n  {('Version ' + r['version'] + ' : ') if r.get('version') else ''}{t}")
    print(f"  {'-' * min(72, max(20, len(t)))}")
    for k, v in parts.items():
        print(f"    {k:<12} {v:3d}  {'#' * (v // 5)}")
    print(f"    {'VERDICT':<12} {r['verdict']:3d}  {r['band']}")
    hits = r["matched"]
    print(f"    formula      {r['formula']}" + (f"  ({hits} pattern{'s' if hits != 1 else ''} matched)" if hits else "  (no formula matched - that is usually a summary, not a hook)"))
    low = min(parts, key=parts.get)
    print(f"    weakest      {low} - {FIX[low]}")
    if r.get("minutage"):
        print(f"    minutage     {r['minutage']}")
    if r.get("titre"):
        print(f"    titre        {r['titre']} des noms du titre dits")
    for a in r["alertes"]:
        print(f"    ALERTE       {a}")

FIX = {
 "DEFI": "pose la mission dès la première phrase : qui fait quoi (« J'ai demandé à X et Y de… »), sans intro",
 "ENJEU": "ajoute la règle qui rend le duel lisible : temps imparti, une seule demande, aucune retouche, ce que le gagnant gagne",
 "SPECIFICITY": "nomme ce qu'on verra (le jeu, le personnage, la technique, les deux IA) et remplace un adjectif par un chiffre",
 "ADDRESS": "say 'you' (or 'vous') in the first six words",
 "STAKES": "name what it costs them to keep doing it the current way",
 "CURIOSITY": "une question sur une chose nommée (« lequel me donne un vrai Dismantle ? ») et une promesse pour la fin (« et à la fin, le domaine »), sans dire le gagnant",
 "BREVITY": f"mission en {round(4 * RATE)} mots au plus, ouverture en {round(15 * RATE)} au plus (15 s à {RATE * 60:.0f} mots/min)",
}

FIX_SOLO = {
 "DEFI": "dis qui tente quoi dès la première phrase : l'IA nommée et l'ordre (« Claude, fais-moi… ») ou le défi en question (« Claude peut-il… ? »)",
 "ENJEU": "ajoute la contrainte (une seule phrase, dix minutes, aucune retouche) et ce qui peut rater",
 "BREVITY": f"l'accroche d'un Short se dit en 3 s : {round(3 * RATE)} mots au plus",
}

def openings(text):
    """[(version, spoken text, slots)] of the timed lines « - **0-3 s** … : « … » » of a script.md,
    slots = [(start s, spoken, [ON SCREEN] note or None)]"""
    out, version = {}, None
    for line in text.splitlines():
        m = re.match(r"^\*\*Version\s+([^\s*]+)", line)
        if m:
            version = m.group(1); continue
        if line.startswith("## "):
            version = None
        s = SLOT.match(line)
        if s:
            screen = ON_SCREEN.search(s.group(3))
            out.setdefault(version or "-", []).append(
                (float(s.group(1).replace(",", ".")), said(s.group(3)), screen.group(1).strip() if screen else None))
    return [(v, " ".join(x[1] for x in slots if x[1]).strip(), slots) for v, slots in out.items()]

ON_SCREEN = re.compile(r"\[ON SCREEN\s*:?\s*((?:[^\[\]]|\[[^\]]*\])*)\]", re.I)
# 0-3 s must show the strongest result; these are not a result
SPLIT = re.compile(r"ecran partage|split")   # matched on plain() text
VENIR = re.compile(r"(?<!\w)a venir\b")   # matched on plain() text
NOT_RESULT = re.compile(r"\b(face ?cam|webcam|mon visage|moi face|logo de la chaîne|intro|générique|fond (noir|uni)"
                        r"|menu|écran titre de la chaîne|bureau)\b", re.I)

def plain(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")

def title_check(early, title):
    """(said, missing) : the title's named things (else its long words) heard in the first seconds"""
    keys = sorted(name_set(title.replace("’", "'"))) or sorted(
        {w for w in words(title) if len(w) >= 5 and w not in COMMUNS})
    heard = set(re.findall(r"[\w]+", plain(early)))
    got = [k for k in keys if all(x in heard for x in re.findall(r"[\w]+", plain(k)))]
    return got, [k for k in keys if k not in got]

def title_line(early, title, delay):
    got, miss = title_check(early, title)
    total = len(got) + len(miss)
    if not total: return None, None
    mark = f"{len(got)}/{total}"
    if 2 * len(got) >= total:
        return mark, None
    return mark, f"titre pas confirmé avant {delay} : manque {', '.join(miss)} (titre : « {title} »)"

def script_title(path):
    """the working or final title, from « # Suivi : … » next to a script.md"""
    if os.path.basename(path).lower() != "script.md": return None
    suivi = os.path.join(os.path.dirname(os.path.abspath(path)), "suivi.md")
    if not os.path.exists(suivi): return None
    m = re.match(r"#\s*Suivi\s*:\s*(.+)", open(suivi, encoding="utf-8-sig").readline())
    return m.group(1).strip() if m else None

def version_checks(slots, title):
    """[alertes] and the title mark for one version of a script's opening"""
    out, mark = [], None
    first = slots[0]
    if first[2] is None:
        out.append(f"{first[0]:g} s sans [ON SCREEN] : le résultat le plus fort doit être à l'image dès la première seconde")
    elif NOT_RESULT.search(first[2]):
        out.append(f"{first[0]:g} s montre « {NOT_RESULT.search(first[2]).group(0)} » : la première image doit être le résultat")
    split = any(x[2] and SPLIT.search(plain(x[2])) for x in slots)
    if split and any(VENIR.search(plain(" ".join(filter(None, x[1:])))) for x in slots):
        out.append("écran partagé et « À venir » dans la même accroche : les résultats se montrent par l'un ou l'autre, pas les deux")
    if title:
        mark, alert = title_line(" ".join(x[1] for x in slots if x[0] < 6), title, "6 s")
        if alert: out.append(alert)
    return out, mark

def timing(text, version):
    """worst minutage verdict over the opening slots of one version"""
    rank = {"ok": 0, "serré": 1, "dépasse": 2}
    prefix = f"version {version} " if version != "-" else ""
    res = [r for r in analyse(text) if r["creneau"].startswith(prefix) and r["creneau"].endswith(" s")
           and not r["creneau"].startswith("déroulé")]
    if not res: return "non mesuré"
    worst = max(res, key=lambda r: rank[r["verdict"]])
    return worst["verdict"] + (f" ({worst['creneau']})" if worst["verdict"] != "ok" else "")

def rate(hook, version=None, minutage=None, extra=(), titre=None):
    parts, verdict, name, hits = score(hook)
    r = {"hook": hook.strip(), "properties": parts, "verdict": verdict, "band": band(verdict),
         "formula": name, "matched": hits, "alertes": alertes(hook) + list(extra)}
    if version: r["version"] = version
    if minutage: r["minutage"] = minutage
    if titre: r["titre"] = titre
    return r

def hook_rate(hook, title):
    """a single hook: the title is checked on its first 20 words (6 s at the channel's pace)"""
    if not title: return rate(hook)
    mark, alert = title_line(" ".join(hook.split()[:round(6 * RATE)]), title, "6 s")
    return rate(hook, extra=[alert] if alert else [], titre=mark)

def table(out):
    rows = ["| Version | Score /100 | Formule détectée | Plus faible | Minutage | Titre avant 6 s |",
            "|---|---:|---|---|---|---|"]
    for r in out:
        low = min(r["properties"], key=r["properties"].get)
        rows.append(f"| {r['version']} | {r['verdict']} | {r['formula']} | {low} {r['properties'][low]} | {r['minutage']} "
                    f"| {r.get('titre', 'n.c.')} |")
    return "\n".join(rows)

def calibrer(as_json):
    d = json.load(open(CALIBRATION, encoding="utf-8"))
    rows = []
    for v in d["videos"]:
        if v.get("ouverture"):
            rows.append({"id": v["id"], "retention_30s": v["retention_30s"], "verdict": score(v["ouverture"])[1]})
    pairs = [(a, b) for i, a in enumerate(rows) for b in rows[i + 1:]
             if abs(a["retention_30s"] - b["retention_30s"]) >= 2]
    ok = sum(1 for a, b in pairs if (a["retention_30s"] - b["retention_30s"]) * (a["verdict"] - b["verdict"]) > 0)
    if as_json:
        print(json.dumps({"videos": rows, "paires": len(pairs), "dans_le_bon_ordre": ok}, indent=1, ensure_ascii=False))
        return
    print(f"\n  {'vidéo':<24} {'rétention 30 s':>14} {'note':>5}")
    for r in sorted(rows, key=lambda r: -r["retention_30s"]):
        print(f"  {r['id']:<24} {r['retention_30s']:>13.1f}% {r['verdict']:>5}")
    skipped = [v["id"] for v in d["videos"] if not v.get("ouverture")]
    if skipped:
        print(f"\n  sans ouverture transcrite (non comptées) : {', '.join(skipped)}")
    print(f"\n  {ok}/{len(pairs)} paires dans le bon ordre (écart de rétention d'au moins 2 points)")
    if len(rows) < 8:
        print(f"  {len(rows)} vidéo(s) : c'est un garde-fou, pas un calibrage (il en faut au moins 8).\n")

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    global PROPS
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if "--profil" in a:
        i = a.index("--profil"); PROPS = PROFILS[a[i + 1]]
        if a[i + 1] == "solo": FIX.update(FIX_SOLO)
        del a[i:i + 2]
    if "--calibrer" in a:
        calibrer(as_json); return
    title = None
    if "--titre" in a:
        i = a.index("--titre"); title = a[i + 1]; del a[i:i + 2]
    script = False
    if "--hook" in a:
        out = [hook_rate(a[a.index("--hook") + 1], title)]
    elif a and os.path.exists(a[0]):
        text = open(a[0], encoding="utf-8-sig").read()
        found = openings(text) if a[0].lower().endswith(".md") else []
        if a[0].lower().endswith(".md"):
            if not found:
                print("aucune ouverture minutée (« - **0-3 s** … : « … » ») trouvée dans ce script"); sys.exit(1)
            script = True
            title = title or script_title(a[0])
            out = []
            for v, t, slots in found:
                extra, mark = version_checks(slots, title)
                out.append(rate(t, v, timing(text, v), extra, mark))
            if title and not as_json:
                print(f"\n  titre comparé : « {title} »")
        else:
            out = [hook_rate(l, title) for l in text.splitlines() if l.strip()]
    else:
        print(__doc__); sys.exit(1 if not a else 0)
    if not script:
        out.sort(key=lambda r: -r["verdict"])
    if as_json:
        print(json.dumps([{k: v for k, v in r.items() if k != "matched"} for r in out], indent=1, ensure_ascii=False)); return
    for r in out:
        report(r)
    if script:
        print("\n" + table(out) + "\n")
    elif len(out) > 1:
        print(f"\n  winner: {out[0]['hook']}  ({out[0]['verdict']}, {out[0]['band']})\n")

if __name__ == "__main__":
    main()
