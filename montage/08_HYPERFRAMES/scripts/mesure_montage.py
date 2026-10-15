"""Mesure le montage d'une vidéo finie (la nôtre ou celle d'une autre chaîne), comme pour WOLF le 2026-10-05.

    python scripts/mesure_montage.py <video.mp4> [--json sortie.json] [--planches <dossier>] [--sous-titres f.json3]
                                     [--mouvements]   (zooms rapides et lents, image fixe ou qui bouge : voir mouvements())

Mesures (config/youtube/references/wolf/style.md § Son et coupes ; recalées sur pokemon-ia le 2026-10-07) :
  - image : changements de plan (scène ≥ 0,3, regroupés à 0,4 s) par minute, durée médiane d'un plan, par minute ;
  - son, après séparation voix / fond par Demucs (carte graphique) : voix présente (%), pauses de voix de 0,3 à 3 s par
    minute, fond sous la voix (dB, médiane par tranche de 30 s), grands changements du fond (plus de 8 dB en 3 s),
    coupures du fond d'au moins 1 s (15 dB sous sa médiane), pics courts dans le fond (bruitages ou jeu) ;
  - volume intégré et crête (EBU R128) ;
  - avec --sous-titres (json3 de yt-dlp, sous-titres automatiques) : débit en mots par minute et texte des 30 premières s ;
  - avec --planches : deux planches d'images, l'accroche (0 à 20 s, 2 images par seconde) et toute la vidéo (une image
    toutes les 15 s), pour juger les éléments à l'écran (étiquettes, cartes, sous-titres, zooms, facecam…).
Utilisé par `controle.py --export` (nos exports) et pour mesurer des chaînes de référence (« mesure le montage de
<chaîne> comme pour WOLF »). Les vidéos téléchargées restent hors du dépôt.
"""
import json, math, re, subprocess, sys, tempfile
from pathlib import Path

W = 0.05  # fenêtres de 50 ms


def niveaux(wav: Path) -> list:
    """Niveau (dB) de chaque fenêtre de 50 ms d'un WAV (numpy et soundfile : toujours là avec Demucs)."""
    import numpy as np
    import soundfile as sf
    x, rate = sf.read(str(wav), dtype="float32", always_2d=True)
    k = int(rate * W)
    x = x[: len(x) // k * k].mean(axis=1).reshape(-1, k)
    return (20 * np.log10(np.maximum(np.sqrt((x ** 2).mean(axis=1)), 1e-6))).tolist()


def separer(video: Path):
    """(voix, fond) : niveaux par fenêtre de 50 ms après Demucs (htdemucs, deux pistes)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        wav = tmp / "son.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100", str(wav)], check=True)
        subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", str(tmp), str(wav)],
                       check=True, capture_output=True)
        sep = tmp / "htdemucs" / "son"
        return niveaux(sep / "vocals.wav"), niveaux(sep / "no_vocals.wav")


def changements_image(video: Path) -> list:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-an", "-vf",
                          "scale=320:-1,select='gt(scene,0.3)',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    out = []
    for t in sorted(float(x) for x in re.findall(r"pts_time:([\d.]+)", err)):
        if not out or t - out[-1] > 0.4:
            out.append(t)
    return out


def sonie(video: Path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    r = err[err.rfind("Summary"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", r).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", r).group(1))


def mesures(voix: list, fond: list, images: list) -> dict:
    duree = len(voix) * W
    minutes = max(duree / 60, 1e-6)
    parle = [x > -40 for x in voix]
    pauses, k = [], 0
    while k < len(parle):                                  # silences de la voix entre deux passages parlés
        if not parle[k]:
            j = k
            while j < len(parle) and not parle[j]:
                j += 1
            if 0 < k and j < len(parle) and 0.3 <= (j - k) * W < 3.0:
                pauses.append(k * W)
            k = j
        else:
            k += 1
    # fond sur 3 s (en énergie), toutes les secondes, comparé à 3 s plus tard (recalé sur pokemon-ia le 2026-10-07)
    niv = [10 * math.log10(max(1e-12, sum(10 ** (x / 10) for x in fond[i:i + 60]) / 60)) for i in range(0, len(fond) - 60, 20)]
    grands, dernier = [], -9
    for k in range(len(niv) - 3):
        if abs(niv[k + 3] - niv[k]) > 8 and k - dernier >= 3:
            grands.append(k); dernier = k
    med = sorted(fond)[len(fond) // 2]
    coupures, k = [], 0
    while k < len(fond):
        if fond[k] < med - 15:
            j = k
            while j < len(fond) and fond[j] < med - 15:
                j += 1
            if (j - k) * W >= 1.0:
                coupures.append(k * W)
            k = j
        else:
            k += 1
    pics, dernier = [], -9.0
    for i in range(1, len(fond)):
        loc = sorted(fond[max(0, i - 20):i + 20])
        local = loc[len(loc) // 2]
        if fond[i] > local + 10 and fond[i - 1] <= local + 10 and i * W - dernier >= 0.25:
            pics.append(i * W); dernier = i * W
    ecarts = []
    for a in range(0, len(voix), 600):                     # fond sous la voix, par tranche de 30 s
        pv = [(v, f) for v, f in zip(voix[a:a + 600], fond[a:a + 600]) if v > -40]
        if len(pv) >= 60:
            ecarts.append(sorted(v for v, _ in pv)[len(pv) // 2] - sorted(f for _, f in pv)[len(pv) // 2])
    plans = [b - a for a, b in zip([0.0] + images, images + [duree]) if b > a]
    par_minute = [sum(1 for t in images if m * 60 <= t < (m + 1) * 60) for m in range(int(duree // 60))]
    return {"duree_s": round(duree, 1), "images_min": round(len(images) / minutes, 1),
            "plan_median_s": round(sorted(plans)[len(plans) // 2], 2) if plans else None,
            "images_par_minute": par_minute,
            "voix_pct": round(100 * sum(parle) / max(1, len(parle)), 1), "pauses_min": round(len(pauses) / minutes, 1),
            "fond_sous_voix_db": round(sorted(ecarts)[len(ecarts) // 2], 1) if ecarts else None,
            "grands_changements_fond_min": round(len(grands) / minutes, 1), "coupures_fond_min": round(len(coupures) / minutes, 1),
            "pics_fond_min": round(len(pics) / minutes, 1)}


def mouvements(video: Path, fps: int = 10, duree_max: float = None) -> dict:
    """Zooms et déplacements de l'image (demande du 2026-10-07) : entre deux images (10 par seconde, 320×180), la
    transformation la plus simple qui fait passer de l'une à l'autre (échelle + déplacement, OpenCV ORB + RANSAC).
    Un zoom = une suite d'images où le cadre grossit (ou rétrécit) dans le même sens, d'au moins 4 % en tout (vitesse
    mesurée sur une fenêtre d'une seconde) ; rapide s'il dure 0,5 s au plus, lent s'il dure 2 s ou plus. Le déplacement de l'image ne distingue pas un panoramique de
    montage d'un mouvement de souris dans le jeu : il est donné ensemble (« image qui bouge »). Un grand élément animé
    qui grossit en apparaissant compte aussi comme un zoom (c'est ce qu'on voit). Les coupes (aucune correspondance entre
    deux images) sont ignorées. Vérifié le 2026-10-07 : vidéo fabriquée (zoom rapide 1,3 et lent 1,08 sur 5 s, trouvés
    exactement) ; pokemon-ia (zooms rapides de 1,25 à 1,35 retrouvés à 116, 127 et 365 s, zooms lents de 1,06).
    Marge : un zoom sur une image trop uniforme peut manquer."""
    import cv2
    import numpy as np
    W_, H_ = 320, 180
    cmd = ["ffmpeg", "-v", "error", "-i", str(video)] + (["-t", str(duree_max)] if duree_max else []) + \
          ["-vf", f"fps={fps},scale={W_}:{H_},format=gray", "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    orb = cv2.ORB_create(nfeatures=500, fastThreshold=12)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    def transfo(pr, cur):
        """(log échelle, déplacement px, fiable ?) de l'image pr à l'image cur, ou None (coupe, image vide)."""
        (pkp, pdes), (kp, des) = pr, cur
        if des is None or pdes is None or len(kp) < 12 or len(pkp) < 12:
            return None
        m = bf.match(pdes, des)
        if len(m) < 12:
            return None
        a = np.float32([pkp[x.queryIdx].pt for x in m]); b = np.float32([kp[x.trainIdx].pt for x in m])
        M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=1.5)
        if M is None or inl is None or inl.sum() < 10:
            return None
        s = math.hypot(M[0, 0], M[1, 0])
        return math.log(s), math.hypot(M[0, 2] + (s - 1) * W_ / 2, M[1, 2] + (s - 1) * H_ / 2), inl.sum() / len(m) >= 0.6
    pas, prev, seconde, hist = [], None, [], []            # pas : d'une image à la suivante ; seconde : à 1 s d'écart
    while True:
        buf = p.stdout.read(W_ * H_)
        if len(buf) < W_ * H_:
            break
        img = np.frombuffer(buf, np.uint8).reshape(H_, W_)
        cur = orb.detectAndCompute(img, None)
        if prev is not None:
            pas.append(transfo(prev, cur))
        hist.append(cur)
        if len(hist) > fps:                                # toutes les 0,5 s : transformation depuis l'image d'il y a 1 s
            old = hist.pop(0)
            if len(pas) % (fps // 2) == 0:
                coupe = any(x is None for x in pas[-fps:])
                seconde.append((len(pas) - fps, None if coupe else transfo(old, cur)))
        prev = cur
    p.stdout.close()
    p.wait()
    dt = 1 / fps
    duree = (len(pas) + 1) * dt
    # zoom = suite d'images où le cadre grossit (ou rétrécit) d'au moins 0,8 % par seconde, mesuré sur une fenêtre d'une
    # seconde (un zoom lent de 1,06 sur 5 s ne bouge que de 0,1 % d'une image à l'autre)
    v = [r[0] if r and r[2] else 0.0 for r in pas]
    n = fps
    fen = [sum(v[max(0, i - n // 2):i + n // 2]) * fps / max(1, len(v[max(0, i - n // 2):i + n // 2])) for i in range(len(v))]
    zooms, k = [], 0
    while k < len(v):
        if abs(fen[k]) >= 0.008 and pas[k] is not None:
            sens, j = fen[k] > 0, k
            while j < len(v) and abs(fen[j]) >= 0.008 and (fen[j] > 0) == sens and pas[j] is not None:
                j += 1
            tot = sum(v[k:j])
            actifs = sum(1 for x in v[k:j] if abs(x) > 0.001 and (x > 0) == sens)
            if abs(tot) >= math.log(1.04) and actifs * dt <= 1.5:
                zooms.append({"t": round(k * dt, 1), "duree": round(max(1, actifs) * dt, 1),
                              "facteur": round(math.exp(abs(tot)), 2), "sens": "avant" if sens else "arrière"})
            k = j
        else:
            k += 1
    # un zoom adouci (lent au début et à la fin) peut sortir en deux morceaux : même sens à moins de 0,6 s → un seul
    fus = []
    for z in zooms:
        if fus and z["sens"] == fus[-1]["sens"] and z["t"] - (fus[-1]["t"] + fus[-1]["duree"]) <= 0.6:
            f = fus[-1]
            f["duree"] = round(z["t"] + z["duree"] - f["t"], 1); f["facteur"] = round(f["facteur"] * z["facteur"], 2)
        else:
            fus.append(dict(z))
    zooms = fus
    # zooms lents : à 1 s d'écart, le cadre grossit (ou rétrécit) d'au moins 0,8 % dans le même sens pendant 2 s ou plus
    # (image par image, un zoom de 1,06 sur 5 s est sous la précision de la mesure)
    k = 0
    while k < len(seconde):
        i0, r = seconde[k]
        if r and r[2] and abs(r[0]) >= 0.008:
            sens, j = r[0] > 0, k
            while j < len(seconde) and seconde[j][1] and seconde[j][1][2] and abs(seconde[j][1][0]) >= 0.008                     and (seconde[j][1][0] > 0) == sens:
                j += 1
            span = (seconde[j - 1][0] - i0) * dt + 1.0
            tot = sum(x[1][0] for x in seconde[k:j]) / 2     # mesures à 1 s d'écart, prises toutes les 0,5 s
            debut = i0 * dt
            rapide = any(debut - 1.0 <= z["t"] <= debut + span for z in zooms)   # déjà compté comme zoom rapide
            if span >= 2.0 and abs(tot) >= math.log(1.04) and not rapide:
                zooms.append({"t": round(debut, 1), "duree": round(span, 1), "facteur": round(math.exp(abs(tot)), 2),
                              "sens": "avant" if sens else "arrière"})
            k = j
        else:
            k += 1
    zooms.sort(key=lambda z: z["t"])
    valides = [r for r in pas if r]
    fixe = sum(1 for r in valides if abs(r[0]) < 0.001 and r[1] < 0.3)
    bouge = sum(1 for r in valides if r[1] >= 1.0 or abs(r[0]) >= 0.002)
    minutes = max(duree / 60, 1e-6)
    rapides = [z for z in zooms if z["duree"] <= 0.5]
    lents = [z for z in zooms if z["duree"] >= 2.0]
    return {"zooms_min": round(len(zooms) / minutes, 1), "zooms_rapides_min": round(len(rapides) / minutes, 1),
            "zooms_lents_min": round(len(lents) / minutes, 1),
            "zoom_facteur_median": sorted(z["facteur"] for z in zooms)[len(zooms) // 2] if zooms else None,
            "zoom_facteur_max": max((z["facteur"] for z in zooms), default=None),
            "image_fixe_pct": round(100 * fixe / max(1, len(valides)), 1),
            "image_qui_bouge_pct": round(100 * bouge / max(1, len(valides)), 1), "zooms": zooms}


def debit(json3: Path) -> dict:
    """Mots par minute et texte des 30 premières secondes, d'après les sous-titres automatiques (json3)."""
    d = json.loads(json3.read_text(encoding="utf-8"))
    mots = [(e["tStartMs"] + s.get("tOffsetMs", 0), s["utf8"].strip()) for e in d.get("events", []) for s in e.get("segs", []) or []
            if s.get("utf8", "").strip() and not s["utf8"].strip().startswith("[")]
    if not mots:
        return {}
    duree = (mots[-1][0] - mots[0][0]) / 60000
    return {"mots_min": round(len(mots) / max(duree, 1e-6)), "debut_30s": " ".join(w for t, w in mots if t < 30000)}


def planches(video: Path, dossier: Path, duree: float):
    dossier.mkdir(parents=True, exist_ok=True)
    nom = video.stem
    for suffixe, filtre, tuile, debut, fin in (("accroche", "fps=2", "8x5", 0, 20), ("ensemble", "fps=1/15", "8x8", 0, min(duree, 960))):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(debut), "-t", str(fin - debut), "-i", str(video), "-vf",
                        f"{filtre},scale=320:-1,drawtext=fontfile='C\\:/Windows/Fonts/arialbd.ttf':text='%{{pts\\:hms}}':"
                        f"x=6:y=6:fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6,tile={tuile}", "-frames:v", "1",
                        str(dossier / f"{nom}_{suffixe}.jpg")], check=True)


def main():
    a = sys.argv[1:]
    val = lambda n: a[a.index(n) + 1] if n in a else None  # noqa: E731
    video = Path(a[0])
    images = changements_image(video)
    voix, fond = separer(video)
    r = mesures(voix, fond, images)
    r["lufs"], r["crete_dbfs"] = sonie(video)
    if val("--sous-titres") and Path(val("--sous-titres")).exists():
        r.update(debit(Path(val("--sous-titres"))))
    if "--mouvements" in a:
        r.update({k: v for k, v in mouvements(video).items()})
    if val("--planches"):
        planches(video, Path(val("--planches")), r["duree_s"])
    if val("--json"):
        Path(val("--json")).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k not in ("images_par_minute", "debut_30s", "zooms")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
