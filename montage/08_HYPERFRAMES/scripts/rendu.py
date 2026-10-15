"""Rendu direct de la vidéo finale, sans CapCut.        python scripts/rendu.py <id> [--de S --a S] [--leger] [--refaire]

Adopté le 2026-10-08 : CapCut ne sert plus qu'au dérush ; le montage lit la timeline dérushée (projet « <id> - final »,
piste principale seulement, jamais ouvert ni modifié ici) et sort le MP4 1080p 60 i/s prêt à publier :
  06_CAPCUT/<id>/<id> - final.mp4   (ou « <id> - extrait <de>-<a>.mp4 » avec --de / --a)
Entrées, toutes produites par la chaîne habituelle : voix.py (voix_timeline.wav), export_capcut.py (plan_capcut.json :
plans de jeu, scènes, éléments, glissements), combler.py (plan_comblement.json), zooms.py (zooms.json), audio.py
(plan_final.json : volumes de la voix, des musiques, des bruitages arbitrés).
Image :
  - plans visibles = le plus haut à chaque instant (plans de plan.json > comblement > piste principale), recadrés à
    chaque image par cadrage.plan_zooms (respiration, zooms rapides), filtre perspective (sous-pixel : pas de
    tremblement, contrairement à zoompan) ;
  - glissements refaits ici à partir des plans DÉJÀ cadrés de part et d'autre (plus de saut d'échelle à l'entrée) ;
  - scènes et éléments par-dessus, par couche (plans 1 < scènes 2 < éléments 3 < repères 6 < flashs 9) puis par heure ;
  - entrée du hook « avec éclaircissement » (sa retouche CapCut de pokemon-ia), video.json "entree": "" pour l'enlever.
Short : video.json "format": "vertical" → 1080×1920, chaque rush recadré en 9:16 autour de "cx" (0 = bord gauche,
0,5 = centre, 1 = bord droit) : "cx" d'un plan de plan.json, sinon video.json "recadrage" [[de, a, cx], …] (secondes de
la timeline) pour la piste principale, sinon "cx" de video.json (0,5 par défaut).
Short, "cadre_vertical": "carre_flou" (sa capture du 2026-10-13, gojo-ia) : le jeu en carré 1080×1080 au milieu (coupé
autour de cx, zooms dans le carré), au-dessus et en dessous le même plan agrandi, flouté et assombri.
Étalonnage des plans de jeu (gojo-ia, 2026-10-13 : « propre, colorful et attirant ») : video.json "etalonnage" =
{"saturation", "contraste", "vibrance", "gamma", "nettete"} (absent = image du rush telle quelle).
Morceaux de 20 s (bornes hors des glissements), rendus en parallèle et gardés en cache (empreinte de tout ce qui les
compose) : après une correction, seuls les morceaux touchés sont refaits ; --refaire force tout.
Son : voix + musiques + bruitages aux volumes de plan_final.json, limiteur à −1 dBFS, AAC 320 k.
"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadrage import echelle, plan_zooms  # noqa: E402
from commun import a_jour, draft, empreinte, h264, marquer, read_json, taille, video  # noqa: E402

FPS, W, H = 60, 1920, 1080  # W, H : remplacés par le format de la vidéo (Rendu.__init__)
CARRE = False  # Short en carré sur fond flou (video.json "cadre_vertical": "carre_flou")
GRADE = ""     # filtres d'étalonnage des plans de jeu (video.json "etalonnage"), suivis d'une virgule


def etalonnage(e: dict) -> str:
    if not e:
        return ""
    f = (f"eq=contrast={float(e.get('contraste', 1.0)):.3f}:saturation={float(e.get('saturation', 1.0)):.3f}"
         f":gamma={float(e.get('gamma', 1.0)):.3f},")
    if float(e.get("vibrance", 0)):
        f += f"vibrance=intensity={float(e['vibrance']):.3f},"
    if float(e.get("nettete", 0)):
        f += f"unsharp=5:5:{float(e['nettete']):.2f}:5:5:0,"
    return f
MORCEAU = 20.0
BELOW_NORMAL = 0x4000
VERSION = "rendu 1"  # à changer si la fabrication des morceaux change (tout est alors refait)


def fr(t: float) -> int:
    return int(round(t * FPS))


# ───────────── timeline (fonctions pures, testées)
def cx_de(t: float, recadrage: list, defaut: float = 0.5) -> float:
    """Centre du recadrage vertical à t s de la timeline : dernière plage [de, a, cx] qui le contient, sinon `defaut`."""
    return next((float(c) for a, b, c in reversed(recadrage or []) if a <= t < b), defaut)


def segments_base(d: dict, plan_capcut: dict, comblement: dict, recadrage=None, cx=0.5) -> list:
    """Plans de jeu possibles : [{file, a, b (images), src (s), speed, niveau, cx}] ; piste principale = niveau 0.
    Une plage de `recadrage` coupe le clip de la piste principale à ses bornes (chaque morceau garde son cx)."""
    vids = {m["id"]: m for m in d["materials"]["videos"]}
    main = next(t for t in d["tracks"] if t["type"] == "video" and t.get("flag", 0) == 0)
    out = []
    bornes_cx = sorted({fr(x) for a, b, _ in recadrage or [] for x in (a, b)})
    for s in main["segments"]:
        tr, so = s["target_timerange"], s.get("source_timerange") or {"start": 0, "duration": s["target_timerange"]["duration"]}
        a, b = fr(tr["start"] / 1e6), fr((tr["start"] + tr["duration"]) / 1e6)
        speed = so["duration"] / max(1, tr["duration"])
        coupes = [a] + [x for x in bornes_cx if a < x < b] + [b]
        for x, y in zip(coupes, coupes[1:]):
            out.append({"file": vids.get(s["material_id"], {}).get("path"), "a": x, "b": y, "src": so["start"] / 1e6 + (x - a) / FPS * speed,
                        "speed": speed, "niveau": 0, "cx": cx_de((x + y) / 2 / FPS, recadrage, cx)})  # milieu : jamais l'arrondi d'une borne
    for niveau, items in ((50, comblement.get("items", [])), (100, plan_capcut.get("items", []))):
        for i in items:
            if i.get("layer") == 1 and "src" in i and not i["file"].startswith("transitions/"):
                out.append({"file": i["file"], "a": fr(i["at"]), "b": fr(i["at"] + i["dur"]), "src": float(i["src"]), "speed": float(i.get("speed", 1.0)),
                            "niveau": niveau, "cx": float(i.get("cx", cx_de(i["at"] + i["dur"] / 2, recadrage, cx)))})
    return [s for s in out if s["b"] > s["a"]]


def visibles(segs: list) -> list:
    """Morceaux d'image de base dans l'ordre : le plan le plus haut à chaque image ; un trou = plan noir (file None)."""
    bornes = sorted({x for s in segs for x in (s["a"], s["b"])} | {0})
    out = []
    for a, b in zip(bornes, bornes[1:]):
        top = max((s for s in segs if s["a"] <= a and b <= s["b"]), key=lambda s: s["niveau"], default=None)
        if out and out[-1]["seg"] is top and out[-1]["b"] == a:
            out[-1]["b"] = b
            continue
        out.append({"seg": top, "a": a, "b": b})
    res = []
    for p in out:
        s = p["seg"]
        res.append({"file": s["file"] if s else None, "a": p["a"], "b": p["b"], "speed": s["speed"] if s else 1.0,
                    "src": (s["src"] + (p["a"] - s["a"]) / FPS * s["speed"]) if s else 0.0, "cx": s.get("cx", 0.5) if s else 0.5})
    return res


def avec_glissements(pieces: list, glisses: list) -> list:
    """Remplace la fenêtre de chaque glissement ({a, b, sens}, images) par un morceau « glisse » qui garde les deux plans
    de part et d'autre de sa coupe (milieu de la fenêtre), avec leurs points de cadrage."""
    out = [dict(p) for p in pieces]
    for g in sorted(glisses, key=lambda g: g["a"]):
        cut = (g["a"] + g["b"]) // 2
        A = next((p for p in out if p["a"] < cut <= p["b"] and p.get("kind") != "glisse"), None)
        B = next((p for p in out if p["a"] <= cut < p["b"] and p.get("kind") != "glisse" and p is not A), None)
        if A is None or B is None or A["file"] is None or B["file"] is None:
            continue
        res = []
        for p in out:
            if p["b"] <= g["a"] or p["a"] >= g["b"]:
                res.append(p)
                continue
            if p["a"] < g["a"]:
                res.append({**p, "b": g["a"]})
            if p["b"] > g["b"]:
                res.append({**p, "a": g["b"], "src": p["src"] + (g["b"] - p["a"]) / FPS * p["speed"], "t0": p.get("t0", 0.0) + (g["b"] - p["a"]) / FPS})
        res.append({"kind": "glisse", "a": g["a"], "b": g["b"], "sens": g["sens"], "A": A, "B": B, "cut": cut})
        out = sorted(res, key=lambda p: p["a"])
    return out


def bornes_morceaux(fin: int, glisses: list, cible: float = MORCEAU) -> list:
    """Bornes des morceaux (images) : tous les `cible` s, jamais dans un glissement."""
    pas, out, t = fr(cible), [0], 0
    while t + pas < fin - fr(3):
        t += pas
        for g in glisses:
            if g["a"] < t < g["b"]:
                t = g["b"]
        out.append(t)
    return out + [fin]


# ───────────── filtres
def expr_lin(points: list, key: str, t: str) -> str:
    """Expression FFmpeg plate (sans imbrication) de la courbe linéaire par morceaux `points[key]` en fonction de `t`."""
    e = f"{points[0][key]:.5f}"
    for p, q in zip(points, points[1:]):
        dv, dt = q[key] - p[key], q["t"] - p["t"]
        if abs(dv) > 1e-7 and dt > 1e-6:
            e += f"+{dv:.5f}*clip(({t}-{p['t']:.4f})/{dt:.4f},0,1)"
    return e


def cadre(points: list, t0: float, W: int = 0, H: int = 0) -> str:
    """Filtre perspective qui applique (échelle, x, y) des points (temps depuis le début du plan) ; t0 = décalage du
    morceau dans son plan. Position bornée pour ne jamais montrer de bord."""
    W, H = W or globals()["W"], H or globals()["H"]
    if not points:
        return ""
    pts = [{"t": p["t"], "scale": p["scale"], "x": max(-(p["scale"] - 1), min(p["scale"] - 1, p.get("x", 0.0))),
            "y": max(-(p["scale"] - 1), min(p["scale"] - 1, p.get("y", 0.0)))} for p in points]
    if all(abs(p["scale"] - 1) < 1e-6 and not p["x"] and not p["y"] for p in pts):
        return ""
    t = f"(on/{FPS}+{t0:.4f})"
    S, X, Y = (f"({expr_lin(pts, k, t)})" for k in ("scale", "x", "y"))
    cx, cy = f"({W / 2}+{X}*{W / 2})", f"({H / 2}-{Y}*{H / 2})"
    coins = [("0", "0"), (str(W), "0"), ("0", str(H)), (str(W), str(H))]
    args = ":".join(f"x{i}='{cx}+({px}-{W / 2})*{S}':y{i}='{cy}+({py}-{H / 2})*{S}'" for i, (px, py) in enumerate(coins))
    return f",perspective={args}:sense=destination:eval=frame:interpolation=linear"


class Graphe:
    """Commande FFmpeg d'un morceau : entrées + script de filtres."""
    def __init__(self):
        self.entrees, self.filtres, self.n = [], [], 0

    def entree(self, *args) -> int:
        self.entrees += list(args)
        self.n += 1
        return self.n - 1

    def plan(self, file, src, speed, n, points, t0, nom, cx=0.5):
        """n images d'un plan de jeu, recadré ; plan noir si file est None. Vertical : rempli en hauteur, coupé autour de cx."""
        if file is None:
            self.filtres.append(f"color=c=black:s={W}x{H}:r={FPS}:d={n / FPS + 0.1:.4f},trim=end_frame={n},setsar=1,format=yuv420p[{nom}]")
            return
        k = self.entree("-ss", f"{max(0.0, src):.4f}", "-t", f"{n / FPS * speed + 0.2:.4f}", "-i", str(file))
        vitesse = f"setpts=(PTS-STARTPTS)/{speed:.6f}," if abs(speed - 1) > 1e-4 else "setpts=PTS-STARTPTS,"
        fin = f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p[{nom}]"
        if CARRE:   # carré du jeu (cadré, zoomé) posé sur le même plan agrandi et flouté
            c, y = W, (H - W) // 2
            self.filtres.append(f"[{k}:v]{vitesse}fps={FPS},{GRADE}split[{nom}f][{nom}g]")
            self.filtres.append(f"[{nom}g]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
                                f"boxblur=12:2,scale={W}:{H}:flags=bicubic,eq=brightness=-0.12,setsar=1[{nom}b]")
            self.filtres.append(f"[{nom}f]scale=-2:{c}:flags=bicubic,crop={c}:{c}:'(iw-{c})*{cx:.4f}':0,setsar=1"
                                f"{cadre(points, t0, c, c)}[{nom}c]")
            self.filtres.append(f"[{nom}b][{nom}c]overlay=0:{y},{fin}")
            return
        taille_ = (f"scale={W}:{H}:flags=bicubic" if W > H else
                   f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,crop={W}:{H}:'(iw-{W})*{cx:.4f}':'(ih-{H})/2'")
        self.filtres.append(f"[{k}:v]{vitesse}fps={FPS},{GRADE}{taille_},setsar=1{cadre(points, t0)},"
                            + fin)


# ───────────── fabrication
class Rendu:
    def __init__(self, vid: str, leger=False):
        global W, H
        self.cfg = cfg = video(vid)
        W, H = self.taille = taille(cfg)
        global CARRE, GRADE
        CARRE = W < H and cfg.get("cadre_vertical") == "carre_flou"
        GRADE = etalonnage(cfg.get("etalonnage"))
        self.vid, self.out, self.leger = vid, cfg["out"], leger
        self.dir = self.out / "rendu"
        self.dir.mkdir(exist_ok=True)
        pc = read_json(self.out / "plan_capcut.json", {"items": []})
        comb = read_json(self.out / "plan_comblement.json", {"items": []})
        segs = segments_base(draft(cfg["projet"]), pc, comb, cfg.get("recadrage"), float(cfg.get("cx", 0.5)))
        self.fin = max(s["b"] for s in segs if s["niveau"] == 0)
        pieces = [p for p in visibles(segs) if p["a"] < self.fin]
        pieces[-1]["b"] = min(pieces[-1]["b"], self.fin)
        # cadrage : chaque morceau d'image de base est un « plan » pour plan_zooms (même rush, moment voisin = séquence)
        zj = read_json(self.out / "zooms.json", {})
        segz = [{"id": i, "start": p["a"] / FPS, "length": (p["b"] - p["a"]) / FPS, "path": p["file"], "level": 1, "src": p["src"]}
                for i, p in enumerate(pieces) if p["file"]]
        z = plan_zooms(segz, zj.get("punch", []), zj.get("slow"))
        for i, p in enumerate(pieces):
            p["points"], p["t0"] = (z.get(i) or {}).get("points", []), 0.0
        self.glisses = [{"a": fr(i["at"]), "b": fr(i["at"] + i["dur"]), "sens": i["type"].split("_")[1]}
                        for i in pc["items"] if i.get("type", "").startswith("glisse_")]
        self.pieces = avec_glissements(pieces, self.glisses)
        self.calques = sorted([i for i in pc["items"] if i["file"].startswith(("scenes/", "overlays/"))],
                              key=lambda i: (i.get("layer", 3), i["at"]))
        self.entree = cfg.get("entree", "eclaircissement")

    def graphe(self, a: int, b: int) -> Graphe:
        g, noms = Graphe(), []
        for k, p in enumerate(q for q in self.pieces if q["a"] < b and q["b"] > a):
            pa, pb = max(a, p["a"]), min(b, p["b"])
            n, nom = pb - pa, f"p{k}"
            if p.get("kind") == "glisse":
                d = p["b"] - p["a"]
                for side, q in (("A", p["A"]), ("B", p["B"])):           # le plan prolongé au-delà / en deçà de la coupe
                    t0 = q.get("t0", 0.0) + (p["a"] - q["a"]) / FPS
                    g.plan(q["file"], q["src"] + (p["a"] - q["a"]) / FPS * q["speed"], q["speed"], d,
                           q["points"], t0, f"{nom}{side}", q.get("cx", 0.5))
                u = f"clip(t/{d / FPS:.4f},0,1)"
                e = f"if(lt({u},0.5),4*pow({u},3),1-pow(-2*{u}+2,3)/2)"
                pos = {"gauche": (f"-{W}*{e}", "0", f"{W}-{W}*{e}", "0"), "droite": (f"{W}*{e}", "0", f"-{W}+{W}*{e}", "0"),
                       "haut": ("0", f"-{H}*{e}", "0", f"{H}-{H}*{e}"), "bas": ("0", f"{H}*{e}", "0", f"-{H}+{H}*{e}")}[p["sens"]]
                g.filtres.append(f"color=c=black:s={W}x{H}:r={FPS}:d={d / FPS + 0.1:.4f},trim=end_frame={d},setsar=1,format=yuv420p[{nom}bg]")
                g.filtres.append(f"[{nom}bg][{nom}A]overlay=x='{pos[0]}':y='{pos[1]}':eval=frame[{nom}t]")
                g.filtres.append(f"[{nom}t][{nom}B]overlay=x='{pos[2]}':y='{pos[3]}':eval=frame,"
                                 f"trim=start_frame={pa - p['a']}:end_frame={pb - p['a']},setpts=PTS-STARTPTS[{nom}]")
            else:
                t0 = p.get("t0", 0.0) + (pa - p["a"]) / FPS
                g.plan(p["file"], p["src"] + (pa - p["a"]) / FPS * p["speed"], p["speed"], n, p["points"], t0, nom, p.get("cx", 0.5))
            noms.append(nom)
        g.filtres.append("".join(f"[{x}]" for x in noms) + f"concat=n={len(noms)}:v=1:a=0[base]")
        cur = "base"
        for k, it in enumerate(i for i in self.calques if fr(i["at"]) < b and fr(i["at"] + i["dur"]) > a):
            debut = (fr(it["at"]) - a) / FPS
            idx = g.entree("-ss", f"{max(0.0, -debut):.4f}", "-i", str(self.out / it["file"]))
            fin = min(b - a, fr(it["at"] + it["dur"]) - a) / FPS
            g.filtres.append(f"[{idx}:v]setpts=PTS-STARTPTS+{max(0.0, debut):.4f}/TB[c{k}]")
            g.filtres.append(f"[{cur}][c{k}]overlay=eof_action=pass:format=auto:enable='between(t,{max(0.0, debut):.4f},{fin - 0.5 / FPS:.4f})'[v{k}]")
            cur = f"v{k}"
        fin_filtre = f"trim=end_frame={b - a},setpts=PTS-STARTPTS,format=yuv420p"
        if a == 0 and self.entree == "eclaircissement":   # « Entrée avec éclaircissement » : l'image sort d'un éclat de lumière
            fin_filtre = f"eq=brightness='0.55*pow(max(0,1-t/0.45),2)':eval=frame," + fin_filtre
        g.filtres.append(f"[{cur}]{fin_filtre}[out]")
        return g

    def morceau(self, k: int, a: int, b: int, refaire=False) -> Path:
        g = self.graphe(a, b)
        dst = self.dir / f"m{k:03d}.mp4"
        fichiers = [Path(x) for x in g.entrees if isinstance(x, str) and (x.endswith((".mkv", ".mp4", ".mov")))]
        emp = empreinte(VERSION, a, b, g.entrees, g.filtres, fichiers=[f for f in fichiers if f.exists()])
        if not refaire and a_jour(dst, emp):
            return dst
        script = self.dir / f"m{k:03d}.filtres.txt"
        script.write_text(";\n".join(g.filtres), encoding="utf-8")
        cmd = ["ffmpeg", "-v", "error", "-y", *g.entrees, "-/filter_complex", str(script), "-map", "[out]", "-an",
               "-r", str(FPS), *h264(16), "-pix_fmt", "yuv420p", "-g", str(2 * FPS), str(dst)]
        r = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                           creationflags=BELOW_NORMAL if self.leger else 0)
        if r.returncode:
            raise SystemExit(f"morceau {k} ({a / FPS:.2f}–{b / FPS:.2f} s) : échec FFmpeg\n{r.stderr[-3000:]}")
        n = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                "stream=nb_read_packets", "-of", "csv=p=0", str(dst)], capture_output=True, text=True).stdout.strip() or 0)
        if n != b - a:
            raise SystemExit(f"morceau {k} : {n} images au lieu de {b - a}")
        marquer(dst, emp)
        script.unlink()
        print(f"morceau {k:3d}  {a / FPS:7.2f} → {b / FPS:7.2f} s  ({len(g.entrees) // 2} entrées)", flush=True)
        return dst

    def son(self, a: float, b: float, dst: Path) -> None:
        """Voix + musiques + bruitages de plan_final.json (volumes arbitrés et gain général d'audio.py), limiteur −1 dBFS."""
        items = read_json(self.out / "plan_final.json")["items"]
        vol_voix = next((i.get("volume", 1.0) for i in items if i["file"].startswith("voix/")), 1.0)
        ins = ["-i", str(self.out / "voix_timeline.wav")]
        ch = [f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol_voix}[a0]"]
        k = 0
        for it in items:
            if not it["file"].startswith(("musique/", "sfx/")):
                continue
            k += 1
            ins += ["-i", str(self.out / it["file"])]
            ms = int(it["at"] * 1000)
            ch.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,volume={it.get('volume', 1.0)},adelay={ms}|{ms}[a{k}]")
        script = self.dir / "son.filtres.txt"
        script.write_text(";".join(ch) + ";" + "".join(f"[a{i}]" for i in range(k + 1)) +
                          f"amix=inputs={k + 1}:normalize=0:duration=first,"
                          # limiteur sur-échantillonné à −2 dB : tient la crête vraie après l'AAC (sukuna-ia, 2026-10-10)
                          f"aresample=192000,alimiter=limit=0.79:level=false,aresample=48000,"
                          f"atrim={a:.4f}:{b:.4f},asetpts=PTS-STARTPTS[out]", encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(script), "-map", "[out]", "-c:a", "pcm_s16le",
                        str(dst)], check=True)
        script.unlink()

    def faire(self, de=None, a=None, refaire=False) -> Path:
        t0 = time.time()
        bornes = bornes_morceaux(self.fin, self.glisses)
        lots = [(k, x, y) for k, (x, y) in enumerate(zip(bornes, bornes[1:]))
                if (de is None or y > fr(de)) and (a is None or x < fr(a))]
        n_par = 1 if self.leger else int(os.environ.get("TSAR_RENDUS_VIDEO", "3"))
        with ThreadPoolExecutor(n_par) as ex:
            fichiers = list(ex.map(lambda l: self.morceau(*l, refaire=refaire), lots))
        x0, x1 = lots[0][1], lots[-1][2]
        nom = f"{self.vid} - final.mp4" if de is None and a is None else f"{self.vid} - extrait {x0 / FPS:.0f}-{x1 / FPS:.0f}.mp4"
        liste = self.dir / "liste.txt"
        liste.write_text("".join(f"file '{f.as_posix()}'\n" for f in fichiers), encoding="utf-8")
        image, son = self.dir / "image.mp4", self.dir / "son.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste), "-c", "copy", str(image)], check=True)
        self.son(x0 / FPS, x1 / FPS, son)
        dst = self.out / nom
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(image), "-i", str(son), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(dst)], check=True)
        image.unlink(); son.unlink(); liste.unlink()
        print(f"{dst}  ({(x1 - x0) / FPS:.2f} s, {len(lots)} morceaux, {time.time() - t0:.0f} s de rendu)")
        return dst


def main() -> None:
    args = sys.argv[1:]
    opt = lambda k: float(args[args.index(k) + 1]) if k in args else None  # noqa: E731
    Rendu(args[0], leger="--leger" in args).faire(opt("--de"), opt("--a"), refaire="--refaire" in args)


if __name__ == "__main__":
    main()
