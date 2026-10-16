#!/usr/bin/env python3
"""atelier.py - the workshop: one page in the browser to follow every video and keep the two PCs in step.

    python atelier.py                     # serves http://127.0.0.1:5555 and opens it (what atelier.bat does)
    python atelier.py --sans-navigateur   # without opening the browser
    python atelier.py --port 5556

The page shows what the scripts already know, never a copy: repo.py (status, dates and stages of suivi.md, reviews
due, publications not noted, what git has not sent or not fetched) and rangement.py (report only: the page empties
nothing). Small actions on a click: maj (setup.py --pull), envoi (envoi.py), open a file or a folder of the repo in
its usual app, and rewrite a text of a video (videos/<id>/, its montage settings) in the page. The stages themselves
stay with Claude: the page gives the phrase to say for the next one, and shows each stage with the files it names.

Listens on this PC only (127.0.0.1), refuses any other Host (DNS rebinding), and every action needs the token of the
page it served, so another site cannot click for you. Reads and opens only files inside the repo (never .git/ nor
secrets/), writes only the texts of the videos (ECRITURE), never over a version newer than the one shown. Works on the repo it sits in (or $CLAUDE_REPO, for the tests).
"""
import json, os, platform, re, secrets, subprocess, sys, threading, urllib.request, webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True                  # no __pycache__ for rangement.py to report at every launch
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "skills" / "nouvelle-video" / "scripts"))
import rangement  # noqa: E402
import repo  # noqa: E402

PORT = 5555
JETON = secrets.token_urlsafe(24)
HOTES = ("127.0.0.1", "localhost")
TEXTES = (".md", ".json", ".txt")
IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
TEXTE_MAX = 2 * 1024 * 1024
# the phrase to say to Claude for the next stage of suivi.md (triggers of the skills), « reprends <id> » otherwise
PHRASES = {"3b": "prépare le tournage {id}", "5": "dérushe {id}", "6": "monte la vidéo {id}",
           "7": "miniature finale {id}", "8": "fais la description {id}", "9": "publie {id}",
           "10": "fais des shorts {id}", "11": "bilan vidéo {id}", "11b": "conseil {id}", "12": "bilan vidéo {id}"}
A_LA_MAIN = {"4": "fiche-tournage.md"}           # stages done without Claude, and the file to have at hand
SANS_SUITE = ("mis de côté", "abandonnée", "terminée")
ETAPE = re.compile(r"^\s*- \[([ xX])\] (\d+[a-z]?)\. (.+)$", re.M)
# files of a video in the order of the workflow, the others after them by name
ORDRE = ("suivi.md", "idees.md", "script.md", "titres-miniatures.md", "fiche-tournage.md", "resultats.md",
         "description.md", "shorts.md")
# where the page may write: the texts of a video and its montage settings, nothing of the workflow itself
ECRITURE = (("videos",), ("montage", "08_HYPERFRAMES", "videos"))
NOMME = re.compile(r"`([^`]+)`")
AUSSI = {"9": " `description.md` `miniatures/`"}    # what a stage uses without naming it in suivi.md
GIT = threading.Lock()                          # one git command at a time: fetch, status, maj, envoi


def repo_root():
    return Path(os.environ.get("CLAUDE_REPO") or HERE)


def aujourdhui():
    return datetime.now(repo.paris_zone(datetime.now()))


def iso(x):
    return x.isoformat() if x else None


# ───────────── one video
def etapes(text):
    """The stages of suivi.md: number, done, name, who does it (skill or « toi »), what it leaves behind."""
    out = []
    for m in ETAPE.finditer(text):
        tete, _, detail = m.group(3).partition(" : ")
        qui = re.search(r"\((.*)\)\s*$", tete)
        out.append({"num": m.group(2), "fait": m.group(1) != " ", "nom": (tete[:qui.start()] if qui else tete).strip(),
                    "qui": qui.group(1) if qui else "", "detail": detail.strip()})
    return out


def titre(text):
    m = re.search(r"^# Suivi : (.+)$", text, re.M)
    return m.group(1).strip() if m and not m.group(1).startswith("[") else ""


def prochaine(v, et, today):
    """The first stage not done (the rule of repo.py list), with the phrase for Claude; None once over or paused.
    A review not due yet gives its date instead of a phrase (repo.py echeances)."""
    e = next((x for x in et if not x["fait"]), None)
    if e is None or v["status"] in SANS_SUITE:
        return None
    a_la_main = A_LA_MAIN.get(e["num"])
    attente = next(({"date": due.isoformat(), "quoi": label} for n, due, label, _ in repo.echeances(v, today)
                    if n == e["num"] and due > repo.paris_date(today)), None)
    return {"num": e["num"], "nom": e["nom"], "fichier": a_la_main, "attente": attente,
            "phrase": None if a_la_main or attente else PHRASES.get(e["num"], "reprends {id}").format(id=v["id"])}


def resume(v, today):
    et = etapes(v["text"])
    return {"id": v["id"], "titre": titre(v["text"]), "statut": v["status"], "publiee": iso(v["published"]),
            "programmee": iso(v["scheduled"]), "visee": iso(v["target"]), "faites": sum(e["fait"] for e in et),
            "total": len(et), "etapes": et, "prochaine": prochaine(v, et, today)}


def fichier(r, f):
    st = f.stat()
    return {"chemin": f.relative_to(r).as_posix(), "nom": f.name, "taille": st.st_size,
            "modifie": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes")}


def fichiers(r, d, ext, recents=False):
    """Files directly in d with these extensions: in the order of the workflow (or newest name first)."""
    fs = [f for f in d.iterdir() if f.is_file() and f.suffix.lower() in ext] if d.is_dir() else []
    if recents:
        fs.sort(key=lambda f: f.name, reverse=True)
    else:
        fs.sort(key=lambda f: (ORDRE.index(f.name) if f.name in ORDRE else len(ORDRE), f.name))
    return [fichier(r, f) for f in fs]


BLOC_PROMPT = re.compile(r"^```text\n(.*?)^```", re.M | re.S)
A_JOINDRE = re.compile(r"`([^`]+\.(?:png|jpe?g|webp))`(?:\s*\((?:image )?(\d+)\))?", re.I)


def joints(r, vd, texte):
    """The images a paragraph says to attach, found in miniatures/ (by path or name) or in config/youtube/ (~/.claude/youtube)."""
    out = []
    for m in A_JOINDRE.finditer(texte):
        nom = m.group(1)
        if nom.startswith("~/.claude/youtube/"):
            p = r / "config" / "youtube" / nom[len("~/.claude/youtube/"):]
            trouve = p if p.is_file() else None
        else:
            cle = nom.removeprefix(f"videos/{vd.name}/").removeprefix("miniatures/")
            trouve = next((p for p in sorted((vd / "miniatures").rglob("*")) if p.is_file()
                           and p.relative_to(vd / "miniatures").as_posix().endswith(cle)), None)
        out.append({"nom": nom, "role": f"image {m.group(2)}" if m.group(2) else "", "chemin": trouve.relative_to(r).as_posix() if trouve else None})
    return out


def prompts(r, vd):
    """The image prompts of the last section of titres-miniatures.md that has any (the final ones), each with the
    bold title and the paragraph just before it, and the images that paragraph says to attach."""
    f = vd / "titres-miniatures.md"
    if not f.is_file():
        return []
    sections = re.split(r"^(?=## )", f.read_text(encoding="utf-8"), flags=re.M)
    sec = next((s for s in reversed(sections) if BLOC_PROMPT.search(s)), "")
    out, pos = [], 0
    for m in BLOC_PROMPT.finditer(sec):
        avant = sec[pos:m.start()].strip().split("\n\n")[-1].strip()
        pos = m.end()
        t = re.match(r"\*\*(.+?)\*\*\s*:?\s*(.*)", avant, re.S)
        out.append({"titre": t.group(1) if t else "", "intro": (t.group(2) if t else avant).strip(),
                    "prompt": m.group(1).rstrip(), "joindre": joints(r, vd, avant)})
    return out


def fichiers_etape(r, vd, detail):
    """The texts a stage names in backquotes: in the folder of the video (even not written yet: the page can start
    it) or in config/youtube/ (~/.claude/youtube, read only); `miniatures/` asks for the images and prompts."""
    out, vus = [], set()
    for nom in NOMME.findall(detail):
        nom = nom.removeprefix(f"videos/{vd.name}/").removeprefix("~/.claude/youtube/")
        if nom.rstrip("/") == "miniatures":
            out.append({"nom": "miniatures/", "chemin": None, "miniatures": True})
            continue
        if Path(nom).suffix.lower() not in TEXTES or "/" in nom or "\\" in nom or nom in vus:
            continue
        vus.add(nom)
        p = vd / nom if (vd / nom).is_file() or not (r / "config" / "youtube" / nom).is_file() else r / "config" / "youtube" / nom
        out.append({"nom": nom, "chemin": p.relative_to(r).as_posix(), "existe": p.is_file(),
                    "editable": ecrivable(r, p) is not None})
    return out


def fiche(r, vid):
    """Everything about one video: stages, notes, its files grouped, its folders. None for an unknown id."""
    if vid not in {d.name for d in repo.video_dirs(r / "videos")}:
        return None
    vd, mont = r / "videos" / vid, r / "montage" / "08_HYPERFRAMES" / "videos" / vid
    v = repo.video_info(vd)
    notes = re.search(r"^## ", v["text"], re.M)
    textes = fichiers(r, vd, TEXTES)
    res = resume(v, aujourdhui())
    for e in res["etapes"]:
        e["fichiers"] = fichiers_etape(r, vd, e["detail"] + AUSSI.get(e["num"], ""))
    return {**res,
            "champs": {k: repo.field(v["text"], k) for k in ("Publiée le", "Lien", "Tournage")},
            "notes": v["text"][notes.start():].strip() if notes else "",
            "dossiers": [{"chemin": d.relative_to(r).as_posix(), "nom": nom}
                         for d, nom in ((vd, "Dossier de la vidéo"), (mont, "Réglages de montage")) if d.is_dir()],
            "groupes": [{"nom": "Production", "fichiers": [f for f in textes if f["nom"].endswith(".md")]},
                        {"nom": "Bilans", "fichiers": fichiers(r, vd / "bilans", (".md", ".txt"), recents=True)},
                        {"nom": "Miniatures", "fichiers": fichiers(r, vd / "miniatures", TEXTES)},
                        {"nom": "Réglages de montage", "fichiers": fichiers(r, mont, TEXTES)},
                        {"nom": "Données", "fichiers": [f for f in textes if not f["nom"].endswith(".md")]}],
            "images": fichiers(r, vd / "miniatures", tuple(IMAGES)),
            "prompts": prompts(r, vd)}


# ───────────── the whole production
def alerte(ligne, phrase=None):
    """A line of repo.py etat, with the video it names and, when there is one, the phrase that handles it."""
    vid, _, reste = ligne.partition(" : ")
    if not (reste and rangement.ID.fullmatch(vid)):
        return {"id": None, "texte": ligne, "phrase": None}
    return {"id": vid, "texte": reste, "phrase": phrase.format(id=vid) if phrase else None}


def etat(r):
    """The quick part, suivi.md only (no network): videos, reviews due, publications not noted."""
    infos, today = repo.videos_info(r / "videos"), aujourdhui()
    return {"pc": platform.node() or "ce PC", "aujourdhui": repo.paris_date(today).isoformat(),
            "videos": [resume(v, today) for v in infos],
            "bilans": [alerte(l, "bilan vidéo {id}") for l in repo.bilans_dus(infos, today)],
            "publications": [alerte(l) for l in repo.publications_oubliees(r / "videos", infos, today, online=False)]}


def controles(r):
    """The slow part: the channel on YouTube (publications not noted, yt-dlp) and the tidying report, emptying nothing."""
    infos, today = repo.videos_info(r / "videos"), aujourdhui()
    return {"publications": [alerte(l) for l in repo.publications_oubliees(r / "videos", infos, today, online=True)],
            "rangement": rangement.rapport(r, repo.paris_date(today))}


def journal(r, *rev):
    out = repo.git(r, "log", "--format=%h%x1f%cI%x1f%s", *rev) or ""
    return [dict(zip(("hash", "date", "message"), l.split("\x1f", 2))) for l in out.splitlines() if l.strip()]


def deux_pc(r, fetch=False):
    """Where this PC stands with the other one: the lines of repo.py etat, and the files and commits behind them."""
    with GIT:
        lignes = repo.git_waiting(r, online=fetch)
        status = repo.git(r, "-c", "core.quotepath=off", "status", "--porcelain") or ""
        distante = repo.git(r, "rev-parse", "--abbrev-ref", "@{u}") is not None
        return {"lignes": lignes, "branche": (repo.git(r, "rev-parse", "--abbrev-ref", "HEAD") or "").strip(),
                "modifies": [{"code": l[:2].strip(), "chemin": l[3:]} for l in status.splitlines() if l.strip()],
                "a_envoyer": journal(r, "-n", "30", "@{u}..HEAD") if distante else [],
                "a_recuperer": journal(r, "-n", "30", "HEAD..@{u}") if distante else [],
                "dernier": next(iter(journal(r, "-1", "HEAD")), None)}


# ───────────── small actions
def lancer(r, script, *args):
    """Runs maj or envoi as a double-click on its .bat would, on the repo the page shows, and returns what it printed."""
    if script == "setup.py" and r.resolve() != HERE.resolve():
        return {"ok": False, "sortie": "maj ne met à jour que le dépôt où se trouve atelier.py"}  # setup.py ignore CLAUDE_REPO
    if not GIT.acquire(timeout=60):
        return {"ok": False, "sortie": "une autre commande git tourne encore : réessaie dans un instant"}
    try:
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf8", GIT_TERMINAL_PROMPT="0", CLAUDE_REPO=str(r))
        p = subprocess.run([sys.executable, str(HERE / script), *args], cwd=str(r), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=600, env=env)
        return {"ok": p.returncode == 0, "sortie": (p.stdout + p.stderr).strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "sortie": f"{script} n'a pas fini en 10 minutes : vérifie dans un terminal (git status)"}
    finally:
        GIT.release()


def chemin_sur(r, chemin, ext=None):
    """The path `chemin` (relative to the repo, with /) names, or None: outside the repo, in .git/ or secrets/,
    missing, or (with ext) not a file of these types."""
    if not isinstance(chemin, str) or not chemin or "\0" in chemin or ":" in chemin or chemin[0] in "/\\":
        return None
    base = r.resolve()
    p = (base / chemin).resolve()
    try:
        parts = p.relative_to(base).parts
    except ValueError:
        return None
    if parts[:1] in ((".git",), ("secrets",)) or not p.exists():
        return None
    if ext is not None and not (p.is_file() and p.suffix.lower() in ext):
        return None
    return p


def ouvrir(r, chemin):
    """Opens a folder, a text or an image of the repo in its usual app (Explorer, editor, viewer); nothing else."""
    p = chemin_sur(r, chemin)
    if p is None or not (p.is_dir() or p.suffix.lower() in TEXTES + tuple(IMAGES)):
        return {"ok": False, "sortie": "seulement un dossier, un texte ou une image du dépôt"}
    if hasattr(os, "startfile"):
        os.startfile(str(p))
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(p)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"ok": True, "sortie": f"ouvert : {chemin}"}


def lire(r, chemin):
    p = chemin_sur(r, chemin, TEXTES)
    if p is None:
        return None
    data = p.read_bytes()
    return {**fichier(r, p), "texte": data[:TEXTE_MAX].decode("utf-8", "replace"), "tronque": len(data) > TEXTE_MAX,
            "version": str(p.stat().st_mtime_ns), "editable": len(data) <= TEXTE_MAX and ecrivable(r, p) is not None}


def ecrivable(r, p):
    """p if the page may write it: a text of a video (ECRITURE), existing, or a new .md right in videos/<id>/."""
    base = r.resolve()
    try:
        parts = p.resolve().relative_to(base).parts
    except ValueError:
        return None
    if p.suffix.lower() not in TEXTES or not any(parts[:len(z)] == z and len(parts) > len(z) + 1 for z in ECRITURE):
        return None
    if p.is_file():
        return p
    neuf = p.suffix.lower() == ".md" and len(parts) == 3 and parts[0] == "videos" and p.parent.is_dir()
    return p if neuf and not p.exists() else None


def ecrire(r, chemin, texte, version):
    """Saves a text rewritten in the page, refusing if the file changed since the page read it (Claude, the other PC)."""
    if not isinstance(chemin, str) or not chemin or "\0" in chemin or ":" in chemin or chemin[0] in "/\\":
        return {"ok": False, "sortie": "chemin refusé"}
    p = ecrivable(r, r.resolve() / chemin)
    if p is None or not isinstance(texte, str):
        return {"ok": False, "sortie": "seulement les textes d'une vidéo (videos/<id>/, ses réglages de montage)"}
    if len(texte.encode("utf-8")) > TEXTE_MAX:
        return {"ok": False, "sortie": "texte trop long pour l'atelier : ouvre-le dans l'appli"}
    if p.suffix.lower() == ".json":
        try:
            json.loads(texte)
        except ValueError as e:
            return {"ok": False, "sortie": f"JSON invalide, rien n'est enregistré : {e}"}
    if p.is_file():
        if str(p.stat().st_mtime_ns) != str(version):
            return {"ok": False, "conflit": True, "sortie": "le fichier a changé depuis que tu l'as ouvert (Claude, maj ?) : "
                    "copie ton texte, recharge-le, puis remets tes changements"}
        if b"\r\n" in p.read_bytes():
            texte = texte.replace("\r\n", "\n").replace("\n", "\r\n")
    elif version:
        return {"ok": False, "conflit": True, "sortie": "le fichier a été supprimé depuis que tu l'as ouvert"}
    tmp = p.with_name(p.name + ".atelier-tmp")
    tmp.write_bytes(texte.encode("utf-8"))
    os.replace(tmp, p)
    return {"ok": True, "sortie": f"enregistré : {chemin}", "version": str(p.stat().st_mtime_ns)}


# ───────────── the server
class Atelier(BaseHTTPRequestHandler):
    server_version = "Atelier"

    def log_message(self, *a):
        pass

    def repondre(self, code, data, kind="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def hote_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in HOTES

    def do_GET(self):
        if not self.hote_ok():
            return self.repondre(403, {"erreur": "hôte refusé : ouvre http://127.0.0.1:%d/" % self.server.server_port})
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        r = self.server.repo
        try:
            if u.path == "/":
                page = (HERE / "atelier.html").read_text(encoding="utf-8").replace("__JETON__", JETON)
                return self.repondre(200, page.encode("utf-8"), "text/html; charset=utf-8")
            if u.path == "/api/ping":
                return self.repondre(200, {"atelier": True})
            if u.path == "/api/etat":
                return self.repondre(200, etat(r))
            if u.path == "/api/git":
                return self.repondre(200, deux_pc(r, fetch=q.get("fetch") == "1"))
            if u.path == "/api/controles":
                return self.repondre(200, controles(r))
            if u.path == "/api/video":
                f = fiche(r, q.get("id", ""))
                return self.repondre(200, f) if f else self.repondre(404, {"erreur": "vidéo inconnue"})
            if u.path == "/api/fichier":
                f = lire(r, q.get("chemin", ""))
                return self.repondre(200, f) if f else self.repondre(404, {"erreur": "fichier introuvable ou non lisible ici"})
            if u.path == "/api/image":
                p = chemin_sur(r, q.get("chemin", ""), tuple(IMAGES))
                return self.repondre(200, p.read_bytes(), IMAGES[p.suffix.lower()]) if p else \
                    self.repondre(404, {"erreur": "image introuvable"})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as e:  # noqa: BLE001 : the page shows the error instead of a dead request
            return self.repondre(500, {"erreur": f"{type(e).__name__} : {e}"})
        self.repondre(404, {"erreur": "introuvable"})

    def do_POST(self):
        r, path = self.server.repo, urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        limite = 4 * TEXTE_MAX if path == "/api/ecrire" else 65536    # JSON escapes can make a text longer
        corps = self.rfile.read(n) if 0 < n <= limite else b""   # read even to refuse: an unread body resets the socket
        self.close_connection = True
        if not self.hote_ok() or self.headers.get("X-Atelier") != JETON:
            return self.repondre(403, {"erreur": "refusé : recharge la page de l'atelier"})
        try:
            data = json.loads(corps.decode("utf-8") or "{}")
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if path == "/api/maj":
            res = lancer(r, "setup.py", "--pull")
        elif path == "/api/envoi":
            message = " ".join(str(data.get("message") or "").split())[:200]
            res = lancer(r, "envoi.py", *([message] if message else []))
        elif path == "/api/ouvrir":
            res = ouvrir(r, data.get("chemin"))
        elif path == "/api/ecrire":
            if n > limite:
                return self.repondre(200, {"ok": False, "sortie": "texte trop long pour l'atelier : ouvre-le dans l'appli"})
            res = ecrire(r, data.get("chemin"), data.get("texte"), data.get("version"))
        else:
            return self.repondre(404, {"erreur": "introuvable"})
        if path != "/api/ouvrir":
            quoi = f"{path[5:]} {data.get('chemin')}" if path == "/api/ecrire" else path[5:]
            print(f"{datetime.now():%H:%M} {quoi} : {'ok' if res['ok'] else 'échec'}")
        self.repondre(200, res)


class Serveur(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = os.name != "nt"   # under Windows, SO_REUSEADDR would let two servers share the port


def deja_ouvert(url):
    try:
        with urllib.request.urlopen(url + "api/ping", timeout=2) as rep:
            return json.loads(rep.read().decode("utf-8")).get("atelier") is True
    except (OSError, ValueError):
        return False


def main():
    a = sys.argv[1:]
    port = int(a[a.index("--port") + 1]) if "--port" in a else PORT
    url = f"http://127.0.0.1:{port}/"
    navigateur = "--sans-navigateur" not in a
    try:
        srv = Serveur(("127.0.0.1", port), Atelier)
    except OSError:
        if not deja_ouvert(url):
            sys.exit(f"le port {port} est pris par un autre programme : python atelier.py --port {port + 1}")
        print(f"l'atelier tourne déjà : {url}")
        if navigateur:
            webbrowser.open(url)
        return
    srv.repo = repo_root()
    print(f"Atelier ouvert sur {url}\nLaisse cette fenêtre ouverte (réduis-la) ; la fermer arrête l'atelier.")
    if navigateur:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
