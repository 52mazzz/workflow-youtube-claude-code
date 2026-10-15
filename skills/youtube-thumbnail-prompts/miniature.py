#!/usr/bin/env python3
"""miniature.py - check thumbnails before Test & Compare: as small as on a phone, against the competition.

    python miniature.py videos/<id>/miniatures/1-*.png videos/<id>/miniatures/2-*.png \\
        --refs videos/<id>/refs.json --chaine videos/<id>/ma-chaine.json [--dossier videos/<id>/miniatures/controle]

For each thumbnail (OpenCV):
  - format: 1280x720 or more, 16:9, under 2 MB (YouTube's limits);
  - contrast (spread of the luminance) and mean brightness, 3 dominant colours;
  - text regions (MSER, a rough count: many small regions = busy or small text);
  - the bottom-right corner, where YouTube prints the duration: busy or free;
  - previews at 120, 246 and 480 px wide (phone feed, suggested videos, desktop).
Then:
  - PLANCHE (contact sheet): each thumbnail at 246 px dropped in the middle of the competitors'
    thumbnails (the best outliers of refs.json), as in a feed, plus its 120 px version: the file to
    LOOK at (Read), the only real legibility test;
  - SIMILARITY with CLIP (ViT-B/32): average cosine against the competitors (under 0.55 stands
    out, 0.55-0.70 typical, over 0.70 blends in) and against the channel's last 11 thumbnails
    (brand consistency: under 0.60 = the style drifts). Without CLIP, a colour-histogram similarity
    is used, labelled "approximative": its scale is not CLIP's, so no verdict, only which side the
    thumbnail is closer to (the channel or the competitors).

Numbers describe the image; they do not predict the click rate. Test & Compare decides.
Needs: pip install opencv-python-headless numpy (setup.py --vision also installs CLIP).
Thumbnails of refs.json / ma-chaine.json are downloaded from i.ytimg.com (public).
Method adapted from youtube-seo-skills (deeployCO, MIT); no face detection: the channel has no face.
"""
import json, os, re, sys, urllib.request
from pathlib import Path

PREVIEWS = ((120, 68), (246, 138), (480, 270))
STANDS_OUT, TYPICAL, BRAND = 0.55, 0.70, 0.60


def need_cv():
    try:
        import cv2, numpy  # noqa: F401
        return cv2, numpy
    except ImportError:
        sys.exit("OpenCV manque : pip install opencv-python-headless numpy (ou python setup.py --vision)")


def analyse(path, out):
    cv2, np = need_cv()
    img = cv2.imread(str(path))
    if img is None:
        return {"fichier": str(path), "erreur": "image illisible"}
    h, w = img.shape[:2]
    size = Path(path).stat().st_size
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    r = {"fichier": str(path), "largeur": w, "hauteur": h, "ratio": round(w / h, 3), "taille_ko": size // 1024,
         "format_ok": w >= 1280 and h >= 720 and abs(w / h - 16 / 9) < 0.02, "moins_de_2_mo": size < 2 * 1024 * 1024,
         "contraste": round(float(gray.std()), 1), "luminosite": round(float(gray.mean()), 1)}
    px = cv2.resize(img, (160, 90), interpolation=cv2.INTER_AREA).reshape(-1, 3).astype("float32")
    _, labels, centers = cv2.kmeans(px, 3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 4,
                                    cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=3)
    r["couleurs"] = [{"hex": "#{:02X}{:02X}{:02X}".format(*[int(c) for c in centers[i][::-1]]),
                      "part": round(float(counts[i]) / len(labels), 2)} for i in counts.argsort()[::-1]]
    small = cv2.resize(gray, (640, 360), interpolation=cv2.INTER_AREA)
    try:
        regions, _ = cv2.MSER_create().detectRegions(small)
        r["zones_texte"] = len(regions)
    except Exception:
        r["zones_texte"] = None
    edges = cv2.Canny(small, 80, 160)
    corner = edges[int(360 * 0.84):, int(640 * 0.80):]
    dens, avg = float(corner.mean()), float(edges.mean()) or 1.0
    r["coin_duree"] = "chargé" if dens > max(25.0, 1.3 * avg) else "libre"
    r["remarques"] = remarks(r)
    out.mkdir(parents=True, exist_ok=True)
    r["apercus"] = {}
    for pw, ph in PREVIEWS:
        p = out / f"{Path(path).stem}_{pw}px.png"
        cv2.imwrite(str(p), cv2.resize(img, (pw, ph), interpolation=cv2.INTER_AREA))
        r["apercus"][f"{pw}px"] = str(p)
    return r


def remarks(r):
    out = []
    if not r["format_ok"]:
        out.append(f"format {r['largeur']}x{r['hauteur']} : exporter en 1280x720 (16:9)")
    if not r["moins_de_2_mo"]:
        out.append(f"{r['taille_ko']} Ko : YouTube refuse au-delà de 2 Mo (exporter en JPG qualité 90)")
    if r["contraste"] < 45:
        out.append(f"contraste faible ({r['contraste']}) : le sujet risque de se fondre à 120 px")
    if r["luminosite"] < 45:
        out.append("image très sombre : elle disparaît dans le mode sombre de YouTube")
    if r["coin_duree"] == "chargé":
        out.append("coin bas droit chargé : la durée de la vidéo s'affiche par-dessus")
    if r.get("zones_texte") and r["zones_texte"] > 450:
        out.append(f"beaucoup de petits détails ({r['zones_texte']} zones) : texte trop petit ou image trop chargée ?")
    return out


# ---------------------------------------------------------------- other thumbnails

def thumb_urls(path, n):
    """Thumbnail URLs from a swipe.py JSON (refs.json: outliers) or a yt-dlp listing (ma-chaine.json)."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    items = data.get("outliers") if isinstance(data, dict) and "outliers" in data else \
        (data.get("entries") if isinstance(data, dict) else data) or []
    urls = []
    for it in items:
        if not isinstance(it, dict):
            continue
        u = it.get("thumbnail")
        if not u and it.get("thumbnails"):
            u = sorted(it["thumbnails"], key=lambda t: t.get("width") or 0)[-1].get("url")
        vid = it.get("id") or ""
        if not u and re.fullmatch(r"[\w-]{11}", vid):
            u = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        if u and "/shorts/" not in (it.get("url") or ""):
            urls.append(u)
        if len(urls) >= n:
            break
    return urls


def fetch_thumbs(src, dest, n):
    """src: a folder of images, or a JSON file -> list of local image paths."""
    src = Path(src)
    if src.is_dir():
        return sorted([p for p in src.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")])[:n]
    dest.mkdir(parents=True, exist_ok=True)
    got = []
    for i, u in enumerate(thumb_urls(src, n), 1):
        p = dest / f"{i:02d}.jpg"
        if not p.exists():
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r, open(p, "wb") as f:
                    f.write(r.read())
            except Exception as e:
                print(f"  miniature non téléchargée ({e.__class__.__name__}) : {u}", file=sys.stderr)
                continue
        got.append(p)
    return got


def planche(target, others, out):
    """The target at 246 px in the middle of up to 11 others, 4 x 3, plus its 120 px version below."""
    cv2, np = need_cv()
    W, H, G = 246, 138, 10
    tiles = [cv2.imread(str(p)) for p in others]
    tiles = [cv2.resize(t, (W, H), interpolation=cv2.INTER_AREA) for t in tiles if t is not None][:11]
    me = cv2.resize(cv2.imread(str(target)), (W, H), interpolation=cv2.INTER_AREA)
    tiles.insert(min(5, len(tiles)), me)
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * (H + G) + G + 68 + 2 * G, cols * (W + G) + G, 3), 15, np.uint8)
    for k, t in enumerate(tiles):
        y, x = G + (k // cols) * (H + G), G + (k % cols) * (W + G)
        sheet[y:y + H, x:x + W] = t
        if t is me:
            cv2.rectangle(sheet, (x - 4, y - 4), (x + W + 3, y + H + 3), (59, 56, 229), 3)
    tiny = cv2.resize(cv2.imread(str(target)), (120, 68), interpolation=cv2.INTER_AREA)
    y = rows * (H + G) + 2 * G
    sheet[y:y + 68, G:G + 120] = tiny
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sheet)
    return str(out)


# ---------------------------------------------------------------- similarity

def embedder():
    """CLIP ViT-B/32 when installed, else a colour-histogram vector (approximate)."""
    if not os.environ.get("MINIATURE_SANS_CLIP"):
        try:
            import torch, open_clip  # noqa: F401
            from PIL import Image
            model, _, prep = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
            model.eval()

            def clip_embed(p):
                with torch.no_grad():
                    f = model.encode_image(prep(Image.open(p).convert("RGB")).unsqueeze(0))[0]
                return (f / f.norm()).tolist()
            return clip_embed, "CLIP ViT-B/32"
        except Exception as e:
            print(f"  CLIP indisponible ({e.__class__.__name__}) : similarité approximative par histogramme de couleurs",
                  file=sys.stderr)
    cv2, np = need_cv()

    def hist_embed(p):
        hsv = cv2.cvtColor(cv2.resize(cv2.imread(str(p)), (160, 90)), cv2.COLOR_BGR2HSV)
        hst = cv2.calcHist([hsv], [0, 1, 2], None, [8, 4, 4], [0, 180, 0, 256, 0, 256]).flatten()
        n = float(np.linalg.norm(hst)) or 1.0
        return (hst / n).tolist()
    return hist_embed, "approximative (histogramme de couleurs, CLIP non installé)"


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / ((sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) or 1)


def similarity(target, others, embed):
    if not others:
        return None
    t = embed(target)
    sims = sorted(((round(cosine(t, embed(o)), 3), str(o)) for o in others), reverse=True)
    return {"moyenne": round(sum(s for s, _ in sims) / len(sims), 3), "max": sims[0][0], "plus_proches": sims[:3], "n": len(sims)}


def verdict_concurrence(avg):
    return "se démarque" if avg < STANDS_OUT else "typique" if avg < TYPICAL else "se fond dans la masse"


def main():
    a = sys.argv[1:]
    val = lambda n: a[a.index(n) + 1] if n in a and a.index(n) + 1 < len(a) else None
    skip = {val(n) for n in ("--refs", "--chaine", "--dossier", "--concurrents")}
    images = [Path(x) for x in a if not x.startswith("--") and x not in skip]
    if not images:
        print(__doc__); sys.exit(1)
    missing = [str(p) for p in images if not p.exists()]
    if missing:
        sys.exit("introuvable : " + ", ".join(missing))
    out = Path(val("--dossier") or images[0].parent / "controle")
    comp_src, own_src = val("--concurrents") or val("--refs"), val("--chaine")
    comps = fetch_thumbs(comp_src, out / "concurrents", 11) if comp_src else []
    own = fetch_thumbs(own_src, out / "chaine", 11) if own_src else []
    embed, how = embedder() if (comps or own) else (None, None)
    calibrated = bool(how) and how.startswith("CLIP")
    report = {"methode_similarite": how, "concurrents": len(comps), "chaine": len(own), "miniatures": []}
    for img in images:
        r = analyse(img, out)
        if comps:
            r["planche"] = planche(img, comps, out / f"planche_{img.stem}.png")
            s = similarity(img, comps, embed)
            r["vs_concurrents"] = dict(s, verdict=verdict_concurrence(s["moyenne"]) if calibrated else "non calibré (sans CLIP)")
        if own:
            mine = [p for p in own if p.resolve() != img.resolve()]
            s = similarity(img, mine, embed)
            if s:
                if calibrated:
                    v = "cohérente avec la chaîne" if s["moyenne"] >= BRAND else "s'éloigne du style de la chaîne"
                elif r.get("vs_concurrents"):
                    v = ("plus proche de la chaîne que des concurrents" if s["moyenne"] > r["vs_concurrents"]["moyenne"]
                         else "plus proche des concurrents que de la chaîne")
                else:
                    v = "non calibré (sans CLIP)"
                r["vs_chaine"] = dict(s, verdict=v)
        report["miniatures"].append(r)
    if "--json" in a:
        print(json.dumps(report, indent=1, ensure_ascii=False)); return
    for r in report["miniatures"]:
        print(f"\n  {r['fichier']}")
        if r.get("erreur"):
            print(f"    {r['erreur']}"); continue
        print(f"    {r['largeur']}x{r['hauteur']}, {r['taille_ko']} Ko ; contraste {r['contraste']}, luminosité {r['luminosite']} ; "
              f"couleurs " + ", ".join(f"{c['hex']} {int(c['part'] * 100)} %" for c in r["couleurs"]))
        print(f"    zones de texte ~{r['zones_texte']} ; coin de la durée {r['coin_duree']}")
        for m in r["remarques"]:
            print(f"    ! {m}")
        if r.get("vs_concurrents"):
            v = r["vs_concurrents"]
            print(f"    contre {v['n']} miniatures concurrentes : {v['moyenne']} en moyenne -> {v['verdict']} (max {v['max']})")
        if r.get("vs_chaine"):
            v = r["vs_chaine"]
            print(f"    contre {v['n']} miniatures de la chaîne : {v['moyenne']} -> {v['verdict']}")
        if r.get("planche"):
            print(f"    planche à regarder : {r['planche']}")
        print(f"    aperçus : {', '.join(r['apercus'].values())}")
    if calibrated:
        print(f"\n  similarité : {how}. Seuils : moins de {STANDS_OUT} se démarque, plus de {TYPICAL} se fond ; "
              f"cohérence de chaîne à partir de {BRAND}.")
    elif how:
        print(f"\n  similarité : {how} ; échelle différente de CLIP, pas de verdict absolu (python setup.py --vision).")
    print("  Ce sont des mesures de l'image, pas une prédiction du taux de clics : Test & Compare tranche.\n")


if __name__ == "__main__":
    main()
