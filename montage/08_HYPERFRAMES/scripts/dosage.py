"""Dosage du montage minute par minute, comparé aux cibles de la direction de montage.   python scripts/dosage.py <id>

Créé le 2026-10-07 (« tout comme WOLF »), cibles passées le même jour à la direction « duel lisible et nerveux »,
tirée des mesures de 27 vidéos de référence (config/youtube/references/montage/analyse-2026-10-07.md). Changements
d'image, zooms, bruitages, musique et pauses de la voix comptés sur le montage posé (06_CAPCUT/<id>/plan_final.json,
après audio.py, avant l'export). Après l'export, `controle.py <id> --export <mp4>` mesure la même chose sur le fichier
final, avec en plus la part d'image immobile.

Compté :
  - changements d'image : début de chaque clip de la piste principale (un par clip de voix), début et fin des plans
    de jeu, des scènes et des grands éléments du kit (carte, capture, insert, progression, score, partage), zooms
    rapides ; regroupés à 0,4 s (comme la mesure de WOLF) ;
  - zooms : zooms rapides de zooms.json, respirations (une par séquence de jeu de 5 s ou plus, cadrage.py),
    captures zoomées du kit ; « forts » = 1,5× ou plus (zooms de lecture) ;
  - bruitages : chaque SFX posé ;
  - musique : changements de morceau, et blancs d'au moins 1 s entre deux morceaux (à éviter : enchaîner directement) ;
  - voix : pauses de 0,3 s et plus (voix_timeline.wav, silence à −40 dB) ; la part du temps où elle parle se mesure
    sur l'export (controle.py --export), comme pour WOLF.
Rapport : 02_ANALYSE/dosage_<id>.txt. Code 1 si le dosage global s'écarte des cibles (à corriger ou à justifier).
"""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ANALYSE, video  # noqa: E402

# cibles par minute de la direction « duel lisible et nerveux » (2026-10-07) ; entre parenthèses : pokemon-ia, la
# médiane des chaînes qui performent, WOLF
CIBLE = {
    "images": (10, 15),        # changements d'image (8,1 ; 9,3 ; 15 à 23), pointes à 20 dans l'accroche et les tests
    "zooms": (5, 7),           # zooms (2,1 ; 3,8 ; 4,8)
    "zooms_forts": (0.5, 1.5), # zooms de lecture de 1,5× ou plus (0 ; jusqu'à 1 / min chez les chaînes rapides)
    "sfx": (12, 18),           # bruitages (19 ; 16 ; 15)
    "musique": (3, 6),         # changements du fond : morceau, coupure, reprise (2,8 ; 4,4 ; 4,7)
    "coupures": (0.0, 0.0),    # blancs d'au moins 1 s entre deux morceaux : aucun (retour du 2026-10-13, gojo-ia : « ça fait bizarre »)
    "pauses": (0, 3),          # pauses de voix de 0,3 s et plus (14,1 ; 6,8 ; 2,7)
}
GRANDS = ("carte", "capture", "insert", "progression", "score", "partage", "duel", "titre_jeu", "note")


def regrouper(ts, ecart=0.4):
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] > ecart:
            out.append(t)
    return out


def duree_wav(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def silences(wav: Path, mini=0.3):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", f"silencedetect=n=-40dB:d={mini}",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(st, en))


def mesures(cfg) -> dict:
    out = cfg["out"]
    items = json.loads((out / "plan_final.json").read_text(encoding="utf-8"))["items"]
    plan = json.loads((cfg["dir"] / "plan.json").read_text(encoding="utf-8-sig")) if (cfg["dir"] / "plan.json").exists() else {}
    zooms = json.loads((out / "zooms.json").read_text(encoding="utf-8")) if (out / "zooms.json").exists() else {}
    voix = [i for i in items if i["file"].startswith("voix/")]
    fin = max(i["at"] + i.get("dur", 0) for i in items)
    # un clip de la piste principale ne change l'image que s'il vient d'un autre rush ou d'un autre moment du même
    # (plus de 1 s plus loin) : sinon c'est la même image, à quelques pauses coupées près (la mesure de WOLF ne le voit pas)
    voix.sort(key=lambda i: i["at"])
    images = [voix[0]["at"]] if voix else []
    images += [b["at"] for a, b in zip(voix, voix[1:])
               if b["file"] != a["file"] or abs(b.get("src", 0) - (a.get("src", 0) + a.get("dur", 0))) > 1.0]
    for i in items:
        if i["file"].startswith(("scenes/",)) or (i.get("layer") == 1 and not i["file"].startswith(("voix/", "transitions/"))):
            images += [i["at"], i["at"] + i.get("dur", 0)]
    for e in plan.get("elements", []):
        if e["type"] in GRANDS:
            images.append(e["at"])
    images += [z["at"] for z in zooms.get("punch", [])]
    punch = zooms.get("punch", [])
    lent = (zooms.get("slow") or {}).get("min_dur", 5.0) if zooms.get("slow") else None
    lents, seq = [], []                                    # comme plan_zooms du bridge : une poussée par séquence
    for i in voix + [None]:                                # (même rush, jump cuts) d'au moins min_dur
        if seq and (i is None or i["file"] != seq[-1]["file"] or abs(i["at"] - (seq[-1]["at"] + seq[-1].get("dur", 0))) > 0.05
                    or abs(i.get("src", 0) - (seq[-1].get("src", 0) + seq[-1].get("dur", 0))) > 1.0):
            if lent and seq[-1]["at"] + seq[-1].get("dur", 0) - seq[0]["at"] >= lent:
                lents.append(seq[0]["at"])
            seq = []
        if i is not None:
            seq.append(i)
    captures = [e["at"] for e in plan.get("elements", []) if e["type"] == "capture"]
    musiques = sorted((i["at"], i["at"] + duree_wav(out / i["file"])) for i in items if i["file"].startswith("musique/"))
    coupures = [b for (_, b), (a2, _) in zip(musiques, musiques[1:]) if a2 - b >= 1.0]
    sil = silences(out / "voix_timeline.wav")
    return {"fin": fin, "images": regrouper([t for t in images if 0 <= t < fin]),
            "sfx": [i["at"] for i in items if i["file"].startswith("sfx/")],
            "zooms": sorted([z["at"] for z in punch] + lents + captures),
            "zooms_forts": sorted([z["at"] for z in punch if z.get("scale", 1) >= 1.5] + captures),
            "musique": [a for a, _ in musiques] + coupures, "coupures": coupures,
            "pauses": [a for a, b in sil if b - a < 3.0], "silences": sil}


def par_minute(m) -> list:
    n = int(m["fin"] // 60) + 1
    lignes = []
    for k in range(n):
        a, b = k * 60, min((k + 1) * 60, m["fin"])
        if b - a < 20 and n > 1:   # bout de minute final ignoré ; un Short (une seule minute, même courte) est compté
            continue
        cpt = lambda ts: sum(1 for t in ts if a <= t < b) * 60 / (b - a)  # noqa: E731
        lignes.append({"minute": k, "images": cpt(m["images"]), "zooms": cpt(m["zooms"]), "zooms_forts": cpt(m["zooms_forts"]),
                       "sfx": cpt(m["sfx"]), "musique": cpt(m["musique"]), "coupures": cpt(m["coupures"]),
                       "pauses": cpt(m["pauses"])})
    return lignes


def rapport(lignes) -> tuple[list, bool]:
    noms = {"images": "changements d'image", "zooms": "zooms", "zooms_forts": "zooms de lecture (≥ 1,5×)", "sfx": "bruitages",
            "musique": "changements de musique", "coupures": "coupures de musique", "pauses": "pauses de voix ≥ 0,3 s"}
    out, ecart = [], False
    out.append(f"{'':32s}{'ce montage':>12s}   cible")
    for k, (lo, hi) in CIBLE.items():
        moy = sum(l[k] for l in lignes) / max(1, len(lignes))
        hors = moy < lo or moy > hi
        ecart |= hors
        out.append(f"{noms[k] + ' / min':32s}{moy:12.1f}   {lo}–{hi}{'   ← à revoir' if hors else ''}")
    out.append("")
    out.append("minute  images  zooms  bruitages  musique  coupures  pauses   (minutes loin des cibles)")
    for l in lignes:
        loin = [n for n, x in (("images", l["images"] < CIBLE["images"][0] * 0.7), ("zooms", l["zooms"] < CIBLE["zooms"][0] * 0.5),
                               ("bruitages", l["sfx"] < CIBLE["sfx"][0] * 0.5), ("pauses", l["pauses"] > CIBLE["pauses"][1] * 2)) if x]
        if loin:
            out.append(f"{l['minute']:4d}:00 {l['images']:7.0f} {l['zooms']:6.0f} {l['sfx']:10.0f} {l['musique']:8.0f} "
                       f"{l['coupures']:9.0f} {l['pauses']:7.0f}   {', '.join(loin)}")
    return out, ecart


def main(vid):
    cfg = video(vid)
    lignes = par_minute(mesures(cfg))
    texte, ecart = rapport(lignes)
    f = ANALYSE / f"dosage_{vid}.txt"
    f.write_text(f"Dosage de « {vid} » comparé aux cibles de la direction de montage (par minute, sur le montage posé)\n" + "\n".join(texte) + "\n", encoding="utf-8")
    print(f.read_text(encoding="utf-8"))
    sys.exit(1 if ecart else 0)


if __name__ == "__main__":
    main(sys.argv[1])
