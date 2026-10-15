#!/usr/bin/env python3
"""rangement.py - the tidying rules of the repo, in one place, and the check that applies them.

    python rangement.py                      # report: what breaks the rules, caches to empty, what waits for your go
    python rangement.py --vider              # empties the caches that are safe to lose (regenerated on demand)
    python rangement.py --supprimer <chemin>...  # deletes only paths the report proposes ("après accord")
    python rangement.py --git                # checks what git holds or would send (CI); code 1 on any breach

The rules (constants below) are the source; CLAUDE.md only points here. They are applied in four places:
`repo.py etat` at the start of every session (empties the safe caches, then reports), `envoi.py` (refuses what
must never go to git, warns about the rest), the hook .claude/hooks/garde.py (stops Claude from creating a file in
the wrong place) and the CI test tests/test_rangement.py (what git holds follows the rules).

Automatic emptying only ever deletes files git does not track: nothing the other PC could conflict with. A tracked
file is only proposed; it is deleted after the user agrees, once `repo.py etat` says the other PC sent nothing.

Works on the repo it sits in (or $CLAUDE_REPO, for the tests).
"""
import hashlib, os, re, shutil, subprocess, sys, time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
MO = 1024 * 1024

# ── A. where things go (whitelist)
RACINE_FICHIERS = {"CLAUDE.md", "README.md", "INSTALLATION_CLAUDE.md", "MODELES.md", ".gitignore", ".gitattributes",
                   "envoi.bat", "envoi.py", "maj.bat", "setup.py", "secrets_vault.py", "trouver_python.bat",
                   "rangement.py", "atelier.bat", "atelier.py", "atelier.html", "LICENSE", "CREDITS.md"}
RACINE_DOSSIERS = {".claude", ".github", "config", "montage", "secrets", "skills", "tests", "videos",
                   ".git", ".tmp"}  # .tmp : ancien emplacement local du jeton OAuth (secrets_vault.py), ignoré
CONFIG = {"youtube", "agents"}
MONTAGE = {"02_ANALYSE", "04_RESSOURCES", "06_CAPCUT", "07_OUTILS", "08_HYPERFRAMES", "README.md", "WORKFLOW.md",
           "sync_ressources.ps1", "01_RUSHS", "05_EXPORTS", "99_ARCHIVE", "_sauvegardes_claude"}
RESSOURCES = {"LICENCES.md", "assets", "musiques", "sfx", "images"}
HYPERFRAMES = {"AGENTS.md", "CLAUDE.md", "hyperframes.json", "index.html", "meta.json", "package.json",
               "package-lock.json", "scripts", "kit", "assets", "compositions", "videos", "shorts",
               "build", "renders", "node_modules", ".whisper", ".hyperframes"}
ANALYSE_DOSSIERS = {"prises", "transcriptions", "audio_16k"}
ANALYSE_COMMUNS = {"fond_sonore.json", "luminance_rushs.json"}
ANALYSE_PAR_VIDEO = re.compile(r"(?:derush|vue|controle_export|controle|capcut|dosage|revue|synchro|ennui)_(.+)")
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){1,2}")
VEILLE = re.compile(r"veille-(\d{4}-\d{2}-\d{2})")
VIDEO_SOUS_DOSSIERS = {"bilans", "miniatures", "veille", "miniatures-refs"}
TEXTE = (".md", ".json", ".txt")
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
# jamais écrits à la main (hook) : générés par make_compositions.py, ou liés à CapCut, ou chiffrés
A_LA_MAIN_JAMAIS = (re.compile(r"montage/08_HYPERFRAMES/compositions/[^/]+\.html"), re.compile(r"montage/06_CAPCUT/"),
                    re.compile(r"secrets/"), re.compile(r"\.git/"))

# ── B. never in git
VIDEO_EXT = (".mkv", ".mp4", ".mov")
MAX_MB = 50
CACHES = {"__pycache__", "node_modules", ".whisper", ".hyperframes", "build", "renders"}
TEMPORAIRES = (".pyc", ".tmp", ".bak", ".log", ".orig")
SYSTEME = {"thumbs.db", "desktop.ini", ".ds_store"}
SECRETS = re.compile(r"(client_secret.*\.json|.*token.*\.json|.*credentials.*\.json|\.env|.*\.pem|.*\.key)$", re.I)
SFX = ("montage/04_RESSOURCES/sfx/", "montage/08_HYPERFRAMES/assets/sfx/")

# ── C. shape of names (videos/ config/ skills/ tests/ ; 02_ANALYSE and 04_RESSOURCES keep the rush and CapCut names)
FORME_DOSSIERS = ("videos/", "config/", "skills/", "tests/")
NOM = re.compile(r"[a-z0-9][a-z0-9._-]*")
NOMS_LIBRES = {"SKILL.md", "README.md", "CLAUDE.md", "AGENTS.md"}
SANS_REGLE_DE_NOM = ("/bilans/", "/veille/", "/miniatures-refs/", "/.obsidian/")  # noms donnés par les scripts, ou ignorés
VERSION = re.compile(r"(?:^|[-_. ])(?:v\d+|copie|copy|old|backup|bak|tmp|temp|brouillon|draft|final[-_ ]?final)"
                     r"(?=$|[-_. ])|\(\d+\)", re.I)

# ── D. lifetime of caches
RUSH_AUDIO_JOURS = 14          # audio_16k/rush_*.wav re-extrait à la demande (commun.py)
VEILLE_JOURS = 3               # videos/veille-* : renommée en videos/<id>/ à la fin de la phase 5
OUBLI_JOURS = 7                # fichier ni suivi ni ignoré : brouillon oublié dans le dépôt
SAUVEGARDES_JOURS = 30         # montage/_sauvegardes_claude/
JAMAIS = ("montage/06_CAPCUT/", "montage/01_RUSHS/", "secrets/", "montage/08_HYPERFRAMES/.whisper/",
          "montage/08_HYPERFRAMES/node_modules/", "montage/08_HYPERFRAMES/compositions/")

# ── E. writing rules of the docs Claude reads (each one costs tokens every time it is loaded)
# One rule lives in one place, elsewhere a pointer ; a replaced rule is deleted (git keeps the history), never kept
# struck through or marked « ancien » ; every doc has a size budget.
DOCS = re.compile(r"CLAUDE\.md|README\.md|INSTALLATION_CLAUDE\.md|montage/[^/]+\.md|montage/08_HYPERFRAMES/CLAUDE\.md"
                  r"|config/youtube/[^/]+\.md|config/agents/[^/]+\.md"
                  r"|skills/(?!youtube/|baoyu-youtube-transcript/)[^/]+/(?:SKILL\.md|references/[^/]+\.md)")
PERIME = re.compile(r"~~[^~\n]+~~|\(\s*ancien(?:ne)?\s*[,)]|\(avant le \d|remplacé par la règle ci-dessus", re.I)
CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
BUDGETS = ((re.compile(r"CLAUDE\.md"), 6000), (re.compile(r".+/CLAUDE\.md"), 3000),
           (re.compile(r"skills/.+/SKILL\.md"), 26000), (re.compile(r".+\.md"), 40000))   # caractères (≈ 4 par token)
DESCRIPTION_MAX = 1024     # description d'un skill, chargée à chaque session
DOUBLON_MIN = 160          # une ligne de règle de cette longueur ne se recopie pas d'un fichier à l'autre


def repo_root():
    return Path(os.environ.get("CLAUDE_REPO") or HERE)


# ───────────── rules on one path (relative, with /)
def emplacement(rel):
    """None when the path is where CLAUDE.md wants it, else why not."""
    p = rel.strip("/").split("/")
    if ".obsidian" in p:
        return None                                  # réglages locaux de l'éditeur, ignorés partout
    top = p[0]
    if len(p) == 1:
        return None if top in RACINE_FICHIERS or top in RACINE_DOSSIERS else \
            f"{rel} : rien d'autre à la racine que les fichiers d'outillage du dépôt (CLAUDE.md, Où va quoi)"
    if top not in RACINE_DOSSIERS:
        return f"{rel} : dossier inconnu à la racine (CLAUDE.md, Où va quoi)"
    if top == "config":
        if p[1] not in CONFIG:
            return f"{rel} : config/ ne contient que youtube/ et agents/"
        if p[1] == "agents" and not (len(p) == 3 and p[2].endswith(".md")):
            return f"{rel} : config/agents/ ne contient que des agents <nom>.md"
        if p[1:3] == ["youtube", "conseils"] and len(p) > 3 and not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", p[3]):
            return f"{rel} : un conseil se nomme config/youtube/conseils/AAAA-MM-JJ.md"
    elif top == "secrets":
        if not rel.endswith(".enc"):
            return f"{rel} : secrets/ ne garde que le chiffré (.enc, secrets_vault.py)"
    elif top == "tests":
        if p[1] != "__pycache__" and (len(p) != 2 or not (re.fullmatch(r"test_\w+\.py", p[1]) or p[1] == "helpers.py")):
            return f"{rel} : tests/ ne contient que test_*.py et helpers.py"
    elif top == "videos":
        return _emplacement_video(rel, p)
    elif top == "montage":
        return _emplacement_montage(rel, p)
    return None


def _emplacement_video(rel, p):
    if not (ID.fullmatch(p[1]) or VEILLE.fullmatch(p[1])):
        return f"{rel} : videos/<id> avec un id de 2 ou 3 mots-clés (repo.py id) ou videos/veille-AAAA-MM-JJ"
    if len(p) == 2:
        return f"{rel} : un fichier directement dans videos/ va dans videos/<id>/"
    if len(p) == 3:
        return None if p[2].endswith(TEXTE) else f"{rel} : videos/<id>/ garde du texte (.md .json .txt) ; les images vont dans miniatures/"
    if p[2] not in VIDEO_SOUS_DOSSIERS:
        return f"{rel} : sous-dossiers de videos/<id>/ : bilans/, miniatures/ (veille/ et miniatures-refs/ restent locaux)"
    if p[2] == "bilans" and not rel.endswith(TEXTE):
        return f"{rel} : bilans/ garde du texte (.md .json .txt)"
    if p[2] == "miniatures" and not rel.lower().endswith(TEXTE + IMAGES):
        return f"{rel} : miniatures/ garde des images et leurs notes"
    return None


def _emplacement_montage(rel, p):
    if p[1] not in MONTAGE:
        return f"{rel} : montage/ ne contient que {', '.join(sorted(x for x in MONTAGE if '.' not in x))} et sa doc"
    if len(p) == 2:
        return None
    if p[1] == "04_RESSOURCES" and p[2] not in RESSOURCES:
        return f"{rel} : 04_RESSOURCES/ : musiques/, sfx/, images/, assets/ et LICENCES.md"
    if p[1] == "08_HYPERFRAMES" and p[2] not in HYPERFRAMES:
        return f"{rel} : inconnu dans 08_HYPERFRAMES/ (scripts/, kit/, assets/, videos/<id>/…)"
    if p[1] == "02_ANALYSE":
        if len(p) == 3:
            name = p[2]
            if name in ANALYSE_DOSSIERS or name in ANALYSE_COMMUNS or ANALYSE_PAR_VIDEO.fullmatch(name):
                return None
            return f"{rel} : 02_ANALYSE/ : derush_, vue_, controle_, capcut_, dosage_<id>… (chemins fixés par les scripts)"
        if p[2] not in ANALYSE_DOSSIERS and not p[2].startswith(("controle_", "revue_")):
            return f"{rel} : sous-dossier inconnu dans 02_ANALYSE/"
    return None


def forme(rel):
    """None when the name follows the shape rules (lowercase, no space nor accent, no version or copy name)."""
    if not rel.startswith(FORME_DOSSIERS) or any(s in "/" + rel for s in SANS_REGLE_DE_NOM):
        return None
    for part in rel.split("/"):
        if part in NOMS_LIBRES or part == "__pycache__":
            continue
        if not NOM.fullmatch(part):
            return f"{rel} : « {part} » : minuscules, chiffres, - ou _, sans espace ni accent"
        stem = part.rsplit(".", 1)[0] if "." in part else part
        if VERSION.search(stem):
            return (f"{rel} : nom de version ou de copie ; garder un seul fichier, ou nommer la version gardée exprès "
                    "d'après ce qu'elle est (script-avant-revision-aywen.md)")
    return None


def interdit_dans_git(rel, taille=0):
    """None when git may hold the file, else why it must not (envoi.py refuses it, the CI fails)."""
    p = rel.split("/")
    name = p[-1]
    low = name.lower()
    if low.endswith(VIDEO_EXT):
        return f"{rel} (fichier vidéo : les rushs et exports ne passent jamais par git)"
    if taille > MAX_MB * MO:
        return f"{rel} ({taille // MO} Mo, plus de {MAX_MB} Mo)"
    if SECRETS.fullmatch(name) and not rel.startswith("secrets/"):
        return f"{rel} (secret en clair : seulement le chiffré, secrets_vault.py)"
    if any(x in CACHES for x in p[:-1]) or low.endswith(".pyc"):
        return f"{rel} (cache, régénérable)"
    if low.endswith(TEMPORAIRES) or name.startswith("~$"):
        return f"{rel} (fichier temporaire)"
    if low in SYSTEME:
        return f"{rel} (fichier système)"
    if low.endswith(".wav") and not rel.startswith(SFX):
        return f"{rel} (audio .wav : seuls les bruitages du kit passent par git)"
    return None


def ecriture(rel, texte):
    """Breaches of the writing rules (E) in one file's text: [] when clean. Control characters: every text file."""
    out = []
    if CONTROLE.search(texte):
        out.append(f"{rel} : caractère de contrôle invisible (\\x{ord(CONTROLE.search(texte).group(0)):02x}) ; le retirer")
    if not DOCS.fullmatch(rel):
        return out
    m = PERIME.search(texte)
    if m:
        ligne = texte.count("\n", 0, m.start()) + 1
        out.append(f"{rel}:{ligne} : règle remplacée gardée (« {m.group(0)[:30]} ») ; la supprimer, git garde l'historique")
    budget = next(n for rx, n in BUDGETS if rx.fullmatch(rel))
    if len(texte) > budget:
        out.append(f"{rel} : {len(texte)} caractères, budget {budget} ; raccourcir (renvois, règles périmées)")
    if rel.endswith("SKILL.md"):
        d = re.search(r"^description:\s*(.+)$", texte[:4000], re.M)
        if d and len(d.group(1)) > DESCRIPTION_MAX:
            out.append(f"{rel} : description de {len(d.group(1))} caractères, maximum {DESCRIPTION_MAX}")
    return out


def lignes_longues(texte):
    """The long rule lines of a doc, normalized, for the copy check."""
    for l in texte.splitlines():
        l = re.sub(r"\s+", " ", l.strip().lstrip("-*0123456789. ").strip())
        if len(l) >= DOUBLON_MIN and not l.startswith(("|", "```", "http")):
            yield l


def a_la_main_jamais(rel):
    return next((f"{rel} : jamais écrit à la main (fichier généré, lié à CapCut, chiffré ou interne à git)"
                 for rx in A_LA_MAIN_JAMAIS if rx.match(rel)), None)


# ───────────── the repo
def git_files(r, others=True):
    """Tracked files, plus (others) the untracked ones git would send: what envoi.py commits. None without git."""
    args = ["git", "-C", str(r), "ls-files", "-z", "--cached"] + (["--others", "--exclude-standard"] if others else [])
    try:
        p = subprocess.run(args, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return sorted({n for n in p.stdout.decode("utf-8", "replace").split("\0") if n})


def statuts(r):
    """{id: status} from videos/<id>/suivi.md, through repo.py (one reading of suivi.md for every script)."""
    sys.path.insert(0, str(HERE / "skills" / "nouvelle-video" / "scripts"))
    import repo
    return {v["id"]: "publiée" if v["published"] and v["status"] not in ("publiée", "terminée") else v["status"]
            for v in repo.videos_info(r / "videos")}


def ids_connus(r):
    vids, montage = r / "videos", r / "montage" / "08_HYPERFRAMES" / "videos"
    return {d.name for base in (vids, montage) if base.exists() for d in base.iterdir() if d.is_dir()}


def video_de(projet, ids):
    """The id a CapCut project or a 02_ANALYSE name belongs to (longest id it starts with), or None."""
    hits = [i for i in ids if projet == i or projet.startswith((i + " ", i + "_", i + ".", i + "-"))]
    return max(hits, key=len) if hits else None


def projet_de(name):
    """'capcut_pokemon-ia - final 2_segments.tsv' -> 'pokemon-ia - final 2' (None if not a per-video name)."""
    m = ANALYSE_PAR_VIDEO.fullmatch(name)
    if not m:
        return None
    s = re.sub(r"(_segments\.tsv|\.wav|\.txt|\.json)$", "", m.group(1))
    return s


def rang_final(projet):
    """'<id>' -> 0, '<id> - final' -> 1, '<id> - final 3' -> 3."""
    m = re.search(r" - final(?: (\d+))?$", projet)
    return 0 if not m else int(m.group(1) or 1)


def taille(path):
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.exists() else 0


def age_jours(path, today):
    return (today - date.fromtimestamp(path.stat().st_mtime)).days


def _caches(r, today):
    """(automatic, proposed) : lists of (path, why). Automatic = untracked and regenerated on demand."""
    auto, propose = [], []
    tracked = set(git_files(r, others=False) or [])
    st = statuts(r)
    publiees = {i for i, s in st.items() if s in ("publiée", "terminée")}
    ids = ids_connus(r)

    for dirpath, dirnames, _ in os.walk(r):
        rel = Path(dirpath).relative_to(r).as_posix()
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", ".whisper", "06_CAPCUT", "01_RUSHS")]
        if "__pycache__" in dirnames:
            auto.append((Path(dirpath) / "__pycache__", "cache Python"))
            dirnames.remove("__pycache__")

    hf = r / "montage" / "08_HYPERFRAMES"
    for sub in ("build", "renders"):
        for d in sorted((hf / sub).iterdir()) if (hf / sub).is_dir() else []:
            if d.name in publiees:
                auto.append((d, f"{sub}/ d'une vidéo publiée, refait par les scripts"))

    analyse = r / "montage" / "02_ANALYSE"
    latest = {}
    for f in list(analyse.glob("capcut_*")) + list((analyse / "audio_16k").glob("capcut_*")) + list(analyse.glob("controle_*")):
        projet = projet_de(f.name)
        vid = video_de(projet, ids) if projet else None
        if vid:
            latest[vid] = max(latest.get(vid, 0), rang_final(projet))
    candidats = sorted(list(analyse.glob("capcut_*_segments.tsv")) + list((analyse / "audio_16k").glob("capcut_*.wav"))
                       + [d for d in analyse.glob("controle_*") if d.is_dir()]) if analyse.is_dir() else []
    for f in candidats:
        rel = f.relative_to(r).as_posix()
        if rel in tracked or any(t.startswith(rel + "/") for t in tracked):
            continue
        projet = projet_de(f.name)
        vid = video_de(projet, ids) if projet else None
        if vid in publiees:
            auto.append((f, f"cache de {vid}, publiée"))
        elif vid and rang_final(projet) < latest.get(vid, 0):
            propose.append((f, f"reste d'un ancien projet CapCut de {vid} (« {projet} »)"))
    for f in sorted((analyse / "audio_16k").glob("rush_*.wav")) if (analyse / "audio_16k").is_dir() else []:
        if age_jours(f, today) > RUSH_AUDIO_JOURS:
            auto.append((f, f"son de rush non utilisé depuis {RUSH_AUDIO_JOURS} jours, re-extrait à la demande"))

    for vid in sorted(publiees):
        for sub in ("veille", "miniatures-refs"):
            d = r / "videos" / vid / sub
            if d.is_dir():
                propose.append((d, f"brouillons de la phase d'idée de {vid}, publiée"))
        rendu = r / "montage" / "06_CAPCUT" / vid / "rendu"
        if rendu.is_dir():
            propose.append((rendu, f"morceaux de rendu de {vid}, publiée (rendu.py --refaire les refait)"))
    for vid, s in sorted(st.items()):
        if s == "terminée":
            for rel in sorted(tracked):
                if rel.startswith("montage/02_ANALYSE/") and "/" not in rel[len("montage/02_ANALYSE/"):]:
                    projet = projet_de(rel.rsplit("/", 1)[1])
                    if projet and video_de(projet, ids) == vid:
                        propose.append((r / rel, f"analyse de {vid}, terminée (bilan J+28 fait)"))
    sauv = r / "montage" / "_sauvegardes_claude"
    for d in sorted(sauv.iterdir()) if sauv.is_dir() else []:
        if age_jours(d, today) > SAUVEGARDES_JOURS:
            propose.append((d, f"sauvegarde CapCut de plus de {SAUVEGARDES_JOURS} jours"))
    auto = [(p, why) for p, why in auto if not p.relative_to(r).as_posix().startswith(JAMAIS)]  # garde-fou
    return auto, propose


def ecarts(r, files=None, contenu=True):
    """Breaches of A, B and C over what git holds or would send; with contenu, also UTF-8 and exact copies."""
    files = git_files(r) if files is None else files
    if files is None:
        return ["git indisponible : emplacements et noms non vérifiés"]
    out, hashes, lignes = [], {}, {}
    for rel in files:
        f = r / rel
        if not f.is_file():
            continue                                         # supprimé, pas encore commité
        why = interdit_dans_git(rel, f.stat().st_size) or emplacement(rel) or forme(rel)
        if why:
            out.append(why)
            continue
        texte, double = rel.endswith(TEXTE + (".py",)), rel.startswith(FORME_DOSSIERS)
        if not contenu or not (texte or double):
            continue
        data = f.read_bytes()
        if texte:
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                out.append(f"{rel} : pas en UTF-8")
            else:
                texte = data.decode("utf-8").replace("\r\n", "\n")
                out += ecriture(rel, texte)
                if DOCS.fullmatch(rel) and not rel.startswith("config/agents/"):   # un agent ne voit que son fichier
                    for l in set(lignes_longues(texte)):
                        lignes.setdefault(l, []).append(rel)
        if double and len(data) >= 64:
            hashes.setdefault(hashlib.sha1(data).hexdigest(), []).append(rel)
    for same in hashes.values():
        names = {x.rsplit("/", 1)[-1] for x in same}
        if len(same) > 1 and not (len(names) == 1 and all(x.startswith("videos/") for x in same)):
            out.append(f"{', '.join(same)} : même contenu ; garder un seul fichier")  # instantané par vidéo : toléré
    for l, where in lignes.items():
        if len(where) > 1:
            out.append(f"{', '.join(sorted(where))} : même règle recopiée (« {l[:50]}… ») ; une source, ailleurs un renvoi")
    return out


def structure(r, today):
    """Breaches the file list cannot show: video folder without suivi.md, old veille, skill without SKILL.md,
    02_ANALYSE name of no known video, forgotten drafts."""
    out, vids = [], r / "videos"
    for d in (sorted(vids.iterdir()) if vids.exists() else []):
        if not d.is_dir() or d.name.startswith((".", "_")):
            continue
        m = VEILLE.match(d.name)
        if m:
            if (today - date.fromisoformat(m.group(1))).days > VEILLE_JOURS:
                out.append(f"videos/{d.name} : veille de plus de {VEILLE_JOURS} jours ; à finir, ou en double d'un "
                           "videos/<id>/ (vérifier qu'il est identique, puis le supprimer)")
        elif not (d / "suivi.md").exists():
            out.append(f"videos/{d.name} : pas de suivi.md, invisible pour list et etat (aucun rappel de bilan)")
    skills = r / "skills"
    for d in (sorted(skills.iterdir()) if skills.exists() else []):
        if d.is_dir() and not d.name.startswith((".", "_")) and not (d / "SKILL.md").exists():
            out.append(f"skills/{d.name} : pas de SKILL.md")
    ids = ids_connus(r)
    analyse = r / "montage" / "02_ANALYSE"
    for f in (sorted(analyse.iterdir()) if analyse.exists() else []):
        m = ANALYSE_PAR_VIDEO.match(f.name)
        if m and not any(m.group(1).startswith(i) for i in ids):
            out.append(f"montage/02_ANALYSE/{f.name} : ne nomme aucune vidéo connue ; à ranger ou à supprimer")
    try:
        p = subprocess.run(["git", "-C", str(r), "ls-files", "-z", "--others", "--exclude-standard"],
                           capture_output=True, timeout=60)
        untracked = [n for n in p.stdout.decode("utf-8", "replace").split("\0") if n] if p.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        untracked = []
    old = [n for n in untracked if (r / n).is_file() and age_jours(r / n, today) > OUBLI_JOURS]
    if old:
        out.append(f"{len(old)} fichier(s) jamais envoyé(s) depuis plus de {OUBLI_JOURS} jours ({', '.join(old[:3])}"
                   f"{'…' if len(old) > 3 else ''}) : à envoyer, à ignorer, ou brouillon à supprimer")
    return out


def rapport(r, today, contenu=True):
    """Every line `repo.py etat` and `rangement.py` print; [] when everything is tidy."""
    auto, propose = _caches(r, today)
    out = ecarts(r, contenu=contenu) + structure(r, today)
    if auto:
        out.append(f"caches à vider ({sum(taille(p) for p, _ in auto) / MO:.0f} Mo) : python rangement.py --vider")
    out += [f"proposé : {p.relative_to(r).as_posix()} ({taille(p) / MO:.1f} Mo) : {why} ; "
            "python rangement.py --supprimer \"<chemin>\" après accord" for p, why in propose]
    return out


def supprimer(path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def vider(r, today):
    """Empties the safe caches; [(relative path, bytes)] of what was freed."""
    freed = []
    for p, _ in _caches(r, today)[0]:
        n = taille(p)
        supprimer(p)
        freed.append((p.relative_to(r).as_posix(), n))
    return freed


def main():
    a = sys.argv[1:]
    r, today = repo_root(), date.today()
    if a[:1] == ["--vider"]:
        freed = vider(r, today)
        print(f"vidé : {sum(n for _, n in freed) / MO:.0f} Mo ({len(freed)} élément(s))" if freed else "aucun cache à vider")
        for rel, n in freed:
            print(f"  {rel}  {n / MO:.1f} Mo")
    elif a[:1] == ["--supprimer"]:
        auto, propose = _caches(r, today)
        allowed = {p.relative_to(r).as_posix(): p for p, _ in auto + propose}
        refused = [x for x in a[1:] if x.replace("\\", "/").strip("/") not in allowed]
        if refused or not a[1:]:
            sys.exit("rien supprimé : seulement des chemins que le rapport propose (python rangement.py)\n  - "
                     + "\n  - ".join(refused or ["aucun chemin donné"]))
        for x in a[1:]:
            p = allowed[x.replace("\\", "/").strip("/")]
            n = taille(p)
            supprimer(p)
            print(f"supprimé : {x}  ({n / MO:.1f} Mo)")
    elif a[:1] == ["--git"]:
        out = ecarts(r, git_files(r, others=False))
        print("\n".join(out) if out else "rangement : rien à signaler dans ce que git contient")
        sys.exit(1 if out else 0)
    elif not a:
        out = rapport(r, today)
        print("\n".join(out) if out else "rangement : rien à signaler")
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
