"""Trouve où une phrase est dite dans la timeline (transcription mot à mot) → début et fin approximatifs.
usage : python scripts/phrases.py <id> "seconde|phrase" ["seconde|phrase" …]
Sortie : début du premier mot, début du mot suivant la phrase (fin max), et le texte entendu."""
import sys
from commun import ANALYSE, read_json, remap, video
from sous_titres import norm

DTW_LAG = 0.12


def locate(toks, t0, spoken):
    target = [norm(w) for w in spoken.split() if norm(w)]
    best = None
    for i, (tok, _, t) in enumerate(toks):
        if abs(t - t0) > 10 or tok != target[0]:
            continue
        score = sum(1 for k, w in enumerate(target) if i + k < len(toks) and toks[i + k][0] == w)
        if best is None or score > best[0] or (score == best[0] and abs(t - t0) < abs(toks[best[1]][2] - t0)):
            best = (score, i)
    if best is None:
        return None
    i = best[1]
    seq = toks[i:i + len(target)]
    nxt = toks[i + len(target)][2] if i + len(target) < len(toks) else seq[-1][2] + 1.5
    return seq[0][2] - DTW_LAG, nxt - DTW_LAG, " ".join(s[1] for s in seq), best[0], len(target)


if __name__ == "__main__":
    cfg = video(sys.argv[1])
    words = read_json(ANALYSE / "transcriptions" / cfg["transcription"])
    toks = [(norm(w["text"]), w["text"].strip(), w["startMs"] / 1000) for w in words]
    cuts = cfg.get("coupes", [])
    for arg in sys.argv[2:]:
        t0, phrase = arg.split("|", 1)
        r = locate(toks, float(t0), phrase)
        if not r:
            print(f"INTROUVABLE {t0} {phrase}")
            continue
        a, b, heard, sc, n = r
        print(f"{remap(a, cuts):8.3f} {remap(b, cuts):8.3f}  ({sc}/{n})  {heard}")
