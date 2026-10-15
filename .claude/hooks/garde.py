#!/usr/bin/env python3
"""garde.py - PreToolUse hook (Write, Edit): stops Claude from creating a file where the repo rules forbid it.

Reads the hook JSON on stdin. Outside the repo (scratchpad, ~/.claude…): lets it through. Inside:
- never by hand, even an existing file: compositions/*.html (make_compositions.py), montage/06_CAPCUT/ (CapCut
  loses the link), secrets/ (secrets_vault.py), .git/;
- a new file: refused if rangement.py says it is in the wrong place, must never go to git, or has a version name;
- any write: refused if its text breaks the writing rules (rangement.py E: replaced rule kept, control character,
  and for a whole file its size budget).
Exit 2 = refused, the reason goes back to Claude on stderr. The rules themselves live in rangement.py.
"""
import json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import rangement  # noqa: E402


def verdict(data, repo=REPO):
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return None
    p = Path(os.path.abspath(path))
    try:
        rel = p.relative_to(Path(os.path.abspath(repo))).as_posix()
    except ValueError:
        return None
    why = rangement.a_la_main_jamais(rel)
    if why:
        return why
    if not p.exists():
        why = rangement.interdit_dans_git(rel) or rangement.emplacement(rel) or rangement.forme(rel)
        if why:
            return (f"{why}\nRègles : CLAUDE.md (Où va quoi) et rangement.py. Un brouillon jetable va dans le scratchpad "
                    "de la session, jamais dans le dépôt.")
    ti = data.get("tool_input") or {}
    entier = "content" in ti                         # Write : tout le fichier ; Edit : seulement le morceau qui change
    texte = ti.get("content") if entier else ti.get("new_string")
    if not texte:
        return None
    why = [x for x in rangement.ecriture(rel, texte) if entier or not ("budget" in x or "description de" in x)]
    if why:
        return "\n".join(why) + "\nConventions : CLAUDE.md (Conventions obligatoires) et rangement.py (E)."
    return None


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        return
    why = verdict(data)
    if why:
        sys.stderr.buffer.write(f"Refusé par la garde de rangement : {why}\n".encode("utf-8"))
        sys.exit(2)


if __name__ == "__main__":
    main()
