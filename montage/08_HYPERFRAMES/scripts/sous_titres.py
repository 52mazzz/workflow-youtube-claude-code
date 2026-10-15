"""Sous-titres « punchlines » : seulement les phrases qui apportent quelque chose, MOTS EXACTS, chaque mot
affiché quand il est dit.                                   python scripts/sous_titres.py <id>

video.json → "transcription" (02_ANALYSE/transcriptions/capcut_<projet>.json, mots DTW ~0,12 s en retard),
"sous_titres": {"fix": {mot_transcrit_normalisé: mot_affiché}, "phrases": [[seconde, phrase dite, phrase affichée?]]}.
Calage : phrase recalée sur le vrai début de voix le plus proche (videos/<id>/debuts_voix.txt, écrit par voix.py).
Un sous-titre qui tomberait sur un élément occupant le bas de l'écran (plan.json) est RETIRÉ, jamais décalé.
Sortie : videos/<id>/captions.json (éléments « soustitre » du kit, pour export_capcut.py).
Contrôle ensuite : retranscrire chaque fenêtre (voir outils.md) et comparer affiché / entendu.
"""
import bisect, re, sys, unicodedata
from commun import ANALYSE, read_json, video, write_json

DTW_LAG = 0.12
SNAP = (-0.35, 0.25)  # fenêtre de recherche du vrai début de voix autour du premier mot
BUSY = ("scene_", "chapitre", "test", "manche", "abonnement")  # types qui occupent le bas de l'écran


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower().replace("’", "'"))
    return re.sub(r"[^a-z0-9']", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def main(vid: str) -> None:
    cfg = video(vid)
    words = read_json(ANALYSE / "transcriptions" / cfg["transcription"])
    toks = [(norm(w["text"]), w["text"].strip(), w["startMs"] / 1000) for w in words]
    # transcription bloc par bloc de controle.py, si elle est à jour : mots normalisés (sans accent ni apostrophe)
    tr = ANALYSE / "transcriptions" / cfg["transcription"]
    bf = tr.with_name(tr.stem + ".blocs.json")
    blocs = [(w, s) for w, s, _ in read_json(bf)] if bf.exists() and bf.stat().st_mtime >= tr.stat().st_mtime else []
    fix = cfg["sous_titres"].get("fix", {})
    onsets_file = cfg["dir"] / "debuts_voix.txt"
    onsets = sorted(float(x) for x in onsets_file.read_text().split()) if onsets_file.exists() else []

    def find(t0, spoken):
        target = [norm(w) for w in spoken.split() if norm(w)]
        best = None
        for i, (tok, _, t) in enumerate(toks):
            if abs(t - t0) > 8 or tok != target[0]:
                continue
            score = sum(1 for k, w in enumerate(target) if i + k < len(toks) and toks[i + k][0] == w)
            if best is None or score > best[0] or (score == best[0] and abs(t - t0) < abs(toks[best[1]][2] - t0)):
                best = (score, i)
        if best is None or best[0] < len(target) - 1:
            raise SystemExit(f"introuvable vers {t0}s : {spoken} (score {best and best[0]}/{len(target)})")
        i = best[1]
        seq = toks[i:i + len(target)]
        nxt = toks[i + len(target)][2] if i + len(target) < len(toks) else seq[-1][2] + 1
        if blocs:  # horaires de la transcription bloc par bloc (controle.py) : celle d'un seul tenant dérive
            new = [(tok, txt, recale_mot(tok, t)) for tok, txt, t in seq]
            shift = new[-1][2] - seq[-1][2]
            seq, nxt = new, nxt + shift
        return [(fix.get(tok, txt), t - DTW_LAG) for tok, txt, t in seq], nxt - DTW_LAG

    def recale_mot(tok, t):
        k = tok.replace("'", "")
        near = [bt for bw, bt in blocs if bw == k and abs(bt - t) < 3]
        return min(near, key=lambda bt: abs(bt - t)) if near else t

    def snap(t):
        k = bisect.bisect_left(onsets, t + SNAP[0])
        near = [o for o in onsets[k:k + 6] if t + SNAP[0] <= o <= t + SNAP[1]]
        return min(near, key=lambda o: abs(o - t)) if near else t

    out = []
    for n, (t0, spoken, *shown) in enumerate(cfg["sous_titres"]["phrases"], 1):
        ws, nxt = find(t0, spoken)
        if shown:  # mots retirés (la transcription en avait inventé) : on garde les temps des autres
            keep = [norm(w) for w in shown[0].split()]
            ws = [w for w in ws if norm(w[0]) in keep]
        start = snap(ws[0][1])
        shift = start - ws[0][1]
        end = min(ws[-1][1] + shift + 0.9, nxt + shift + 0.3)
        text = [w.rstrip(".") for w, _ in ws]
        text[-1] = text[-1].rstrip(",")
        text[0] = text[0][:1].upper() + text[0][1:]
        out.append({"id": f"st{n:02d}-sous-titre", "type": "soustitre", "at": round(start, 3), "dur": round(end - start, 3),
                    "vars": {"mots": [{"text": w, "t": round(t + shift - start, 3)} for w, (_, t) in zip(text, ws)]}})
    for x, y in zip(out, out[1:]):
        x["dur"] = round(min(x["dur"], y["at"] - x["at"] - 0.02), 3)
    plan = read_json(cfg["dir"] / "plan.json", {"elements": []})
    busy = [(e["at"], e["at"] + e["dur"]) for e in plan["elements"] if e["type"].startswith(BUSY)]
    kept = []
    for c in out:
        a, b = c["at"], c["at"] + c["dur"]
        said = " ".join(w["text"] for w in c["vars"]["mots"])
        if any(s - 0.1 <= a < e for s, e in busy):
            print(f"  retiré (bas de l'écran occupé) : {said}")
            continue
        for s, _ in busy:
            if a < s < b:
                b = s - 0.05
        if b - a < max(w["t"] for w in c["vars"]["mots"]) + 0.3:
            print(f"  retiré (coupé avant la fin) : {said}")
            continue
        c["dur"] = round(b - a, 3)
        kept.append(c)
        print(f"{c['at']:7.2f} +{c['dur']:.2f}  {said}")
    write_json(cfg["dir"] / "captions.json", {"elements": kept})
    print(len(kept), "sous-titres →", cfg["dir"] / "captions.json")


if __name__ == "__main__":
    main(sys.argv[1])
