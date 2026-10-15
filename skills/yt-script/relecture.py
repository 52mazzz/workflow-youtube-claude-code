#!/usr/bin/env python3
"""relecture.py - relit un script.md entier avant de le montrer : accroches, minutage, structure, voix.

    python relecture.py videos/<id>/script.md          # rapport ; code 1 s'il reste une ALERTE
    python relecture.py videos/<id>/script.md --json

Ce qui est contrôlé (règles de nouvelle-video/references/accroches-script.md, phase 4, et du skill yt-script) :
  ACCROCHES  2 versions au moins ; le tableau de hookscore.py collé dans script.md a les notes d'aujourd'hui ;
             les alertes de hookscore.py (salut, chaîne, abonnement, « tu », titre non confirmé avant 6 s,
             première image qui n'est pas un résultat).
  MINUTAGE   aucun créneau ni beat ne déborde (minutage.py).
  BEATS      dans l'ordre, sans trou ni chevauchement ; un [ON SCREEN] par beat ; mise en place finie à 0:45 ;
             verdict en 20 s au plus, avec sa raison.
  VOIX       une seule demande au spectateur, dans le dernier beat ; pas d'abonnement, pas de « tu », pas de
             « salut » ni de « avant de commencer » avant la fin ; un prompt montré est dit « dans la description ».
  À VÉRIFIER (sans effet sur le code de sortie) : premier test après 1:00, tests hors de 20 à 45 s, crochets sans
             budget de mots, créneaux serrés, durée écrite.

Un script sans beats (un Short) n'a que les deux premiers contrôles. Passer la relecture ne dit pas que le script est
bon : elle retire ce qui se voit mécaniquement, pour que la relecture humaine porte sur le fond.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hookscore  # noqa: E402
from minutage import BEAT, PLACE, RATE, SLOT, analyse, said  # noqa: E402

TEST = re.compile(r"\b(test|manche|épreuve)\b", re.I)
ACTION = re.compile(r"\b(génération|test|manche|épreuve|essai|résultat|partie)\b", re.I)
ASK = re.compile(r"\b(dites[- ]moi|écrivez|en commentaires?|dans les commentaires|abonn\w*|like|pouce|cloche"
                 r"|partagez|regardez (aussi|cette|la vidéo))\b", re.I)
TU = re.compile(r"\b(tu|toi|ton|ta|tes|t'as|t'es)\b", re.I)
EARLY = re.compile(r"\b(salut|bienvenue|coucou|avant de commencer|n'oubliez pas)\b", re.I)
REASON = re.compile(r"\b(parce que|parce qu|car|grâce à|à cause de)\b", re.I)


def ask_kind(word):
    """« Dites-moi dans les commentaires » is one ask, « … et abonnez-vous » a second"""
    w = word.lower()
    if re.match(r"dites|écrivez|en comm|dans les comm", w): return "commentaire"
    if w.startswith("abonn"): return "abonnement"
    if w in ("like", "pouce"): return "like"
    return w


def mmss(s): return f"{int(s) // 60}:{int(s) % 60:02d}"


def beats(text):
    """[{nom, debut, fin, lignes, dit, dit_principal}] of the « ## Beat N. … (m:ss à m:ss) » sections"""
    out, cur = [], None
    for line in text.splitlines():
        m = BEAT.match(line)
        if m:
            cur = {"nom": m.group(1).strip(), "debut": int(m.group(2)) * 60 + int(m.group(3)),
                   "fin": int(m.group(4)) * 60 + int(m.group(5)), "lignes": [], "dit": [], "dit_principal": [],
                   "variante": False}
            out.append(cur)
            continue
        if line.startswith("## "):
            cur = None
        if cur is None:
            continue
        cur["lignes"].append(line)
        if re.match(r"^\s*\*\*Cas\b", line):
            cur["variante"] = True
        if line.startswith(">") or re.match(r"^\s*-\s", line) or re.match(r"^\s*\*\*Cas\b", line):
            s = said(line.split("**", 2)[-1] if line.lstrip().startswith("**Cas") else line)
            if s:
                cur["dit"].append(s)
                if not cur["variante"]:
                    cur["dit_principal"].append(s)
    return out


def hook_table(text):
    """{version: note} read from the pasted « | Version | Score /100 | … » table"""
    notes, inside = {}, False
    for line in text.splitlines():
        if re.match(r"^\|\s*Version\s*\|\s*Score", line):
            inside = True
            continue
        if inside:
            m = re.match(r"^\|\s*([A-Z0-9]+)\b[^|]*\|\s*(\d+)\s*\|", line)
            if m:
                notes[m.group(1)] = int(m.group(2))
            elif not line.startswith("|"):
                inside = False
    return notes


def relire(path):
    text = open(path, encoding="utf-8-sig").read()
    alertes, verifier, ok = [], [], []

    # ACCROCHES
    title = hookscore.script_title(path)
    found = hookscore.openings(text)
    rated = []
    for v, t, slots in found:
        extra, mark = hookscore.version_checks(slots, title)
        rated.append(hookscore.rate(t, v, hookscore.timing(text, v), extra, mark))
    if len(found) < 2:
        alertes.append(f"{len(found)} version(s) d'accroche minutée(s) : il en faut 3 écrites, 2 gardées")
    pasted = hook_table(text)
    if rated:
        stale = [f"{r['version']} {pasted[r['version']]} au lieu de {r['verdict']}" for r in rated
                 if r["version"] in pasted and pasted[r["version"]] != r["verdict"]]
        if not pasted:
            alertes.append("tableau de hookscore.py absent de script.md : le coller")
        elif stale:
            alertes.append("tableau des accroches périmé (" + ", ".join(stale) + ") : recoller celui de hookscore.py")
        else:
            ok.append(f"accroches : {len(rated)} versions, tableau à jour")
        for r in rated:
            for a in r["alertes"]:
                alertes.append(f"accroche {r['version']} : {a}")

    # MINUTAGE
    res = analyse(text)
    over = [r for r in res if r["verdict"] == "dépasse"]
    tight = [r for r in res if r["verdict"] == "serré"]
    for r in over:
        alertes.append(f"minutage : {r['creneau']} déborde ({r['mots']} mots pour {r['duree_s']:g} s, {r['mots_max']} au plus)")
    for r in tight:
        verifier.append(f"minutage : {r['creneau']} serré ({r['mots']} mots pour {r['duree_s']:g} s)")
    if res and not over:
        ok.append(f"minutage : {len(res)} créneaux, aucun ne déborde")

    # BEATS
    bs = beats(text)
    if not bs:
        verifier.append("aucun « ## Beat N. … (m:ss à m:ss) » : contrôles des beats sautés (normal pour un Short)")
    else:
        holes = []
        for a, b in zip(bs, bs[1:]):
            if b["debut"] != a["fin"]:
                kind = "trou" if b["debut"] > a["fin"] else "chevauchement"
                holes.append(f"{kind} entre « {a['nom']} » ({mmss(a['fin'])}) et « {b['nom']} » ({mmss(b['debut'])})")
        alertes += [f"beats : {h}" for h in holes]
        blind = [b["nom"] for b in bs if not any("[ON SCREEN" in l for l in b["lignes"])]
        alertes += [f"« {n} » sans [ON SCREEN] : dire ce qu'on voit" for n in blind]
        if not holes and not blind:
            ok.append(f"beats : {len(bs)} dans l'ordre, chacun avec son [ON SCREEN]")
        first_action = next((b for b in bs[1:] if ACTION.search(b["nom"])), None)
        if first_action and first_action["debut"] > 45:
            alertes.append(f"mise en place finie à {mmss(first_action['debut'])} (« {first_action['nom']} ») : 0:45 au plus")
        first_test = next((b for b in bs if TEST.search(b["nom"])), None)
        if first_test and first_test["debut"] > 60:
            verifier.append(f"premier test à {mmss(first_test['debut'])} : un résultat doit être à l'image avant 1:00 "
                            "(le beat d'avant le montre-t-il ?)")
        for b in bs:
            d = b["fin"] - b["debut"]
            if TEST.search(b["nom"]) and not 20 <= d <= 45:
                verifier.append(f"« {b['nom']} » dure {d} s (20 à 45 s par test)")
        verdict = next((b for b in bs if re.search(r"\bverdict\b", b["nom"], re.I)), None)
        if verdict:
            d = verdict["fin"] - verdict["debut"]
            if d > 20:
                alertes.append(f"verdict en {d} s : 20 s au plus, le score dit déjà presque tout")
            if not REASON.search(" ".join(verdict["dit_principal"])):
                alertes.append("verdict sans sa raison : « le gagnant, c'est X, parce que … »")
        unbudgeted = sum(1 for b in bs[1:] for s in b["dit_principal"] for p in PLACE.findall(s)
                         if not re.search(r"\d+\s*mots", p))
        if unbudgeted:
            verifier.append(f"{unbudgeted} crochets sans budget de mots dans les beats : le minutage ne les compte pas, "
                            "la durée réelle se jouera au tournage")

        # VOIX
        last = bs[-1]
        spoken = [(b, s) for b in bs for s in b["dit"]]   # the opening's versions are hookscore's job (above)
        for b, s in spoken:
            m = ASK.search(s)
            if m and b is not last:
                alertes.append(f"demande au spectateur dans « {b['nom']} » (« {m.group(0)} ») : une seule, à la fin")
            if re.search(r"\babonn", s, re.I):
                alertes.append(f"abonnement demandé dans « {b['nom']} »")
            m = TU.search(s)
            if m:
                alertes.append(f"« {m.group(0)} » dit au spectateur dans « {b['nom']} » : la chaîne vouvoie")
            m = EARLY.search(s)
            if m and b is not last:
                alertes.append(f"« {m.group(0)} » dans « {b['nom']} » : rien avant d'avoir donné quelque chose")
        kinds = {ask_kind(m.group(0)) for s in last["dit_principal"] for m in ASK.finditer(s)}
        if len(kinds) > 1:
            alertes.append(f"{len(kinds)} demandes dans « {last['nom']} » : une seule")
        elif not kinds:
            verifier.append(f"aucune demande dans « {last['nom']} » : la demande finale demande le prochain jeu")
        if "```" in text and not any(re.search(r"description", s, re.I) for _, s in spoken):
            alertes.append("un prompt est montré mais jamais annoncé « dans la description »")

        words = sum(r["mots"] for r in res if not r.get("creneau", "").startswith("version"))
        words += max((sum(r["mots"] for r in res if r["creneau"].startswith(f"version {v} ")) for v, _, _ in found), default=0)
        verifier.append(f"voix écrite : {words} mots, {words / RATE / 60:.1f} min à {RATE * 60:.0f} mots/min, pour un "
                        f"conducteur de {mmss(bs[-1]['fin'])} : le reste vient des réactions au tournage")
    return {"script": path, "alertes": alertes, "a_verifier": verifier, "ok": ok,
            "tableau": hookscore.table(rated) if rated else None}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = [x for x in sys.argv[1:] if x != "--json"]
    if not a or not os.path.exists(a[0]):
        print(__doc__); sys.exit(1)
    r = relire(a[0])
    if "--json" in sys.argv:
        print(json.dumps(r, indent=1, ensure_ascii=False))
    else:
        print(f"\n  Relecture de {r['script']}\n")
        for x in r["alertes"]:
            print(f"  ALERTE      {x}")
        for x in r["a_verifier"]:
            print(f"  À VÉRIFIER  {x}")
        for x in r["ok"]:
            print(f"  ok          {x}")
        if r["tableau"] and any("tableau" in x for x in r["alertes"]):
            print("\n  Tableau à coller dans script.md :\n\n" + r["tableau"])
        print("\n  " + ("Corriger les alertes, puis relancer." if r["alertes"] else
                       "Aucune alerte. Reste la relecture à voix haute, chronomètre en main.") + "\n")
    sys.exit(1 if r["alertes"] else 0)


if __name__ == "__main__":
    main()
