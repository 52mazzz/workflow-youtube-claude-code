import json, subprocess, sys, threading, unittest, urllib.error, urllib.request
from datetime import timedelta
from helpers import ROOT, TempDir

sys.path.insert(0, str(ROOT))
import atelier  # noqa: E402
import repo  # noqa: E402  (atelier.py puts skills/nouvelle-video/scripts on the path)

SUIVI = """# Suivi : Mon titre

- Id : `mon-sujet-ia`
- Statut : {statut}
- Publication visée : 2030-01-01
- Publiée le : {publiee}
- Lien : [https://youtu.be/…]

- [x] 1. Idée validée (nouvelle-video, phases 1-2) : `idees.md`, `refs.json`
- [x] 3b. Préparation du tournage (nouvelle-video, fin de run, ou « prépare le tournage <id> ») : `fiche-tournage.md` générée
- [{t}] 4. Tournage sur le PC fixe (toi) : `resultats.md` rempli le jour même
- [{t}] 5. Dérushage (derush-capcut) : prises choisies d'après `script.md`
- [ ] 11. Bilan à J+3/J+7 (bilan-video) : ligne dans `apprentissages.md`

## Écarts par rapport au plan
- montage : beat 4 coupé
"""


def video(r, vid="mon-sujet-ia", statut="en cours", publiee="[AAAA-MM-JJ]", tourne=False):
    d = r / "videos" / vid
    d.mkdir(parents=True, exist_ok=True)
    (d / "suivi.md").write_text(SUIVI.format(statut=statut, publiee=publiee, t="x" if tourne else " "), encoding="utf-8")
    return d


def git(*a, cwd=None):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True)


def clone(remote, dest):
    git("clone", "-q", str(remote), str(dest))
    for k, val in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
        git("config", k, val, cwd=dest)


class Serveur:
    """The atelier on a free port of 127.0.0.1, serving the repo r."""
    def __init__(self, r):
        self.srv = atelier.Serveur(("127.0.0.1", 0), atelier.Atelier)
        self.srv.repo = r
        self.url = f"http://127.0.0.1:{self.srv.server_port}"

    def __enter__(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()

    def get(self, path, host=None):
        req = urllib.request.Request(self.url + path, headers={"Host": host} if host else {})
        return self._ouvrir(req)

    def post(self, path, data, jeton=atelier.JETON):
        headers = {"Content-Type": "application/json", **({"X-Atelier": jeton} if jeton else {})}
        return self._ouvrir(urllib.request.Request(self.url + path, json.dumps(data).encode(), headers, method="POST"))

    @staticmethod
    def _ouvrir(req):
        try:
            with urllib.request.urlopen(req, timeout=60) as rep:
                return rep.status, rep.headers.get("Content-Type"), rep.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()


class EtapesTest(unittest.TestCase):
    def test_parse_suivi(self):
        et = atelier.etapes(SUIVI.format(statut="en cours", publiee="", t=" "))
        self.assertEqual([e["num"] for e in et], ["1", "3b", "4", "5", "11"])
        self.assertEqual([e["fait"] for e in et], [True, True, False, False, False])
        self.assertEqual(et[1]["nom"], "Préparation du tournage")
        self.assertEqual(et[1]["qui"], "nouvelle-video, fin de run, ou « prépare le tournage <id> »")
        self.assertEqual(et[3]["detail"], "prises choisies d'après `script.md`")

    def test_next_stage_and_phrase(self):
        with TempDir() as r:
            today = atelier.aujourdhui()
            video(r)
            p = atelier.etat(r)["videos"][0]["prochaine"]
            self.assertEqual((p["num"], p["phrase"], p["fichier"]), ("4", None, "fiche-tournage.md"))  # à toi
            video(r, tourne=True)
            self.assertEqual(atelier.etat(r)["videos"][0]["prochaine"]["phrase"], "bilan vidéo mon-sujet-ia")
            video(r, statut="abandonnée")
            self.assertIsNone(atelier.etat(r)["videos"][0]["prochaine"])
            hier = (repo.paris_date(today) - timedelta(days=1)).isoformat()
            video(r, statut="publiée", publiee=hier, tourne=True)            # bilan pas encore dû : sa date, pas de phrase
            p = atelier.etat(r)["videos"][0]["prochaine"]
            self.assertIsNone(p["phrase"])
            self.assertEqual(p["attente"]["date"], (repo.paris_date(today) + timedelta(days=2)).isoformat())
            avant = (repo.paris_date(today) - timedelta(days=5)).isoformat()
            video(r, statut="publiée", publiee=avant, tourne=True)           # dû : la phrase, et l'alerte
            e = atelier.etat(r)
            self.assertEqual(e["videos"][0]["prochaine"]["phrase"], "bilan vidéo mon-sujet-ia")
            self.assertEqual([(a["id"], a["phrase"]) for a in e["bilans"]], [("mon-sujet-ia", "bilan vidéo mon-sujet-ia")])


class FicheTest(unittest.TestCase):
    def test_fiche(self):
        with TempDir() as r:
            d = video(r)
            for name in ("script.md", "idees.md", "refs.json"):
                (d / name).write_text("x", encoding="utf-8")
            (d / "bilans").mkdir()
            (d / "bilans" / "2030-01-04-J3.md").write_text("x", encoding="utf-8")
            (d / "miniatures").mkdir()
            (d / "miniatures" / "1-duel.png").write_bytes(b"\x89PNG")
            f = atelier.fiche(r, "mon-sujet-ia")
            groupes = {g["nom"]: [x["nom"] for x in g["fichiers"]] for g in f["groupes"]}
            self.assertEqual(groupes["Production"], ["suivi.md", "idees.md", "script.md"])   # ordre du workflow
            self.assertEqual(groupes["Données"], ["refs.json"])
            self.assertEqual(groupes["Bilans"], ["2030-01-04-J3.md"])
            self.assertEqual([x["chemin"] for x in f["images"]], ["videos/mon-sujet-ia/miniatures/1-duel.png"])
            self.assertTrue(f["notes"].startswith("## Écarts"))
            self.assertEqual(f["champs"]["Lien"], "")                                        # encore un [modèle]
            for bad in ("inconnu-ia", "../secrets", ""):
                self.assertIsNone(atelier.fiche(r, bad))

    def test_prompts(self):
        with TempDir() as r:
            d = video(r)
            (d / "miniatures" / "refs").mkdir(parents=True)
            (d / "miniatures" / "refs" / "rick.png").write_bytes(b"\x89PNG")
            (d / "titres-miniatures.md").write_text(
                "## 3. Ancien\n\n**vieux** : x\n\n```text\nold\n```\n\n## 5. Finales\n\nIntro.\n\n"
                "**1-duo** : joindre `rick.png` (image 1) et `absent.png` (2).\n\n```text\nprompt un\n```\n\n"
                "**2-ia** : rien.\n\n```text\nprompt deux\n```\n", encoding="utf-8")
            p = atelier.fiche(r, "mon-sujet-ia")["prompts"]                                 # seulement la dernière section
            self.assertEqual([(x["titre"], x["prompt"]) for x in p], [("1-duo", "prompt un"), ("2-ia", "prompt deux")])
            self.assertEqual([(j["role"], j["chemin"]) for j in p[0]["joindre"]],
                             [("image 1", "videos/mon-sujet-ia/miniatures/refs/rick.png"), ("image 2", None)])
            self.assertEqual(p[1]["joindre"], [])

    def test_fichiers_etape(self):
        with TempDir() as r:
            d = video(r)
            (d / "idees.md").write_text("x", encoding="utf-8")
            (r / "config" / "youtube").mkdir(parents=True)
            (r / "config" / "youtube" / "apprentissages.md").write_text("x", encoding="utf-8")
            et = {e["num"]: e["fichiers"] for e in atelier.fiche(r, "mon-sujet-ia")["etapes"]}
            self.assertEqual([(x["nom"], x["existe"], x["editable"]) for x in et["1"]],
                             [("idees.md", True, True), ("refs.json", False, False)])   # un .json ne se crée pas ici
            self.assertEqual(et["5"][0], {"nom": "script.md", "chemin": "videos/mon-sujet-ia/script.md",
                                          "existe": False, "editable": True})             # pas encore écrit : à commencer
            self.assertEqual([(x["chemin"], x["editable"]) for x in et["11"]],
                             [("config/youtube/apprentissages.md", False)])               # lu, pas modifié ici

    def test_ecrire(self):
        with TempDir() as r:
            d = video(r)
            (d / "script.md").write_bytes(b"ligne 1\r\nligne 2\r\n")
            v = atelier.lire(r, "videos/mon-sujet-ia/script.md")
            self.assertTrue(v["editable"])
            res = atelier.ecrire(r, "videos/mon-sujet-ia/script.md", "nouveau\ntexte\n", v["version"])
            self.assertTrue(res["ok"], res)
            self.assertEqual((d / "script.md").read_bytes(), b"nouveau\r\ntexte\r\n")          # fins de ligne gardées
            conflit = atelier.ecrire(r, "videos/mon-sujet-ia/script.md", "vieux", v["version"])
            self.assertTrue(conflit.get("conflit"))                                            # Claude a écrit entre-temps
            self.assertEqual((d / "script.md").read_bytes(), b"nouveau\r\ntexte\r\n")
            self.assertTrue(atelier.ecrire(r, "videos/mon-sujet-ia/shorts.md", "# Shorts\n", "")["ok"])   # créé
            (d / "refs.json").write_text("{}", encoding="utf-8")
            vj = atelier.lire(r, "videos/mon-sujet-ia/refs.json")["version"]
            self.assertFalse(atelier.ecrire(r, "videos/mon-sujet-ia/refs.json", "{pas du json", vj)["ok"])
            (r / "config").mkdir()
            (r / "config" / "x.md").write_text("x", encoding="utf-8")
            for bad in ("config/x.md", "../x.md", "videos/x.md", "videos/mon-sujet-ia/a/b.md", "videos/autre-ia/n.md",
                        "videos/mon-sujet-ia/n.py", "/videos/mon-sujet-ia/s.md", "C:/x.md", None):
                self.assertFalse(atelier.ecrire(r, bad, "x", "")["ok"], bad)
            self.assertFalse(atelier.lire(r, "config/x.md")["editable"])
            self.assertFalse(any(p.name.endswith(".atelier-tmp") for p in d.iterdir()))

    def test_chemin_sur(self):
        with TempDir() as r:
            video(r)
            (r / "secrets").mkdir()
            (r / "secrets" / "cle.enc").write_text("x", encoding="utf-8")
            (r / ".git").mkdir()
            (r / ".git" / "config").write_text("x", encoding="utf-8")
            ok = atelier.chemin_sur(r, "videos/mon-sujet-ia/suivi.md", atelier.TEXTES)
            self.assertEqual(ok, (r / "videos" / "mon-sujet-ia" / "suivi.md").resolve())
            for bad in ("../x", "/etc/passwd", "C:/Windows/win.ini", "videos/../../x", ".git/config", "secrets/cle.enc",
                        "videos/absent.md", None, 3):
                self.assertIsNone(atelier.chemin_sur(r, bad), bad)
            self.assertIsNone(atelier.chemin_sur(r, "videos/mon-sujet-ia", atelier.TEXTES))  # un dossier n'est pas un texte
            self.assertFalse(atelier.ouvrir(r, "../x")["ok"])


class ServeurTest(unittest.TestCase):
    def test_pages_and_guards(self):
        with TempDir() as r:
            d = video(r)
            (d / "script.md").write_bytes("# Script\nBonjour".encode("utf-8"))
            (d / "miniatures").mkdir()
            (d / "miniatures" / "a.png").write_bytes(b"\x89PNG")
            with Serveur(r) as s:
                code, kind, body = s.get("/")
                self.assertEqual((code, kind), (200, "text/html; charset=utf-8"))
                self.assertIn(atelier.JETON, body.decode("utf-8"))
                code, _, body = s.get("/api/etat")
                self.assertEqual([v["id"] for v in json.loads(body)["videos"]], ["mon-sujet-ia"])
                code, _, body = s.get("/api/fichier?chemin=videos/mon-sujet-ia/script.md")
                self.assertEqual(json.loads(body)["texte"], "# Script\nBonjour")
                self.assertEqual(s.get("/api/image?chemin=videos/mon-sujet-ia/miniatures/a.png")[1], "image/png")
                self.assertEqual(s.get("/api/fichier?chemin=../etc/passwd")[0], 404)
                self.assertEqual(s.get("/api/video?id=inconnu-ia")[0], 404)
                self.assertEqual(s.get("/api/etat", host="evil.example:80")[0], 403)          # DNS rebinding
                self.assertEqual(s.post("/api/ouvrir", {"chemin": "videos"}, jeton=None)[0], 403)  # autre site
                self.assertEqual(s.post("/api/ouvrir", {"chemin": "videos"}, jeton="faux")[0], 403)
                code, _, body = s.post("/api/ouvrir", {"chemin": "../x"})
                self.assertEqual((code, json.loads(body)["ok"]), (200, False))
                code, _, body = s.post("/api/maj", {})                                        # pas le dépôt de l'atelier
                self.assertFalse(json.loads(body)["ok"])
                self.assertEqual(s.post("/api/inconnu", {})[0], 404)
                v = json.loads(s.get("/api/fichier?chemin=videos/mon-sujet-ia/script.md")[2])["version"]
                self.assertEqual(s.post("/api/ecrire", {"chemin": "videos/mon-sujet-ia/script.md", "texte": "x", "version": v},
                                        jeton=None)[0], 403)                                  # autre site : rien d'écrit
                code, _, body = s.post("/api/ecrire", {"chemin": "videos/mon-sujet-ia/script.md", "texte": "# Réécrit\n", "version": v})
                self.assertTrue(json.loads(body)["ok"])
                self.assertEqual((d / "script.md").read_text(encoding="utf-8"), "# Réécrit\n")

    def test_two_pcs(self):
        with TempDir() as t:
            remote, r, autre = t / "remote.git", t / "work", t / "autre-pc"
            git("init", "-q", "--bare", str(remote))
            clone(remote, r)
            video(r)
            git("add", "-A", cwd=r); git("commit", "-qm", "premier", cwd=r); git("push", "-q", "-u", "origin", "HEAD", cwd=r)
            clone(remote, autre)
            (autre / "videos" / "mon-sujet-ia" / "script.md").write_text("x", encoding="utf-8")
            git("add", "-A", cwd=autre); git("commit", "-qm", "mon-sujet-ia : script", cwd=autre); git("push", "-q", cwd=autre)
            (r / "videos" / "mon-sujet-ia" / "idees.md").write_text("x", encoding="utf-8")
            with Serveur(r) as s:
                g = json.loads(s.get("/api/git?fetch=1")[2])
                self.assertEqual([c["message"] for c in g["a_recuperer"]], ["mon-sujet-ia : script"])
                self.assertEqual(g["modifies"], [{"code": "??", "chemin": "videos/mon-sujet-ia/idees.md"}])
                self.assertTrue(any("maj.bat" in l for l in g["lignes"]))
                code, _, body = s.post("/api/envoi", {"message": "mon-sujet-ia : idée"})   # commit, pull, push
                res = json.loads(body)
                self.assertTrue(res["ok"], res["sortie"])
                g = json.loads(s.get("/api/git?fetch=1")[2])
                self.assertEqual((g["lignes"], g["modifies"], g["a_recuperer"], g["a_envoyer"]), ([], [], [], []))
            log = git("log", "--format=%s", cwd=remote).stdout
            self.assertIn("mon-sujet-ia : idée", log)

    def test_without_git(self):
        with TempDir() as r:
            g = atelier.deux_pc(r)
            self.assertTrue(any("git indisponible" in l for l in g["lignes"]))
            self.assertEqual((g["modifies"], g["a_envoyer"], g["dernier"]), ([], [], None))


if __name__ == "__main__":
    unittest.main()
