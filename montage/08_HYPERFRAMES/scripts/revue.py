"""Revue du rendu direct avant de le montrer.        python scripts/revue.py <id> [fichier.mp4] [--sans-images]

Ce que je regarde moi-même avant tout envoi (2026-10-08 : « je veux pas devoir réitérer ») :
  - planches d'images (02_ANALYSE/revue_<id>/planche_NN.png) : chaque glissement (avant, milieu, après), chaque zoom
    rapide (départ, plein, fin), chaque élément (entrée, milieu, sortie), légendés ;
  - rapport (02_ANALYSE/revue_<id>.txt) :
      zooms : saut d'échelle d'une image à l'autre ailleurs qu'à un changement de plan (doit être 0) ;
      bruitages : élément qui entre sans aucun son, seconde avec plus de 3 sons ;
      image : passages noirs (≥ 0,1 s), image figée ≥ 2 s ;
      son : volume intégré (−14 LUFS visés), crête (≤ −1 dBFS), durée = timeline.
Code 1 si un point est à corriger.
"""
import json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cadrage import echelle  # noqa: E402
from commun import ANALYSE, read_json  # noqa: E402
from rendu import FPS, Rendu  # noqa: E402

SANS_SON = {"soustitre", "scene_fond"}


def mm(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def courbe_zoom(r: Rendu) -> list:
    """Problèmes de cadrage :
      - dans un plan, une échelle qui change brusquement de vitesse (à-coup : plus de 0,012 d'écart de vitesse d'une
        image à l'autre ; les montées adoucies des zooms rapides restent en dessous) ;
      - d'une coupe à l'autre dans une même séquence (même rush, moins de 1 s sautée), la respiration qui ne
        continue pas (les zooms rapides, eux, sortent par la coupe : c'est voulu).
    Le retour net de la respiration à 1 au début d'une phrase (mode « pousse », zooms.json slow.remises) est voulu."""
    pb = []
    remises = [float(x) for x in read_json(r.out / "zooms.json", {}).get("slow", {}).get("remises", [])]
    pres = lambda t, eps: any(abs(t - x) <= eps for x in remises)  # noqa: E731
    for p in r.pieces:
        if p.get("kind") == "glisse":
            continue
        v = [echelle(p.get("points", []), p.get("t0", 0.0) + k / FPS)[0] for k in range(p["b"] - p["a"])]
        d = [y - x for x, y in zip(v, v[1:])]
        for k, (d1, d2) in enumerate(zip(d, d[1:])):
            if abs(d2 - d1) > 0.012 and not pres((p["a"] + k + 1.5) / FPS, 3 / FPS):
                pb.append(f"zoom : à-coup d'échelle ({v[k + 1]:.3f} → {v[k + 2]:.3f}) à {mm((p['a'] + k + 2) / FPS)}")
                break
    # respiration seule, d'une coupe à l'autre
    zj = read_json(r.out / "zooms.json", {})
    base = [p for p in r.pieces if p.get("kind") != "glisse" and p["file"]]
    segz = [{"id": i, "start": p["a"] / FPS, "length": (p["b"] - p["a"]) / FPS, "path": p["file"], "level": 1,
             "src": p["src"]} for i, p in enumerate(base)]
    import contextlib, io
    from cadrage import plan_zooms
    with contextlib.redirect_stdout(io.StringIO()):
        z = plan_zooms(segz, [], zj.get("slow"))
    for i, (p, q) in enumerate(zip(base, base[1:])):
        if p["b"] != q["a"] or p["file"] != q["file"] or abs(q["src"] - (p["src"] + (p["b"] - p["a"]) / FPS * p["speed"])) > 1.0:
            continue
        fin = echelle((z.get(i) or {}).get("points", []), (p["b"] - p["a"] - 1) / FPS)[0]
        debut = echelle((z.get(i + 1) or {}).get("points", []), 0.0)[0]
        if abs(debut - fin) > 0.004 and not pres(q["a"] / FPS, 0.05):
            pb.append(f"zoom : la respiration saute de {fin:.3f} à {debut:.3f} à la coupe de {mm(q['a'] / FPS)} (même séquence)")
    return pb


def sons(r: Rendu) -> list:
    pb = []
    pc = read_json(r.out / "plan_capcut.json", {"items": []})
    sfx = sorted(i["at"] for i in read_json(r.out / "plan_final.json", {"items": []})["items"] if i["file"].startswith("sfx/"))
    for it in pc["items"]:
        t = it.get("type", "")
        if not t or t in SANS_SON or t.startswith("glisse") or it.get("layer") == 1:
            continue
        avant = 0.3 if t == "frise" else 0.15  # frise : le succès Minecraft part 0,25 s avant, avec le glissement (2026-10-15)
        if not any(it["at"] - avant <= x <= it["at"] + 0.45 for x in sfx):  # même écart que l'arbitre d'audio.py
            pb.append(f"bruitage : {it.get('id', it['file'])} ({t}) entre à {mm(it['at'])} sans aucun son")
    for k, x in enumerate(sfx):
        n = sum(1 for y in sfx[k:] if y < x + 1.0)
        if n > 4:
            pb.append(f"bruitage : {n} sons en 1 s à partir de {mm(x)}")
    return sorted(set(pb))


def mesures(mp4: Path, fin: float) -> list:
    pb = []
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-vf",
                          "blackdetect=d=0.1:pix_th=0.06,freezedetect=n=0.002:d=2", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err):
        pb.append(f"image : noir de {mm(float(a))} à {mm(float(b))}")
    debuts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", err)]
    fins = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", err)] + [fin]
    for a, b in zip(debuts, fins):
        pb.append(f"image : figée de {mm(a)} à {mm(b)} ({b - a:.1f} s)")
    resume = err[err.rfind("Summary"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resume).group(1))
    crete = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", resume).group(1))
    if not -14.6 <= i <= -13.4:
        pb.append(f"son : {i:.1f} LUFS (viser −14)")
    if crete > -1.0:
        pb.append(f"son : crête {crete:.1f} dBFS (au plus −1)")
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                             capture_output=True, text=True).stdout or 0)
    if abs(d - fin) > 0.1:
        pb.append(f"durée : {d:.2f} s au lieu de {fin:.2f} s")
    return pb, i, crete


def instants(r: Rendu, de=0.0) -> list:
    """(seconde, légende) à regarder."""
    out = []
    for g in r.glisses:
        out += [((g["a"] - 2) / FPS, "avant glissement"), ((g["a"] + g["b"]) / 2 / FPS, "glissement"), ((g["b"] + 2) / FPS, "après glissement")]
    for z in read_json(r.out / "zooms.json", {}).get("punch", []):
        out += [(z["at"] + 0.03, f"zoom {z['scale']} départ"), (z["at"] + 0.5, f"zoom {z['scale']} plein"),
                (z["at"] + z["dur"] - 0.05, f"zoom {z['scale']} fin")]
    for it in read_json(r.out / "plan_capcut.json", {"items": []})["items"]:
        t = it.get("type", "")
        if not t or t.startswith("glisse") or it.get("layer") == 1:
            continue
        d = it["dur"]
        out += [(it["at"] + min(0.35, d / 3), f"{t} entrée"), (it["at"] + d / 2, f"{t} milieu"), (it["at"] + d - 0.06, f"{t} sortie")]
    return sorted((t - de, x) for t, x in out if t >= de)


def planches(mp4: Path, points: list, dossier: Path, vertical=False) -> list:
    dossier.mkdir(parents=True, exist_ok=True)
    for f in dossier.glob("*.png"):
        f.unlink()

    def vignette(k):
        t, leg = points[k]
        dst = dossier / f"v{k:03d}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(mp4), "-frames:v", "1", "-vf",
                        "scale=270:480" if vertical else "scale=480:270", str(dst)], check=False)
        if dst.exists():
            subprocess.run(["magick", str(dst), "-gravity", "north", "-background", "#111", "-splice", "0x22", "-fill", "yellow",
                            "-pointsize", "16", "-annotate", "+0+3", f"{mm(t)}  {leg}", str(dst)], check=False)
        return dst
    with ThreadPoolExecutor(6) as ex:
        vs = [v for v in ex.map(vignette, range(len(points))) if v.exists()]
    out = []
    for n in range(0, len(vs), 16):
        dst = dossier / f"planche_{n // 16 + 1:02d}.png"
        subprocess.run(["magick", "montage", *map(str, vs[n:n + 16]), "-tile", "8x" if vertical else "4x", "-geometry", "+3+3", "-background", "#000",
                        str(dst)], check=True)
        out.append(dst)
    for v in vs:
        v.unlink()
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vid = args[0]
    r = Rendu(vid)
    mp4 = Path(args[1]) if len(args) > 1 else r.out / f"{vid} - final.mp4"
    de = 0.0
    m = re.search(r"extrait (\d+)-(\d+)", mp4.name)
    if m:
        de = float(m.group(1))
    fin = (int(m.group(2)) if m else r.fin / FPS) - de
    pb = courbe_zoom(r) + sons(r)
    pm, lufs, crete = mesures(mp4, fin)
    pb += pm
    lignes = [f"Revue de {mp4.name} : {fin:.1f} s, {lufs:.1f} LUFS, crête {crete:.1f} dBFS"]
    lignes += pb or ["aucun problème mesuré"]
    if "--sans-images" not in sys.argv:
        pl = planches(mp4, instants(r, de), ANALYSE / f"revue_{vid}", vertical=r.taille[0] < r.taille[1])
        lignes.append(f"{len(pl)} planche(s) à regarder : {ANALYSE / f'revue_{vid}'}")
    (ANALYSE / f"revue_{vid}.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    return 1 if pb else 0


if __name__ == "__main__":
    sys.exit(main())
