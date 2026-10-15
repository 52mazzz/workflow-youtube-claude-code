"""Short vertical (1080×1920, 60 i/s) style LAirHisson, décrit entièrement par un fichier de réglages.

usage : python scripts/short.py videos/<id>/<short>.json [captures|video|voix|mots|audio|html|planche|rendu|tout] [--leger]
        (« tout » = captures → html ; « rendu » à part, après la planche de contrôle)

Réglages (JSON) — voir videos/_exemple/short1.json (Short 1 de la 0927) :
  video (id), projet (copie CapCut finale), dossier (sous assets/shorts/), sortie (MP4 final),
  musique {fichier (dans 04_RESSOURCES/musiques), depart, lufs} ou liste de morceaux [{fichier, depart, de, a, lufs,
  fondu, suite}] (de/a = s ou [n° passage, décalage] ; coupures nettes entre deux, suite = reprend où il en serait), captures {nom: [rush, s, x, y, w, h]},
  passages : [{a, b (voix dans la timeline finale), texte (mots exacts dits), plans: [...], surgit: [...],
              interrupteur: [[t, "off"|"on"], …]}]
  plan : {"rush": fichier, "src": s} | {"sync": true} (plans de la timeline sous la voix) | {"image": chemin}
         + "dur" (s ; absent sur le dernier = le reste), "vitesse" (10 = accéléré réel d'un rush, génération), "cx" (centre du recadrage 0..1), "zoom" (1.3 = zoom
         punch immédiat, [1, 1.2] = zoom progressif), "secousse", "flash" (éclair + déclic à l'entrée du plan).
  surgit : {"capture": nom, "t": s, "dur": s} (capture qui surgit en haut, avec pop) + "surligne": [x, y, w, h] (zone
         de la capture, en pixels de la capture, surlignée en jaune à "sa" s, défaut 0,35 s).

Style WOLF (référence config/youtube/references/wolf/style.md, tout est facultatif ; un temps = s du short ou
[n° passage, décalage]) :
  sous_titres (false = aucun), ducking (false = la musique ne baisse pas sous la voix), musique_sous_voix (dB : chaque
  morceau sans "lufs" est réglé à la voix − cet écart), coupe ("net" = coupures de musique sèches par défaut),
  duel {a: {nom, couleur, logo}, b: {…}} (noms des deux côtés),
  etiquettes [{de, a, texte, couleur, etat: [[temps, "ok"|"rate"], …]}] (pastille persistante en haut à gauche),
  cartes [{t, dur, texte, fond, logo}] (carte titre plein écran, gros texte blanc sur fond uni),
  score [{t, dur, avant: [a, b], point: "a"|"b"|""}] (tableau de score plein écran qui revient entre les parties),
  par passage "sfx": [[décalage, nom], …] (bruitages d'événements) ;
  plan "partage": [{rush, src, cx}, {rush, src, cx}] (écran partagé haut / bas, noms du duel), "pixel": true ou
  [x, y, w, h] (floutage en gros pixels, en pixels du short 1080 × 1920).

Garde-fous (bug du Short 1 v1) : bornes de voix recalées dans les silences ; audio = durée exacte de la vidéo ;
aucun trou de son. Le script s'arrête si l'un d'eux échoue.
"""
import difflib, json, os, re, subprocess, sys, unicodedata
from pathlib import Path
from commun import DRAFTS, HF, MODEL, MUSIQUES, NOMBRES, ROOT, SFX, WHISPER, h264, seuil_silence
from commun import rush as chemin_rush

FPS = 60
BELOW = 0x4000 if "--leger" in sys.argv else 0
CFG_PATH = Path(sys.argv[1]) if Path(sys.argv[1]).is_absolute() else HF / sys.argv[1]
CFG = json.loads(CFG_PATH.read_text(encoding="utf-8-sig"))
OUT = HF / "assets" / "shorts" / CFG["dossier"]
VOICE = ROOT / "06_CAPCUT" / CFG["video"] / "voix_timeline.wav"
COMP = "short_" + re.sub(r"\W", "_", CFG["dossier"])
P = CFG["passages"]


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, creationflags=BELOW)


def probe(path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True).stdout)


def draft():
    return json.loads((DRAFTS / CFG["projet"] / "draft_content.json").read_text(encoding="utf-8-sig"))


# ───────────── garde-fou 1 : chaque passage commence et finit dans un silence (ou sur une coupe du dérushage)
def silences(a, b):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(VOICE),
                          "-af", f"silencedetect=n={seuil_silence(VOICE)}dB:d=0.04", "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [a + float(l.split("silence_start: ")[1].split()[0]) for l in err.splitlines() if "silence_start" in l]
    en = [a + float(l.split("silence_end: ")[1].split()[0]) for l in err.splitlines() if "silence_end" in l]
    return list(zip(st, en + [b] * (len(st) - len(en))))


def snap_bounds():
    main = next(t for t in draft()["tracks"] if t["type"] == "video")
    joins = [s["target_timerange"]["start"] / 1e6 for s in main["segments"]]
    for p in P:
        sil = silences(p["a"] - 0.8, p["b"] + 0.8)
        a, b = p["a"], p["b"]
        clean = lambda t: any(s <= t <= e for s, e in sil) or any(abs(t - j) < 0.03 for j in joins)
        if not clean(a):  # début dans la parole : silence juste avant (≤ 0,15 s), sinon le creux le plus bas juste avant
            prev = [e for s, e in sil if abs(e - a) <= 0.15]  # fin de silence la plus proche (avant ou juste après)
            if prev:
                p["a"] = round(min(prev, key=lambda e: abs(e - a)) - 0.03, 3)
            else:
                t, db = quietest(a - 0.12, a + 0.15)  # la transcription donne parfois le mot ~0,1 s trop tôt
                if db > -26:
                    raise SystemExit(f"ERREUR passage {a}–{b} : le début tombe dans la parole ({db:.0f} dB)")
                p["a"] = round(t, 3)
        if not clean(b):
            before = [s for s, e in sil if p["a"] + 0.3 < s <= b]
            if before:
                p["b"] = round(max(before) + 0.06, 3)
        if not clean(p["b"]):  # phrases enchaînées sans vrai silence : couper dans le creux le plus bas juste avant
            t, db = quietest(p["b"] - 0.15, p["b"] + 0.03)  # juste avant le mot suivant, pas au milieu de la phrase
            if db > -26:
                raise SystemExit(f"ERREUR passage {a}–{b} : la fin tombe dans la parole ({db:.0f} dB), choisir une autre borne")
            p["b"] = round(t, 3)
        if (p["a"], p["b"]) != (a, b):
            print(f"  voix recalée sur les silences : {a:.3f}–{b:.3f} → {p['a']:.3f}–{p['b']:.3f}")


def quietest(a, b):
    """Milieu de la tranche de 25 ms la plus silencieuse entre a et b → (seconde, dB)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(VOICE), "-af",
                          "aresample=8000,asetnsamples=200,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    levels = [float(l.split("=")[-1]) for l in err.splitlines() if "RMS_level" in l]
    k = min(range(len(levels)), key=lambda i: levels[i])
    return a + (k + 0.5) * 0.025, levels[k]


def starts():
    t, res = 0.0, []
    for p in P:
        res.append(round(t, 3))
        t += p["b"] - p["a"]
    return res, round(t, 3)


def at(x, defaut=0.0):
    """Temps dans le short : secondes, ou [n° passage (1 = premier), décalage dans ce passage]."""
    s0, _ = starts()
    return defaut if x is None else s0[x[0] - 1] + x[1] if isinstance(x, list) else x


RYTHME = CFG.get("rythme", {"cible": 1.3, "min": 0.8, "punch": 1.18})  # style LAirHisson : ça bouge toutes les ~1,3 s


def shots():
    """Plans à la suite, avec leur début dans le short (le dernier plan d'un passage prend le reste).
    Dynamisme automatique : un plan long sans zoom imposé est redécoupé en morceaux d'~1,3 s, coupés sur des débuts
    de mots, qui alternent cadre large / zoom punch (jump cuts, comme LAirHisson), avec une légère poussée."""
    s0, _ = starts()
    words = json.loads((OUT / "mots.json").read_text(encoding="utf-8")) if (OUT / "mots.json").exists() else []
    out = []
    for pi, (p, t0) in enumerate(zip(P, s0)):
        d, used = p["b"] - p["a"], 0.0
        for i, sh in enumerate(p["plans"]):
            dur = d - used if i == len(p["plans"]) - 1 or "dur" not in sh else min(sh["dur"], d - used)
            if dur <= 0.01:
                continue
            base = dict(sh, t=round(t0 + used, 3), d=round(dur, 3), off=round(used, 3), a=p["a"], srcoff=0.0)
            if i == 0 and p.get("transition") and pi > 0:
                base["trans"] = True
            if (not RYTHME or "zoom" in sh or "cadre" in sh or sh.get("fixe") or dur < RYTHME["cible"] + RYTHME["min"]
                    or "image" in sh or "partage" in sh):
                out.append(base)
            else:
                cuts = [w["t"] for w in words if base["t"] + RYTHME["min"] <= w["t"] <= base["t"] + dur - RYTHME["min"]]
                pts, last = [], base["t"]
                for c in cuts:
                    if c - last >= RYTHME["cible"]:
                        pts.append(c); last = c
                bounds = [base["t"]] + pts + [base["t"] + dur]
                for k, (x, y) in enumerate(zip(bounds, bounds[1:])):
                    z = 1.0 if k % 2 == 0 else RYTHME["punch"]
                    out.append(dict(base, t=round(x, 3), d=round(y - x, 3), off=round(used + x - base["t"], 3),
                                    srcoff=round(x - base["t"], 3), zoom=[z, z + 0.04], trans=base.get("trans") and k == 0))
            used += dur
    return out


def sync_pieces(a, b, main):
    vids = {m["id"]: m for m in draft()["materials"]["videos"]}
    res = []
    for s in main["segments"]:
        st = s["target_timerange"]["start"] / 1e6
        en = st + s["target_timerange"]["duration"] / 1e6
        lo, hi = max(st, a), min(en, b)
        if hi - lo > 0.02:
            res.append((Path(vids[s["material_id"]]["path"]).name, s["source_timerange"]["start"] / 1e6 + (lo - st), hi - lo))
    return res


def build_captures():
    (OUT / "captures").mkdir(parents=True, exist_ok=True)
    for name, (rush, t, x, y, w, h) in CFG.get("captures", {}).items():
        run("-ss", str(t), "-i", str(chemin_rush(rush)), "-frames:v", "1", "-vf", f"crop={w}:{h}:{x}:{y}", str(OUT / "captures" / f"{name}.png"))
    print("captures :", ", ".join(CFG.get("captures", {})))


def pixel(zone, k):
    """Floutage en gros pixels (teasing de l'accroche, style WOLF) : toute l'image (true) ou une zone [x, y, w, h]."""
    if not zone:
        return ""
    if zone is True:
        return ",scale=54:96,scale=1080:1920:flags=neighbor"
    x, y, w, h = zone
    return (f",split[z{k}a][z{k}b];[z{k}b]crop={w}:{h}:{x}:{y},scale={max(2, w // 20)}:{max(2, h // 20)},"
            f"scale={w}:{h}:flags=neighbor[z{k}c];[z{k}a][z{k}c]overlay={x}:{y}")


def build_video():
    OUT.mkdir(parents=True, exist_ok=True)
    main = next(t for t in draft()["tracks"] if t["type"] == "video")
    args, chains, labels, n = [], [], [], 0
    for sh in shots():
        x = int(min(max(sh.get("cx", 0.5) * 1920 - 304, 0), 1312))
        k = len(labels)
        px = pixel(sh.get("pixel"), k)
        if "image" in sh:
            args += ["-loop", "1", "-t", f"{sh['d']:.3f}", "-i", str(ROOT / sh["image"])]
            chains.append(f"[{n}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},setsar=1,"
                          f"trim=duration={sh['d']:.3f},setpts=PTS-STARTPTS{px}[p{k}]")
            labels.append(f"[p{k}]"); n += 1
            continue
        if "partage" in sh:  # écran partagé : deux rushs l'un au-dessus de l'autre, chacun en 1080 × 960
            moities = []
            for j, part in enumerate(sh["partage"]):
                xj = int(min(max(part.get("cx", 0.5) * 1920 - 607, 0), 705))
                args += ["-ss", f"{part['src'] + sh.get('srcoff', 0.0):.3f}", "-t", f"{sh['d']:.3f}", "-i", str(chemin_rush(part["rush"]))]
                chains.append(f"[{n}:v]fps={FPS},crop=1215:1080:{xj}:0,scale=1080:960:flags=lanczos,setsar=1,"
                              f"trim=duration={sh['d']:.3f},setpts=PTS-STARTPTS[h{k}_{j}]")
                moities.append(f"[h{k}_{j}]"); n += 1
            chains.append(f"{''.join(moities)}vstack=inputs=2{px}[p{k}]")
            labels.append(f"[p{k}]")
            continue
        pieces = (sync_pieces(sh["a"] + sh["off"], sh["a"] + sh["off"] + sh["d"], main) if sh.get("sync")
                  else [(sh["rush"], sh["src"] + sh.get("srcoff", 0.0), sh["d"])])
        for rush, src, d in pieces:
            k = len(labels)
            vit = 1.0 if sh.get("sync") else float(sh.get("vitesse", 1))  # accéléré réel (génération) : lit d × vit s de rush
            args += ["-ss", f"{src:.3f}", "-t", f"{d * vit:.3f}", "-i", str(chemin_rush(rush))]
            chains.append(f"[{n}:v]{f'setpts=PTS/{vit},' if vit != 1 else ''}fps={FPS},crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1,"
                          f"trim=duration={d:.3f},setpts=PTS-STARTPTS{pixel(sh.get('pixel'), k)}[p{k}]")
            labels.append(f"[p{k}]"); n += 1
    graph = ";".join(chains) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0[v]"
    (OUT / "video.ffgraph").write_text(graph, encoding="utf-8")
    run(*args, "-/filter_complex", str(OUT / "video.ffgraph"), "-map", "[v]", "-r", str(FPS),
        *h264(15), "-pix_fmt", "yuv420p", str(OUT / "base.mp4"))
    _, total = starts()
    got = probe(OUT / "base.mp4")
    if abs(got - total) > 0.05:
        raise SystemExit(f"ERREUR image {got:.2f} s ≠ passages {total:.2f} s")
    print(f"image : {OUT / 'base.mp4'} ({got:.2f} s)")


def build_voice():
    args, chains = [], []
    for i, p in enumerate(P):
        d = p["b"] - p["a"]
        args += ["-ss", f"{p['a']:.3f}", "-t", f"{d:.3f}", "-i", str(VOICE)]
        chains.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={d:.3f},"
                      f"afade=t=in:d=0.012,afade=t=out:st={d - 0.025:.3f}:d=0.025[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(P))) + f"concat=n={len(P)}:v=0:a=1[out]"
    run(*args, "-filter_complex", graph, "-map", "[out]", "-c:a", "pcm_s16le", str(OUT / "voix.wav"))
    print("voix :", OUT / "voix.wav")


def norm(w):
    w = unicodedata.normalize("NFD", w.lower().replace("’", "'"))
    w = re.sub(r"[^a-z0-9]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))
    return NOMBRES.get(w, w)


def whisper_words(wav: Path, offset: float):
    """Mots entendus (texte, début DTW) dans un fichier, décalés de offset."""
    base = wav.with_suffix("")
    subprocess.run([str(WHISPER), "-m", str(MODEL), "-f", str(wav), "-l", "fr", "--dtw", "large.v3.turbo",
                    "-nfa", "-ojf", "-of", str(base), "-t", "8", "-np"], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, creationflags=BELOW)
    heard = []
    for s in json.loads(Path(f"{base}.json").read_text(encoding="utf-8"))["transcription"]:
        for tok in s["tokens"]:
            if tok["text"].startswith("[_") or not tok["text"].strip():
                continue
            t = offset + (tok["t_dtw"] * 10 if tok["t_dtw"] >= 0 else tok["offsets"]["from"]) / 1000
            if tok["text"].startswith(" ") or not heard:
                heard.append([tok["text"].strip(), t])
            else:
                heard[-1][0] += tok["text"]
    return heard


def build_words():
    """Mots exacts (texte des passages), calés sur les débuts de mots whisper DTW ; hésitations ignorées.
    Chaque passage est retranscrit SEUL (plus précis que la voix recollée : bug de calage du Short 1 v2)."""
    s0, total = starts()
    words = []
    (OUT / "passages").mkdir(exist_ok=True)
    for p, t0 in zip(P, s0):
        d = p["b"] - p["a"]
        wav = OUT / "passages" / f"p{P.index(p):02d}.wav"
        run("-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", str(OUT / "voix.wav"), "-af", "apad=pad_dur=0.6", "-ar", "16000", "-ac", "1", str(wav))
        said = p["texte"].split()
        h = [w for w in whisper_words(wav, t0) if w[1] < t0 + d]
        sm = difflib.SequenceMatcher(a=[norm(w) for w in said], b=[norm(w[0]) for w in h], autojunk=False)
        ts = [None] * len(said)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                ts[blk.a + k] = max(t0, h[blk.b + k][1] - 0.12)
        if all(t is None for t in ts):  # rien d'entendu (passage très court) : mots répartis depuis le début
            ts[0] = t0
        known = [(i, t) for i, t in enumerate(ts) if t is not None]
        for i in range(len(ts)):
            if ts[i] is None:
                pv = max((k for k in known if k[0] < i), default=None, key=lambda k: k[0])
                nx = min((k for k in known if k[0] > i), default=None, key=lambda k: k[0])
                ts[i] = pv[1] + (nx[1] - pv[1]) * (i - pv[0]) / (nx[0] - pv[0]) if pv and nx else (pv or nx)[1] + 0.25 * (i - (pv or nx)[0])
        miss = len(said) - sum(b.size for b in sm.get_matching_blocks())
        print(f"{t0:6.2f}  {miss} mot(s) interpolé(s)  | entendu : {' '.join(w[0] for w in h)}")
        words += [{"text": w, "t": round(t, 3), "p": P.index(p)} for w, t in zip(said, ts)]
    (OUT / "mots.json").write_text(json.dumps(words, ensure_ascii=False, indent=0), encoding="utf-8")


VOL = {"flash_capcut": 1.0, "pop": 0.45, "pop_sortie": 0.4, "tick": 0.45, "riser": 0.3, "impact": 0.45,
       "whoosh": 0.4, "whoosh_court": 0.4, "valide": 0.5, "croix": 0.5}  # bruitages


def cues():
    """Bruitages : clic (son CapCut) à chaque changement d'interrupteur et sur les flashs, pop quand une capture surgit."""
    s0, _ = starts()
    res = []
    for p, t0 in zip(P, s0):
        res += [(t0 + it[0], CLIC) for it in p.get("interrupteur", [])]
        res += [(t0 + s["t"], "pop") for s in p.get("surgit", [])]
        sc = p.get("scene")
        if sc and sc.get("type") == "duel":  # motion design sans musique : les bruitages le font vivre (retour du v4)
            lg, tr = t0 + sc.get("logos", sc["t"]), t0 + sc.get("transforme", p["b"] - p["a"])
            res += [(t0 + sc["t"] + 0.05, "pop_sortie"), (lg, "pop"), (lg + 0.12, "pop"),
                    (tr - 0.25, "tick"), (tr - 1.6, "riser"), (tr, "impact")]
        res += [(t0 + dt, nom) for dt, nom in p.get("sfx", [])]
        res += [(t0 + s["t"] + s.get("sa", 0.35), "whoosh_court") for s in p.get("surgit", []) if s.get("surligne")]
    res += [(sh["t"], CLIC) for sh in shots() if sh.get("flash") or sh.get("trans") or sh.get("partage")]
    # style WOLF : chaque élément à l'écran a son bruitage
    for c in CFG.get("cartes", []):
        res += [(at(c["t"]) - 0.08, "whoosh"), (at(c["t"]), "impact")]
    for e in CFG.get("etiquettes", []):
        res += [(at(e.get("de")), "pop")] + [(at(x), "valide" if etat == "ok" else "croix") for x, etat in e.get("etat", [])]
    for s in CFG.get("score", []):
        res += [(at(s["t"]), "whoosh_court")] + ([(at(s["t"]) + SCORE_POINT, "valide")] if s.get("point") else [])
    return sorted((round(max(0, t - 0.02), 3), n) for t, n in res)


CLIC = "flash_capcut"  # tout clic ou déclic = le son CapCut « click (camera shutter sound single shot) » (demande du 2026-10-05)
SCORE_POINT = 0.55  # le +1 du tableau de score tombe 0,55 s après son apparition (même valeur dans kit/tsar.js)


def tape_stop(path, L):
    """Remplace les L dernières secondes par un arrêt de bande : vitesse 1 → 0 (le son ralentit et descend dans les
    graves), fondu sur le dernier quart. Retour du v5 : les coupures nettes doivent faire « vrooom », pas un simple arrêt."""
    import array, wave
    with wave.open(str(path)) as w:
        p = w.getparams(); a = array.array("h", w.readframes(p.nframes))
    n = min(int(L * p.framerate), p.nframes // 2); start = p.nframes - n
    src, out, pos = a[2 * start:], array.array("h", bytes(4 * n)), 0.0
    for i in range(n):
        u = i / n
        j = int(pos); fr = pos - j
        if j + 1 < n:
            g = 1 - max(0.0, (u - 0.75) / 0.25)
            out[2 * i] = int((src[2 * j] * (1 - fr) + src[2 * j + 2] * fr) * g)
            out[2 * i + 1] = int((src[2 * j + 1] * (1 - fr) + src[2 * j + 3] * fr) * g)
        pos += (1 - u) ** 1.6
    a[2 * start:] = out
    with wave.open(str(path), "wb") as w:
        w.setparams(p); w.writeframes(a.tobytes())


def music_segments():
    """Morceaux de musique [(début, fin, réglages)] dans le temps du short (musique en liste)."""
    _, total = starts()
    segs = sorted(((at(g.get("de"), 0), at(g.get("a"), total), g) for g in CFG["musique"]), key=lambda z: z[0])
    for k, (a, b, g) in enumerate(segs):
        if g.get("suite"):  # reprise après une coupure : le morceau repart là où il en serait s'il avait continué
            pa, _, pg = next(z for z in reversed(segs[:k]) if z[2]["fichier"] == g["fichier"])
            segs[k] = (a, b, dict(g, depart=pg.get("depart", 0) + a - pa))
    return segs


def lufs(path) -> float:
    """Volume intégré (LUFS) d'un fichier : les silences sont exclus par la norme (portes de l'EBU R128)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def niveau_musique(g):
    """LUFS d'un morceau : le sien, sinon voix − musique_sous_voix (style WOLF, ~9 dB), sinon −24."""
    if "lufs" in g:
        return g["lufs"]
    if "musique_sous_voix" in CFG:
        if "_voix_lufs" not in CFG:
            CFG["_voix_lufs"] = lufs(OUT / "voix.wav")
            print(f"voix : {CFG['_voix_lufs']:.1f} LUFS → musique à {CFG['_voix_lufs'] - CFG['musique_sous_voix']:.1f} LUFS")
        return round(CFG["_voix_lufs"] - CFG["musique_sous_voix"], 1)
    return -24


def ducking(graph_m):
    """Musique baissée sous la voix (compresseur) ; "ducking": false = aucune baisse (style WOLF)."""
    if CFG.get("ducking", True) is False:
        return f"{graph_m}[md];[v1]anullsink"
    return f"{graph_m}[m];[m][v1]sidechaincompress=threshold=0.04:ratio=4:knee=6:attack=100:release=600:makeup=1[md]"


def build_audio():
    s0, total = starts()
    m = CFG.get("musique")
    dur = total + 0.5
    gaps = []  # silences de musique voulus (avant le 1er morceau, coupures nettes) : pas des trous de son
    if isinstance(m, list):  # plusieurs morceaux : [{fichier, depart, de, a, lufs, fondu}] ; de/a = s ou [n° passage, décalage]
        segs = music_segments()
        gaps = [(0, segs[0][0])] + [(a[1], b[0]) for a, b in zip(segs, segs[1:]) if b[0] - a[1] > 0.05]
        graph, inputs = "", []
        for k, (a, b, g) in enumerate(segs):
            src = Path(g["fichier"]) if Path(g["fichier"]).is_absolute() else MUSIQUES / g["fichier"]
            fin = b >= total - 0.01
            fd = min(0.6, (b - a) / 5)  # fin du short : fondu court si le morceau vient de repartir
            fo = f",afade=t=out:st={b - a - fd:.3f}:d={fd:.3f}" if fin else ""
            piece = OUT / f"musique_{k}.wav"
            run("-ss", str(g.get("depart", 0)), "-i", str(src), "-af",
                f"aresample=48000,aformat=channel_layouts=stereo,loudnorm=I={niveau_musique(g)}:TP=-3:LRA=11,aresample=48000,"
                f"atrim=0:{b - a:.3f},asetpts=N/SR/TB,afade=t=in:d={g.get('fondu', 0.02)}{fo}", "-c:a", "pcm_s16le", str(piece))
            if not fin and g.get("coupe", CFG.get("coupe", "vroom")) == "vroom":  # « tape stop » (ralentit et plonge) qui finit pile sur la coupure ; "net" = arrêt sec
                tape_stop(piece, g.get("arret", 0.45))
            graph += f"[{k}:a]adelay={int(a * 1000)}|{int(a * 1000)}[s{k}];"
            inputs += ["-i", str(piece)]
        n = len(segs)
        graph += (ducking(f"{''.join(f'[s{k}]' for k in range(n))}amix=inputs={n}:normalize=0:duration=longest,apad,atrim=0:{dur:.3f}")
                  + f";[{n}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.3f},asplit=2[v1][v2]")
        inputs += ["-i", str(OUT / "voix.wav")]
        print("musique : " + ", ".join(f"{a:.2f}-{b:.2f} {Path(g['fichier']).stem[:20]}" for a, b, g in segs))
    elif m:  # musique continue, nettement sous la voix (« pas trop forte » : −24 LUFS par défaut, baisse marquée quand il parle)
        src = Path(m["fichier"]) if Path(m["fichier"]).is_absolute() else MUSIQUES / m["fichier"]
        graph = (ducking(f"[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I={niveau_musique(m)}:TP=-3:LRA=11,apad,atrim=0:{dur:.3f},"
                         f"afade=t=in:d=0.15,afade=t=out:st={total - 0.6:.3f}:d=0.6")
                 + f";[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.3f},asplit=2[v1][v2]")
        inputs = ["-ss", str(m["depart"]), "-i", str(src), "-i", str(OUT / "voix.wav")]
    else:  # version sans musique (musique ajoutée ensuite par l'utilisateur, ex. éditeur Shorts de YouTube)
        graph = (f"anullsrc=r=48000:cl=stereo,atrim=0:{dur:.3f}[md];"
                 f"[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{dur:.3f}[v2]")
        inputs = ["-f", "lavfi", "-t", "0.1", "-i", "anullsrc", "-i", str(OUT / "voix.wav")]
    cs = cues()
    vol = VOL
    base = inputs.count("-i")
    for k, (t, name) in enumerate(cs, base):
        inputs += ["-i", str(SFX / f"{name}.wav")]
        graph += f";[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol.get(name, 0.4)},adelay={int(t * 1000)}|{int(t * 1000)}[c{k}]"
    mix = "[mdA][v2]" + "".join(f"[c{k}]" for k in range(base, len(cs) + base))
    # sorties annexes pour l'export CapCut : musique déjà baissée sous la voix, mix avant normalisation (pour le gain)
    graph += (f";[md]asplit=2[mdA][mdB];{mix}amix=inputs={len(cs) + 2}:normalize=0:duration=longest,asplit=2[pre][mx];"
              f"[mx]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,apad,asetpts=N/SR/TB,atrim=0:{total:.3f}[out]")
    (OUT / "audio.ffgraph").write_text(graph, encoding="utf-8")
    run(*inputs, "-/filter_complex", str(OUT / "audio.ffgraph"), "-map", "[out]", "-c:a", "pcm_s16le", str(OUT / "audio.wav"),
        "-map", "[mdB]", "-c:a", "pcm_s16le", str(OUT / "musique_duckee.wav"), "-map", "[pre]", "-c:a", "pcm_f32le", str(OUT / "mix_brut.wav"))
    # garde-fous 2 et 3
    got = probe(OUT / "audio.wav")
    if (OUT / "base.mp4").exists():  # référence = durée réelle de l'image (arrondie à l'image près)
        total = probe(OUT / "base.mp4")
    if abs(got - total) > 0.05:  # tolérance : 3 images
        raise SystemExit(f"ERREUR audio {got:.2f} s ≠ vidéo {total:.2f} s")
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(OUT / "audio.wav"), "-af", "silencedetect=n=-45dB:d=0.3",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    holes = [float(l.split("silence_start: ")[1].split()[0]) for l in err.splitlines() if "silence_start" in l]
    holes = [h for h in holes if not any(a - 0.05 <= h <= b for a, b in gaps)]  # silences voulus exclus
    if holes and m:
        raise SystemExit(f"ERREUR trou de son à {holes} s")
    print(f"audio : {got:.2f} s = vidéo, aucun trou de son, {len(cs)} bruitages")


def build_html():
    page(HF / "shorts" / f"{COMP}.html", COMP, html_data())
    print("composition :", HF / "shorts" / f"{COMP}.html")


def html_data():
    s0, total = starts()
    words = json.loads((OUT / "mots.json").read_text(encoding="utf-8"))
    return {
        "duration": total,
        "plans": [dict({k: sh[k] for k in ("t", "d", "zoom", "cadre", "flash", "trans") if sh.get(k)},
                       **({"partage": True} if sh.get("partage") else {})) for sh in shots()],
        "scenes": [dict(p["scene"], t=t0 + p["scene"]["t"], logos=t0 + p["scene"].get("logos", p["scene"]["t"]),
                        transforme=t0 + p["scene"].get("transforme", p["b"] - p["a"]), fin=t0 + p["b"] - p["a"],
                        dossier=f"assets/shorts/{CFG['dossier']}/captures")
                   for p, t0 in zip(P, s0) if p.get("scene")],
        "surgit": [dict({"t": t0 + s["t"], "d": s["dur"], "src": f"assets/shorts/{CFG['dossier']}/captures/{s['capture']}.png"},
                        **cadre_capture(s, t0)) for p, t0 in zip(P, s0) for s in p.get("surgit", [])],
        "interrupteur": [{"t": t0 + it[0], "etat": it[1], "nom": it[2] if len(it) > 2 else "", "fin": t0 + p["b"] - p["a"]}
                         for p, t0 in zip(P, s0) for it in p.get("interrupteur", [])],
        "mots": words,
        # style WOLF
        "sous_titres": CFG.get("sous_titres", True),
        "duel": CFG.get("duel", {"a": {"nom": "CLAUDE", "couleur": "#E07A5A", "logo": "claude"},
                                 "b": {"nom": "CHATGPT", "couleur": "#3CCFB0", "logo": "chatgpt"}}),
        "etiquettes": [{"de": at(e.get("de")), "a": at(e.get("a"), total), "texte": e["texte"], "couleur": e.get("couleur", "#E5383B"),
                        "etat": [{"t": at(x), "etat": etat} for x, etat in e.get("etat", [])]} for e in CFG.get("etiquettes", [])],
        "cartes": [{"t": at(c["t"]), "d": c.get("dur", 0.8), "texte": c["texte"], "fond": c.get("fond", "#2F6FED"),
                    "logo": c.get("logo", "")} for c in CFG.get("cartes", [])],
        "score": [{"t": at(s["t"]), "d": s.get("dur", 1.8), "avant": s.get("avant", [0, 0]), "point": s.get("point", ""),
                   "a": SCORE_POINT} for s in CFG.get("score", [])],
    }


def cadre_capture(s, t0):
    """Capture surgie : taille affichée (820 px de large au plus, 620 de haut) et zone surlignée en pixels affichés."""
    if not s.get("surligne"):
        return {}
    _, _, _, _, w, h = CFG["captures"][s["capture"]]
    k = min(820 / w, 620 / h)
    x, y, zw, zh = s["surligne"]
    return {"w": round(w * k), "h": round(h * k),
            "surligne": {"x": round(x * k), "y": round(y * k), "w": round(zw * k), "h": round(zh * k), "t": t0 + s["t"] + s.get("sa", 0.35)}}


def page(path, comp, data, calque=False):
    """Écrit la composition. calque=True : sans la vidéo ni le son, fond transparent (pièces pour CapCut)."""
    total = data["duration"]
    faces = (HF / "assets" / "fonts" / "fonts.css").read_text(encoding="utf-8").replace("../assets/fonts/", "assets/fonts/")
    rel = OUT.relative_to(HF).as_posix()
    media = "" if calque else f"""
      <div id="short-video-wrap">
        <video id="short-base" class="clip" src="{rel}/base.mp4" data-start="0" data-duration="{total}" data-track-index="0" muted playsinline></video>
      </div>
      <audio id="short-audio" src="{rel}/audio.wav" data-start="0" data-duration="{total}" data-track-index="10" data-volume="1"></audio>"""
    html = f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <!-- Short généré par scripts/short.py depuis {CFG_PATH.relative_to(HF).as_posix()} (ne pas éditer à la main) -->
    <script src="assets/vendor/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/tsar.css" />
    <style>
{faces}
      #root {{ width: 100%; height: 100%; background: {"transparent" if calque else "#000"}; }}
      #short-video-wrap {{ position: absolute; inset: 0; }}
      #short-video-wrap video {{ width: 100%; height: 100%; object-fit: cover; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{comp}" data-start="0" data-duration="{total}" data-fps="60" data-width="1080" data-height="1920">{media}
    </div>
    <script src="kit/tsar.js"></script>
    <script>TSAR.run("{comp}", "short_lh", {{ data: {json.dumps(data, ensure_ascii=False)} }});</script>
  </body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def render():
    final = ROOT / CFG["sortie"]
    final.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npx", "hyperframes", "render", ".", "-c", f"shorts/{COMP}.html", "-f", "60", "--crf", "16", "--quiet",
                    "-o", str(final)] + (["-w", "2"] if BELOW else []), cwd=HF, check=True, shell=True, creationflags=BELOW,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    got = probe(final)
    _, total = starts()
    if abs(got - total) > 0.1:
        raise SystemExit(f"ERREUR rendu {got:.2f} s ≠ {total:.2f} s")
    print("short :", final, f"({got:.2f} s)")


if __name__ == "__main__":
    step = next((a for a in sys.argv[2:] if not a.startswith("--")), "tout")
    if step in ("video", "voix", "mots", "audio", "html", "rendu", "tout"):
        snap_bounds()
    # ordre : les mots avant l'image (le découpage dynamique coupe sur des débuts de mots)
    for name, fn in (("captures", build_captures), ("voix", build_voice), ("mots", build_words), ("video", build_video),
                     ("audio", build_audio), ("html", build_html)):
        if step in (name, "tout"):
            fn()
    if step == "rendu":
        render()
