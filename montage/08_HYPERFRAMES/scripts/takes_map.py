"""Carte des prises d'un rush : découpe la voix en blocs (entre les silences) et transcrit
chaque bloc SEUL. Whisper sur un long fichier a tendance à fusionner les prises répétées ;
bloc par bloc, chaque reprise apparaît telle qu'elle est dite.
Les blocs sans voix (son du jeu seul, d'après le VAD Silero : commun.voix) ne sont pas transcrits :
Whisper y inventait du texte (« sous-titrage Société Radio-Canada »…) et c'est le plus gros du temps de calcul.
Les blocs de plus de MAX_BLOC s (commentaire en jouant) sont redécoupés aux pauses du VAD (decouper).

Usage : python scripts/takes_map.py <rush.mkv> [<rush2.mkv> ...]
Sortie : 02_ANALYSE/prises/<rush>.txt   (une ligne par bloc : début, fin, texte)
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_cuts import transcribe  # noqa: E402
from commun import seuil_silence, voix  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "02_ANALYSE" / "prises"
PAD = 0.5


def islands(path: Path, noise=None, gap=0.35):
    noise = noise or f"{seuil_silence(path, -42.0)}dB"   # plus haut si le son du jeu reste sous la voix
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                          f"silencedetect=n={noise}:d={gap}", "-f", "null", "-"], capture_output=True, text=True).stderr
    h, m, s_ = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    dur = int(h) * 3600 + int(m) * 60 + float(s_)
    s = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    e = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    out, prev = [], 0.0
    for i, start in enumerate(s):
        if start - prev > 0.12:
            out.append((prev, start))
        prev = e[i] if i < len(e) else dur
    if dur - prev > 0.12:
        out.append((prev, dur))
    return out


MAX_BLOC = 20.0  # au-delà, Whisper tourne en boucle (« on va aller de ce côté pour moi » x50)


def decouper(a: float, b: float, parle) -> list[tuple[float, float]]:
    """Bloc long (commentaire en jouant, sans pause nette pour silencedetect) : redécoupé aux pauses du VAD
    en morceaux d'au plus MAX_BLOC s, sans le jeu seul qui les entoure."""
    segs = [(max(s, a), min(e, b)) for s, e in parle or [] if s < b and e > a]
    if b - a <= MAX_BLOC or not segs:
        return [(a, b)]
    out, (cs, ce) = [], segs[0]
    for s, e in segs[1:]:
        if e - cs > MAX_BLOC:
            out.append((cs, ce))
            cs = s
        ce = e
    out.append((cs, ce))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for arg in sys.argv[1:]:
        rush = Path(arg)
        lines = []
        parle = voix(rush)
        if parle is None:
            print("VAD absent (.whisper/ggml-silero-v5.1.2.bin) : tous les blocs sont transcrits", flush=True)
        sautes, blocs = 0, []
        for a, b in islands(rush):
            if parle is not None and not any(s < b and e > a for s, e in parle):
                sautes += 1
            else:
                blocs += decouper(a, b, parle)
        with tempfile.TemporaryDirectory() as t:
            for k, (a, b) in enumerate(blocs):
                wav = Path(t) / f"i{k:03d}.wav"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", str(PAD), "-i", "anullsrc=r=16000:cl=mono",
                                "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(rush),
                                "-filter_complex", "[1:a]aformat=sample_rates=16000:channel_layouts=mono[v];"
                                "[0][v][0]concat=n=3:v=0:a=1", "-ac", "1", "-ar", "16000", str(wav)], check=True)
                words = transcribe(wav)
                text = " ".join(w for w, _, _ in words)
                if not text:  # rien qu'un crédit de sous-titres inventé (verify_cuts.sans_credits)
                    continue
                lines.append(f"{a:7.2f} {b:7.2f}  {text}")
                print(f"{rush.stem}  {lines[-1]}", flush=True)
        if sautes:
            print(f"{rush.stem}  {sautes} blocs sans voix sautés", flush=True)
        (OUT / f"{rush.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
