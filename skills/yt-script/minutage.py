#!/usr/bin/env python3
"""minutage.py - does each sentence of a script fit in its time slot, at a natural reading pace?

    python minutage.py script.md                 # 3.33 words per second (200 per minute: the channel's measured pace,
                                                 # pokemon-ia 201, shaders 237, niche median 198 ; was 2.5 until 2026-10-07)
    python minutage.py script.md --debit 2.8     # a faster voice (measure yours: read the opening aloud, count)
    python minutage.py script.md --json

Two kinds of slots are read from script.md:
  - timed lines of the opening: "- **0-3 s** ... : « sentence »" (one line per slot; a "**Version X**"
    line starts a new version);
  - beats: "## Beat 2. ... (0:15 à 0:40)", with every "> « sentence »" framing line and every "- … : « … »"
    bullet under it (Claude, ChatGPT, the point); a "**Cas …**" line starts the alternatives, not counted;
  - rows of a Short's timed table: "| 0-3 s | « sentence » | image |" (the « » of the row are said).
Words are counted inside « » only (what is said). A [PLACEHOLDER] counts as the number it announces
("[CONTRASTE : 7 mots au plus]" = 7 words), else as 0 with a warning: write the budget in the
placeholder so the shoot knows how long the real sentence may be (warned for the opening only). A beat whose sentences are mostly
placeholders filled live is only checked on what is written.

Exit code 1 when a slot is too short for what is written ("dépasse"), 0 otherwise. A pass is not a
timing: read the whole opening aloud once with a stopwatch before recording.
"""
import json, re, sys
from pathlib import Path

SLOT = re.compile(r"^\s*-\s*\*\*(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*s\*\*(.*)$")
ROW = re.compile(r"^\s*\|\s*(\d+(?:[.,]\d+)?)\s*(?:-|–|à)\s*(\d+(?:[.,]\d+)?)\s*s\s*\|(.*)$")
BEAT = re.compile(r"^##\s+(Beat[^()]*?)\s*\((\d+):(\d{2})\s*(?:à|-|–)\s*(\d+):(\d{2})\)")
QUOTE = re.compile(r"«\s*(.*?)\s*»", re.S)
PLACE = re.compile(r"\[([^\[\]]*)\]")


def count(text):
    """(words, warnings): words said, placeholders counted at their announced budget."""
    warn, extra = [], 0
    for p in PLACE.findall(text):
        m = re.search(r"(\d+)\s*mots", p)
        if m:
            extra += int(m.group(1))
        else:
            warn.append(f"[{p[:40]}] sans budget de mots")
    plain = PLACE.sub(" ", text)
    return len(re.findall(r"[\w’'-]+", plain)) + extra, warn


def said(line):
    """The spoken text of a line: the « » quotes, ON SCREEN notes left out."""
    line = re.sub(r"\[ON SCREEN[^\]]*(\[[^\]]*\][^\]]*)*\]", " ", line)
    return " ".join(QUOTE.findall(line))


RATE = 200 / 60


def analyse(text, rate=RATE):
    slots, version, beat = [], None, None
    for line in text.splitlines():
        if re.match(r"^\*\*Version\s+([^\s*]+)", line):
            version = re.match(r"^\*\*Version\s+([^\s*]+)", line).group(1)
            continue
        m = BEAT.match(line)
        if m:
            a, b = int(m.group(2)) * 60 + int(m.group(3)), int(m.group(4)) * 60 + int(m.group(5))
            beat = {"nom": m.group(1).strip(), "debut": a, "fin": b, "texte": []}
            slots.append(beat)
            version = None
            continue
        if line.startswith("## "):
            beat = None
        row = ROW.match(line)
        if row:
            version = None
        s = SLOT.match(line) or row
        if s:
            a, b = float(s.group(1).replace(",", ".")), float(s.group(2).replace(",", "."))
            label = "déroulé " if row else f"version {version} " if version else ""
            slots.append({"nom": f"{label}{s.group(1)}-{s.group(2)} s",
                          "debut": a, "fin": b, "texte": [said(s.group(3))], "ouverture": True})
            continue
        if beat is None:
            continue
        # « **Cas « aucun des deux ne marche »** » : an alternative to what is above, said instead of it, not after it
        if re.match(r"^\s*\*\*Cas\b", line):
            beat["variante"] = True
        if not beat.get("variante") and (line.startswith(">") or re.match(r"^\s*-\s", line)):
            beat["texte"].append(said(line))
    out = []
    for s in slots:
        txt = " ".join(t for t in s["texte"] if t).strip()
        if not txt:
            continue
        words, warn = count(txt)
        dur = s["fin"] - s["debut"]
        need = round(words / rate, 1)
        out.append({"creneau": s["nom"], "duree_s": dur, "mots": words, "besoin_s": need,
                    "verdict": "dépasse" if need > dur + 0.05 else "serré" if need > dur * 0.9 else "ok",
                    "mots_max": int(dur * rate), "alertes": warn if s.get("ouverture") else [], "texte": txt})
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    files = [x for x in a if not x.startswith("--") and (a.index(x) == 0 or a[a.index(x) - 1] != "--debit")]
    if not files or not Path(files[0]).exists():
        print(__doc__); sys.exit(1)
    rate = float(a[a.index("--debit") + 1]) if "--debit" in a else RATE
    res = analyse(Path(files[0]).read_text(encoding="utf-8-sig"), rate)
    if not res:
        error = "contrôle impossible : aucun créneau de parole reconnu ; utiliser les lignes minutées ou les Beats documentés"
        print(json.dumps({"error": error}, ensure_ascii=False) if "--json" in a else error)
        sys.exit(1)
    if "--json" in a:
        print(json.dumps(res, indent=1, ensure_ascii=False))
    else:
        print(f"\n  Débit : {rate:g} mots par seconde ({rate * 60:.0f} par minute)\n")
        for r in res:
            mark = {"ok": "  ", "serré": "~ ", "dépasse": "X "}[r["verdict"]]
            print(f"  {mark}{r['creneau']:<34} {r['mots']:>3} mots -> {r['besoin_s']:>5} s pour {r['duree_s']:g} s "
                  f"(au plus {r['mots_max']} mots) : {r['verdict']}")
            for w in r["alertes"]:
                print(f"       {w}")
        print("\n  À faire ensuite : lire l'ouverture à voix haute, chronomètre en main.\n")
    sys.exit(1 if any(r["verdict"] == "dépasse" for r in res) else 0)


if __name__ == "__main__":
    main()
