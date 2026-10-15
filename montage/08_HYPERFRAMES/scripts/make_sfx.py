"""Construit la banque de sound design du montage.

1. Sons synthétisés avec FFmpeg (créations originales, aucune licence tierce) :
   whoosh, impact grave, montée (reverse swell), sub-drop.
2. Sons d'interface Kenney (CC0) convertis en WAV.
3. Sons Pixabay choisis par l'utilisateur (pop), coupés au début du son.

Sorties : 04_RESSOURCES/sfx/synth/*.wav (masters) et 08_HYPERFRAMES/assets/sfx/*.wav (utilisés).
Usage : python scripts/make_sfx.py
"""

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = ROOT / "04_RESSOURCES" / "sfx" / "synth"
KENNEY_DIR = ROOT / "04_RESSOURCES" / "sfx" / "kenney_interface-sounds" / "Audio"
PUBLIC_DIR = ROOT / "08_HYPERFRAMES" / "assets" / "sfx"
RATE = 48000
PEAK_DB = -3.0


def whoosh(duration: float, peak: float, sharpness: float, lo: int, hi: int) -> str:
    """Bruit rose filtré, enveloppe montée/descente ; le canal droit arrive un peu après
    le gauche pour donner un léger mouvement gauche -> droite."""
    def env(delay: float) -> str:
        p = peak + delay
        return (f"volume='if(lt(t,{p}),pow(max(t-{delay},0)/{peak},2),exp(-(t-{p})*{sharpness}))'"
                ":eval=frame")
    return (
        f"anoisesrc=color=pink:r={RATE}:d={duration}:a=0.9,highpass=f={lo},lowpass=f={hi},"
        f"asplit[l][r];[l]{env(0)}[l2];[r]{env(0.05)}[r2];[l2][r2]amerge=inputs=2"
    )


def impact(duration: float, base: float, sweep: float, speed: float, decay: float) -> str:
    """Sinus qui chute rapidement en fréquence + transitoire de bruit : un 'boum' propre."""
    body = (f"sin(2*PI*({base}*t+{sweep}*(1-exp(-{speed}*t))/{speed}))*exp(-{decay}*t)")
    click = "0.35*(2*random(0)-1)*exp(-70*t)"
    return (
        f"aevalsrc='0.9*{body}+{click}':s={RATE}:d={duration},lowpass=f=5000,"
        "aecho=0.6:0.5:70|140:0.25|0.12,pan=stereo|c0=c0|c1=c0"
    )


def riser(duration: float) -> str:
    """Souffle inversé (bruit qui décroît, joué à l'envers) + sinus ascendant discret."""
    noise = (f"anoisesrc=color=pink:r={RATE}:d={duration}:a=0.8,highpass=f=700,lowpass=f=9000,"
             "volume='exp(-3.2*t)':eval=frame,areverse[n]")
    tone = (f"aevalsrc='0.18*sin(2*PI*(220*t+300*t*t/{duration}))*pow(t/{duration},3)'"
            f":s={RATE}:d={duration}[s]")
    return f"{noise};{tone};[n][s]amix=inputs=2:normalize=0,pan=stereo|c0=c0|c1=c0"


SYNTH = {
    "whoosh": whoosh(0.7, 0.32, 9, 250, 5000),
    "whoosh_court": whoosh(0.35, 0.14, 18, 500, 7000),
    "impact": impact(1.6, 45, 140, 14, 3.2),
    "sub_drop": impact(2.6, 30, 90, 7, 1.6),
    "riser": riser(1.6),
}

# Sons Kenney (CC0) retenus -> nom utilisé dans le projet
KENNEY = {
    "tick_001": "tick",
    "click_002": "clic",
    "click_004": "clic_2",
    "error_006": "croix",
    "confirmation_002": "valide",
}

# Sons Pixabay (licence Pixabay) : fichier -> (nom, début, fin en s, filtre) ; le silence autour est coupé pour que
# le son parte à l'instant où il est posé. Pop choisi le 2026-10-06 (l'ancien, select_006 de Kenney, refusé) ;
# pop_sortie = le même, un peu plus grave.
PIXABAY_DIR = ROOT / "04_RESSOURCES" / "sfx" / "pixabay"
PIXABAY = {
    "Bubble Pop 06 - Universfield.mp3": [("pop", 0.105, 0.30, ""),
                                         ("pop_sortie", 0.105, 0.30, f"asetrate={RATE * 0.82:.0f},aresample={RATE},")],
}


def run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def max_volume(path: Path) -> float:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    return float(out.split("max_volume:")[1].split("dB")[0])


def main() -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    for name, graph in SYNTH.items():
        master = SYNTH_DIR / f"{name}.wav"
        raw = SYNTH_DIR / f"{name}.raw.wav"
        run(["-filter_complex", graph, "-ar", str(RATE), "-c:a", "pcm_f32le", str(raw)])
        # normalisation crête à PEAK_DB : les niveaux finaux se règlent dans audio.ts
        gain = PEAK_DB - max_volume(raw)
        run(["-i", str(raw), "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_s16le", str(master)])
        raw.unlink()
        shutil.copy(master, PUBLIC_DIR / master.name)
        print(f"synth  {name}")

    for src, name in KENNEY.items():
        run(["-i", str(KENNEY_DIR / f"{src}.ogg"), "-ar", str(RATE), "-ac", "2",
             "-c:a", "pcm_s16le", str(PUBLIC_DIR / f"{name}.wav")])
        print(f"kenney {src} -> {name}")

    for src, outs in PIXABAY.items():
        for name, start, end, extra in outs:
            run(["-ss", str(start), "-to", str(end), "-i", str(PIXABAY_DIR / src), "-af",
                 f"{extra}afade=t=out:st={end - start - 0.03:.3f}:d=0.03", "-ar", str(RATE), "-ac", "2",
                 "-c:a", "pcm_s16le", str(PUBLIC_DIR / f"{name}.wav")])
            print(f"pixabay {src} -> {name}")


if __name__ == "__main__":
    main()
