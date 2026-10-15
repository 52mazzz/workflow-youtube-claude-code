"""Met un short dans CapCut, en pièces modifiables (au lieu d'un MP4 figé).
usage : python scripts/short_capcut.py videos/<id>/<short>.json [--pieces-seules | --projet-seul] [--leger]
Prérequis : short.py … tout (base.mp4, voix.wav, mots.json, audio → musique_duckee.wav + mix_brut.wav).

Pièces dans 06_CAPCUT/<id>/shorts/<short>/ :
  plans/     un MP4 par plan (déjà recadré 9:16), posés à la suite sur la piste principale ; zooms, cadrage et
             transitions = images clés d'échelle adoucies (modifiables dans CapCut)
  calques/   MOV transparents (qtrle) : scène d'intro, captures qui surgissent, interrupteurs, sous-titres (un par phrase)
  voix/      un WAV par passage · musique/ un WAV par morceau (déjà baissé sous la voix, coupures « vrooom » incluses)
  sfx/       bruitages utilisés
Projet CapCut « projet_capcut » du JSON (défaut « <id> - <short> ») : copie vide du projet de la vidéo, en 1080×1920
60 i/s. Volumes : gain commun pour que le tout sorte vers −14 LUFS comme le MP4."""
import json, math, re, shutil, subprocess, sys
from pathlib import Path

import short as S
from commun import ROOT, h264

sys.path.insert(0, str(ROOT / "07_OUTILS" / "capcut-bridge-windows"))
import capcut_bridge as CB  # noqa: E402

HF, CFG, OUT = S.HF, S.CFG, S.OUT
NAME = S.CFG_PATH.stem
DST = ROOT / "06_CAPCUT" / CFG["video"] / "shorts" / NAME
BUILD = HF / "build"
PROJET = CFG.get("projet_capcut") or f"{CFG['video']} - {NAME}"
FPS = 60


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, creationflags=S.BELOW)


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def shift(data, t0, dur, keep):
    """Sous-partie des données du short, recalée pour commencer à t0 et durer dur. keep : {clé: liste gardée}."""
    out = {"duration": round(dur, 3), "plans": [{"t": 0, "d": round(dur, 3)}], "scenes": [], "surgit": [], "interrupteur": [], "mots": [],
           "sous_titres": data.get("sous_titres", True), "duel": data.get("duel"), "etiquettes": [], "cartes": [], "score": []}
    for k, items in keep.items():
        if k == "plans":  # écran partagé : noms du duel sur toute la durée du calque
            out[k] = [dict({f: v for f, v in it.items() if f not in ("t", "d")}, t=0, d=round(dur, 3)) for it in items]
            continue
        temps = ("t", "fin", "logos", "transforme", "de") + (("a",) if k == "etiquettes" else ())  # score.a = décalage, pas un temps
        out[k] = [{f: ([dict(x, t=x["t"] - t0) for x in v] if f == "etat" else dict(v, t=v["t"] - t0) if f == "surligne"
                       else v - t0 if f in temps else v) for f, v in it.items()}
                  for it in items]
    return out


def calques():
    data, (s0, total) = S.html_data(), S.starts()
    res = []
    for i, s in enumerate(data["scenes"], 1):
        res.append((f"scene_{i}", s["t"], s["fin"] - s["t"], {"scenes": [s]}))
    for i, s in enumerate(data["surgit"], 1):
        res.append((f"capture_{i}_{Path(s['src']).stem}", s["t"], s["d"], {"surgit": [s]}))
    for i, fin in enumerate(dict.fromkeys(it["fin"] for it in data["interrupteur"]), 1):
        its = [it for it in data["interrupteur"] if it["fin"] == fin]
        res.append((f"interrupteur_{i}", its[0]["t"], fin - its[0]["t"], {"interrupteur": its}))
    # style WOLF : cartes titre, pastilles persistantes, tableaux de score, noms de l'écran partagé
    res += [(f"carte_{i}", c["t"], c["d"], {"cartes": [c]}) for i, c in enumerate(data["cartes"], 1)]
    res += [(f"etiquette_{i}", e["de"], e["a"] - e["de"], {"etiquettes": [e]}) for i, e in enumerate(data["etiquettes"], 1)]
    res += [(f"score_{i}", s["t"], min(s["d"], total - s["t"]), {"score": [s]}) for i, s in enumerate(data["score"], 1)]
    res += [(f"partage_{i}", p.get("t", 0), p["d"], {"plans": [p]}) for i, p in enumerate([p for p in data["plans"] if p.get("partage")], 1)]
    for i, p in enumerate(S.P):
        mots = [w for w in data["mots"] if w["p"] == i]
        if mots and data.get("sous_titres", True) is not False:
            end = s0[i + 1] if i + 1 < len(S.P) else total
            res.append((f"soustitre_{i + 1:02d}", s0[i], end - s0[i], {"mots": mots}))
    return res


def frames():
    """Plans en numéros d'image [(première, nombre)] : collés exactement, jusqu'à la dernière image de base.mp4."""
    n = int(subprocess.check_output(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                     "stream=nb_read_packets", "-of", "csv=p=0", str(OUT / "base.mp4")]).strip())
    cuts = [round(sh["t"] * FPS) for sh in S.shots()] + [n]
    return [(a, b - a) for a, b in zip(cuts, cuts[1:])]


def build_pieces():
    for d in ("plans", "calques", "voix", "musique", "sfx"):
        (DST / d).mkdir(parents=True, exist_ok=True)
    s0, total = S.starts()
    # 1. plans (coupés à l'image exacte)
    for k, (a, n) in enumerate(frames(), 1):
        ff("-i", str(OUT / "base.mp4"), "-vf", f"select='between(n,{a},{a + n - 1})',setpts=N/{FPS}/TB", "-an", "-r", str(FPS),
           "-frames:v", str(n), *h264(14, "fast"), "-pix_fmt", "yuv420p",
           str(DST / "plans" / f"plan_{k:02d}.mp4"))
    print(f"{len(frames())} plans")
    if "--plans-seuls" in sys.argv:
        return
    # 2. calques transparents
    BUILD.mkdir(exist_ok=True)
    for name, t0, dur, keep in calques():
        comp = f"cc_{name}"
        S.page(BUILD / f"{comp}.html", comp, shift(S.html_data(), t0, dur, keep), calque=True)
        mov = BUILD / f"{comp}.mov"
        subprocess.run(["npx", "hyperframes", "render", ".", "-c", f"build/{comp}.html", "-f", str(FPS), "--quiet", "--format", "mov",
                        "-o", str(mov)] + (["-w", "1"] if S.BELOW else []), cwd=HF, check=True, shell=True, creationflags=S.BELOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ff("-i", str(mov), "-r", str(FPS), "-c:v", "qtrle", "-pix_fmt", "argb", str(DST / "calques" / f"{name}.mov"))
        mov.unlink()
        print(f"calque {name:28s} à {t0:6.2f} s  {dur:5.2f} s", flush=True)
    shutil.rmtree(BUILD, ignore_errors=True)
    # 3. voix par passage, musique par morceau, bruitages
    for i in range(len(S.P)):
        end = s0[i + 1] if i + 1 < len(S.P) else total
        ff("-i", str(OUT / "voix.wav"), "-ss", f"{s0[i]:.4f}", "-t", f"{end - s0[i]:.4f}", "-c:a", "pcm_s16le", str(DST / "voix" / f"voix_{i + 1:02d}.wav"))
    if isinstance(CFG.get("musique"), list):
        for k, (a, b, g) in enumerate(S.music_segments(), 1):
            ff("-i", str(OUT / "musique_duckee.wav"), "-ss", f"{a:.4f}", "-t", f"{b - a:.4f}", "-c:a", "pcm_s16le",
               str(DST / "musique" / f"musique_{k}_{Path(g['fichier']).stem.split(' (')[0]}.wav"))
    elif CFG.get("musique"):
        shutil.copy(OUT / "musique_duckee.wav", DST / "musique" / "musique.wav")
    for _, n in S.cues():
        shutil.copy(S.SFX / f"{n}.wav", DST / "sfx" / f"{n}.wav")
    print("audio découpé")


def zoom_points(sh, nxt, d):
    """Échelle du plan dans le temps (même calcul que le kit) → images clés aux instants qui comptent."""
    base = sh.get("cadre") or 1.0
    z = sh.get("zoom")

    def scale(t):
        v = base
        if isinstance(z, list):
            v *= z[0] + (z[1] - z[0]) * (t / d)
        elif z:
            v *= 1 + (z - 1) * min(1, t / 0.6)
        return v
    ts = {0.0, d}
    if sh.get("trans"): ts.add(0.2)
    if z and not isinstance(z, list): ts.add(min(0.6, d))
    if nxt and nxt.get("trans"): ts.add(max(0.0, d - 0.14))
    pts = []
    for t in sorted(ts):
        v = scale(t)
        if sh.get("trans") and t == 0.0: v *= 1.35
        if nxt and nxt.get("trans") and abs(t - d) < 1e-6: v *= 1.35
        pts.append({"t": round(min(t, d - 1 / FPS), 4), "scale": round(v, 4)})
    return pts if len({p["scale"] for p in pts}) > 1 else None, base


def build_project():
    shots, (s0, total) = S.shots(), S.starts()
    gain = 10 ** ((-14 - loudness(OUT / "mix_brut.wav")) / 20)
    folder = CB.DRAFT_ROOT / PROJET
    if not folder.exists():
        CB.cmd_duplicate(S.CFG["projet"], PROJET, [])
    else:  # il retouche ses shorts dans CapCut : ne jamais écraser son travail sans le lui demander
        saves = sorted((folder / "_sauvegardes_claude").glob("*"))
        last = saves[-1].stat().st_mtime if saves else 0
        if (folder / CB.CONTENT).stat().st_mtime > last + 120 and "--ecraser" not in sys.argv:
            raise SystemExit(f"« {PROJET} » a été retouché dans CapCut depuis mon dernier passage : je ne l'écrase pas. "
                             "Choisir un autre projet_capcut, ou --ecraser si l'utilisateur l'a demandé.")

    def mutate(d):
        d.fps = FPS
        d.d["fps"] = float(FPS)
        d.d["canvas_config"] = {**d.d.get("canvas_config", {}), "width": 1080, "height": 1920, "ratio": "9:16"}
        tpl = d.template_segment()
        d.template_segment = lambda: tpl
        for g in d.meta["draft_materials"]:  # panneau Médias : seulement les pièces du short
            if g["type"] == 0:
                g["value"] = []
        main = {"id": CB.uid(), "type": "video", "segments": [], "flag": 0, "attribute": 0, "name": "", "is_default_name": True}
        d.d["tracks"] = [main]
        fr = frames()
        for k, (sh, (a, n)) in enumerate(zip(shots, fr)):
            seg = d.new_video_segment(str(DST / "plans" / f"plan_{k + 1:02d}.mp4"), 0, None, a / FPS, mute=True)
            # durée exacte en images : les plans se touchent sans trou ni chevauchement
            seg["target_timerange"]["start"] = CB.us(a / FPS, FPS)
            seg["target_timerange"]["duration"] = CB.us((a + n) / FPS, FPS) - CB.us(a / FPS, FPS)
            seg["source_timerange"] = {"start": 0, "duration": seg["target_timerange"]["duration"]}
            pts, base = zoom_points(sh, shots[k + 1] if k + 1 < len(shots) else None, n / FPS)
            seg["clip"]["scale"] = {"x": base, "y": base}
            if pts:
                CB.add_keyframes(seg, FPS, pts)
                CB.ease_keyframes(seg)
            main["segments"].append(seg)
        layer = {"scene": 1, "partage": 1, "capture": 2, "interrupteur": 3, "etiquette": 3, "soustitre": 4, "carte": 5, "score": 5}
        for name, t0, dur, _ in calques():
            seg = d.new_video_segment(str(DST / "calques" / f"{name}.mov"), 0, None, t0, mute=True, overlay_level=layer[name.split("_")[0]])
            d.place_overlay(seg, layer[name.split("_")[0]])
        for i in range(len(S.P)):
            d.place_audio(d.new_audio_segment(str(DST / "voix" / f"voix_{i + 1:02d}.wav"), 0, None, s0[i], gain), 1)
        for f in sorted((DST / "musique").glob("*.wav")):
            k = int(f.stem.split("_")[1]) if isinstance(CFG.get("musique"), list) else 0
            a = S.music_segments()[k - 1][0] if k else 0
            d.place_audio(d.new_audio_segment(str(f), 0, None, a, gain), 2)
        for t, n in S.cues():
            d.place_audio(d.new_audio_segment(str(DST / "sfx" / f"{n}.wav"), 0, None, t, round(S.VOL.get(n, 0.4) * gain, 3)), 3)
        # matériaux de l'ancienne timeline : retirés (le projet ne garde que ce qui sert)
        used = {s["material_id"] for t in d.d["tracks"] for s in t["segments"]} | \
               {r for t in d.d["tracks"] for s in t["segments"] for r in s.get("extra_material_refs", [])}
        for kind, lst in d.d["materials"].items():
            if isinstance(lst, list) and lst and all(isinstance(m, dict) and "id" in m for m in lst):
                d.d["materials"][kind] = [m for m in lst if m["id"] in used]

    CB.edit(PROJET, ["--quit"], mutate)
    print(f"projet CapCut « {PROJET} » : {len(shots)} plans, {len(calques())} calques, gain audio {20 * math.log10(gain):+.1f} dB")


if __name__ == "__main__":
    S.snap_bounds()
    if "--projet-seul" not in sys.argv:
        build_pieces()
    if "--pieces-seules" not in sys.argv:
        build_project()
