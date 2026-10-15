"""Musiques : catalogue, choix automatique par moment, recherche de nouveaux morceaux.   python scripts/musique.py <commande>

Demande du 2026-10-08 : varier les musiques sans qu'il ait à y penser, prendre pour chaque moment la meilleure parmi celles
qui restent (pas déjà prises récemment), réutiliser ce qui marche, et chercher du neuf (StreamBeats, Pixabay filtré) qu'il
écoute avant de le garder. Je n'entends pas : je mesure (profil_musique.py) et je m'appuie sur les étiquettes du catalogue.

  catalogue                       mesure les morceaux de musiques/perso/ et a_ecouter/ (tempo, durée, montée, meilleurs
                                  départs) dans musiques/catalogue.json ; liste ceux qui n'ont pas encore de moments
  choisir <id> [--short f.json] [--ecrire]
                                  pour chaque partie de video.json "musiques" (ou de la liste "musique" d'un Short) : le
                                  meilleur morceau de perso/ pour son moment, avec les 2 suivants et les raisons ; --ecrire
                                  remplace fichier et départ (le reste de la ligne ne bouge pas)
  chercher <moment> [--genre g …] [--nb 3] [--max 12] [--oui]
                                  StreamBeats (via Bandcamp, instrumentaux seulement) : mesure jusqu'à --max morceaux des
                                  genres du moment, classe, montre les --nb meilleurs ; --oui les télécharge dans a_ecouter/
  pixabay <resultats.json> <moment> [--nb 3] [--max 12] [--oui]
                                  idem avec des résultats Pixabay relevés dans le navigateur (extrait JS : références du
                                  skill montage-capcut, outils.md § Musiques) ; jamais d'IA ni de Content ID
  garder <morceau> [--moments a,b]   après son écoute : a_ecouter/ → perso/ (+ ligne dans LICENCES.md)
  refuser <morceau> [raison …]    après son écoute : supprimé, gardé dans le catalogue comme refusé (plus jamais proposé,
                                  et les morceaux qui lui ressemblent perdent des points)
  historique                      où chaque morceau a servi (vidéos et Shorts, le plus récent d'abord)
  ecoute                          page d'écoute a_ecouter/ecoute.html (lecteur, Garder / Refuser / J'hésite, moments) à ouvrir
                                  dans le navigateur intégré ; ses choix : window.verdicts() dans la page

Moments (video.json "moments_musique": {"partie": "moment"} pour forcer ; sinon déduit du nom de la partie) :
"""
import argparse, html, json, math, random, re, shutil, subprocess, sys, unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from profil_musique import UA, profil  # noqa: E402
from variete import ANCIENS, VIDEOS, date_de, lire  # noqa: E402

MUSIQUES = VIDEOS.parent.parent / "04_RESSOURCES" / "musiques"
PERSO, ECOUTE = MUSIQUES / "perso", MUSIQUES / "a_ecouter"
CATALOGUE = MUSIQUES / "catalogue.json"
LICENCES = MUSIQUES.parent / "LICENCES.md"
EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac")

# préférences § Musique (« une musique adaptée à chaque moment ») ; sb = genres StreamBeats, px = recherches Pixabay
MOMENTS = {
    "hook": dict(dit="épique / énergique, un peu plus haut (vraies batteries : gardées le 2026-10-08)", tempo=(110, 180),
                 fort=True, sb=["synthwave"], px=["epic drums", "drums epic action", "stomp percussion"], voisins=["verdict", "vainqueur"]),
    "explication": dict(dit="pizzicato malicieux", tempo=(85, 120), sb=["lofi", "hifi"],
                        px=["quirky", "pizzicato", "sneaky"], voisins=["comique", "decouverte"]),
    "decouverte": dict(dit="curieux / tech", tempo=(90, 125), sb=["synthwave", "lofi", "ambient"],
                       px=["curious", "technology", "mysterious"], voisins=["explication", "test"]),
    "test": dict(dit="synthwave / aventure jeu vidéo, pas trop rapide (l'IA joue, on teste ; au-delà de 120 BPM et chiptune pur "
                     "refusés le 2026-10-08)", tempo=(100, 120), sb=["synthwave"],
                 px=["video game adventure", "synthwave", "retro game"], voisins=["decouverte", "calme"]),
    "comique": dict(dit="pizzicato comique", tempo=(90, 140), sb=[], px=["funny", "comedy", "cartoon"],
                    voisins=["explication"]),
    "tension": dict(dit="suspense (bug, attente, échec)", tempo=(70, 120), sb=["ambient", "hip-hop"],
                    px=["suspense", "tension", "mystery"], voisins=["decouverte"]),
    "verdict": dict(dit="percussions épiques, vraies batteries (notes, comparaison ; beats hip-hop / edm et bande-annonce "
                        "orchestrale refusés le 2026-10-08)", tempo=(100, 135), fort=True, sb=[],
                    px=["epic drums", "percussion stomp", "drums action", "tribal drums"], voisins=["hook", "vainqueur"]),
    "vainqueur": dict(dit="retour du thème fort du hook", tempo=(100, 180), fort=True, sb=["edm", "synthwave"],
                      px=["epic", "victory"], voisins=["hook", "verdict"]),
    "fin": dict(dit="énergique ou lofi posé, jamais le « joyeux » corporate (cheerful, uplifting, positive : refusés le "
                    "2026-10-08)", tempo=(100, 125), sb=["lofi"], px=["percussion upbeat", "lofi upbeat", "drums groove"],
                voisins=["calme", "verdict"]),
    "calme": dict(dit="fond calme sous un long passage de jeu", tempo=(70, 105), sb=["lofi", "hifi"],
                  px=["lofi", "chill"], voisins=["test", "fin"]),
}
__doc__ += "\n".join(  # la liste des moments à la fin de l'aide
f"  {k:12s} {v['dit']}" for k, v in MOMENTS.items())
# nom de partie → moment (le premier qui correspond) ; à forcer avec "moments_musique" quand c'est faux
MOTS = [(r"hook|accroche|ouverture", "hook"), (r"vainqueur|gagnant|victoire", "vainqueur"),
        (r"verdict|note|comparaison|classement|score|duel", "verdict"), (r"\bfin\b|^fin|conclusion|outro", "fin"),
        (r"bug|echec|attente|tension|panne", "tension"), (r"blague|comique|fail|drole", "comique"),
        (r"jeu|test|partie|gameplay|essai", "test"), (r"decouverte|resultat|reveal", "decouverte"),
        (r"calme|chill", "calme")]
LICENCE = {
    "streambeats": "StreamBeats (Harris Heller) : gratuit, monétisation permise, sans attribution ; protégé du Content ID "
                   "(fausse réclamation : formulaire de streambeats.com)",
    "pixabay": "Licence Pixabay ; sans Content ID ni IA au moment du choix",
}


# ── outils ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def sans_accent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def page(url: str) -> str:
    """curl, pas urllib : Bandcamp renvoie une page de vérification à urllib."""
    return subprocess.run(["curl", "-sL", "-A", UA, url], capture_output=True).stdout.decode("utf-8", "replace")


def duree_de(path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 1)
    except ValueError:
        return 0.0


def mesurer(src, duree=None, limite=None) -> dict:
    """tempo, durée, montée (dB : meilleure fenêtre de 8 s − médiane) et 3 départs forts (s, écartés d'au moins 20 s)."""
    p = profil(src, limite)
    e = p["energie"]
    fin = len(e) - 3 - (0 if limite else 6)  # pas de départ dans les 12 dernières secondes (la fin du morceau)
    fen = [sum(e[i:i + 4]) / 4 for i in range(max(1, fin))] if e else [0.0]
    med = sorted(e)[len(e) // 2] if e else 0.0
    departs = []
    for i in sorted(range(len(fen)), key=lambda i: -fen[i]):
        if all(abs(i - j) >= 10 for j in departs):
            departs.append(i)
        if len(departs) == 3:
            break
    return {"duree": duree or duree_de(src), "tempo": p["tempo"][0], "montee": round(max(fen) - med, 1),
            "basse": p["basse"], "aigus": p["aigus"], "departs": [2 * i for i in departs]}


def charger() -> dict:
    cat = lire(CATALOGUE) or {}
    for k in ("morceaux", "refuses", "vus"):
        cat.setdefault(k, {} if k != "refuses" else [])
    return cat


def sauver(cat: dict):
    CATALOGUE.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")


def moment_de(cfg: dict, partie: str) -> str:
    force = cfg.get("moments_musique", {}).get(partie)
    if force:
        return force
    p = sans_accent(partie)
    return next((m for rx, m in MOTS if re.search(rx, p)), "explication")


def parties_short(entrees: list) -> list:
    """Moment d'un morceau de Short : "moment" s'il est écrit, sinon par position (1er hook, dernier vainqueur, test)."""
    n = len(entrees)
    return [e.get("moment") or ("hook" if i == 0 else "vainqueur" if i == n - 1 and n > 2 else "test")
            for i, e in enumerate(entrees)]


def usages(d: Path) -> list:
    """(fichier relatif à musiques/, moment, départ, "vidéo"|"short") de toutes les musiques d'un dossier de montage."""
    out, cfg = [], lire(d / "video.json")
    for m in cfg.get("musiques", []):
        out.append((Path(m[3]).as_posix(), moment_de(cfg, m[0]), m[4] if len(m) > 4 else 0, "vidéo"))
    for f in sorted(d.glob("short*.json")):
        mus = lire(f).get("musique") or []
        mus = [mus] if isinstance(mus, dict) else mus
        for e, mo in zip(mus, parties_short(mus)):
            if e.get("fichier") and not e.get("suite"):
                out.append((Path(e["fichier"]).as_posix(), mo, e.get("depart", 0), "short"))
    return out


def historique(vid: str = None) -> list:
    """Montages d'avant (ou tous), le plus récent d'abord : [{"id", "usages"}]."""
    jour = date_de(VIDEOS / vid) if vid else "9999"
    dirs = [d for d in VIDEOS.iterdir() if d.is_dir() and d.name != vid and (d.name in ANCIENS or not d.name.startswith("_"))
            and date_de(d) < jour]
    return [{"id": ANCIENS.get(d.name, d.name), "usages": usages(d)} for d in sorted(dirs, key=date_de, reverse=True)]


# ── catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def maj_catalogue(cat: dict, bavard=True) -> dict:
    fichiers = [p for dos in (PERSO, ECOUTE) if dos.exists() for p in sorted(dos.iterdir()) if p.suffix.lower() in EXT]
    for p in fichiers:
        k = f"{p.parent.name}/{p.name}"
        if k not in cat["morceaux"]:  # déplacé à la main de a_ecouter/ vers perso/ ?
            ancien = f"a_ecouter/{p.name}"
            if p.parent == PERSO and ancien in cat["morceaux"] and not (ECOUTE / p.name).exists():
                cat["morceaux"][k] = cat["morceaux"].pop(ancien) | {"avis": "gardée"}
            else:
                cat["morceaux"][k] = {"titre": p.stem, "source": "fourni" if p.parent == PERSO else "?", "moments": [],
                                      "humeur": [], "avis": "gardée" if p.parent == PERSO else "à écouter",
                                      "ajoute_le": date.today().isoformat()}
        t = cat["morceaux"][k]
        if t.get("mesure", {}).get("taille") != p.stat().st_size:
            if bavard:
                print(f"mesure de {k}…")
            t["mesure"] = mesurer(p) | {"taille": p.stat().st_size}
    presents = {f"{p.parent.name}/{p.name}" for p in fichiers}
    for k in cat["morceaux"]:
        if k not in presents and bavard:
            print(f"(info) {k} : dans le catalogue mais plus sur le disque")
    return cat


def cmd_catalogue(a):
    cat = maj_catalogue(charger())
    sauver(cat)
    for k, t in sorted(cat["morceaux"].items()):
        me = t.get("mesure", {})
        print(f"{k:40s} {t.get('avis', ''):10s} {', '.join(t.get('moments', [])) or '— À ÉTIQUETER —':28s} "
              f"{me.get('tempo', '?')} BPM  {me.get('duree', 0):.0f} s  montée {me.get('montee', 0):+.1f} dB  "
              f"départs forts {me.get('departs', [])}")
    vides = [k for k, t in cat["morceaux"].items() if not t.get("moments")]
    if vides:
        print(f"\nà étiqueter dans catalogue.json (moments parmi {', '.join(MOMENTS)}, humeur) : {', '.join(vides)}")
    print(f"refusés : {len(cat['refuses'])}  |  candidats déjà mesurés : {len(cat['vus'])}")


# ── choix ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def noter(k, t, moment, dur, choisis, hist):
    s, why = 0.0, []
    ms, me, M = t.get("moments", []), t.get("mesure", {}), MOMENTS.get(moment, MOMENTS["explication"])
    if moment in ms:
        s += 3 - 0.5 * ms.index(moment); why.append(f"fait pour « {moment} »")
    elif set(ms) & set(M["voisins"]):
        s += 1.5; why.append("moment voisin")
    elif ms:
        s -= 1; why.append("pas fait pour ce moment")
    else:
        why.append("pas étiqueté")
    lo, hi = M["tempo"]
    if me.get("tempo"):
        if lo <= me["tempo"] <= hi:
            s += 0.5
        else:
            s -= 0.5; why.append(f"tempo {me['tempo']} hors {lo}–{hi}")
    if M.get("fort") and me.get("montee", 0) >= 3:
        s += 0.5; why.append("a une vraie montée")
    pen, meme = 0.0, False
    for r, v in enumerate(hist[:4]):
        for f, mo, _, _ in v["usages"]:
            if f == k:
                pen += 1 / 2 ** r
                meme |= r == 0 and mo == moment
    if pen:
        s -= pen; why.append(f"pris récemment (−{pen:.1f})")
    if meme:
        s -= 2.5 if moment == "hook" else 1.5; why.append(f"déjà sur « {moment} » dans {hist[0]['id']}")
    if not any(f == k for v in hist for f, *_ in v["usages"]) and not any(c["k"] == k for c in choisis):
        s += 0.75; why.append("jamais utilisé : nouveauté")
    hook = next((c["k"] for c in choisis if c["moment"] == "hook"), None)
    n = sum(c["k"] == k for c in choisis)
    if moment == "vainqueur" and k == hook:
        s += 2; why.append("reprend le thème du hook")
    elif n:
        s -= 2 * n; why.append(f"déjà {n} fois dans la vidéo")
    if choisis and choisis[-1]["k"] == k:
        s -= 10; why.append("même morceau que la partie d'avant")
    if t.get("avis") == "favori":
        s += 0.75; why.append("favori")
    if dur and me.get("duree") and me["duree"] < dur:
        s -= 3; why.append(f"trop court ({me['duree']:.0f} s pour {dur:.0f} s)")
    return round(s, 2), why


def depart_pour(k, t, moment, dur, choisis, hist):
    me = t.get("mesure", {})
    D, forts = me.get("duree") or 0, me.get("departs", [])
    deja = [c for c in choisis if c["k"] == k]
    if deja and moment != "vainqueur":  # le même morceau revient : on le reprend où on l'avait laissé
        suite = deja[-1]["depart"] + (deja[-1]["dur"] or 0)
        if not dur or suite + dur <= D:
            return round(suite * 2) / 2
    pris = [dep for f, _, dep, _ in (hist[0]["usages"] if hist else []) if f == k]
    opts = forts + [0] if MOMENTS.get(moment, {}).get("fort") else [0] + forts
    for o in opts:
        if (not dur or o + dur <= D) and all(abs(o - p) > 5 for p in pris):
            return float(o)
    return float(max(0, min(opts[0], D - (dur or 0))))


def cmd_choisir(a):
    d = VIDEOS / a.id
    cfg = lire(d / "video.json")
    if not cfg:
        sys.exit(f"{d / 'video.json'} introuvable")
    cat = maj_catalogue(charger(), bavard=False)
    sauver(cat)
    if a.short:
        sc = lire(d / a.short)
        mus = sc.get("musique") or []
        mus = [mus] if isinstance(mus, dict) else mus
        parties = [(f"{i + 1}", mo, None) for i, mo in enumerate(parties_short(mus))]
    else:
        parties = [(m[0], moment_de(cfg, m[0]), m[2] - m[1]) for m in cfg.get("musiques", [])]
    if not parties:
        sys.exit("aucune partie : remplir d'abord video.json \"musiques\" (partie, début, fin, fichier provisoire, 0, 0)")
    hist = historique(a.id)
    vertical = a.short or cfg.get("format") == "vertical"  # OST (sous Content ID) : Shorts seulement, 2026-10-13
    dispo = {k: t for k, t in cat["morceaux"].items() if k.startswith("perso/") and (MUSIQUES / k).exists()
             and (vertical or not t.get("shorts_seulement"))}
    print(f"{a.id}{' / ' + a.short if a.short else ''} : {len(dispo)} morceaux dans perso/, comparée à "
          f"{', '.join(v['id'] for v in hist[:3]) or 'aucune vidéo'}")
    choisis, faibles = [], set()
    for i, (nom, moment, dur) in enumerate(parties):
        if a.short and mus[i].get("suite"):
            choisis.append(choisis[-1] | {"nom": nom}); print(f"  {nom:22s} (suite du morceau d'avant)"); continue
        notes = sorted(((noter(k, t, moment, dur, choisis, hist), k) for k, t in dispo.items()), key=lambda x: -x[0][0])
        (s, why), k = notes[0]
        dep = depart_pour(k, dispo[k], moment, dur, choisis, hist)
        choisis.append({"nom": nom, "k": k, "moment": moment, "depart": dep, "dur": dur})
        duree = f"{dur:5.1f} s" if dur else "      "
        print(f"  {nom:22s} {moment:11s} {duree} → {k} départ {dep:g} s  [{s:+.1f} : {', '.join(why)}]")
        autres = "  ".join(f"{k2} ({s2:+.1f})" for (s2, _), k2 in notes[1:3])
        if autres:
            print(f"  {'':22s} autres : {autres}")
        if s < 1:
            faibles.add(moment)
    for mo in sorted(faibles):
        print(f"→ rien de vraiment adapté pour « {mo} » parmi ce qui reste : python scripts/musique.py chercher {mo}"
              + (f"  (ou Pixabay : {', '.join(MOMENTS[mo]['px'])})" if mo in MOMENTS else ""))
    if a.ecrire:
        if a.short:
            for e, c in zip(mus, choisis):
                if not e.get("suite"):
                    e["fichier"], e["depart"] = c["k"], c["depart"]
            (d / a.short).write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            for m, c in zip(cfg["musiques"], choisis):
                m[3], m[4] = c["k"], c["depart"]
            (d / "video.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"écrit dans {a.short or 'video.json'}")


# ── recherche ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def classer(c, moment, cat):
    s, why = 0.0, []
    M, me = MOMENTS[moment], c["mesure"]
    lo, hi = M["tempo"]
    if lo <= me["tempo"] <= hi:
        s += 1 + 0.5 * (1 - abs(me["tempo"] - (lo + hi) / 2) / ((hi - lo) / 2)); why.append(f"tempo {me['tempo']}")
    else:
        dist = min(abs(me["tempo"] - lo), abs(me["tempo"] - hi))
        s -= min(2, dist / 15); why.append(f"tempo {me['tempo']} hors {lo}–{hi}")
    if M.get("fort") and me.get("montee", 0) >= 3:
        s += 0.5; why.append(f"montée {me['montee']:+.0f} dB")
    if c["duree"] >= 120:
        s += 0.5
    if c.get("telechargements"):
        s += min(1.5, math.log10(c["telechargements"] + 1) / 3); why.append(f"{c['telechargements']} téléchargements")
    if c.get("note"):
        s += (c["note"] - 5.5) / 2; why.append(f"note Pixabay {c['note']}")
    g = sans_accent(c.get("genre") or "")
    for k, t in cat["morceaux"].items():
        tm = t.get("mesure", {}).get("tempo")
        genres = {sans_accent(x) for x in [t.get("genre") or "", *t.get("humeur", [])]}
        if moment in t.get("moments", []) and tm and abs(tm - me["tempo"]) < 6 and g and g in genres:
            s -= 1; why.append(f"ressemble à {Path(k).name}"); break
    # ses goûts, appris à l'écoute : gardés (passés par a_ecouter/) contre refusés, par genre
    if g:
        k_ = sum(sans_accent(t.get("genre") or "") == g for t in cat["morceaux"].values() if t.get("garde_le"))
        r_ = sum(sans_accent(r.get("genre") or "") == g for r in cat["refuses"])
        if k_ or r_:
            s += 2 * (k_ - r_) / (k_ + r_ + 1); why.append(f"genre « {c['genre']} » : {k_} gardé(s), {r_} refusé(s)")
    for r in cat["refuses"]:
        if r.get("album") and r["album"] == c.get("album"):
            s -= 0.5; why.append(f"même album qu'un refusé"); break
    for r in cat["refuses"]:
        if r.get("genre") == c.get("genre") and r.get("tempo") and abs(r["tempo"] - me["tempo"]) < 6:
            s -= 1.5; why.append(f"ressemble à « {r['titre']} », refusé ({r.get('raison') or 'sans raison'})"); break
    return round(s, 2), why


def deja_connu(cat, url, titre="", auteur=""):
    """déjà dans le catalogue ou refusé (par lien, ou par titre et auteur pour les refusés d'avant le catalogue)."""
    if url in {t.get("url") for t in cat["morceaux"].values()} | {r.get("url") for r in cat["refuses"]}:
        return True
    nu = lambda x: re.sub(r"[^a-z0-9]", "", sans_accent(x or ""))
    return any(nu(titre) == nu(r["titre"]) and (not auteur or not r.get("auteur") or nu(auteur) == nu(r["auteur"]))
               for r in cat["refuses"] if not r.get("url") and titre)


def candidats_streambeats(a, cat):
    genres = a.genre or MOMENTS[a.moment]["sb"]
    if not genres:
        sys.exit(f"StreamBeats n'a pas de genre pour « {a.moment} » : passer par Pixabay ({', '.join(MOMENTS[a.moment]['px'])})")
    albums = []
    for g in genres:
        for slug in dict.fromkeys(re.findall(r'href="/album/([^"/?#]+)', page(f"https://www.streambeats.com/genre/{g}"))):
            albums.append((g, slug))
    rng = random.Random(f"{date.today()}{a.moment}")
    rng.shuffle(albums)
    out, mesures = [], 0
    for g, slug in albums:
        if mesures >= a.max:
            break
        m = re.search(r'data-tralbum="([^"]+)"', page(f"https://streambeats.bandcamp.com/album/{slug}"))
        if not m:
            continue
        j = json.loads(html.unescape(m.group(1)))
        pistes = [t for t in j.get("trackinfo", []) if t.get("file") and not t.get("has_lyrics") and (t.get("duration") or 0) >= 90]
        for t in rng.sample(pistes, min(3, len(pistes))):  # 3 par album au plus : de la variété
            url = "https://streambeats.bandcamp.com" + t["title_link"]
            if deja_connu(cat, url, t["title"], "StreamBeats"):
                continue
            if mesures >= a.max:  # déjà mesurés compris : la même commande redonne la même liste (pour --oui)
                break
            if url not in cat["vus"]:
                print(f"mesure : {t['title']} ({j['current']['title']}, {g})…")
                cat["vus"][url] = {"titre": t["title"], "mesure": mesurer(t["file"]["mp3-128"], t["duration"], 150)}
            mesures += 1
            out.append({"titre": t["title"], "auteur": "StreamBeats", "album": j["current"]["title"], "genre": g,
                        "url": url, "src": t["file"]["mp3-128"], "duree": t["duration"], "source": "streambeats",
                        "mesure": cat["vus"][url]["mesure"]})
    return out


def candidats_pixabay(a, cat):
    brut = json.loads(Path(a.resultats).read_text(encoding="utf-8-sig"))
    out, mesures = [], 0
    for r in brut:
        if r.get("ia") or r.get("cid") or (r.get("duree") or 0) < 90 or deja_connu(cat, r["page"], r["nom"], r["auteur"]):
            continue
        if mesures >= a.max:
            break
        if r["page"] not in cat["vus"]:
            print(f"mesure : {r['nom']} ({r['auteur']})…")
            cat["vus"][r["page"]] = {"titre": r["nom"], "mesure": mesurer(r["src"], r["duree"], 150)}
        mesures += 1
        out.append({"titre": r["nom"], "auteur": r["auteur"], "genre": r.get("genre") or "", "url": r["page"],
                    "src": r["src"], "duree": r["duree"], "source": "pixabay", "telechargements": r.get("telech", 0), "note": r.get("note"),
                    "mesure": cat["vus"][r["page"]]["mesure"]})
    return out


def nom_fichier(c):
    base = re.sub(r'[\\/:*?"<>|]+', "", f"{c['titre']} - {c['auteur']}").strip()
    return f"{base}.mp3"


def cmd_chercher(a):
    if a.moment not in MOMENTS:
        sys.exit(f"moment inconnu : {a.moment} (parmi {', '.join(MOMENTS)})")
    cat = maj_catalogue(charger(), bavard=False)
    cands = candidats_pixabay(a, cat) if a.cmd == "pixabay" else candidats_streambeats(a, cat)
    sauver(cat)  # garde les mesures (pas besoin de remesurer au --oui)
    if not cands:
        sys.exit("aucun candidat (tout est déjà connu ou refusé : changer de genre ou de recherche)")
    notes = sorted(((classer(c, a.moment, cat), c) for c in cands), key=lambda x: -x[0][0])
    print(f"\n{len(cands)} candidats pour « {a.moment} » ({MOMENTS[a.moment]['dit']}), les {a.nb} meilleurs :")
    gardes = [c for _, c in notes[:a.nb]]
    for (s, why), c in notes[:a.nb]:
        print(f"  {s:+.1f}  {c['titre']} — {c['auteur']} ({c.get('album') or c['genre']}, {c['duree']:.0f} s, "
              f"~{c['duree'] * 16 / 1000:.1f} Mo)  {', '.join(why)}\n        {c['url']}")
    if not a.oui:
        print("\npour les télécharger dans musiques/a_ecouter/ : même commande avec --oui (après son accord)")
        return
    ECOUTE.mkdir(parents=True, exist_ok=True)
    for c in gardes:
        dest = ECOUTE / nom_fichier(c)
        src = c["src"]
        if c["source"] == "streambeats":  # le lien de lecture expire : on le relit sur la page du morceau
            m = re.search(r'data-tralbum="([^"]+)"', page(c["url"]))
            src = json.loads(html.unescape(m.group(1)))["trackinfo"][0]["file"]["mp3-128"] if m else src
        subprocess.run(["curl", "-sL", "-A", UA, "-o", str(dest), src], check=True)
        cat["morceaux"][f"a_ecouter/{dest.name}"] = {
            "titre": c["titre"], "source": c["source"], "auteur": c["auteur"], "album": c.get("album", ""),
            "genre": c["genre"], "url": c["url"], "licence": LICENCE[c["source"]], "moments": [a.moment],
            "humeur": [c["genre"]] if c["genre"] else [], "avis": "à écouter", "ajoute_le": date.today().isoformat()}
        print(f"  → a_ecouter/{dest.name}")
    sauver(maj_catalogue(cat, bavard=False))
    print("à lui de les écouter : python scripts/musique.py garder <morceau>  ou  refuser <morceau> <raison>")


# ── verdict après écoute ──────────────────────────────────────────────────────────────────────────────────────────────
def trouver(cat, nom):
    ks = [k for k in cat["morceaux"] if k.startswith("a_ecouter/") and sans_accent(nom) in sans_accent(k)]
    if len(ks) != 1:
        sys.exit(f"« {nom} » : {len(ks)} morceaux à écouter correspondent ({', '.join(ks) or 'aucun'})")
    return ks[0]


def cmd_garder(a):
    cat = charger()
    k = trouver(cat, a.morceau)
    src, dst = MUSIQUES / k, PERSO / Path(k).name
    if dst.exists():
        sys.exit(f"{dst} existe déjà")
    shutil.move(src, dst)
    t = cat["morceaux"].pop(k) | {"avis": "gardée", "garde_le": date.today().isoformat()}
    if a.moments:
        t["moments"] = a.moments.split(",")
    cat["morceaux"][f"perso/{dst.name}"] = t
    sauver(cat)
    ligne = (f"| {dst.name} | {t['titre']} | {t.get('auteur', '')} ({t['source']}) | {t.get('licence', '?')} | "
             f"{t.get('url', '')} | {date.today().isoformat()} |\n")
    txt = LICENCES.read_text(encoding="utf-8")
    i = txt.index("\n## Sound effects")
    LICENCES.write_text(txt[:i].rstrip("\n") + "\n" + ligne + txt[i:], encoding="utf-8")
    print(f"gardé : perso/{dst.name} (moments : {', '.join(t['moments'])}) ; ligne ajoutée dans LICENCES.md")


def cmd_refuser(a):
    cat = charger()
    k = trouver(cat, a.morceau)
    t = cat["morceaux"].pop(k)
    (MUSIQUES / k).unlink(missing_ok=True)
    cat["refuses"].append({"titre": t["titre"], "source": t.get("source"), "url": t.get("url"), "album": t.get("album"),
                           "genre": t.get("genre"), "tempo": t.get("mesure", {}).get("tempo"),
                           "raison": " ".join(a.raison), "le": date.today().isoformat()})
    sauver(cat)
    print(f"refusé et supprimé : {k}")


PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Musiques à écouter</title><style>
:root{--fond:#f6f5f2;--carte:#fff;--texte:#1d1d1f;--doux:#6b6b70;--trait:#e2e0da;--vert:#1f8a4c;--rouge:#c23b32;--ambre:#b7791f}
@media (prefers-color-scheme:dark){:root{--fond:#161618;--carte:#222226;--texte:#ececef;--doux:#9a9aa2;--trait:#34343a;--vert:#3fbf75;--rouge:#e5645a;--ambre:#e0a64a}}
body{margin:0;background:var(--fond);color:var(--texte);font:15px/1.45 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 120px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px}
.aide{color:var(--doux);margin:0 0 8px}.carte{background:var(--carte);border:1px solid var(--trait);border-radius:10px;padding:14px;margin:10px 0}
.haut{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}.titre{font-weight:600}.meta{color:var(--doux);font-size:13px}
audio{width:100%;margin:10px 0 6px}.ligne{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;margin-top:6px}
.choix label{border:1px solid var(--trait);border-radius:20px;padding:4px 12px;cursor:pointer}
.choix input{margin-right:6px}.choix label:has(input[value=garder]:checked){border-color:var(--vert);color:var(--vert)}
.choix label:has(input[value=refuser]:checked){border-color:var(--rouge);color:var(--rouge)}
.choix label:has(input[value=hesite]:checked){border-color:var(--ambre);color:var(--ambre)}
.moments label{font-size:13px;color:var(--doux)}input[type=text]{flex:1;min-width:200px;padding:6px 8px;border:1px solid var(--trait);border-radius:6px;background:var(--fond);color:var(--texte)}
button.saut{font-size:12px;padding:3px 8px;border:1px solid var(--trait);border-radius:6px;background:none;color:var(--texte);cursor:pointer}
a{color:inherit}#bilan{position:fixed;left:0;right:0;bottom:0;background:var(--carte);border-top:1px solid var(--trait);padding:10px 16px;text-align:center;font-size:14px}
</style></head><body><main><h1>Musiques à écouter</h1>
<p class="aide">Écoute, puis coche <b>Garder</b>, <b>Refuser</b> ou <b>J'hésite</b>. Les moments cochés disent où tu la vois. Une raison
pour un refus m'aide à ne plus proposer le même genre. Tu peux me dire « c'est fait » dans le chat : je lis la page.</p>
__CARTES__</main><div id="bilan"></div><script>
const maj=()=>{const c=[...document.querySelectorAll('.carte[data-k]')].filter(x=>x.querySelector('.choix input'));const n=v=>c.filter(x=>x.querySelector('input[value='+v+']:checked')).length;
document.getElementById('bilan').textContent=`${n('garder')} gardées · ${n('refuser')} refusées · ${n('hesite')} hésitations · ${c.length-n('garder')-n('refuser')-n('hesite')} pas encore écoutées`;};
document.addEventListener('change',maj);maj();
document.querySelectorAll('button.saut').forEach(b=>b.onclick=()=>{const a=b.closest('.carte').querySelector('audio');a.currentTime=+b.dataset.t;a.play();});
window.verdicts=()=>[...document.querySelectorAll('.carte[data-k]')].map(c=>({k:c.dataset.k,avis:(c.querySelector('.choix input:checked')||{}).value||null,
moments:[...c.querySelectorAll('.moments input:checked')].map(i=>i.value),raison:(c.querySelector('input[type=text]')||{}).value||''}));
</script></body></html>"""


def cmd_ecoute(a):
    """Page d'écoute (a_ecouter/ecoute.html) : un lecteur par morceau, Garder / Refuser / J'hésite, moments ; je relis
    ses choix dans le navigateur intégré (window.verdicts()). Ses morceaux de perso/ en bas, pour corriger leurs moments."""
    from urllib.parse import quote
    cat = maj_catalogue(charger(), bavard=False)
    sauver(cat)
    esc = html.escape

    def carte(k, t, avis=True):
        me, rel = t.get("mesure", {}), quote(Path(k).name) if k.startswith("a_ecouter/") else "../" + quote(k)
        sauts = " ".join(f'<button class="saut" data-t="{d}">passage fort {d // 60}:{d % 60:02d}</button>' for d in me.get("departs", [])[:2])
        lien = f' · <a href="{esc(t["url"])}" target="_blank">page</a>' if t.get("url") else ""
        choix = "".join(f'<label><input type="radio" name="{esc(k)}" value="{v}">{l}</label>'
                        for v, l in (("garder", "Garder"), ("refuser", "Refuser"), ("hesite", "J'hésite"))) if avis else ""
        moms = "".join(f'<label><input type="checkbox" value="{m}"{" checked" if m in t.get("moments", []) else ""}>{m}</label>'
                       for m in MOMENTS)
        raison = '<input type="text" placeholder="raison (si refus) ou remarque">' if avis else \
            '<input type="text" placeholder="remarque (ex. super sur le hook, trop calme pour un verdict)">'
        return (f'<div class="carte" data-k="{esc(k)}"><div class="haut"><span class="titre">{esc(t["titre"])}</span>'
                f'<span class="meta">{esc(t.get("auteur") or t.get("source", ""))} · {esc(t.get("genre") or ", ".join(t.get("humeur", [])))} · '
                f'{me.get("tempo", "?")} BPM · {me.get("duree", 0) // 60:.0f}:{me.get("duree", 0) % 60:02.0f}{lien}</span></div>'
                f'<audio controls preload="none" src="{rel}"></audio><div class="ligne">{sauts}</div>'
                f'<div class="ligne choix">{choix}</div><div class="ligne moments">{moms}</div><div class="ligne">{raison}</div></div>')

    a_ecouter = {k: t for k, t in cat["morceaux"].items() if k.startswith("a_ecouter/") and (MUSIQUES / k).exists()}
    blocs = []
    for mo in MOMENTS:
        ks = [k for k, t in a_ecouter.items() if (t.get("moments") or ["?"])[0] == mo]
        if ks:
            blocs.append(f"<h2>Pour « {mo} » ({esc(MOMENTS[mo]['dit'])})</h2>" + "".join(carte(k, a_ecouter[k]) for k in ks))
    perso = {k: t for k, t in cat["morceaux"].items() if k.startswith("perso/") and (MUSIQUES / k).exists()}
    blocs.append("<h2>Ta bibliothèque : les bons moments ?</h2>" + "".join(carte(k, t, avis=False) for k, t in sorted(perso.items())))
    ECOUTE.mkdir(parents=True, exist_ok=True)
    out = ECOUTE / "ecoute.html"
    out.write_text(PAGE.replace("__CARTES__", "\n".join(blocs)), encoding="utf-8")
    print(f"{len(a_ecouter)} à écouter → {out}  (navigateur intégré : file:///{out.as_posix()} ; ses choix : window.verdicts())")


def cmd_historique(a):
    par = {}
    for v in historique():
        for f, mo, dep, genre in v["usages"]:
            par.setdefault(f, []).append(f"{v['id']}{' (short)' if genre == 'short' else ''}:{mo}@{dep:g}")
    cat = charger()
    for k in sorted(set(par) | {k for k in cat["morceaux"] if k.startswith("perso/")}):
        print(f"{k:40s} {', '.join(par.get(k, [])) or 'jamais utilisé'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalogue")
    p = sub.add_parser("choisir"); p.add_argument("id"); p.add_argument("--short"); p.add_argument("--ecrire", action="store_true")
    for nom in ("chercher", "pixabay"):
        p = sub.add_parser(nom)
        if nom == "pixabay":
            p.add_argument("resultats")
        p.add_argument("moment"); p.add_argument("--genre", nargs="*"); p.add_argument("--nb", type=int, default=3)
        p.add_argument("--max", type=int, default=12); p.add_argument("--oui", action="store_true")
    p = sub.add_parser("garder"); p.add_argument("morceau"); p.add_argument("--moments")
    p = sub.add_parser("refuser"); p.add_argument("morceau"); p.add_argument("raison", nargs="*")
    sub.add_parser("historique")
    sub.add_parser("ecoute")
    a = ap.parse_args()
    {"ecoute": cmd_ecoute, "catalogue": cmd_catalogue, "choisir": cmd_choisir, "chercher": cmd_chercher, "pixabay": cmd_chercher,
     "garder": cmd_garder, "refuser": cmd_refuser, "historique": cmd_historique}[a.cmd](a)


if __name__ == "__main__":
    main()
