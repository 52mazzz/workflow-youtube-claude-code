"""Vérifie et resserre chaque coupe d'une liste de dérushage.

Pour chaque clip [rush, entrée, sortie, "texte voulu"] :
  1. retranscrit l'audio EXACT du clip (whisper.cpp, horodatage mot à mot) ;
  2. compare au texte voulu : mots en trop au début (« donc donc… », « ok », fin de la prise
     précédente) ou à la fin (début de la prise suivante) ;
  3. déplace le point de coupe juste avant le premier bon mot / juste après le dernier,
     dans le creux de voix entre les deux (micro-silence), sinon au point le plus calme.

Écrit <liste>.verifie.json + un rapport lisible. Ne touche pas au projet CapCut.
Usage : python scripts/verify_cuts.py <liste.json>
"""

import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import MODEL, NOMBRES, audio16k, seuil_silence  # noqa: E402
from commun import rush as chemin_rush  # noqa: E402
from commun import WHISPER as CLI  # noqa: E402  (Vulkan si présent, sinon processeur)

HERE = Path(__file__).resolve().parent
PAD = 0.6          # silence ajouté autour du clip pour aider whisper
LOOK = 1.2         # on regarde aussi un peu avant/après la coupe actuelle
MARGIN = 0.05      # marge laissée avant le premier mot / après le dernier


def norm(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)


def words_of(text: str) -> list[str]:
    text = re.sub(r"\(.*?\)", "", text)
    # même découpage que la transcription : « j'ai » -> « jai », « c'est » -> « cest »
    return [NOMBRES.get(n, n) for n in (norm(w) for w in re.split(r"[\s-]+", text)) if n]


def extract(rush: Path, a: float, b: float, out: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(PAD), "-i", "anullsrc=r=16000:cl=mono",
                    "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(audio16k(rush)),  # son du rush extrait une fois
                    "-filter_complex", "[1:a]aformat=sample_rates=16000:channel_layouts=mono[v];[0][v][0]concat=n=3:v=0:a=1",
                    "-ac", "1", "-ar", "16000", str(out)], check=True)


def transcribe(wav: Path) -> list[tuple[str, float, float]]:
    """Mots (texte normalisé, début, fin) en secondes dans le wav."""
    base = wav.with_suffix("")
    subprocess.run([str(CLI), "-m", str(MODEL), "-f", str(wav), "-l", "fr", "--dtw", "large.v3.turbo", "-nfa",
                    "-ojf", "-of", str(base), "-t", "6", "-np"], capture_output=True, check=True)
    return _mots(json.loads(base.with_suffix(".json").read_text(encoding="utf-8")))


def transcribe_many(wavs: list, lot: int = 120) -> list:
    """Comme transcribe, pour beaucoup de petits fichiers : le modèle (570 Mo) est chargé une fois par lot au lieu
    d'une fois par fichier (~4x plus rapide sur les blocs de voix). Résultat dans le même ordre que `wavs`."""
    out = []
    for i in range(0, len(wavs), lot):
        part = [Path(w) for w in wavs[i:i + lot]]
        args = [a for w in part for a in ("-f", str(w))]
        subprocess.run([str(CLI), "-m", str(MODEL), *args, "-l", "fr", "--dtw", "large.v3.turbo", "-nfa",
                        "-ojf", "-t", "6", "-np"], capture_output=True, check=True)
        out += [_mots(json.loads(Path(str(w) + ".json").read_text(encoding="utf-8"))) for w in part]
    return out


def _mots(data) -> list[tuple[str, float, float]]:
    words: list[list] = []
    for seg in data["transcription"]:
        for tok in seg["tokens"]:
            t = tok["text"]
            if t.startswith("[_") or not t.strip():
                continue
            start = (tok["t_dtw"] * 10 if tok["t_dtw"] >= 0 else tok["offsets"]["from"]) / 1000
            if t.startswith(" ") or not words:
                words.append([t, start, tok["offsets"]["to"] / 1000])
            else:
                words[-1][0] += t
                words[-1][2] = tok["offsets"]["to"] / 1000
    return sans_credits([(norm(w), s, e) for w, s, e in words if norm(w)])


# Crédits de sous-titres appris par Whisper sur les vidéos sous-titrées : il les « entend » dans le son du jeu
# ou le silence. Seulement les formules complètes (« activez les sous-titres » reste).
CREDITS = [["soustitrage", "societe", "radiocanada"], ["soustitrage", "st", "501"], ["soustitrage", "st501"],
           ["soustitres", "par", "jeremy", "diaz"], ["soustitres", "realises", "par", "la", "communaute", "damaraorg"]]


def sans_credits(words: list) -> list:
    out, i = [], 0
    while i < len(words):
        c = next((c for c in CREDITS if [w[0] for w in words[i:i + len(c)]] == c), None)
        if c:
            i += len(c)
        else:
            out.append(words[i])
            i += 1
    return out


def silences(wav: Path) -> list[tuple[float, float]]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                          f"silencedetect=n={seuil_silence(wav)}dB:d=0.04", "-f", "null", "-"], capture_output=True, text=True).stderr
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(s, e + [1e9] * (len(s) - len(e))))


def quietest(wav: Path, t0: float, t1: float) -> float:
    """Instant le plus calme entre t0 et t1 (fenêtres de 10 ms)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{max(0, t0):.3f}", "-to", f"{t1:.3f}",
                          "-i", str(wav), "-af", "asetnsamples=160,astats=metadata=1:reset=1,"
                          "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    best, best_t, t = 1e9, (t0 + t1) / 2, None
    for line in err.splitlines():
        if "pts_time:" in line:
            t = max(0, t0) + float(line.split("pts_time:")[1].split()[0])
        elif "RMS_level=" in line and t is not None:
            v = float(line.split("=")[1]) if "inf" not in line else -200
            if v < best:
                best, best_t = v, t
    return best_t


def find_seq(hay: list[str], needle: list[str], from_end=False, allowed=None):
    """Position de `needle` (2 à 3 mots) dans `hay`, tolérante à un mot mal transcrit.
    `allowed` : indices de départ autorisés (limite la recherche à la zone de la coupe)."""
    k = min(len(needle), 3)
    target = needle[-k:] if from_end else needle[:k]
    candidates = []
    for i in range(len(hay) - k + 1):
        if allowed is not None and (i + (k - 1 if from_end else 0)) not in allowed:
            continue
        score = sum(1 for j in range(k) if hay[i + j] == target[j])
        if score >= max(1, k - 1):
            candidates.append((score, i))
    if not candidates:
        return None
    best = max(c[0] for c in candidates)
    positions = [i for s, i in candidates if s == best]
    # début : dernière occurrence (la bonne prise suit les faux départs) ; fin : dernière aussi
    return positions[-1] if not from_end else positions[-1] + k - 1


def fix_clip(rush: Path, a: float, b: float, text: str, tmp: Path, n: int):
    wanted = words_of(text)
    if len(wanted) < 2:
        return a, b, "trop court pour vérifier"
    lo = max(0.0, a - LOOK)
    wav = tmp / f"c{n:03d}.wav"
    extract(rush, lo, b + LOOK, wav)
    words = transcribe(wav)
    to_src = lambda t: lo + t - PAD  # temps wav -> temps rush
    hay = [NOMBRES.get(w, w) for w, _, _ in words]  # « trois » = « 3 » (whisper varie)
    # le premier bon mot doit commencer dans la coupe (pas dans la prise suivante),
    # le dernier doit finir avant la fin de la coupe (+ petite marge)
    # (whisper donne des FINS de mots peu fiables, surtout le dernier : on raisonne sur les débuts)
    start_ok = {i for i, (_, s, _) in enumerate(words) if a - 0.6 <= to_src(s) <= b - 0.3}
    end_ok = {i for i, (_, s, _) in enumerate(words) if a <= to_src(s) <= b + 0.5}
    # tolère un premier / dernier mot raté par whisper (« Ça, encore une fois… »)
    i0 = find_seq(hay, wanted, allowed=start_ok)
    if i0 is None:
        i0 = find_seq(hay, wanted[1:], allowed=start_ok)
    i1 = find_seq(hay, wanted, from_end=True, allowed=end_ok)
    if i1 is None:
        i1 = find_seq(hay, wanted[:-1], from_end=True, allowed=end_ok)
    if i0 is None or i1 is None or i1 < i0:
        return a, b, f"non reconnu : « {' '.join(hay)} »"

    sil = silences(wav)
    # DÉBUT : fin du dernier silence situé entre le mot précédent et le premier bon mot
    first_start = words[i0][1]
    prev_start = words[i0 - 1][1] if i0 > 0 else 0.0
    gap = [s for s in sil if prev_start + 0.1 <= s[1] <= first_start + 0.12]
    new_a = to_src(gap[-1][1] - MARGIN) if gap else to_src(
        quietest(wav, max(prev_start + 0.1, first_start - 0.35), first_start - 0.02))

    # FIN : début du premier silence après le dernier bon mot (et avant le mot suivant)
    last_start = words[i1][1]
    next_start = words[i1 + 1][1] if i1 + 1 < len(words) else last_start + 2.0
    gap = [s for s in sil if last_start + 0.1 <= s[0] <= next_start + 0.05]
    new_b = to_src(gap[0][0] + MARGIN) if gap else to_src(
        quietest(wav, last_start + 0.15, min(next_start - 0.02, last_start + 0.6)))

    before = [w for w, s, _ in words[:i0] if to_src(s) >= a - 0.02]
    after = [w for w, s, _ in words[i1 + 1:] if to_src(s) <= b]
    note = []
    if before:
        note.append(f"retiré au début : « {' '.join(before)} »")
    if after:
        note.append(f"retiré à la fin : « {' '.join(after)} »")
    # ne jamais élargir fortement la coupe d'origine (sécurité) : max 0,4 s de plus de chaque côté
    new_a, new_b = max(new_a, a - 0.4), min(new_b, b + 0.4)
    return round(new_a, 2), round(new_b, 2), "; ".join(note) or "ok"


def main():
    src = Path(sys.argv[1])
    spec = json.loads(src.read_text(encoding="utf-8-sig"))  # tolère un BOM (fichiers écrits par PowerShell)
    rush_dir = spec.get("rush_dir")  # facultatif : sinon le rush est cherché dans tous les dossiers (commun.rush)
    report = []
    with tempfile.TemporaryDirectory() as t:
        tmp, n = Path(t), 0
        for g in spec["groupes"]:
            for clip in g["clips"]:
                n += 1
                rush = chemin_rush(clip[0], rush_dir)
                a, b = clip[1], clip[2]
                na, nb, note = fix_clip(rush, a, b, clip[3] if len(clip) > 3 else "", tmp, n)
                changed = abs(na - a) > 0.02 or abs(nb - b) > 0.02
                clip[1], clip[2] = na, nb
                report.append(f"{'*' if changed else ' '} {clip[0][-8:]} {a:7.2f}-{b:7.2f} → {na:7.2f}-{nb:7.2f}  {note}")
                print(report[-1], flush=True)
    out = src.with_name(src.stem + ".verifie.json")
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    src.with_name(src.stem + ".rapport.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
