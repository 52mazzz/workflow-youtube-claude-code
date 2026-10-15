"""Profil d'un morceau (je n'entends pas : je mesure) : tempo (autocorrélation de la basse), niveau de basse,
brillance (part des aigus), et énergie toutes les 2 s (pour choisir le départ).
usage : python scripts/profil_musique.py fichier.mp3 [autres…]   (aussi importé par musique.py ; accepte une URL)"""
import subprocess, sys

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0"


def levels(path, filt, n, limite=None):
    t = ["-t", str(limite)] if limite else []
    ua = ["-user_agent", UA] if str(path).startswith("http") else []
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *ua, *t, "-i", str(path), "-af",
                          f"{filt}aresample=8000,asetnsamples={n},astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return [max(-90.0, float(l.split("=")[-1])) for l in err.splitlines() if "RMS_level" in l and "inf" not in l]


def profil(path, limite=None):
    """tempo (4 meilleurs), basse et aigus (dB par rapport au tout), énergie toutes les 2 s (dB RMS). limite : secondes lues."""
    env = [10 ** (db / 20) for db in levels(path, "lowpass=f=120,", 80, min(limite or 60, 60))]  # 10 ms, 60 s suffisent
    onset = [max(0.0, b - a) for a, b in zip(env, env[1:])]
    scores = []
    for bpm in range(70, 181):
        lag = round(6000 / bpm)
        scores.append((sum(onset[i] * onset[i - lag] for i in range(lag, len(onset))), bpm))
    top = [b for _, b in sorted(scores, reverse=True)[:4]]
    full = levels(path, "", 16000, limite)  # 2 s
    low = levels(path, "lowpass=f=150,", 16000, limite)
    high = levels(path, "highpass=f=4000,", 16000, limite)
    avg = lambda xs: sum(xs) / max(1, len(xs))
    return {"tempo": top, "basse": round(avg(low) - avg(full), 1), "aigus": round(avg(high) - avg(full), 1),
            "energie": [round(x, 1) for x in full]}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        p = profil(path)
        print(f"{path.split(chr(92))[-1]:28s} tempo≈{p['tempo']}  basse {p['basse']:+.1f} dB  aigus {p['aigus']:+.1f} dB"
              f"  énergie/2s : {' '.join(str(round(x)) for x in p['energie'][:30])}")
