#!/usr/bin/env python3
"""envoi.py - send this PC's work to the other one: add, commit, pull, push, in one go.

    python envoi.py                       # message: "Envoi du <date> depuis <PC>"
    python envoi.py "pokemon-ia : script"

What envoi.bat does on a double-click. Refuses, before committing anything, what must never go to git
(rangement.py: video files, files over 50 MB, secrets in clear, caches, temporary and system files); a file in
the wrong place or with a version name is sent, with a warning (`repo.py etat` and the CI recall it).
If the other PC pushed in the meantime, its work is merged first (git pull, merge commit); a real
conflict stops here and says which files, without losing anything.

Works on the repo it sits in (or $CLAUDE_REPO, for the tests).
"""
import os, platform, subprocess, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rangement  # noqa: E402

REPO = Path(os.environ.get("CLAUDE_REPO") or Path(__file__).resolve().parent)


def git(*args, check=True):
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        sys.exit(f"git {args[0]} a échoué :\n{(p.stderr or p.stdout).strip()}")
    return p


def too_heavy(names):
    """What must never go to git (refused), and what breaks the tidying rules (sent, with a warning)."""
    bad, warn = [], []
    for n in names:
        f = REPO / n
        if not f.is_file():
            continue                     # suppression : toujours permise
        why = rangement.interdit_dans_git(n, f.stat().st_size)
        if why:
            bad.append(why)
        else:
            w = rangement.emplacement(n) or rangement.forme(n)
            if w:
                warn.append(w)
    return bad, warn


def main():
    message = " ".join(sys.argv[1:]).strip() or \
        f"Envoi du {datetime.now():%Y-%m-%d %H:%M} depuis {platform.node() or 'ce PC'}"
    git("add", "-A")
    staged = [n for n in git("diff", "--cached", "--name-only", "-z").stdout.split("\0") if n]
    bad, warn = too_heavy(staged)
    if bad:
        git("reset", "-q")
        sys.exit("Rien n'est envoyé : ces fichiers ne doivent pas aller dans git.\n  - " + "\n  - ".join(bad)
                 + "\nDéplace-les hors du dépôt (ou ajoute-les à .gitignore), puis relance.")
    if warn:
        print("à ranger (envoyé quand même ; règles de rangement.py) :\n  - " + "\n  - ".join(warn))
    if staged:
        git("commit", "-q", "-m", message)
        print(f"{len(staged)} fichier(s) commité(s) : {message}")
    else:
        print("aucun changement local à commiter")

    has_upstream = git("rev-parse", "--abbrev-ref", "@{u}", check=False).returncode == 0
    if has_upstream:
        pulled = git("pull", "--no-rebase", "--no-edit", check=False)
        if pulled.returncode != 0:
            conflicts = git("diff", "--name-only", "--diff-filter=U", check=False).stdout.split()
            if conflicts:
                sys.exit("Conflit avec le travail de l'autre PC sur : " + ", ".join(conflicts)
                         + "\nRien n'est perdu. Ouvre Claude Code dans ce dossier et demande « résous le conflit git ».")
            sys.exit(f"git pull a échoué :\n{(pulled.stderr or pulled.stdout).strip()}")
        git("push", "-q")
    else:
        git("push", "-q", "-u", "origin", "HEAD")
    print("envoyé : l'autre PC le récupère avec maj.bat")


if __name__ == "__main__":
    main()
