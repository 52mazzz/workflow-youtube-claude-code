"""Voix nettoyée de la timeline CapCut, sans toucher aux rushs.       python scripts/voix.py <id>

Pour chaque rush de la piste principale du projet (video.json « projet ») :
  rush.mkv -> 06_CAPCUT/<id>/voix/<rush>.wav (même durée que le rush → mêmes points de coupe)
Chaîne : double mono -> passe-haut 80 Hz -> réduction de bruit (afftdn) -> de-esser doux -> compression
(si le son du jeu reste sous la voix, enregistré bas dans OBS : réduction de bruit douce et sans suivi du bruit,
pour ne pas traiter la musique du jeu comme un bruit ; détecté sur le rush, voir commun.seuil_silence)
-> gain mesuré vers -14 LUFS (cible de YouTube, qui ne remonte jamais une vidéo trop basse) -> limiteur -1,5 dBTP.
Puis voix_timeline.wav (voix recollée dans l'ordre de la timeline : ducking, shorts, contrôle des sous-titres)
et voix_segments.json (un clip audio par clip de la piste principale, pour le bridge).
À relancer après une cut-range. Un rush déjà nettoyé est réutilisé seulement si son empreinte (rush, chaîne
de traitement, cibles) n'a pas changé (<rush>.wav.empreinte) ; sinon il est refait.
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from commun import a_jour, draft, empreinte, fond_sonore, marquer, seuil_silence, video, write_json

LUFS, TP = -14.0, -1.5
PRE = ("pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,highpass=f=80,"
       "afftdn=nr=12:nf=-45:tn=1,deesser=i=0.35,"
       "acompressor=threshold=-24dB:ratio=3:attack=6:release=120:makeup=1")
# son du jeu sous la voix : on garde le jeu, on retire seulement le souffle
PRE_JEU = PRE.replace("afftdn=nr=12:nf=-45:tn=1", "afftdn=nr=5:nf=-60:tn=0")


def chaine(src: Path) -> str:
    return PRE_JEU if fond_sonore(src) >= -48 else PRE


def clean(src: Path, voix: Path) -> Path:
    dst = voix / f"{src.stem}.wav"
    pre = chaine(src)
    emp = empreinte(pre, LUFS, TP, fichiers=[src])   # rush, chaîne de traitement et cibles
    if a_jour(dst, emp):
        return dst
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vn", "-af",
                          f"{pre},loudnorm=I={LUFS}:TP={TP}:LRA=7:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8").stderr
    gain = LUFS - float(json.loads(err[err.rindex("{"): err.rindex("}") + 1])["input_i"])
    if not math.isfinite(gain) or gain > 40:  # piste muette (plan accéléré sans son) : pas de gain, sinon bruit plein
        gain = 0.0
    tmp = dst.with_suffix(".tmp.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-af",
                    f"{pre},volume={gain:.2f}dB,alimiter=limit={10 ** (TP / 20):.3f}:attack=2:release=50:level=disabled",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(tmp)], check=True)
    tmp.replace(dst)
    marquer(dst, emp)
    print(f"voix : {src.name}  gain {gain:+.1f} dB" + ("  (son du jeu gardé)" if pre is PRE_JEU else ""), flush=True)
    return dst


def main(vid: str) -> None:
    cfg = video(vid)
    out, voix = cfg["out"], cfg["out"] / "voix"
    voix.mkdir(exist_ok=True)
    d = draft(cfg["projet"])
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main_track = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    segs = [{"path": vids[s["material_id"]].get("path", ""), "at": s["target_timerange"]["start"] / 1e6,
             "src": s["source_timerange"]["start"] / 1e6, "dur": s["target_timerange"]["duration"] / 1e6}
            for s in main_track["segments"]]
    rushes = sorted({s["path"] for s in segs if s["path"] and Path(s["path"]).exists()})
    with ThreadPoolExecutor(4) as pool:
        cleaned = dict(zip(rushes, pool.map(lambda p: clean(Path(p), voix), rushes)))
    items = [{"file": f"voix/{Path(cleaned[s['path']]).name}", "at": round(s["at"], 6), "src": round(s["src"], 6),
              "dur": round(s["dur"], 6), "layer": 1} for s in segs if s["path"] in cleaned]
    write_json(out / "voix_segments.json", items)
    work = out / "_tmp_voix"
    work.mkdir(exist_ok=True)
    parts = []
    for i, s in enumerate(segs):
        p = work / f"{i:04d}.wav"
        cmd = (["-ss", f"{s['src']:.6f}", "-t", f"{s['dur']:.6f}", "-i", str(cleaned[s["path"]])] if s["path"] in cleaned
               else ["-f", "lavfi", "-t", f"{s['dur']:.6f}", "-i", "anullsrc=r=48000:cl=stereo"])
        subprocess.run(["ffmpeg", "-v", "error", "-y", *cmd, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(p)], check=True)
        parts.append(p)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le",
                    str(out / "voix_timeline.wav")], check=True)
    for p in work.iterdir():
        p.unlink()
    work.rmdir()
    # débuts de voix (fins de silence) : calage des sous-titres
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out / "voix_timeline.wav"), "-af",
                          f"silencedetect=n={seuil_silence(out / 'voix_timeline.wav')}dB:d=0.05", "-f", "null", "-"], capture_output=True, text=True).stderr
    onsets = [l.split("silence_end: ")[1].split(" ")[0] for l in err.splitlines() if "silence_end" in l]
    (cfg["dir"] / "debuts_voix.txt").write_text("\n".join(onsets) + "\n", encoding="utf-8")
    print(f"{len(items)} clips voix, {len(rushes)} rushs nettoyés, {len(onsets)} débuts de voix -> {out / 'voix_timeline.wav'}")


if __name__ == "__main__":
    main(sys.argv[1])
