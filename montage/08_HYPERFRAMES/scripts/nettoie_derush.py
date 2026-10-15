"""Nettoie une liste de dérushage (02_ANALYSE/derush_<id>_*.json) avant de la poser : ce que l'utilisateur a reproché
au premier montage de pokemon-ia (2026-10-03) — prises ratées gardées avant la bonne, mots coupés, blancs trop longs.

  1. bords : chaque clip commence et finit dans un silence de la voix (jamais au milieu d'un mot) ;
  2. blancs : un silence plus long que --blanc (0,3 s, voix seule ou rush de jeu : style WOLF, méthode par défaut depuis
     le 2026-10-06 ; avant : 0,35 et 0,5) est raccourci (le clip est coupé en deux, une marge reste de part et d'autre :
     0,28 s de blanc en tout, sous les 0,3 s que WOLF dépasse moins de 3 fois par minute ; un silence plus court que ces
     marges n'est jamais touché, il serait rallongé). Un passage sans voix d'après le VAD compte
     aussi comme un blanc, même avec des clics ou le son du jeu (navigation dans un menu : « 5 s, c'est trop »,
     2026-10-03). Un moment de jeu sans parole à garder : "garder": {"<rush>": [[début, fin], …]} dans la liste ;
  3. redites : chaque clip est retranscrit seul (whisper, DTW) et les mêmes 2 mots ou plus dits deux fois à moins de
     12 mots d'écart sont signalés (« il me demande quelle… il me demande quelle direction visuelle… »). Une énumération
     voulue (« il n'y a pas de crédit, il n'y a pas de fin ») ressemble à une redite : la liste est relue, puis les
     retraits acceptés sont passés avec --retirer (ou écrits dans "retirer" de la liste) ;
  4. faux départs dans un même bloc : début de phrase redit après une hésitation (« et en vrai, et en vrai, c'est… »),
     signalés avec le passage à retirer.

Usage : python scripts/nettoie_derush.py <liste.json> [--appliquer] [--blanc 0.6] [--rapport-seul]
  sans --appliquer : rapport seulement (02_ANALYSE/<liste>.nettoyage.txt) ;
  --appliquer : écrit les bords, les blancs et les retraits de "retirer" dans la liste (sauvegarde .avant-nettoyage.json dans le dossier temporaire).
La liste peut contenir "retirer": {"<rush>": [[début, fin], …]} (secondes du rush) : passages retirés des clips.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import audio16k, seuil_silence, voix  # noqa: E402
from commun import rush as chemin_rush  # noqa: E402
from verify_cuts import PAD, extract, norm, transcribe_many  # noqa: E402

DTW_LAG = 0.12
LEGIT = {"lets", "go", "bref", "super", "non", "oui", "ok", "ouais"}  # répétitions voulues fréquentes
VIDES = {"il", "a", "de", "la", "le", "les", "des", "et", "en", "un", "une", "est", "cest", "que", "qui", "du", "au",
         "on", "y", "ca", "pas", "ne", "se", "sa", "son", "ses", "dans", "sur", "pour"}  # « il a… il a » : pas un faux départ


def opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def silences(path, a, b, th):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(audio16k(path)),
                          "-vn", "-af", f"silencedetect=n={th}dB:d=0.25", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8").stderr
    st = [a + float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [a + float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    en += [b] * (len(st) - len(en))
    return [(max(s, a), e) for s, e in zip(st, en)]


_VOIX = {}


def sans_voix(path, a, b, garder=()):
    """Passages sans voix de [a, b] d'après le VAD (clics, son du jeu, menus), hors passages à garder. [] sans VAD."""
    if path not in _VOIX:
        _VOIX[path] = voix(path, pad_ms=100)
    parle = _VOIX[path]
    if parle is None:
        return []
    out, cur = [], a
    for s, e in parle:
        if e <= a or s >= b:
            continue
        if s > cur:
            out.append((cur, s))
        cur = max(cur, e)
    if cur < b:
        out.append((cur, b))
    return [(x, y) for x, y in out if not any(gx < y and gy > x for gx, gy in garder)]


def fusion(intervalles):
    out = []
    for x, y in sorted(intervalles):
        if out and x <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], y))
        else:
            out.append((x, y))
    return out


def faux_departs(ws, ecart=6):
    """Début de phrase redit dans un même bloc après une hésitation (« et en vrai, et en vrai, c'est… ») :
    [(début de la 1re fois, début de la reprise, mots)]. ws = [(mot, début, fin)]."""
    w = [x[0] for x in ws]
    out, i = [], 0
    while i < len(w):
        for k in (4, 3, 2):
            g = w[i:i + k]
            if len(g) < k or set(g) <= LEGIT or (k == 2 and set(g) <= VIDES):
                continue
            j = next((j for j in range(i + k, min(i + k + ecart, len(w) - k) + 1) if w[j:j + k] == g), None)
            if j is not None:
                out.append((ws[i][1], ws[j][1], " ".join(w[i:j])))
                i = j
                break
        else:
            i += 1
    return out


def bornes(path, a, b, gap, garder=()):
    """Bords calés sur les silences (ou passages sans voix) et blancs raccourcis → liste de (début, fin)."""
    pre, post = 0.1, 0.18  # resserré le 2026-10-03 (« trop de blanc »), puis le 2026-10-07 (WOLF : mêmes marges sur le jeu)
    sil = fusion(silences(path, max(0.0, a - 1.5), b + 1.5, seuil_silence(path))
                 + sans_voix(path, max(0.0, a - 1.5), b + 1.5, garder))
    inside = lambda t: next((s for s in sil if s[0] <= t <= s[1]), None)  # noqa: E731
    s = inside(a)
    if s:
        a = max(a, s[1] - pre)
    else:
        prev = [x for x in sil if x[1] <= a and a - x[1] < 0.4]
        a = prev[-1][1] - 0.05 if prev else a
    s = inside(b)
    if s:
        b = min(b, s[0] + post)
    else:
        nxt = [x for x in sil if x[0] >= b and x[0] - b < 0.3]  # 0,3 s au plus : au-delà on reprendrait une prise retirée
        b = nxt[0][0] + post if nxt else b
    out, cur = [], a
    for s0, s1 in sil:
        if s0 > cur + 0.05 and s1 < b - 0.05 and s1 - s0 > max(gap, pre + post + 0.02):
            out.append((cur, s0 + post))
            cur = s1 - pre
    out.append((cur, b))
    return out


def blocs_voix(path, a, b):
    """Passages parlés de [a, b] séparés par des pauses d'au moins 0,08 s (une reprise suit parfois à 0,15 s) → [(début, fin)]."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(audio16k(path)),
                          "-vn", "-af", f"silencedetect=n={seuil_silence(path)}dB:d=0.08", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8").stderr
    st = [a + float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [a + float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    out, cur = [], a
    for s, e in zip(st, en + [b] * (len(st) - len(en))):
        if s - cur > 0.25:
            out.append((cur, s))
        cur = max(cur, e)
    if b - cur > 0.25:
        out.append((cur, b))
    return out


def reprise(w1, w2):
    """Le bloc w2 recommence ce que disait w1 (prise ratée puis reprise) : mêmes 2 premiers mots, ou faux départ d'un
    mot repris tout de suite (« donc… donc sur ce point »). Les répétitions voulues (let's go, bref…) ne comptent pas."""
    if not w1 or not w2:
        return False
    if len(w1) >= 2 and len(w2) >= 2 and w1[:2] == w2[:2] and not set(w1[:2]) <= LEGIT:
        return True
    if len(w1) <= 2 and w1[0] == w2[0] and w1[0] not in LEGIT:
        return True
    # même mot en fin de bloc puis en début du suivant (« … à ChatGPT | ChatGPT, je… »)
    return w1[-1] == w2[0] and len(w1[-1]) > 3 and w1[-1] not in LEGIT


def main():
    src = Path(sys.argv[1])
    spec = json.loads(src.read_text(encoding="utf-8-sig"))
    appliquer = "--appliquer" in sys.argv
    retirer = spec.get("retirer", {})
    blocs, a_faire, total_avant, total_apres = [], [], 0.0, 0.0
    with tempfile.TemporaryDirectory() as t:
        tmp, n = Path(t), 0
        for g in spec["groupes"]:
            new = []
            for c in g["clips"]:
                nom, a, b = c[0], c[1], c[2]
                if b is None or not Path(nom).name[:4].isdigit():
                    new.append(c)
                    continue
                path = chemin_rush(nom, spec.get("rush_dir"))
                gap = opt("--blanc", 0.3)
                total_avant += b - a
                parts = bornes(path, a, b, gap, spec.get("garder", {}).get(Path(nom).stem, []))
                for ra, rb in retirer.get(Path(nom).stem, []):
                    parts = [p for x, y in parts for p in ((x, min(y, ra)), (max(x, rb), y)) if p[1] - p[0] > 0.05]
                parts = [p for p in parts if p[1] - p[0] > 0.25]
                for x, y in parts:
                    # un bloc de voix = entre deux pauses ; chaque bloc est transcrit seul (whisper fusionne les
                    # prises redites quand il transcrit le clip entier)
                    for bx, by in blocs_voix(path, x, y):
                        n += 1
                        wav = tmp / f"b{n:04d}.wav"
                        extract(path, bx, by, wav)
                        a_faire.append((Path(nom).stem, bx, by, wav))
                    total_apres += y - x
                new += [[nom, round(x, 3), round(y, 3), c[3] if len(c) > 3 and m == 0 else "(suite)"] for m, (x, y) in enumerate(parts)]
            g["clips"] = new
        # transcription par lots : le modèle est chargé une fois par lot, pas une fois par bloc (~4x plus rapide)
        print(f"{len(a_faire)} blocs de voix à transcrire", flush=True)
        for (r, bx, by, _), ws in zip(a_faire, transcribe_many([w for *_, w in a_faire])):
            blocs.append((r, bx, by, [(w, s - PAD + bx, e - PAD + bx) for w, s, e in ws]))
    mots = lambda ws: [w[0] for w in ws]  # noqa: E731
    rapport = [f"{r1}  {a1:8.2f} → {a2:8.2f}  « {' '.join(mots(w1))} »   puis   « {' '.join(mots(w2)[:12])} »"
               for (r1, a1, _, w1), (r2, a2, _, w2) in zip(blocs, blocs[1:]) if r1 == r2 and reprise(mots(w1), mots(w2))]
    rapport += [f"{r}  {t1:8.2f} → {t2:8.2f}  faux départ « {txt} » puis reprise : retirer [{t1:.2f}, {t2:.2f}["
                for r, _, _, ws in blocs for t1, t2, txt in faux_departs(ws)]
    # whisper fusionne parfois une redite en un seul mot anormalement long (« vis…uelle » sur 2,4 s) : à écouter
    rapport += [f"{r}  {s:8.2f} → {e:8.2f}  mot étiré « {w} » ({e - s:.1f} s) : redite fusionnée possible, retranscrire ce passage"
                for r, _, _, ws in blocs for w, s, e in ws if e - s > 0.9 and len(w) > 1]
    out = src.with_suffix(".nettoyage.txt")
    out.write_text(f"Voix : {total_avant:.1f} s → {total_apres:.1f} s\nRedites probables (rush, début de la 1re, "
                   f"début de la reprise ; retirer [1re, reprise[ si c'est bien une redite) :\n" + "\n".join(rapport) + "\n",
                   encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    if appliquer:
        shutil.copy2(src, Path(tempfile.gettempdir()) / (src.stem + ".avant-nettoyage.json"))  # hors du dépôt (pas de doublon)
        spec.pop("retirer", None)
        src.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"écrit : {src}")


if __name__ == "__main__":
    main()
