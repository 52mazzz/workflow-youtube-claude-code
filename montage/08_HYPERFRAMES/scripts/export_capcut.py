"""Rend les éléments d'une vidéo avec le kit Hyperframes et écrit le plan de pose CapCut.

usage : python scripts/export_capcut.py <id_video> plan.json [autres.json …] [--nouveaux] [--leger] [--seul REGEX] [--force] [--capcut]

Avant tout rendu : verifie_plan.py (variables inconnues ou manquantes, chevauchements…) ; arrêt sur erreur, sauf --force.
Glissements : rendus seulement avec --capcut (pose dans CapCut) ; le rendu direct (rendu.py) les refait lui-même à partir
des plans déjà cadrés, un fichier ici ne servirait à rien.

Chaque JSON contient "elements" : [{id, type, at, dur, vars?, layer?}] (type = compositions/<type>.html),
et éventuellement "plans" : [{rush, at, dur, src}] + "rush_dir" (plans de jeu sous les scènes, piste 1).
Sorties dans 06_CAPCUT/<id>/ :
  scenes/<id>.mp4    scènes plein écran (H.264, 60 i/s)
  overlays/<id>.mov  éléments transparents : MOV ProRes 4444 d'Hyperframes → QuickTime Animation (qtrle argb, 60 i/s),
                     seul format transparent vérifié dans CapCut 9.5 Windows (WebM alpha = rectangle noir)
  plan_capcut.json   pour : capcut_bridge.py place "<projet>" plan_capcut.json
--nouveaux : ne rend que ce qui manque ou a changé : chaque rendu garde une empreinte (<fichier>.empreinte : composition,
kit tsar.js/tsar.css, variables, durée) ; un élément dont l'empreinte diffère est refait. Une image d'assets/ modifiée
n'est pas suivie : --seul <id> pour la refaire. --leger : 1 worker, priorité basse.
Short : video.json "format": "vertical" → éléments rendus en 1080×1920 (le kit place chaque élément pour l'écran
vertical) et écran partagé en haut / en bas ; "cx" d'un plan (recadrage 9:16) passe à rendu.py.
"""
import json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import a_jour, empreinte, h264, marquer, taille  # noqa: E402
from commun import rush as chemin_rush  # noqa: E402  (rush_dir facultatif : cherché dans Videos/*/Rush)

HF = Path(__file__).resolve().parent.parent
MONTAGE = HF.parent
from make_compositions import SPECS  # noqa: E402
# éléments opaques (plein écran) → MP4 sur la piste des scènes ; les autres → MOV transparents
SCENES = {k for k, (_, transparent, _) in SPECS.items() if not transparent} | {"partage"}
# Carte graphique pour le rendu (Chrome) et l'encodage des scènes MP4 ; TSAR_GPU=0 pour revenir au processeur
def _hyperframes():
    """Commande Hyperframes : la version épinglée dans package.json, lancée avec node directement depuis le cache de npx
    (npx coûte ~3 s par élément, sur ~100 éléments) ; sinon npx avec cette version."""
    pin = re.search(r"hyperframes@([\d.]+)", (HF / "package.json").read_text(encoding="utf-8")).group(1)
    for d in Path(os.path.expandvars(r"%LOCALAPPDATA%\npm-cache\_npx")).glob("*/node_modules/hyperframes"):
        try:
            if json.loads((d / "package.json").read_text(encoding="utf-8"))["version"] == pin:
                return ["node", str(d / "bin" / "hyperframes.mjs")]
        except (OSError, ValueError, KeyError):
            continue
    return ["npx", "--yes", f"hyperframes@{pin}"]


HYPERFRAMES = _hyperframes() if __name__ == "__main__" else None
GPU = os.environ.get("TSAR_GPU", "1") != "0"
BELOW_NORMAL = 0x4000
W, H = 1920, 1080  # format de la vidéo (main : video.json "format")

def run(cmd, **kw):
    """Commande silencieuse ; en cas d'échec, affiche sa sortie d'erreur puis arrête."""
    r = subprocess.run(cmd, creationflags=BELOW_NORMAL if leger else 0, stderr=subprocess.PIPE, text=True,
                       encoding="utf-8", errors="replace", **kw)
    if r.returncode:
        print(r.stderr[-3000:])
        raise SystemExit(f"échec : {' '.join(map(str, cmd[:6]))}…")


GLISSE_VERSION = "courbe cubique 1"  # à changer si le mouvement des glissements change (tout est alors refait)


def glisse(el, dst):
    """Push gauche / droite / haut / bas entre le plan sortant A et l'entrant B (vars.A, vars.B = [fichier, seconde à la
    coupe]) : les deux images bougent ensemble, courbe douce (accélère puis ralentit), sans flou ni fondu."""
    v, d = el["vars"], float(el["dur"])
    p = f"clip(t/{d},0,1)"
    e = f"if(lt({p},0.5),4*pow({p},3),1-pow(-2*{p}+2,3)/2)"
    pos = {"gauche": (f"-1920*{e}", "0", f"1920-1920*{e}", "0"), "droite": (f"1920*{e}", "0", f"-1920+1920*{e}", "0"),
           "haut": ("0", f"-1080*{e}", "0", f"1080-1080*{e}"), "bas": ("0", f"1080*{e}", "0", f"-1080+1080*{e}")}
    xa, ya, xb, yb = pos[v["sens"]]
    prep = "fps=60,scale=1920:1080,setsar=1,format=yuv420p,setpts=PTS-STARTPTS"
    run(["ffmpeg", "-v", "error", "-y",
         "-ss", f"{max(0.0, v['A'][1] - d / 2):.3f}", "-t", f"{d + 0.1:.3f}", "-i", v["A"][0],
         "-ss", f"{max(0.0, v['B'][1] - d / 2):.3f}", "-t", f"{d + 0.1:.3f}", "-i", v["B"][0],
         "-filter_complex", f"[0:v]{prep}[a];[1:v]{prep}[b];color=c=black:s=1920x1080:r=60:d={d}[bg];"
         f"[bg][a]overlay=x='{xa}':y='{ya}':eval=frame[t];[t][b]overlay=x='{xb}':y='{yb}':eval=frame[v]",
         "-map", "[v]", "-an", "-t", f"{d:.3f}", *h264(14), "-pix_fmt", "yuv420p", str(dst)])


PARTAGE_VERSION = "partage 1"  # à changer si le dessin de l'écran partagé change (tout est alors refait)
FONTE = r"C\:/Windows/Fonts/ariblk.ttf"  # Arial Black (deux-points échappé pour FFmpeg) : FFmpeg ne lit pas les polices web du kit


def partage(el, dst):
    """Écran partagé de l'accroche, comme WOLF (« 99 nights » / « realistic ») : deux plans de jeu côte à côte
    (vars.A, vars.B = [rush, seconde de départ]), trait blanc au milieu, nom de chaque côté (nomA, nomB), et le côté
    pas encore montré flouté en gros pixels (flou = "a" | "b" | "")."""
    v, d = el["vars"], float(el["dur"])
    def cote(k):
        flou = ",scale=48:54:flags=area,scale=960:1080:flags=neighbor" if v.get("flou") == k else ""
        nom = v.get("nom" + k.upper(), "")
        txt = (f",drawtext=fontfile='{FONTE}':text='{nom}':fontsize=72:fontcolor=white:borderw=8:bordercolor=black"
               f":x=(w-text_w)/2:y=h-text_h-70") if nom else ""
        return f"fps=60,scale=1920:1080,crop=960:1080:480:0,setsar=1{flou}{txt},format=yuv420p,setpts=PTS-STARTPTS"
    def cote_v(k):  # vertical : une moitié en haut, l'autre en bas (1080×960 chacune), recadrée autour de cx
        cx = float(v.get("cx" + k.upper(), 0.5))
        flou = ",scale=54:48:flags=area,scale=1080:960:flags=neighbor" if v.get("flou") == k else ""
        nom = v.get("nom" + k.upper(), "")
        txt = (f",drawtext=fontfile='{FONTE}':text='{nom}':fontsize=80:fontcolor=white:borderw=9:bordercolor=black"
               f":x=(w-text_w)/2:y={'h-text_h-60' if k == 'a' else '60'}") if nom else ""
        return (f"fps=60,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960:'(iw-1080)*{cx:.4f}':'(ih-960)/2',"
                f"setsar=1{flou}{txt},format=yuv420p,setpts=PTS-STARTPTS")
    A, B = v["A"], v["B"]
    vert = H > W
    pile = ("[0:v]{a}[a];[1:v]{b}[b];[a][b]vstack=inputs=2,drawbox=x=0:y=956:w=1080:h=8:color=white:t=fill[v]" if vert else
            "[0:v]{a}[a];[1:v]{b}[b];[a][b]hstack=inputs=2,drawbox=x=956:y=0:w=8:h=1080:color=white:t=fill[v]")
    f_ = cote_v if vert else cote
    run(["ffmpeg", "-v", "error", "-y",
         "-ss", f"{float(A[1]):.3f}", "-t", f"{d + 0.1:.3f}", "-i", str(chemin_rush(A[0], rush_dir)),
         "-ss", f"{float(B[1]):.3f}", "-t", f"{d + 0.1:.3f}", "-i", str(chemin_rush(B[0], rush_dir)),
         "-filter_complex", pile.format(a=f_("a"), b=f_("b")),
         "-map", "[v]", "-an", "-t", f"{d:.3f}", *h264(14), "-pix_fmt", "yuv420p", str(dst)])


def rendre(el, kind, dur, scene, dst, emp):
    """Rendu d'un élément (Hyperframes, ou FFmpeg pour un glissement) puis empreinte à côté."""
    if kind.startswith("glisse"):
        glisse(el, dst)
    elif kind == "partage":
        partage(el, dst)
    else:
        # copie du modèle avec la bonne durée (la durée racine est fixée à la compilation, pas par variable)
        html = (HF / "compositions" / f"{kind}.html").read_text(encoding="utf-8")
        html = re.sub(r'(data-composition-id="[^"]+" data-start="0" data-duration=")[^"]+"', rf'\g<1>{dur}"', html, count=1)
        if (W, H) != (1920, 1080):  # Short : même composition, page à la taille de la vidéo (le kit lit data-width/height)
            html = html.replace('data-width="1920" data-height="1080"', f'data-width="{W}" data-height="{H}"')
            html = html.replace('content="width=1920, height=1080"', f'content="width={W}, height={H}"')
        src = BUILD / f"{el['id']}.html"
        src.write_text(html, encoding="utf-8")
        (BUILD / f"{el['id']}.vars.json").write_text(json.dumps(el.get("vars", {}), ensure_ascii=False), encoding="utf-8")
        # plusieurs rendus en parallèle : 2 navigateurs par rendu suffisent (1 en mode léger)
        common = HYPERFRAMES + ["render", ".", "-c", src.relative_to(HF).as_posix(), "-f", "60", "--quiet",
                  "--variables-file", str(BUILD / f"{el['id']}.vars.json"), "-w", "1" if leger else "2"] \
            + (["--browser-gpu"] if GPU else [])
        if scene:
            enc = ["--gpu", "--video-bitrate", "20M"] if GPU else ["--crf", "16"]
            run(common + ["--format", "mp4"] + enc + ["-o", str(dst)], cwd=HF, shell=HYPERFRAMES[0] == "npx", stdout=subprocess.DEVNULL)
        else:
            prores = BUILD / f"{el['id']}.mov"
            run(common + ["--format", "mov", "-o", str(prores)], cwd=HF, shell=HYPERFRAMES[0] == "npx", stdout=subprocess.DEVNULL)
            run(["ffmpeg", "-v", "error", "-y", "-i", str(prores), "-r", "60", "-c:v", "qtrle", "-pix_fmt", "argb", str(dst)])
            prores.unlink()
    marquer(dst, emp)
    print(f"{'glisse' if kind.startswith('glisse') else 'partage' if kind == 'partage' else 'scène' if scene else 'overlay':8s} {el['id']:32s} à {el['at']:8.2f}s  {dur:5.2f}s", flush=True)


# couches (première piste libre à partir de ce niveau, au-dessus de tout ce qui est plus bas) : plans de jeu 1, scènes 2,
# éléments 3, repères tenus pendant un test 6 (jamais recouverts par un élément posé après eux), flashs 9 (toujours devant)
PERSISTANTS = {"pastille", "carte", "minuteur", "accelere"}
FLASHS = {"flash", "obturateur"}


def couche(el, scene, glis):
    if glis:
        return 1
    if "layer" in el:
        return el["layer"]
    return 9 if el["type"] in FLASHS else 6 if el["type"] in PERSISTANTS else 2 if scene else 3



def sfx_of(el):
    """Bruitages par défaut de chaque type (secondes relatives au début de l'élément), + el["sfx"] en plus.
    Tout ce qui bouge a son bruitage (retours du 2026-10-03) : pop à l'ouverture, tick à chaque ligne ou détail qui
    apparaît, croix sur une barre, déclic CapCut sur les flashs, whoosh sur les glissements ; jamais de montée (riser)."""
    t, v, d = el["type"], el.get("vars", {}), float(el["dur"])
    js = lambda k: (json.loads(v[k]) if isinstance(v.get(k), str) else v.get(k)) or []  # noqa: E731
    table = {
        "chapitre": [(0.05, "pop")], "test": [(0.05, "pop")], "etiquette": [(0.0, "pop")], "annotation": [(0.0, "tick")],
        "point": [(0.0, "valide")], "reaction": [(0.0, "pop")], "abonnement": [(0.05, "pop"), (1.55, "tick"), (1.6, "valide"), (2.55, "tick"), (2.6, "valide")],
        "obturateur": [(d / 2 - 0.03, "flash_capcut")], "flash": [(d / 3 - 0.02, "flash_capcut")],
        "glisse_gauche": [(d / 2 - 0.3, "whoosh")], "glisse_droite": [(d / 2 - 0.3, "whoosh")],
        "glisse_haut": [(d / 2 - 0.3, "whoosh")], "glisse_bas": [(d / 2 - 0.3, "whoosh")],
        "manche": [(0.0, "pop"), (float(v.get("a", 2.7)), "valide")], "scene_vainqueur": [(0.0, "sub_drop"), (0.15, "impact")],
        "scene_fenetre": [(0.05, "pop")], "scene_outro": [(0.05, "pop"), (0.9, "tick"), (1.6, "tick")],
        "scene_description": [(0.05, "pop"), (float(v.get("etiquetteA", 0.6)), "pop")],
    }
    cues = list(table.get(t, []))
    if t == "scene_fenetre":  # chaque ligne qui apparaît, chaque mot barré
        for l in js("lignes"):
            cues.append((float(l.get("t", 0)) + 0.02, "tick"))
            if l.get("barre") is not None:
                cues.append((float(l["barre"]), "croix"))
    if t == "scene_description":
        cues += [(float(l.get("t", 0)) + 0.02, "tick") for l in js("lignes")]
    if t == "scene_vs":  # chaque IA qui entre, puis la pastille VS
        A, B = (json.loads(v[k]) if isinstance(v.get(k), str) else v.get(k, {}) for k in ("A", "B"))
        cues += [(float(A.get("entree", 0.05)), "pop"), (float(B.get("entree", 1.5)), "pop"), (float(v.get("vs", 3.2)), "impact")]
    if t == "etiquettes":
        items_ = v.get("items", [])
        cues += [(float(i[0]) + 0.05, "tick") for i in (json.loads(items_) if isinstance(items_, str) else items_)]
    if t == "barres":
        lignes = v.get("lignes", [])
        cues += [(0.1, "pop")] + [(float(l.get("t", 0.5)) + 0.5, "tick") for l in (json.loads(lignes) if isinstance(lignes, str) else lignes)]
    if t == "pastille":  # style WOLF : pop à l'entrée, validation ou croix quand le test réussit ou rate
        cues += [(0.0, "pop")] + [(float(x), "valide" if e == "ok" else "croix") for x, e in js("etat")]
    if t == "carte":  # entrée plein écran, puis réduction dans le coin (si elle a lieu)
        cues += [(0.0, "whoosh_court"), (0.05, "impact")]
        if float(v.get("plein", 2.5)) < d - 0.3:
            cues.append((float(v.get("plein", 2.5)), "whoosh_court"))
    if t == "progression":
        cues += [(0.0, "whoosh")] + ([(float(v.get("a", 1.0)), "valide")] if any(x.get("gagnant") for x in js("tests")[int(v.get("actuel", 0)):][:1]) else [])
    if t == "capture":  # tick à chaque ligne surlignée (zones) ou au surlignage unique (a)
        cues += [(0.0, "pop")] + ([(float(z[0]), "tick") for z in js("zones")] or [(float(v.get("a", 0.6)), "tick")])
    if t == "insert":
        cues += [(0.0, "flash_capcut")]
    if t == "vignette":  # case qui entre et ressort en glissant (whoosh) ; logo sans cadre (gros logo sur son mot) : un pop seul
        cues += ([(0.0, "pop")] if str(v.get("cadre", True)).lower() == "false" else
                 [(0.0, "whoosh_court"), (max(0.3, d - 0.2), "whoosh_court")])  # pas de pop : seulement le glissement (2026-10-13)
    if t == "partage":
        cues += [(0.0, "flash_capcut")]
    if t == "duel":  # chaque IA qui entre, puis le VS
        cues += [(float(v.get("a", 0.0)), "pop")] + ([] if str(v.get("seul", False)).lower() == "true" else
                 [(float(v.get("b", 0.6)), "pop"), (float(v.get("vs", 1.2)), "impact")])
    if t == "titre_jeu":
        cues += [(0.0, "whoosh_court"), (0.05, "impact")]
    if t in ("minuteur", "fleche"):
        cues += [(0.0, "pop")]
    if t == "accelere":
        cues += [(0.0, "whoosh_court")]
    if t == "a_venir":
        cues += [(0.0, "whoosh")]
    if t == "note":
        cues += [(0.0, "pop"), (float(v.get("a", 0.6)), "impact")] +                 [(float(v.get("a", 0.6)) + 0.5 + i * 0.45, "tick") for i in range(len(js("points")))]
    if t == "mot":
        cues += [(0.0, "impact")]
    if t == "scene_mots":  # un pop par mot ou logo qui arrive, un impact sur le mot souligné, tick quand le chrono tourne
        for it in js("items"):
            at = float(it.get("t", 0))
            cues.append((at, "impact" if it.get("souligne") else "pop"))
            if it.get("icone") == "chrono":
                cues.append((at + 0.45, "tick"))
    if t == "score":
        cues += [(0.0, "pop")] + ([(float(v.get("a", 0.8)), "valide")] if v.get("point") else [])
    if el.get("sfx") is not None:  # liste explicite : remplace ou complète (« +sfx »)
        cues = ([] if not el.get("sfx_plus") else cues) + [tuple(c) for c in el["sfx"]]
    return [(round(max(0.0, el["at"] + dt), 3), name) for dt, name in cues]

def main():
    global video, plan_files, leger, nouveaux, seul, OUT, BUILD, rush_dir, HYPERFRAMES, W, H
    HYPERFRAMES = _hyperframes()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    seul = next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--seul"), None)
    if seul in args:
        args.remove(seul)
    video, plan_files = args[0], args[1:]
    leger, nouveaux = "--leger" in flags, "--nouveaux" in flags
    OUT = MONTAGE / "06_CAPCUT" / video
    BUILD = HF / "build" / video
    for d in (OUT / "scenes", OUT / "overlays", BUILD):
        d.mkdir(parents=True, exist_ok=True)
    if (HF / "videos" / video / "video.json").exists():
        from commun import video as reglages
        W, H = taille(reglages(video))
    fmt = [] if (W, H) == (1920, 1080) else [f"{W}x{H}"]  # dans l'empreinte : un changement de format refait tout

    elements, plans, rush_dir = [], [], None
    for pf in plan_files:
        data = json.loads(Path(pf).read_text(encoding="utf-8-sig"))
        elements += data.get("elements", [])
        plans += data.get("plans", [])
        rush_dir = data.get("rush_dir", rush_dir)
    if "--force" not in flags:  # le plan d'abord : rien ne doit arriver à l'écran par accident
        from verifie_plan import fin_timeline, rapport, verifier
        cfg = None
        if (HF / "videos" / video / "video.json").exists():
            cfg = reglages(video)
        err, warn = verifier(elements, cfg, fin_timeline(cfg) if cfg else None)
        if err or warn:
            print(rapport(err, warn))
        if err:
            raise SystemExit("plan à corriger avant le rendu (verifie_plan.py) ; --force pour passer outre")


    # déjà rendus, par empreinte : un sous-titre ou une transition seulement renumérotés (st07 → st08, tr03 → tr04)
    # sont recopiés au lieu d'être rendus de nouveau
    deja = {}
    for d_ in (OUT / "scenes", OUT / "overlays", OUT / "transitions"):
        for side in d_.glob("*.empreinte") if d_.exists() else []:
            f = side.with_name(side.name[: -len(".empreinte")])
            if f.exists():
                deja.setdefault(side.read_text(encoding="utf-8").strip(), f)

    items, jobs, reuse = [], [], []
    for el in elements:
        kind, dur = el["type"], round(float(el["dur"]), 3)
        glis = kind.startswith("glisse")
        scene = kind in SCENES
        if glis:
            if "--capcut" in flags:
                (OUT / "transitions").mkdir(exist_ok=True)
            dst = OUT / "transitions" / f"{el['id']}.mp4"
            emp = empreinte(kind, dur, el["vars"], GLISSE_VERSION)
        elif kind == "partage":
            (OUT / "scenes").mkdir(exist_ok=True)
            dst = OUT / "scenes" / f"{el['id']}.mp4"
            emp = empreinte(kind, dur, el["vars"], PARTAGE_VERSION, *fmt)
        else:
            dst = OUT / ("scenes" if scene else "overlays") / f"{el['id']}.{'mp4' if scene else 'mov'}"
            emp = empreinte(kind, dur, el.get("vars", {}), *fmt, fichiers=[HF / "compositions" / f"{kind}.html", HF / "kit" / "tsar.js", HF / "kit" / "tsar.css"])
        if glis and "--capcut" not in flags:
            pass
        elif not (nouveaux and a_jour(dst, emp)) and (seul is None or re.search(seul, el["id"])):
            same = deja.get(emp)
            if nouveaux and same is not None and same != dst and same.exists():
                reuse.append((same, dst, emp))
            else:
                jobs.append((el, kind, dur, scene, dst, emp))
        items.append({"file": dst.relative_to(OUT).as_posix(), "at": el["at"], "dur": dur, "layer": couche(el, scene, glis),
                      "mute": True, "type": kind, "id": el["id"]})

    # Préserver toutes les sources avant d'écraser une destination : des éléments renumérotés peuvent
    # échanger leurs fichiers (st01 A / st02 B → st01 B / st02 A). Le cache garde les chemins d'avant.
    # Une copie est nécessaire : un lien physique suivrait l'écrasement ultérieur du fichier source.
    if reuse:
        with tempfile.TemporaryDirectory(prefix="cache-rendus-", dir=BUILD) as cache:
            sources = {}
            for same, _, _ in reuse:
                if same not in sources:
                    saved = Path(cache) / str(len(sources))
                    shutil.copy2(same, saved)
                    sources[same] = saved
            for same, dst, emp in reuse:
                shutil.copy2(sources[same], dst)
                marquer(dst, emp)

    # rendus en parallèle (TSAR_RENDUS, 8 par défaut : mesuré 2,4x plus rapide qu'en série sur le fixe ; 1 en mode léger) : le démarrage de Chrome domine, pas le dessin
    n_par = 1 if leger else int(os.environ.get("TSAR_RENDUS", "8"))
    print(f"{len(jobs)} rendu(s), {len(reuse)} recopié(s) ; {n_par} en parallèle", flush=True)
    with ThreadPoolExecutor(max_workers=n_par) as pool:
        for f in [pool.submit(rendre, *j) for j in jobs]:
            f.result()

    # "vitesse" (ex. 10 pour une génération en accéléré) : lue par rendu.py ; la pose CapCut l'ignore (plan à vitesse 1)
    shots = [{"file": chemin_rush(s["rush"], rush_dir).as_posix(), "at": s["at"], "dur": s["dur"], "src": s["src"], "layer": 1, "mute": True,
              **({"speed": float(s["vitesse"])} if s.get("vitesse") else {}), **({"cx": float(s["cx"])} if "cx" in s else {})} for s in plans]
    if seul is None:
        sfx = sorted((t, n, el["id"]) for el in elements for t, n in sfx_of(el))   # 3e valeur : l'élément (arbitre d'audio.py)
        # déclic d'appareil photo sur chaque plan rapide de « À venir » (préférences : plans rapides du début)
        declics = [[e["at"], round(e["at"] + float(e["dur"]), 3)] for e in elements if e["type"] == "a_venir"]
        (OUT / "plan_capcut.json").write_text(json.dumps({"items": shots + items, "sfx": sfx, "declics": declics}, ensure_ascii=False,
                                                         indent=1), encoding="utf-8")
        print(f"plan : {len(shots)} plans + {len(items)} éléments + {len(sfx)} bruitages → {OUT / 'plan_capcut.json'}")


if __name__ == "__main__":
    main()
