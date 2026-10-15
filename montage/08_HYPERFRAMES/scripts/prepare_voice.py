"""Prépare la voix de chaque rush (dérushage, formes d'onde), sans jamais toucher aux originaux.

01_RUSHS/<rush>.mkv  ->  02_ANALYSE/voix/<rush>.wav
                     +  02_ANALYSE/audio_16k/<rush>.wav (copie 16 kHz mono pour la transcription)

Chaîne : double mono (voix centrée) -> passe-haut 70 Hz -> compression douce -> gain linéaire mesuré (loudnorm
en mesure seule) vers VOICE_LUFS -> limiteur transparent au plafond TRUE_PEAK.
Le rush reste entier : les coupes se font dans Remotion (trimBefore / durationInFrames),
ce qui garde le montage modifiable dans le Studio.

Usage : python scripts/prepare_voice.py [--force]
Un fichier déjà prêt est gardé seulement si son empreinte (rush, filtres, cibles) n'a pas changé.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import a_jour, empreinte, marquer  # noqa: E402

VOICE_LUFS = -16.0  # voix seule ; la musique passe dessous, master final vers -14 LUFS
TRUE_PEAK = -1.5
LRA = 7.0  # paramètre requis par loudnorm pour la mesure
PRE_FILTERS = "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=150:makeup=1"

ROOT = Path(__file__).resolve().parents[2]
RUSHS = ROOT / "01_RUSHS"
OUT = ROOT / "02_ANALYSE" / "voix"
ANALYSIS_AUDIO = ROOT / "02_ANALYSE" / "audio_16k"


def slug(path: Path) -> str:
    return path.stem.replace(" ", "_")


def measure(src: Path) -> dict:
    """Première passe loudnorm : mesure les valeurs d'entrée."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vn",
        "-af", f"{PRE_FILTERS},loudnorm=I={VOICE_LUFS}:TP={TRUE_PEAK}:LRA={LRA}:print_format=json",
        "-f", "null", "-",
    ]
    stderr = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stderr
    return json.loads(stderr[stderr.rindex("{"): stderr.rindex("}") + 1])


def render(src: Path, dst: Path, m: dict) -> None:
    # Gain linéaire vers la cible, puis limiteur transparent qui ne touche que les rares pics.
    gain_db = VOICE_LUFS - float(m["input_i"])
    limit = 10 ** (TRUE_PEAK / 20)
    chain = f"{PRE_FILTERS},volume={gain_db:.2f}dB,alimiter=limit={limit:.3f}:attack=2:release=50:level=disabled"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn",
         "-af", chain, "-ar", "48000", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )


def main() -> None:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    ANALYSIS_AUDIO.mkdir(parents=True, exist_ok=True)
    for src in sorted(RUSHS.rglob("*")):
        if src.suffix.lower() not in {".mkv", ".mp4", ".mov", ".wav", ".m4a"}:
            continue
        dst = OUT / f"{slug(src)}.wav"
        emp = empreinte(PRE_FILTERS, VOICE_LUFS, TRUE_PEAK, fichiers=[src])
        if a_jour(dst, emp) and not force:
            print(f"déjà prêt : {dst.name}")
            continue
        m = measure(src)
        render(src, dst, m)
        marquer(dst, emp)
        # copie 16 kHz mono pour la transcription (scripts/transcribe.ts)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(dst), "-ac", "1", "-ar", "16000",
             "-c:a", "pcm_s16le", str(ANALYSIS_AUDIO / dst.name)],
            check=True,
        )
        print(f"{dst.name}  (entrée {m['input_i']} LUFS -> {VOICE_LUFS} LUFS)")


if __name__ == "__main__":
    main()
