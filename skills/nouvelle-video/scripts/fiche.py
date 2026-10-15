#!/usr/bin/env python3
"""fiche.py - the shooting sheet of a video, to keep on the phone while filming (GitHub app, or a copy).

    python fiche.py <id>            # writes videos/<id>/fiche-tournage.md and prints its path
    python fiche.py <id> --stdout   # prints it instead

Built only from what is already written, nothing is invented: from videos/<id>/script.md, the beats
in order with the framing sentences to say (the "> « … »" lines) and the exact prompt (code block; when
no beat holds one, the code blocks of the "## … prompt …" section, placed before the beats);
the "Notes de tournage" as boxes to tick; from resultats.md (if present), the "Avant de tourner"
checklist. The [ON SCREEN : …] notes are for the edit, not for the shoot: left out. [CROCHETS] stay
as they are: they are what the shoot decides.

Regenerate it after any change to script.md (it is overwritten).
"""
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repo  # noqa: E402


def sections(text):
    """[(title, body)] for every '## ' section."""
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts), 2)]


def strip_onscreen(line):
    """Remove every [ON SCREEN …] note, brackets inside it included ([DURÉE] in a caption)."""
    out, i = "", 0
    while True:
        j = line.find("[ON SCREEN", i)
        if j < 0:
            return re.sub(r"\s+([.,])", r"\1", re.sub(r"\s{2,}", " ", out + line[i:])).strip()
        out, depth, k = out + line[i:j], 0, j
        while k < len(line):
            depth += {"[": 1, "]": -1}.get(line[k], 0)
            k += 1
            if depth == 0:
                break
        i = k


def beat_lines(body):
    out, in_code, code = [], False, []
    for line in body.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                out.append("Prompt à coller (mot pour mot) :")
                out.append("```text\n" + "\n".join(code).strip() + "\n```")
                code = []
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
        elif line.startswith(">"):
            out.append("- [ ] " + line.lstrip("> ").strip())
        elif line.startswith("- **") or line.startswith("**"):   # steps of a beat, alternative cases
            text = strip_onscreen(line[2:] if line.startswith("- ") else line)
            if text:
                out.append("  - " + text if line.startswith("- ") else "\n" + text + "\n")
    return out


def prompt_lines(body):
    """Every code block of a « ## … prompt … » section, each under the line that introduces it (« Message 1 … : »)."""
    out, in_code, code, label = [], False, [], None
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("```"):
            if in_code:
                out += [label or "Prompt à coller (mot pour mot) :", "```text\n" + "\n".join(code).strip() + "\n```", ""]
                code, label = [], None
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
        elif s:
            label = s if s.endswith(":") else None
    return out


def build(d):
    script = (d / "script.md").read_text(encoding="utf-8")
    m = re.search(r"^# (.+)$", script, re.M)
    title = m.group(1).replace("Script : ", "") if m else d.name
    out = [f"# Fiche de tournage : {title}", "",
           f"Id `{d.name}`. Générée depuis `script.md` (à refaire après toute modification du script : "
           f"`fiche.py {d.name}`). Coche au fur et à mesure ; ce qui est entre [crochets] se décide au tournage.", ""]
    res = d / "resultats.md"
    if res.exists():
        avant = next((b for t, b in sections(res.read_text(encoding="utf-8")) if t.startswith("Avant de tourner")), "")
        boxes = [l for l in avant.splitlines() if l.strip().startswith("- [")]
        if boxes:
            out += ["## Avant de lancer OBS", "", *boxes, ""]
    beats = [(t, b) for t, b in sections(script) if t.lower().startswith("beat")]
    if not beats:
        sys.exit(f"aucun « ## Beat … » dans {d / 'script.md'}")
    if not any("```" in b for _, b in beats):   # prompt written in its own section, the beats only point to it
        for t, b in sections(script):
            if "prompt" in t.lower() and "```" in b:
                out += [f"## {t}", "", *prompt_lines(b)]
    out += ["## Les beats, dans l'ordre", ""]
    for t, b in beats:
        out += [f"### {t}", "", *(beat_lines(b) or ["- [ ] (réactions en direct, rien d'écrit)"]), ""]
    notes = next((b for t, b in sections(script) if t.lower().startswith("notes de tournage")), "")
    tips = [re.sub(r"^\s*-\s*", "- [ ] ", l) for l in notes.splitlines() if l.strip().startswith("- ")]
    if tips:
        out += ["## Pendant et après le tournage", "", *tips, ""]
    out += ["## Juste après", "",
            "- [ ] Remplir `resultats.md` (vainqueur, versions exactes, heures de début et de fin, nombre de rushs, bugs, captures)",
            "- [ ] Copier tous les rushs sur le portable dans `Documents/TSAR/Videos/<Nom de la vidéo>/Rush`, sans les renommer ; vérifier nombre et taille des deux côtés",
            "- [ ] `envoi.bat` sur ce PC si `resultats.md` y a été rempli", ""]
    return "\n".join(out)


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__); sys.exit(1)
    d = repo.root() / "videos" / a[0]
    if not (d / "script.md").exists():
        sys.exit(f"pas de script : {d / 'script.md'} (vérifie l'id avec repo.py list)")
    text = build(d)
    if "--stdout" in a:
        print(text)
    else:
        (d / "fiche-tournage.md").write_text(text, encoding="utf-8")
        print(d / "fiche-tournage.md")


if __name__ == "__main__":
    main()
