#!/usr/bin/env python3
r"""setup.py - set up this machine from the repo: skills + config + Python deps + API keys.

    git clone https://github.com/52mazzz/workflow-youtube-claude-code && cd workflow-youtube-claude-code && python setup.py --ici

    python setup.py --pull            # git pull, then relink (what maj.bat does); no pip, no passphrase
    python setup.py --skip-deps       # do not pip install anything
    python setup.py --vision          # also the thumbnail analysis (OpenCV, and CLIP: PyTorch CPU, ~1 GB with the model)
    python setup.py --skip-secrets    # do not ask for the vault passphrase
    python setup.py --copy            # copy instead of linking (old behaviour, see below)
    python setup.py --adopt montage-capcut derush-capcut
                                      # bring skills that exist only on this machine into the repo
    python setup.py --save            # copy mode only: send this machine's ~/.claude/youtube/ back

WHERE. On every PC the repo lives in Documents\TSAR\Claude workflow youtube (the real Documents folder,
even when Windows moved it into OneDrive). setup.py refuses to run from anywhere else, so that the
links in ~/.claude never point to an old copy; --ici overrides that (tests, a deliberate choice).
Running it from the right folder re-points links that still lead to an old clone, and says so.

LINK MODE (default). The repo is the only copy. ~/.claude/skills/<skill>, ~/.claude/youtube and
~/.claude/montage are links to skills/<skill>, config/youtube and config/montage in this folder
(symlinks, or directory junctions on Windows, which need no admin rights). A preference written by
a skill, a new row in apprentissages.md, a new reference collection: all land in the repo directly,
`git pull` updates the machine without running setup.py again, and `git commit && git push` sends
the changes to the other PC. Nothing is ever edited "on the machine only".

The first time, what this machine already has in ~/.claude is merged into the repo before the link
replaces it: files the repo does not have are copied into it (to commit), apprentissages.md rows
are united (one row per video), and a file that differs from the repo keeps the repo's version
while the machine's copy is moved to ~/.claude/.sauvegarde-<date>/ and listed. Nothing is deleted.

--adopt NAME...: a skill that lives only in ~/.claude/skills/ on this machine is copied into
skills/NAME/ of the repo, then linked like the others. Commit and push, and the other PC has it.

If a link cannot be made, that folder falls back to a copy and setup.py says so. --copy forces the
old behaviour for everything: skills overwritten, config copied only when missing, --save to send
changes back.
"""
import filecmp, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = ("TSAR", "Claude workflow youtube")   # under Documents
REPO_URL = "https://github.com/52mazzz/workflow-youtube-claude-code.git"
CLAUDE = Path.home() / ".claude"
DEST = CLAUDE / "skills"
CONFIG = HERE / "config"
DEPS = ["cryptography", "google-api-python-client", "google-auth-oauthlib", "yt-dlp"]
# miniature.py: OpenCV for the image checks, CLIP (open_clip + PyTorch, CPU build) for the similarity
VISION = ["opencv-python-headless", "numpy", "pillow", "open_clip_torch"]
TORCH_CPU = ["torch", "--index-url", "https://download.pytorch.org/whl/cpu"]
MERGED = {"apprentissages.md"}   # one table row per video: rows are merged, never overwritten


# ---------------------------------------------------------------- where the repo must live

def documents():
    """The user's real Documents folder (Windows may have moved it, e.g. into OneDrive)."""
    if os.environ.get("CLAUDE_DOCUMENTS"):  # tests
        return Path(os.environ["CLAUDE_DOCUMENTS"])
    if os.name == "nt":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:  # CSIDL_PERSONAL
                return Path(buf.value)
        except (OSError, AttributeError):
            pass
    return Path.home() / "Documents"


def expected_dir():
    return documents().joinpath(*FOLDER)


def same_path(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def check_location():
    target = expected_dir()
    if same_path(HERE, target) or "--ici" in sys.argv:
        if "onedrive" in str(HERE).lower():
            print("note    ce dépôt est dans OneDrive : les gros dossiers ignorés par git (.whisper, 06_CAPCUT,\n"
                  "        musiques) seront aussi synchronisés par OneDrive. Les exclure de la synchro OneDrive.\n")
        return
    print(f"Ce dépôt est dans : {HERE}")
    print(f"Il doit être dans : {target}\n")
    if target.exists():
        print("Ce dossier existe déjà : travaille dedans (git pull puis python setup.py), et supprime cette\n"
              "copie-ci après avoir vérifié qu'elle n'a rien de non poussé (git status, git log origin/main..).")
    else:
        print("Pour l'installer au bon endroit (PowerShell) :")
        print(f'    mkdir "{target.parent}" -Force')
        print(f'    git clone {REPO_URL} "{target}"')
        print(f'    cd "{target}"')
        print("    python setup.py")
        print("\nPuis supprime cette copie-ci après avoir vérifié qu'elle n'a rien de non poussé (git status).")
    print("\n(--ici pour forcer l'installation depuis ce dossier)")
    sys.exit(1)


# ---------------------------------------------------------------- table rows

def row_key(line):
    """A table row is identified by its first two cells (date, title): an updated row replaces."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return tuple(cells[:2])


def merge_lines(first, second):
    """Lines of `first`, then the table rows of `second` whose video `first` does not have.
    `first` wins for a video present in both (it is the side being kept)."""
    a = first.splitlines()
    seen = {row_key(l) for l in a if l.startswith("|")}
    extra = [l for l in second.splitlines() if l.startswith("|") and row_key(l) not in seen]
    while a and not a[-1].strip():
        a.pop()
    return "\n".join(a + extra) + "\n"


# ---------------------------------------------------------------- links

def is_link(p):
    """Symlink or Windows junction (os.readlink reads both since Python 3.8)."""
    if p.is_symlink():
        return True
    try:
        os.readlink(p)
        return True
    except (OSError, ValueError, NotImplementedError):
        return False


def points_to(p, target):
    try:
        return Path(os.path.realpath(p)) == Path(os.path.realpath(target))
    except OSError:
        return False


def remove_link(p):
    # never rmtree a link: on old Pythons that would empty the repo folder it points to
    try:
        p.unlink()
    except (IsADirectoryError, PermissionError, OSError):
        os.rmdir(p)


def make_link(target, link):
    """Directory symlink, else (Windows without developer mode) a junction. True if made."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        try:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
            return True
        except (OSError, ImportError, AttributeError):
            pass
    return False


BACKUP = CLAUDE / f".sauvegarde-{datetime.now():%Y-%m-%d-%H%M%S}"


def backup_dir():
    return BACKUP


def absorb(local, target, label, report):
    """Before linking: bring what the machine has into the repo folder, without losing anything."""
    bak = None
    for src in sorted(p for p in local.rglob("*") if p.is_file()):
        rel = src.relative_to(local)
        if "__pycache__" in rel.parts:
            continue
        dest = target / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            report["added"].append(f"{label}/{rel.as_posix()}")
        elif rel.name in MERGED:
            merged = merge_lines(dest.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))
            if merged != dest.read_text(encoding="utf-8"):
                dest.write_text(merged, encoding="utf-8")
                report["merged"].append(f"{label}/{rel.as_posix()}")
        elif not filecmp.cmp(src, dest, shallow=False):
            bak = bak or backup_dir() / label
            (bak / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bak / rel)
            report["backed_up"].append(f"{label}/{rel.as_posix()}")
    return bak


def link_dir(target, link, label, report):
    """Make `link` point to `target` (a folder of the repo). Returns 'linked', 'ok' or 'copied'."""
    target.mkdir(parents=True, exist_ok=True)
    link.parent.mkdir(parents=True, exist_ok=True)
    if is_link(link):
        if points_to(link, target):
            return "ok"
        report.setdefault("repointed", []).append(f"{label} (pointait vers {os.path.realpath(link)})")
        remove_link(link)
    elif link.exists():
        absorb(link, target, label, report)
        shutil.rmtree(link)
    if make_link(target, link):
        return "linked"
    shutil.copytree(target, link, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    return "copied"


def orphan_links():
    """Links of ~/.claude/skills/ that led to a skill of this repo since deleted: removed (a dead link only lists a skill
    that no longer exists). Links to anything else, and real folders, are left alone."""
    removed = []
    for p in sorted(DEST.iterdir()) if DEST.exists() else []:
        if not is_link(p):
            continue
        try:
            target = os.readlink(p)
        except OSError:
            continue
        target = Path(target[4:] if target.startswith("\\\\?\\") else target)  # préfixe \\?\ des jonctions Windows
        if not target.exists() and same_path(target.parent, HERE / "skills"):
            remove_link(p)
            removed.append(p.name)
    return removed


def install_links():
    report = {"added": [], "merged": [], "backed_up": []}
    copied = []
    DEST.mkdir(parents=True, exist_ok=True)
    for skill in sorted(p for p in (HERE / "skills").iterdir() if p.is_dir()):
        state = link_dir(skill, DEST / skill.name, f"skills/{skill.name}", report)
        print(f"skill   {skill.name} ({state})")
        if state == "copied":
            copied.append(skill.name)
    gone = orphan_links()
    if gone:
        print("liens retirés (skill supprimé du dépôt) : " + ", ".join(gone))
    for sub in sorted(p for p in CONFIG.iterdir() if p.is_dir()) if CONFIG.exists() else []:
        state = link_dir(sub, CLAUDE / sub.name, f"config/{sub.name}", report)
        print(f"config  {sub.name} -> ~/.claude/{sub.name} ({state})")
        if state == "copied":
            copied.append(f"config/{sub.name}")
    if report.get("repointed"):
        print("\nliens qui menaient à une ancienne copie, maintenant vers ce dépôt :\n  " + "\n  ".join(report["repointed"]))
    if report["added"]:
        print("\nadded to the repo from this machine (to commit):\n  " + "\n  ".join(report["added"]))
    if report["merged"]:
        print("\nmerged into the repo (to commit):\n  " + "\n  ".join(report["merged"]))
    if report["backed_up"]:
        print(f"\nthe repo's version was kept; this machine's version is in {CLAUDE}/.sauvegarde-*/ :\n  "
              + "\n  ".join(report["backed_up"]))
    if copied:
        print("\nno link possible for: " + ", ".join(copied) + " (copied instead; enable Windows developer"
              " mode or run as admin, then run setup.py again)")
    if report["added"] or report["merged"]:
        print("\nNow: git add -A && git commit -m \"Bring machine config into the repo\" && git push")


# ---------------------------------------------------------------- copy mode (old behaviour)

def install_copies():
    DEST.mkdir(parents=True, exist_ok=True)
    for skill in sorted((HERE / "skills").iterdir()):
        if skill.is_dir():
            if is_link(DEST / skill.name):
                remove_link(DEST / skill.name)
            shutil.copytree(skill, DEST / skill.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            print(f"skill   {skill.name}")
    if not CONFIG.exists():
        return
    differs = []
    for src in sorted(p for p in CONFIG.rglob("*") if p.is_file()):
        rel = src.relative_to(CONFIG)
        target = CLAUDE / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            print(f"config  {rel.as_posix()}")
        elif rel.name in MERGED:
            merged = merge_lines(target.read_text(encoding="utf-8"), src.read_text(encoding="utf-8"))
            if merged != target.read_text(encoding="utf-8"):
                target.write_text(merged, encoding="utf-8")
                print(f"config  {rel.as_posix()} (merged with the repo)")
        elif not filecmp.cmp(src, target, shallow=False):
            differs.append(rel.as_posix())
    if differs:
        print("config  kept this machine's version of: " + ", ".join(differs))
        print("        (run `python setup.py --save` to send it to the repo, or delete it here to take the repo's)")


def save_config():
    changed = []
    for sub in sorted(p for p in CONFIG.iterdir() if p.is_dir()) if CONFIG.exists() else []:
        src_root = CLAUDE / sub.name
        if not src_root.exists() or is_link(src_root):
            continue   # linked: the repo already is the machine's copy
        for src in sorted(p for p in src_root.rglob("*") if p.is_file()):
            rel = src.relative_to(CLAUDE)
            if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
                continue
            dest = CONFIG / rel
            if rel.name in MERGED and dest.exists():
                merged = merge_lines(src.read_text(encoding="utf-8"), dest.read_text(encoding="utf-8"))
                if merged != dest.read_text(encoding="utf-8"):
                    dest.write_text(merged, encoding="utf-8")
                    changed.append(rel.as_posix())
                continue
            if dest.exists() and filecmp.cmp(src, dest, shallow=False):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            changed.append(rel.as_posix())
    if changed:
        print("saved   " + "\n        ".join(changed))
        print("\nNow: git add config && git commit -m \"Save YouTube config\" && git push")
    else:
        print("saved   nothing new (in link mode there is nothing to save: the repo is the machine's copy)")


def adopt(names):
    for name in names:
        local, target = DEST / name, HERE / "skills" / name
        if is_link(local) and points_to(local, target):
            print(f"skill   {name} is already in the repo")
            continue
        if not (local / "SKILL.md").exists():
            print(f"skill   {name}: no SKILL.md in {local}, skipped")
            continue
        report = {"added": [], "merged": [], "backed_up": []}
        state = link_dir(target, local, f"skills/{name}", report)
        print(f"skill   {name}: {len(report['added'])} file(s) copied into the repo ({state})")
        for f in report["backed_up"]:
            print(f"        kept the repo's {f}, this machine's copy is in {BACKUP}")
    print("\nNow: git add skills && git commit -m \"Add skills from this machine\" && git push")


def pull():
    r = subprocess.run(["git", "-C", str(HERE), "pull", "--ff-only"], capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode != 0:
        sys.exit("git pull a échoué (changements locaux non commités ?) : rien n'a été relié.")


def main():
    if "--save" not in sys.argv:
        check_location()
    if "--pull" in sys.argv:
        pull()
        install_links()
        return
    if "--save" in sys.argv:
        save_config()
        return
    if "--adopt" in sys.argv:
        names = [x for x in sys.argv[sys.argv.index("--adopt") + 1:] if not x.startswith("--")]
        if not names:
            sys.exit("usage: python setup.py --adopt SKILL [SKILL...]")
        adopt(names)
        return
    if "--copy" in sys.argv:
        install_copies()
    else:
        install_links()

    if "--skip-deps" not in sys.argv:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *DEPS])
        if "--vision" in sys.argv:
            # PyTorch first, from the CPU index: the default build pulls ~2 GB of GPU libraries for nothing
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *TORCH_CPU])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *VISION])
        print("deps    ok")

    if "--skip-secrets" not in sys.argv and any((HERE / "secrets").glob("*.enc")):
        code = subprocess.call([sys.executable, str(HERE / "secrets_vault.py"), "decrypt"])
        if code != 0:
            print("Installation incomplète : le coffre n'a pas pu être déchiffré.\n"
                  "Les liens et dépendances déjà installés sont conservés. Relance "
                  "`python secrets_vault.py decrypt` dans ton terminal, puis vérifie "
                  "`python secrets_vault.py status`.", file=sys.stderr)
            sys.exit(code)


if __name__ == "__main__":
    main()
