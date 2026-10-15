"""Contrôle du montage posé dans CapCut, à lancer AVANT d'ajouter la musique et AVANT l'export (demande du
2026-10-03 : « refaire une transcription pour vraiment s'assurer qu'il n'y a pas d'erreur »).

Refait la transcription de la timeline (whisper, carte graphique si présente) et la retranscrit aussi BLOC DE VOIX
PAR BLOC DE VOIX : d'un seul tenant, Whisper fusionne les répétitions (« ChatGPT… ChatGPT recevra » écrit une fois,
final 3 de pokemon-ia à 0:13). Les blocs sans voix (musique du jeu seule, VAD) ne sont pas transcrits. Puis liste :
  - redites : même mot (« ChatGPT… ChatGPT ») ou mêmes 2 mots redits à moins de 3 s ;
  - faux départ : début de phrase redit après une hésitation (« et en vrai, et en vrai, c'est… ») ;
  - pause sans parole de plus de PAUSE s (musique ou clics du jeu seuls, que silencedetect ne voit pas) ;
  - coupe dans la voix : le son de la voix continue des deux côtés d'une coupe (mot mangé), avec le creux le plus proche ;
  - mots étirés (> 0,9 s) : whisper fusionne parfois une redite en un seul mot → retranscrire le passage ;
  - blancs : silences de la voix plus longs que --blanc (0,5 s ; 0,7 avant le style WOLF du 2026-10-06) ;
  - écran noir : passage d'un rush « voix seule » (luminance < 25) sans plan ni scène posé au-dessus ;
  - phrase redite : mêmes REDITE mots redits à moins de FENETRE s (prise en double, ou formule répétée à varier) ;
    3 fois ou plus, c'est une boucle de Whisper (jeu seul) : ignorée ;
  - passage du dérush absent : clip de derush_<id>_court.json (nettoyé) introuvable dans la timeline ;
  - sous-titre décalé : phrase de video.json (sous_titres.phrases) qui n'est plus dite à ce moment-là ;
  - micro-clip : bout de clip de moins de MICRO s resté sur la timeline.
L'image (hors écran noir) n'est pas vérifiée : à l'écoute.
Rapport : 02_ANALYSE/controle_<projet>.txt. Chaque ligne est à corriger (dérush : nettoie_derush.py « retirer »,
image : plan.json) ou à justifier avant de continuer.

Usage : python scripts/controle.py <id> [--sans-transcription] [--blanc 0.5] [--pause 1.0] [--derush <fichier.json>]
  --sans-transcription : réutilise l'audio et les transcriptions déjà faites (timeline inchangée)
  --sans-images : pas d'image par coupe signalée (sinon 02_ANALYSE/controle_<projet>/coupe_<t>.png : 4 images de la
                  timeline autour de la coupe, forme d'onde ±1,5 s avec la coupe en rouge, mots dits)
  --export <fichier.mp4> : contrôle du son de l'export final à la place (volume, crête, passages très bas, fin trop
                  basse ; avec Demucs, fond sous la voix par tranche de 30 s) → 02_ANALYSE/controle_export_<id>.txt
"""
import difflib
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ANALYSE, HF, NOMBRES, draft, seuil_silence, video, voix  # noqa: E402
from nettoie_derush import blocs_voix, faux_departs  # noqa: E402
from takes_map import decouper  # noqa: E402
from verify_cuts import PAD, extract, quietest, transcribe_many, words_of  # noqa: E402

LEGIT = {"lets", "go", "bref", "super", "non", "oui", "ok", "ouais", "vraiment", "tres"}
REDITE = 6          # mots identiques d'affilée pour une phrase redite
FENETRE = 90.0      # la même phrase redite à moins de ça
MICRO = 0.25        # clip plus court que ça : bout oublié
DECALAGE = 1.5      # tolérance autour d'un sous-titre
COTE = 0.03         # son mesuré de chaque côté d'une coupe (s)
PROCHE = 0.08       # voix cherchée jusqu'à ça de chaque côté : une coupe dans la fermeture d'un « p » ou d'un « t »
                    # est silencieuse sur 30 ms, mais pas sur 80 ms (« descri|ption », pokemon-ia 0:12)


def mots_par_blocs(wav: Path, parle) -> list[tuple[str, float, float]]:
    """Mots (normalisés, début, fin) de la timeline, chaque bloc de voix transcrit seul."""
    duree = wave.open(str(wav)).getnframes() / 16000
    blocs = [x for a, b in blocs_voix(wav, 0.0, duree)
             if parle is None or any(s < b and e > a for s, e in parle) for x in decouper(a, b, parle)]
    out = []
    with tempfile.TemporaryDirectory() as t:
        parts = [Path(t) / f"b{k:04d}.wav" for k in range(len(blocs))]
        for (a, b), part in zip(blocs, parts):
            extract(wav, a, b, part)
        print(f"{len(blocs)} blocs de voix", flush=True)
        for (a, b), mots in zip(blocs, transcribe_many(parts)):  # modèle chargé une fois par lot
            out += [(NOMBRES.get(w, w), s - PAD + a, e - PAD + a) for w, s, e in mots]
    return out


def pauses(parle, mini) -> list[tuple[float, float]]:
    """Écarts de plus de `mini` s entre deux passages de voix (VAD)."""
    return [(e, s) for (_, e), (s, _) in zip(parle, parle[1:]) if s - e > mini]


def niveaux(wav: Path):
    """Fonction (t0, t1) -> niveau RMS en dB de la timeline entre t0 et t1 (wav 16 bits mono)."""
    import array
    import math
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = array.array("h", w.readframes(w.getnframes()))
    if sys.byteorder == "big":
        x.byteswap()

    def db(t0, t1):
        seg = x[max(0, int(t0 * sr)):max(0, int(t1 * sr))]
        rms = math.sqrt(sum(v * v for v in seg) / len(seg)) / 32768 if len(seg) else 0
        return 20 * math.log10(max(rms, 1e-6))
    return db


def coupes_dans_la_voix(coupes, db, seuil, parle) -> list[tuple[float, float, float]]:
    """(temps, dB avant, dB après) des coupes où la voix sonne des deux côtés, au milieu d'un passage parlé ; ou des
    coupes où la voix est encore forte juste avant (seuil + 4 dB dans les 30 dernières ms : une coupe propre finit dans
    un silence) et reprend dans les 0,15 s, même après un trou de silence numérique (« description » coupé à 12,07 s
    de pokemon-ia : 60 ms à zéro après la coupe, que la première règle ne voyait pas ; vérifié le 2026-10-06 sur les
    164 coupes du montage : 13 signalées, dont 4 par cette règle)."""
    out = []
    for t in coupes:
        pas = [k * COTE for k in range(round(PROCHE / COTE))]
        avant = max(db(t - x - COTE, t - x) for x in pas)
        apres = max(db(t + x, t + x + COTE) for x in pas)
        dedans = parle is None or any(s < t - COTE and e > t + COTE for s, e in parle)
        fin = db(t - COTE, t)
        reprise = max(db(t + x, t + x + COTE) for x in [k * COTE for k in range(5)])
        if dedans and ((avant > seuil and apres > seuil) or (fin > seuil + 4 and reprise > seuil)):
            out.append((t, avant, apres))
    return out


def redites_longues(mots, n=REDITE, fenetre=FENETRE) -> list[tuple[float, float, str]]:
    """(temps 1re fois, temps 2e fois, phrase) ; mots = [(mot, début, fin), …]."""
    vus: dict[tuple, list[int]] = {}
    for i in range(len(mots) - n + 1):
        vus.setdefault(tuple(w for w, _, _ in mots[i:i + n]), []).append(i)
    boucle = set()   # dit 3 fois ou plus de suite : boucle de Whisper, pas une redite de montage
    for pos in vus.values():
        for k in range(2, len(pos)):
            if mots[pos[k]][1] - mots[pos[k - 2]][1] <= fenetre:
                boucle.update(range(pos[k - 2], pos[k] + n))
    paires = []
    for pos in vus.values():
        for k in range(1, len(pos)):
            i, j = pos[k - 1], pos[k]
            if j - i >= n and mots[j][1] - mots[i][1] <= fenetre and i not in boucle and j not in boucle:
                paires.append((i, j))
    out, fin = [], None   # les n-grammes qui se chevauchent d'une même redite n'en font qu'une
    for i, j in sorted(paires):
        if fin and i - fin[0] == j - fin[1] and i <= fin[2]:
            fin = (i, j, i + n)
            out[-1][1] = j + n
            continue
        fin = (i, j, i + n)
        out.append([i, j + n, j])
    return [(mots[i][1], mots[j][1], " ".join(w for w, _, _ in mots[j:fin_j]))
            for i, fin_j, j in out]


def absents(clips, mots, seuil=0.5) -> list[tuple[str, str]]:
    """Clips du dérush [(titre, texte voulu), …] dont moins de `seuil` des mots (et moins de 3) se retrouvent,
    dans l'ordre, dans la timeline."""
    ref, qui = [], []
    for k, (_, texte) in enumerate(clips):
        for w in words_of(texte):
            ref.append(w)
            qui.append(k)
    entendu = [w for w, _, _ in mots]
    trouve = [0] * len(clips)
    for a, _, size in difflib.SequenceMatcher(None, ref, entendu, autojunk=False).get_matching_blocks():
        for x in range(a, a + size):
            trouve[qui[x]] += 1
    out = []
    for k, (titre, texte) in enumerate(clips):
        total = len(words_of(texte))
        if total and trouve[k] / total < seuil and trouve[k] < 3:   # Whisper entend parfois autrement un clip court
            out.append((titre, texte))
    return out


def sous_titres_faux(phrases, mots, seuil=0.6, marge=DECALAGE) -> list[tuple[float, str, str]]:
    """(temps, sous-titre, ce qui est dit autour) pour chaque phrase affichée qui n'est pas dite à ce moment-là."""
    out = []
    for t, texte in phrases:
        voulu = words_of(texte)
        if not voulu:
            continue
        fin = t + len(voulu) * 0.5 + marge
        autour = [w for w, s, _ in mots if t - marge <= s <= fin]
        commun = sum(b.size for b in difflib.SequenceMatcher(None, voulu, autour, autojunk=False).get_matching_blocks())
        if commun / len(voulu) < seuil:
            out.append((t, texte, " ".join(autour) or "(rien)"))
    return out


def micro_clips(segments, mini=MICRO) -> list[tuple[float, float, str]]:
    """(début, durée, source) des clips de la timeline plus courts que `mini` s."""
    return [(a, d, src) for a, d, src in segments if d < mini and src != "(clip combiné)"]


def derush_de(vid: str):
    """Le dérush nettoyé de la vidéo (pas la copie « .avant-nettoyage »)."""
    if "--derush" in sys.argv:
        return Path(sys.argv[sys.argv.index("--derush") + 1])
    cands = [p for p in ANALYSE.glob(f"derush_{vid}*.json") if "." not in p.stem]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def opt(name, default):
    return float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def sonie(path: Path):
    """Volume intégré, crête vraie et volume court terme (fenêtres de 3 s, toutes les 0,1 s) d'un fichier (EBU R128)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true:metadata=1,"
                          "ametadata=print:key=lavfi.r128.S", "-f", "null", "-"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    resume = err[err.rfind("Summary"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resume).group(1))
    pic = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", resume).group(1))
    temps = [float(x) for x in re.findall(r"pts_time:([\d.]+)", err)]
    s = [float(x) for x in re.findall(r"lavfi\.r128\.S=(-?[\d.]+|-inf)", err.replace("-inf", "-120"))]
    return i, pic, list(zip(temps, s))


def controle_export(vid: str, mp4: Path):
    """Son de l'export final (chantier du 2026-10-04, inspiré de browser-use/video-use) : volume et crête, passages
    beaucoup plus bas que le reste, fin trop basse ; avec Demucs (mesure_montage.py), fond sous la voix par tranche de
    30 s, et le dosage comparé à WOLF (mêmes mesures que pour lui)."""
    lignes = []
    i, pic, court = sonie(mp4)
    lignes.append(f"   total  volume {i:.1f} LUFS, crête {pic:.1f} dBFS (viser −14 LUFS entre −13 et −15, crête ≤ −1)")
    if not -15 <= i <= -13:
        lignes.append(f"   total  volume hors cible : {i:.1f} LUFS")
    if pic > -1:
        lignes.append(f"   total  crête trop haute : {pic:.1f} dBFS")
    duree = court[-1][0] if court else 0
    for t0 in range(0, int(duree), 10):
        vals = [s for t, s in court if t0 <= t < t0 + 10 and s > -70]
        if vals and max(vals) < i - 10:
            fin = " (fin de la vidéo)" if t0 + 10 >= duree - 15 else ""
            lignes.append(f"{t0:8.2f}  passage très bas : {max(vals):.0f} LUFS au plus pendant 10 s, {i - max(vals):.0f} dB sous le reste{fin}")
    try:
        import demucs  # noqa: F401
    except ImportError:
        lignes.append("   (Demucs absent : fond et voix non séparés, voir INSTALLATION_CLAUDE.md)")
        return lignes
    import mesure_montage as mm
    voix, fond = mm.separer(mp4)
    for n in range(0, len(voix), 600):                     # fond sous la voix, par tranche de 30 s
        pv = [(v, f) for v, f in zip(voix[n:n + 600], fond[n:n + 600]) if v > -40]
        if len(pv) < 60:
            continue
        ecart = sorted(v for v, _ in pv)[len(pv) // 2] - sorted(f for _, f in pv)[len(pv) // 2]
        if ecart > 20:
            lignes.append(f"{n * mm.W:8.2f}  fond presque inaudible : {ecart:.0f} dB sous la voix sur 30 s (WOLF : ~9)")
        elif ecart < 4:
            lignes.append(f"{n * mm.W:8.2f}  fond qui couvre la voix : {ecart:.0f} dB sous la voix sur 30 s")
    r = mm.mesures(voix, fond, mm.changements_image(mp4))
    r.update(mm.mouvements(mp4))
    lignes.insert(1, f"   total  fond sous la voix : {r['fond_sous_voix_db']} dB en médiane (cible 12 à 15 ; pokemon-ia : 22,7)")
    lignes += ["", "Dosage comparé aux cibles de la direction de montage (2026-10-07 ; ±30 % sur les changements d'image"
               " et du fond) :", f"{'':32s}{'export':>8s}   cible         pokemon-ia"]
    hors = []
    for nom, cle, lo, hi, poke in (
            ("changements d'image / min", "images_min", 10, 15, "8,1"),
            ("plan médian (s)", "plan_median_s", 2.0, 5.0, "3,5"),
            ("image immobile (%)", "image_fixe_pct", 0, 35, "66"),
            ("zooms / min", "zooms_min", 5, 7, "2,1"),
            ("voix présente (%)", "voix_pct", 90, 100, "83"),
            ("pauses de voix > 0,3 s / min", "pauses_min", 0, 3, "14,1"),
            ("fond sous la voix (dB)", "fond_sous_voix_db", 12, 15, "22,6"),
            ("grands changements du fond / min", "grands_changements_fond_min", 3, 6, "2,8"),
            ("coupures du fond ≥ 1 s / min", "coupures_fond_min", 0.3, 0.7, "0,7"),
            ("pics courts dans le fond / min", "pics_fond_min", 12, 18, "19")):
        v = r.get(cle)
        loin = v is not None and not lo <= v <= hi
        hors += [nom] if loin else []
        lignes.append(f"   {nom:32s}{(v if v is not None else float('nan')):8.1f}   {lo:g} à {hi:g}{'' if not loin else ' ←':4s}"
                      f"     {poke}")
    if hors:
        lignes.append(f"   à corriger ou à justifier : {', '.join(hors)}")
    return lignes


def images_coupes(projet: str, wav: Path, mots, points, dossier: Path):
    """Une image par coupe signalée : 4 images de la timeline autour de la coupe, forme d'onde de ±1,5 s avec la coupe
    en rouge et les mots dits, pour juger une coupe douteuse sans réécouter (chantier du 2026-10-04)."""
    dossier.mkdir(parents=True, exist_ok=True)
    for old in dossier.glob("coupe_*.png"):
        old.unlink()
    faits = []
    for t in points:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            images = subprocess.run([sys.executable, str(HF / "scripts" / "timeline_frames.py"), projet, str(tmp / "img.png"),
                                     *(f"{t + d:.2f}" for d in (-0.5, -0.1, 0.1, 0.5))], capture_output=True).returncode == 0
            if not images:  # rush déplacé ou supprimé : la forme d'onde et les mots suffisent à juger
                subprocess.run(["magick", "-size", "1300x60", "xc:#111", "-fill", "#F5B942", "-pointsize", "26", "-gravity",
                                "center", "-annotate", "+0+0", "images de la timeline indisponibles (rush introuvable)",
                                str(tmp / "img.png")], check=True)
            a = max(0.0, t - 1.5)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", "3", "-i", str(wav), "-filter_complex",
                            "showwavespic=s=1300x220:colors=#3CCFB0", "-frames:v", "1", str(tmp / "onde.png")], check=True)
            dits = " ".join(w for w, x, _ in mots if a <= x <= a + 3)
            x_coupe = int((t - a) / 3 * 1300)
            subprocess.run(["magick", str(tmp / "onde.png"), "-background", "#111", "-flatten", "-fill", "#E5383B",
                            "-draw", f"rectangle {x_coupe - 2},0 {x_coupe + 2},220", "-gravity", "south", "-splice", "0x60",
                            "-fill", "white", "-pointsize", "26", "-annotate", "+0+12", dits[:110] or "(aucun mot)",
                            str(tmp / "onde2.png")], check=True)
            out = dossier / f"coupe_{t:08.2f}.png"
            subprocess.run(["magick", str(tmp / "img.png"), str(tmp / "onde2.png"), "-background", "#111", "-gravity", "center",
                            "-append", str(out)], check=True)
            faits.append(out)
    return faits


def main(vid):
    cfg = video(vid)
    if "--export" in sys.argv:
        mp4 = Path(sys.argv[sys.argv.index("--export") + 1])
        lignes = controle_export(vid, mp4)
        out = ANALYSE / f"controle_export_{vid}.txt"
        out.write_text(f"Son de l'export « {mp4.name} », heures en secondes de la vidéo\n" + "\n".join(lignes) + "\n",
                       encoding="utf-8")
        print(out.read_text(encoding="utf-8"))
        return
    projet = cfg["projet"]
    if "--sans-transcription" not in sys.argv:
        subprocess.run([sys.executable, str(HF / "scripts" / "capcut_timeline_audio.py"), projet], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["node", "scripts/transcribe.ts", f"capcut_{projet}.wav"], cwd=HF, check=True, shell=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(HF / "scripts" / "timeline_overview.py"), projet], check=True, stdout=subprocess.DEVNULL)
    wav = ANALYSE / "audio_16k" / f"capcut_{projet}.wav"
    parle = voix(wav)
    cache = ANALYSE / "transcriptions" / f"capcut_{projet}.blocs.json"
    if "--sans-transcription" in sys.argv and cache.exists():
        mots = [tuple(m) for m in json.loads(cache.read_text(encoding="utf-8"))]
    else:
        mots = mots_par_blocs(wav, parle)
        cache.write_text(json.dumps([[w, round(a, 2), round(b, 2)] for w, a, b in mots]), encoding="utf-8")
    toks = [(w, a, b, w) for w, a, b in mots]
    lignes = []

    # redites (sur la transcription par blocs : les répétitions n'y sont pas fusionnées)
    for i in range(1, len(toks)):
        w, t, _, txt = toks[i]
        p = toks[i - 1]
        if w == p[0] and len(w) > 3 and w not in LEGIT and t - p[1] < 3:
            lignes.append(f"{t:8.2f}  redite d'un mot : « {p[3]} … {txt} »")
        if i >= 3 and (toks[i - 1][0], w) == (toks[i - 3][0], toks[i - 2][0]) and t - toks[i - 3][1] < 3 \
                and not {w, toks[i - 1][0]} <= LEGIT:
            lignes.append(f"{toks[i - 3][1]:8.2f}  redite : « {toks[i - 3][3]} {toks[i - 2][3]} » redit")
    lignes += [f"{a:8.2f}  faux départ « {txt} » puis reprise à {b:.2f} : retirer [{a:.2f}, {b:.2f}["
               for a, b, txt in faux_departs(mots) if len(txt.split()) > 2]   # 2 mots : déjà dans « redite »
    # mots étirés
    lignes += [f"{t:8.2f}  mot étiré « {txt} » ({e - t:.1f} s) : redite fusionnée possible" for w, t, e, txt in toks
               if e - t > 0.9 and len(w) > 1]
    # blancs (voix seule de la timeline) et pauses sans parole (musique ou clics du jeu seuls)
    pz = pauses(parle, opt("--pause", 1.0)) if parle else []
    lignes += [f"{a:8.2f}  pause sans parole de {b - a:.1f} s (jusqu'à {b:.2f}) : musique ou son du jeu seul, à raccourcir"
               for a, b in pz]
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                          f"silencedetect=n=-40dB:d={opt('--blanc', 0.5)}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    lignes += [f"{a:8.2f}  blanc de {b - a:.1f} s (jusqu'à {b:.2f})" for a, b in zip(st, en)
               if not any(x <= a and b <= y + 0.3 for x, y in pz)]   # déjà dans une pause
    # écran noir non couvert
    lum_f = ANALYSE / "luminance_rushs.json"
    lum = json.loads(lum_f.read_text(encoding="utf-8")) if lum_f.exists() else {}
    d = draft(projet)
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    dessus = sorted((s["target_timerange"]["start"] / 1e6, (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6)
                    for t in d["tracks"] if t["type"] == "video" and t is not main for s in t["segments"]
                    if not vids.get(s["material_id"], {}).get("path", "").lower().endswith(".mov"))  # MOV = calques transparents
    for s in main["segments"]:
        if lum.get(vids[s["material_id"]].get("path", ""), 99) >= 25:
            continue
        a = s["target_timerange"]["start"] / 1e6
        b = a + s["target_timerange"]["duration"] / 1e6
        cur = a
        for x, y in dessus:
            if y <= cur or x >= b:
                continue
            if x - cur > 0.3:
                lignes.append(f"{cur:8.2f}  écran noir {x - cur:.1f} s (rien au-dessus jusqu'à {x:.2f})")
            cur = max(cur, y)
        if b - cur > 0.3:
            lignes.append(f"{cur:8.2f}  écran noir {b - cur:.1f} s (rien au-dessus jusqu'à {b:.2f})")

    # coupes dans la voix (mot mangé) : son de la voix des deux côtés de la coupe
    bords = [(s["target_timerange"]["start"] / 1e6, (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6,
              bool(vids[s["material_id"]].get("path"))) for s in main["segments"]]
    coupes = [b1 for (_, b1, ok1), (a2, _, ok2) in zip(bords, bords[1:]) if ok1 and ok2 and abs(a2 - b1) < 0.02]
    douteuses = coupes_dans_la_voix(coupes, niveaux(wav), seuil_silence(wav) + 6, parle)
    images = ANALYSE / f"controle_{projet}"
    for t, av, ap in douteuses:
        lignes.append(f"{t:8.2f}  coupe dans la voix ({av:.0f} dB avant, {ap:.0f} dB après) : mot mangé ? "
                      f"creux le plus proche à {quietest(wav, t - 0.3, t + 0.3):.2f} ; image : {images.name}/coupe_{t:08.2f}.png")
    if douteuses and "--sans-images" not in sys.argv:
        images_coupes(projet, wav, mots, [t for t, _, _ in douteuses], images)

    # phrases redites, sous-titres décalés, micro-clips (transcription par blocs)
    lignes += [f"{b:8.2f}  phrase redite (déjà dite à {a:.2f}) : « {p} »" for a, b, p in redites_longues(mots)]
    lignes += [f"{t:8.2f}  sous-titre décalé : prévu « {txt} », entendu « {ent} »"
               for t, txt, ent in sous_titres_faux((cfg.get("sous_titres") or {}).get("phrases", []), mots)]
    segs = [(s["target_timerange"]["start"] / 1e6, s["target_timerange"]["duration"] / 1e6,
             Path(vids[s["material_id"]].get("path", "")).name or "(clip combiné)") for s in main["segments"]]
    lignes += [f"{a:8.2f}  micro-clip de {d:.2f} s ({src}) : bout oublié ?" for a, d, src in micro_clips(segs)]

    lignes.sort(key=lambda l: float(l.split()[0]))
    # passages du dérush absents (sans temps : ils ne sont plus sur la timeline)
    fd = derush_de(vid)
    if fd:
        dr = json.loads(fd.read_text(encoding="utf-8-sig"))
        clips = [(g.get("titre", ""), c[3]) for g in dr.get("groupes", []) for c in g.get("clips", []) if len(c) > 3]
        lignes += [f"  absent  passage du dérush ({g}) : « {txt} »" for g, txt in absents(clips, mots)]
    out = ANALYSE / f"controle_{projet}.txt"
    out.write_text(f"Contrôle de « {projet} » ({len(lignes)} point(s)), heures en secondes de timeline\n"
                   + "\n".join(lignes) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main(sys.argv[1])
