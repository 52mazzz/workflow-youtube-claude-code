"""Musique + SFX d'une vidéo, et plan de pose final pour CapCut.     python scripts/audio.py <id> [--garder-mix]

Entrées : 06_CAPCUT/<id>/voix_timeline.wav + voix_segments.json (voix.py), plan_capcut.json (export_capcut.py :
visuels + bruitages des éléments), zooms.json (zooms.py : tick discret sur un zoom léger, whoosh court sur un zoom de
lecture). Tous les bruitages passent par l'arbitre (`arbitre`) : jamais deux sons d'éléments différents à moins de
0,15 s (le plus fort reste), au plus 3 sons par seconde (les ticks partent d'abord), et chaque élément garde au moins
son premier son (« un élément sans SFX », « des SFX en trop » : retour du 2026-10-08).
video.json → "musiques": [[section, début, fin, fichier (dans 04_RESSOURCES/musiques), départ dans le morceau, gain en plus dB]],
"coupes": [[a, b]] (cut-range déjà faites : bornes recalées), "declics": [[de, à]] (déclic sur chaque plan de jeu
qui commence dans cette fenêtre : plans rapides de l'intro).
Musique : uniquement les morceaux de 04_RESSOURCES/musiques/perso (choisis par musique.py choisir). Par défaut (direction « duel lisible et nerveux » du
2026-10-07) : chaque morceau à la voix − 13 dB (video.json "musique_sous_voix", mesure EBU R128 de voix_timeline.wav ;
WOLF 9, niche 28, duels d'IA qui marchent 7,5 à 24), jamais baissé
sous la voix, coupures sèches ("coupe": "fondu" pour les anciens fondus). "musique_lufs" impose un niveau fixe à la
place (pokemon-ia : −32). Sorties : musique/*.wav, sfx/*.wav, plan_final.json (→ capcut_bridge.py place).
Le mixage de contrôle est mesuré puis supprimé (place disque) sauf --garder-mix.
"""
import json, shutil, sys
from pathlib import Path
from commun import MUSIQUES, SFX, read_json, remap, run, video, write_json
import subprocess

MUSIC_LUFS = -20.0  # ancien réglage (0927) ; par défaut maintenant video.json "musique_lufs" ou MUSIQUE_FOND
# Retours du 2026-10-03 : -32 LUFS, vraiment de fond. Le 2026-10-06, style WOLF : la voix - 9 dB. Le 2026-10-07,
# direction « duel lisible et nerveux » : la voix - 13 dB.
MUSIQUE_FOND = -32.0
MUSIQUE_SOUS_VOIX = 13.0
VOL = {"pop": 0.35, "tick": 0.3, "croix": 0.4, "valide": 0.35,
       "impact": 0.35, "sub_drop": 0.4, "frappe": 0.4, "whoosh": 0.4,
       "flash_capcut": 1.0, "flash_camera": 0.45}


# arbitre des bruitages : du plus fort au plus discret
PRIORITE = {"flash_camera": 7, "impact": 6, "sub_drop": 6, "flash_capcut": 5, "whoosh": 4, "whoosh_court": 4,
            "valide": 3, "croix": 3, "frappe": 2, "pop": 2, "pop_sortie": 2, "tick": 1}


def arbitre(cues, ecart=0.15, par_seconde=3):
    """cues : [(t, son, source)] → (gardés, retirés). Deux sons de sources différentes à moins de `ecart` s : le plus
    fort reste (les sons d'un même élément, voulus ensemble, restent : whoosh + impact de la carte). Puis au plus
    `par_seconde` moments sonores par seconde (un moment = les sons d'une source à moins de `ecart` s) : on retire
    d'abord le plus discret parmi ceux dont la source garde un autre moment, sinon le plus discret de tous."""
    prio = lambda c: PRIORITE.get(c[1].split("_")[0] if c[1].startswith("frappe") else c[1], 2)  # noqa: E731
    gardes = []
    for c in sorted(cues, key=lambda c: (-prio(c), c[0])):
        if not any(abs(g[0] - c[0]) < ecart and g[2] != c[2] for g in gardes):
            gardes.append(c)
    moments = []                                       # [[sons…]] d'une même source, serrés
    for c in sorted(gardes):
        m = next((m for m in moments if m[0][2] == c[2] and c[0] - m[-1][0] < ecart), None)
        (m.append(c) if m else moments.append([c]))
    while True:
        moments.sort(key=lambda m: m[0][0])
        trop = next((m for m in moments if sum(1 for n in moments if m[0][0] <= n[0][0] < m[0][0] + 1.0) > par_seconde), None)
        if trop is None:
            break
        fenetre = [n for n in moments if trop[0][0] <= n[0][0] < trop[0][0] + 1.0]
        par_source = {}
        for n in moments:
            par_source[n[0][2]] = par_source.get(n[0][2], 0) + 1
        libres = [n for n in fenetre if par_source[n[0][2]] > 1] or fenetre
        moments.remove(min(libres, key=lambda n: (max(prio(c) for c in n), -n[0][0])))
    gardes = sorted(c for m in moments for c in m)
    return gardes, sorted(set(cues) - set(gardes))


def measure(args, chain):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args, "-af",
                          f"{chain},loudnorm=I={MUSIC_LUFS}:TP=-2:LRA=11:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8").stderr
    return float(json.loads(err[err.rindex("{"): err.rindex("}") + 1])["input_i"])


def voice_lufs(path) -> float:
    """Volume intégré de la voix (EBU R128 : les silences sont exclus par les portes de la norme)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8").stderr
    return float(err[err.rfind("Summary"):].split("I:")[1].split("LUFS")[0])


def build_music(cfg):
    out, cuts, items = cfg["out"], cfg.get("coupes", []), []
    (out / "musique").mkdir(exist_ok=True)
    voice = out / "voix_timeline.wav"
    if "musique_lufs" in cfg:
        lufs = float(cfg["musique_lufs"])
    else:
        voix = voice_lufs(voice)
        lufs = round(voix - float(cfg.get("musique_sous_voix", MUSIQUE_SOUS_VOIX)), 1)
        print(f"voix : {voix:.1f} LUFS → musique à {lufs:.1f} LUFS")
    ducking, net = bool(cfg.get("ducking", False)), cfg.get("coupe", "net") == "net"
    for n, (name, a, b, file, offset, boost, *fondu) in enumerate(cfg["musiques"], 1):  # 7e valeur : fondu d'entrée (s)
        a, b = round(remap(a, cuts), 3), round(remap(b, cuts), 3)
        dur = b - a
        src = ["-ss", f"{offset}", "-t", f"{dur:.3f}", "-i", str(MUSIQUES / file)]
        fo = 0.05 if net else min(1.8, dur / 4)  # WOLF : la musique s'arrête net, pas de fondu de sortie
        gain = lufs - measure(src, "aresample=48000") + boost
        dst = out / "musique" / f"{n}_{name}.wav"
        duck = ("[m][v]sidechaincompress=threshold=0.05:ratio=4:knee=6:attack=150:release=1100:makeup=1[out]" if ducking
                else "[v]anullsink;[m]anull[out]")
        graph = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
                 f"afade=t=in:d={fondu[0] if fondu else 0.02 if net else 0.3},afade=t=out:st={dur - fo:.3f}:d={fo:.3f}[m];"
                 f"[1:a]aresample=48000,aformat=channel_layouts=stereo[v];" + duck)
        run(*src, "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", str(voice), "-filter_complex", graph, "-map", "[out]",
            "-c:a", "pcm_s16le", str(dst))
        items.append({"file": f"musique/{dst.name}", "at": a, "layer": 2, "volume": 1.0})
        print(f"musique {n} {name:<16} {file:<44} {a:7.2f} → {b:7.2f} s  gain {gain:+.1f} dB", flush=True)
    return items


def typing(out, name, dur, every=0.085):
    """Frappes clavier : le tick d'interface répété, hauteur légèrement variée."""
    n = int(dur / every)
    parts = [f"[0:a]asetrate={48000 * (1 + ((i * 7) % 5 - 2) * 0.04):.0f},aresample=48000,volume={0.7 + (i % 3) * 0.15:.2f},"
             f"adelay={int(i * every * 1000)}|{int(i * every * 1000)}[t{i}]" for i in range(n)]
    graph = ";".join(parts) + f";{''.join(f'[t{i}]' for i in range(n))}amix=inputs={n}:normalize=0,atrim=0:{dur + 0.1:.3f}[out]"
    run("-i", str(SFX / "tick.wav"), "-filter_complex", graph, "-map", "[out]", "-ac", "2", "-c:a", "pcm_s16le",
        str(out / "sfx" / f"{name}.wav"))


def main(vid: str) -> None:
    cfg = video(vid)
    out = cfg["out"]
    plan = read_json(out / "plan_capcut.json")
    voice = read_json(out / "voix_segments.json")
    music = build_music(cfg)
    (out / "sfx").mkdir(exist_ok=True)
    for f in SFX.glob("*.wav"):
        shutil.copy2(f, out / "sfx" / f.name)
    for name, dur, every in (("frappe_1", 1.4, 0.085), ("frappe_2", 1.6, 0.085), ("frappe_3", 2.3, 0.06)):
        typing(out, name, dur, every)
    cues = [(c[0], c[1], c[2] if len(c) > 2 else f"element{n}") for n, c in enumerate(plan.get("sfx", []))]
    # déclic d'appareil photo sur chaque plan rapide (fenêtres de video.json, et « À venir » d'export_capcut)
    for a, b in cfg.get("declics", []) + plan.get("declics", []):
        cues += [(i["at"], "flash_capcut", f"declic{i['at']}") for i in plan["items"]
                 if i.get("layer") == 1 and a <= i["at"] < b and not i["file"].startswith("transitions/")]  # son choisi par lui (2026-10-03)
    zooms = read_json(out / "zooms.json")
    if zooms:
        cues += [(z["at"] - 0.02, "whoosh_court" if z.get("scale", 1) >= 1.5 else "tick", f"zoom{z['at']}") for z in zooms["punch"]]
    cues += [(c[0], c[1], f"jeu{c[0]}") for c in cfg.get("sfx", [])]  # événements du jeu
    if cfg.get("entree", "eclaircissement"):  # le hook entre sur le son flash_camera (sa retouche de pokemon-ia, 2026-10-03)
        cues.append((0.0, "flash_camera", "entree"))
    cues = [(round(max(t, 0), 3), s, src) for t, s, src in cues]
    cues, retires = arbitre(cues)
    if retires:
        print(f"{len(retires)} bruitage(s) retiré(s) par l'arbitre : " +
              ", ".join(f"{s} {t:.2f} s ({src})" for t, s, src in retires[:12]) + (" …" if len(retires) > 12 else ""))
    cues = [(t, s) for t, s, _ in cues]
    sfx = [{"file": f"sfx/{s}.wav", "at": t, "layer": 3, "volume": VOL.get(s.split("_")[0] if s.startswith("frappe") else s, 0.4)}
           for t, s in cues]
    write_json(out / "plan_final.json", {"mute_main": True, "items": plan["items"] + voice + music + sfx})
    print(f"plan_final.json : {len(plan['items'])} visuels, {len(voice)} clips voix, {len(music)} musiques, {len(sfx)} SFX")
    # mixage de contrôle (voix + musiques + SFX) : niveau intégré et crête, puis supprimé
    inputs, chains = ["-i", str(out / "voix_timeline.wav")], ["[0:a]aresample=48000,aformat=channel_layouts=stereo[a0]"]
    for k, it in enumerate(music + sfx, 1):
        inputs += ["-i", str(out / it["file"])]
        ms = int(it["at"] * 1000)
        chains.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={it['volume']},adelay={ms}|{ms}[a{k}]")
    n = len(music) + len(sfx) + 1
    script = out / "_mix.txt"
    script.write_text(";".join(chains) + ";" + "".join(f"[a{k}]" for k in range(n)) +
                      f"amix=inputs={n}:normalize=0:duration=first[out]", encoding="utf-8")
    mix = out / "mix_controle.wav"
    run(*inputs, "-/filter_complex", str(script), "-map", "[out]", "-c:a", "pcm_s16le", str(mix))
    script.unlink()
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mix), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary"):]
    print("mix de contrôle :", " ".join(l.strip() for l in summary.splitlines() if l.strip().startswith(("I:", "Peak:"))),
          "(viser ≈ −14 LUFS, entre −13 et −14,5 ; crête ≤ −1 dBFS : YouTube ramène tout à −14 et ne remonte pas une vidéo trop basse)")
    # gain général (voix, musiques, SFX ensemble) : −14 LUFS visés, crête ≤ −1,1 dBFS
    import re
    i_lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    peak = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1))
    g_db = min(-14.0 - i_lufs, -1.1 - peak)
    if abs(g_db) > 0.2:
        g = 10 ** (g_db / 20)
        plan_final = read_json(out / "plan_final.json")
        for it in plan_final["items"]:
            if it["file"].startswith(("voix/", "musique/", "sfx/")):
                it["volume"] = round(it.get("volume", 1.0) * g, 4)
        write_json(out / "plan_final.json", plan_final)
        print(f"gain général {g_db:+.1f} dB → ≈ {i_lufs + g_db:.1f} LUFS, crête ≈ {peak + g_db:.1f} dBFS")
    if "--garder-mix" not in sys.argv:
        mix.unlink()


if __name__ == "__main__":
    main(sys.argv[1])
