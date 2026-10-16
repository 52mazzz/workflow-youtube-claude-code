"""veille.py hors ligne : un faux yt-dlp répond avec des JSON préparés (chaînes, recherches)."""
import json, os, sys, unittest
from datetime import datetime, timezone
from pathlib import Path

from helpers import SKILLS, TempDir, run, write_json

VEILLE = SKILLS / "yt-viral" / "veille.py"
NOW = "2026-10-15"
FAKE = r'''
import json, os, sys
url = sys.argv[-1]
table = json.load(open(os.environ["FAKE_YT_MAP"], encoding="utf-8"))
for key, path in table.items():
    if key in url:
        print(open(path, encoding="utf-8").read()); sys.exit(0)
print("ERROR: introuvable " + url, file=sys.stderr); sys.exit(1)
'''


def ts(days_ago):
    return int(datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp()) - days_ago * 86400


def vid(i, title, views, channel, cid, days_ago=40, curl=None):
    v = {"_type": "url", "ie_key": "Youtube", "id": f"{i:011d}", "url": f"https://www.youtube.com/watch?v={i:011d}",
         "title": title, "view_count": views, "duration": 600, "channel": channel, "channel_id": cid,
         "timestamp": ts(days_ago)}
    if curl:
        v["channel_url"] = curl
    return v


def tab(channel, cid, videos):
    return {"_type": "playlist", "channel": channel, "channel_id": cid, "entries": videos}


class VeilleTest(unittest.TestCase):
    def setUp(self):
        self._t = TempDir(); self.d = self._t.__enter__()
        d = self.d
        (d / "cfg" / "references").mkdir(parents=True)
        (d / "fx").mkdir()
        (d / "fake_ytdlp.py").write_text(FAKE, encoding="utf-8")
        # chaîne suivie A : 6 vidéos, un outlier à 10x (300 000 vues)
        a = [vid(i, f"Video A {i}", 30000, "Chaine A", "UCA") for i in range(1, 6)]
        a.append(vid(6, "ChatGPT vs Claude Make Minecraft From Scratch", 300000, "Chaine A", "UCA", days_ago=20))
        # chaîne B, découverte par la recherche : une seule vidéo dans la recherche, forte
        b_search = vid(20, "I Let Claude Build a Horror Game", 80000, "Chaine B", "UCB", 15, "https://www.youtube.com/channel/UCB")
        b = [vid(20 + i, f"Video B {i}", 10000, "Chaine B", "UCB") for i in range(1, 6)] + [
            vid(20, "I Let Claude Build a Horror Game", 80000, "Chaine B", "UCB", 15)]
        # chaîne C : une petite vidéo, sous le plancher, pas de deuxième passage
        c_search = vid(40, "Tiny AI game", 900, "Chaine C", "UCC", 30, "https://www.youtube.com/channel/UCC")
        own = [vid(50, "J'ai demandé à une IA de créer un mod Minecraft", 564, "tsar rouge555", "UCOWN")]
        fx = {"@letsar555": tab("tsar rouge555", "UCOWN", own), "channel/UCA": tab("Chaine A", "UCA", a),
              "channel/UCB": tab("Chaine B", "UCB", b),
              "ytsearch25:claude horreur": {"_type": "playlist", "id": "ytsearch25:claude horreur", "entries": [b_search, c_search]},
              "ytsearch20:jeu d'horreur ia": {"_type": "playlist", "id": "ytsearch20:x", "entries": [
                  vid(60, "J'ai demandé à une IA de créer un jeu d'horreur", 450000, "Aywen", "UCAY"),
                  vid(61, "AI makes a horror game from scratch", 90000, "Some EN", "UCEN")]},
              "ytsearch20:ia pokemon": {"_type": "playlist", "id": "ytsearch20:y", "entries": [
                  vid(62, "ChatGPT plays Pokemon", 900000, "Poepeo", "UCP")]}}
        table = {}
        for k, data in fx.items():
            p = d / "fx" / (str(abs(hash(k))) + ".json")
            write_json(p, data)
            table[k] = str(p)
        write_json(d / "map.json", table)
        write_json(d / "cfg" / "chaines.json", {"chaines": [
            {"nom": "Chaine A", "channel_id": "UCA", "url": "https://www.youtube.com/channel/UCA", "source": "référence",
             "ajoutee": "2026-10-01", "derniere_collecte": "2026-10-01", "mediane": 30000}]})
        write_json(d / "cfg" / "veille-requetes.json", {"fr": [], "en": [], "hors_niche": []})
        # veille précédente : l'outlier de A avait 100 000 vues à 6 jours
        write_json(d / "cfg" / "references" / "2026-10-01-veille.json", {"collected_at": "2026-10-01", "outliers": [
            {"id": f"{6:011d}", "title": "ChatGPT vs Claude Make Minecraft From Scratch", "channel": "Chaine A",
             "views": 100000, "age_days": 6, "multiple": 4.0}], "channels": []})
        self.env = {"YTDLP": f'"{sys.executable}" "{d / "fake_ytdlp.py"}"', "FAKE_YT_MAP": str(d / "map.json"),
                    "YT_CONFIG_DIR": str(d / "cfg"), "YT_REFS_DIR": str(d / "cfg" / "references"),
                    "SWIPE_NOW": NOW, "SWIPE_OFFLINE": "1"}

    def tearDown(self):
        self._t.__exit__(None, None, None)

    def test_collecte_second_pass_chaines_dynamics(self):
        r = run(VEILLE, "collecte", "--mode", "complete", "--requete", "claude horreur", "--dossier", self.d / "w" / "veille",
                env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("deuxième passage : 1 chaîne", r.stdout)            # B oui, C non (900 vues)
        refs = json.loads((self.d / "w" / "refs.json").read_text(encoding="utf-8"))
        titles = {o["title"]: o for o in refs["outliers"]}
        self.assertIn("I Let Claude Build a Horror Game", titles)          # trouvé grâce au deuxième passage
        self.assertAlmostEqual(titles["ChatGPT vs Claude Make Minecraft From Scratch"]["multiple"], 10.0, places=1)
        self.assertTrue((self.d / "w" / "ma-chaine.json").exists())
        ch = json.loads((self.d / "cfg" / "chaines.json").read_text(encoding="utf-8"))["chaines"]
        names = {c["nom"]: c for c in ch}
        self.assertEqual(names["Chaine B"]["source"], "découverte")
        self.assertEqual(names["Chaine A"]["derniere_collecte"], NOW)
        self.assertNotIn("Chaine C", names)
        resume = (self.d / "w" / "veille" / "veille-resume.md").read_text(encoding="utf-8")
        self.assertIn("**monte**", resume)                                 # 200 000 vues en 14 j contre 16 666/j avant
        self.assertIn("Chaine B", resume.split("## Chaînes ajoutées")[1])
        self.assertTrue((self.d / "cfg" / "references" / f"{NOW}-veille-complete.json").exists())

    def test_cache_and_light_mode(self):
        env = dict(self.env, SWIPE_NOW="2026-10-03")
        r = run(VEILLE, "collecte", "--mode", "legere", "--requete", "claude horreur", "--dossier", self.d / "w2" / "veille", env=env)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertIn("il en faut au moins 4", r.stdout)
        self.assertIn("1 chaîne(s) déjà à jour", r.stdout)                 # A collectée le 01/10 : pas recollectée

    def test_creneau(self):
        r = run(VEILLE, "creneau", "jeu d'horreur ia", "ia pokemon", "--json", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = {x["concept"]: x for x in json.loads(r.stdout)}
        self.assertEqual(res["jeu d'horreur ia"]["verdict"], "partiel")    # Aywen, 450 000 vues, en français
        self.assertEqual(res["jeu d'horreur ia"]["videos_fr"], 1)
        self.assertEqual(res["ia pokemon"]["verdict"], "libre")            # que de l'anglais
        txt = run(VEILLE, "creneau", "ia pokemon", env=self.env).stdout
        self.assertIn("aucune référence FR forte trouvée", txt)
        self.assertIn("ne prouve pas", txt)

    def test_grille(self):
        ideas = [{"titre": "Mod de dragons", "type": "duel", "multiple": 36, "vues": 2300000, "faisabilite": 2, "urgence": 2,
                  "creneau": "partiel", "demande": 2, "apprentissages": 0},
                 {"titre": "Pari obscur", "type": "pari", "multiple": 249, "vues": 3984, "faisabilite": 1, "urgence": 0,
                  "creneau": "libre", "demande": 0, "apprentissages": 0}]
        write_json(self.d / "idees.json", ideas)
        r = run(VEILLE, "grille", self.d / "idees.json", "--json", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        self.assertEqual(rows[0]["titre"], "Mod de dragons")
        self.assertEqual(rows[1]["_parts"]["preuve"], 1.5)                 # ×249 mais 3 984 vues : preuve divisée par 2
        md = run(VEILLE, "grille", self.d / "idees.json", env=self.env).stdout
        self.assertIn("**total /13**", md)
        write_json(self.d / "idees2.json", [dict(ideas[1], demande=0, sondage=True)])
        voted = json.loads(run(VEILLE, "grille", self.d / "idees2.json", "--json", env=self.env).stdout)
        self.assertEqual(voted[0]["_parts"]["demande"], 2)                 # option gagnante du sondage

    def test_idee_croisee(self):
        base = {"faisabilite": 2, "creneau": "libre", "demande": 0}
        croisee = dict(base, titre="Croisée", morceaux=[{"role": "format", "multiple": 7.8, "vues": 71777},
                                                         {"role": "matière", "multiple": 4, "vues": 3664485}])
        trou = dict(base, titre="Trou", morceaux=[{"role": "format", "multiple": 7.8, "vues": 71777}, {"role": "matière"}])
        write_json(self.d / "idees.json", [croisee, trou])
        rows = {r["titre"]: r for r in json.loads(run(VEILLE, "grille", self.d / "idees.json", "--json", env=self.env).stdout)}
        self.assertEqual(rows["Croisée"]["_parts"]["preuve"], 1.0)        # le morceau le plus faible (4×), pas la moyenne
        self.assertEqual(rows["Croisée"]["_confiance"], "élevée")
        self.assertEqual(rows["Trou"]["_parts"]["preuve"], 0.0)           # un morceau sans preuve : 0, et preuve inconnue
        self.assertIn("preuve", rows["Trou"]["_inconnues"])
        md = run(VEILLE, "grille", self.d / "idees.json", env=self.env).stdout
        self.assertIn("croisée, min 4×", md)

    def test_unknowns_never_help(self):
        measured = {"titre": "Mesurée", "multiple": 4, "vues": 50000, "faisabilite": 2, "creneau": "pris", "demande": 0}
        partial = {"titre": "Partielle", "multiple": 4, "vues": 50000, "faisabilite": 2}     # créneau et demande inconnus
        write_json(self.d / "idees.json", [partial, measured])
        env = dict(self.env, SWIPE_OFFLINE="1")
        out = json.loads(run(VEILLE, "grille", self.d / "idees.json", "--json", "--avec-verdict", env=env).stdout)
        by = {r["titre"]: r for r in out["idees"]}
        self.assertEqual(by["Partielle"]["_total"], by["Mesurée"]["_total"])          # avant : +2 pour l'inconnue
        self.assertEqual(out["idees"][0]["titre"], "Mesurée")                           # à égalité, la mieux mesurée d'abord
        self.assertEqual((by["Partielle"]["_confiance"], by["Partielle"]["_max_possible"]), ("faible", by["Mesurée"]["_total"] + 4))
        self.assertEqual(by["Mesurée"]["_confiance"], "élevée")
        self.assertIn("Partielle (créneau, demande)", out["non_tranche"])
        md = run(VEILLE, "grille", self.d / "idees.json", env=env).stdout
        self.assertIn("Classement non tranché", md)
        self.assertIn("non mesuré (?)", md)
        self.assertIn("déjà fait en FR", md)


    def test_tendance_and_season_in_grid(self):
        from datetime import date, timedelta
        start = date(2021, 10, 18)
        horreur, montant = {}, {}
        for k in range(260):                      # 5 ans, chaque semaine
            d = start + timedelta(weeks=k)
            horreur[d.isoformat()] = 90 if d.month == 10 else 12      # pic chaque octobre
            montant[d.isoformat()] = 5 if d < date(2025, 10, 1) else 40  # décolle depuis un an
        fx = self.d / "trends.json"
        write_json(fx, {"minecraft halloween": sorted(horreur.items()), "ia pokemon": sorted(montant.items())})
        env = dict(self.env, TRENDS_FIXTURE=str(fx), SWIPE_NOW="2026-09-01")
        r = run(VEILLE, "tendance", "minecraft halloween", "ia pokemon", "inconnu", "--json", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        res = {x["terme"]: x for x in json.loads(r.stdout)}
        self.assertEqual(res["minecraft halloween"]["classe"], "saisonnier")
        self.assertEqual(res["minecraft halloween"]["pic"], "2026-10-15")
        self.assertEqual(res["ia pokemon"]["classe"], "tendance")
        self.assertEqual(res["inconnu"]["classe"], "trop peu de données")
        ideas = [{"titre": "Halloween", "multiple": 10, "vues": 100000, "urgence": 1, "pic": "10-31", "intention": "divertissement",
                  "creneau": "libre", "demande": 1},
                 {"titre": "Sans date", "multiple": 10, "vues": 100000, "urgence": 1, "creneau": "libre", "demande": 1}]
        write_json(self.d / "idees.json", ideas)
        rows = json.loads(run(VEILLE, "grille", self.d / "idees.json", "--json", env=env).stdout)
        by = {r["titre"]: r for r in rows}
        self.assertEqual(by["Halloween"]["_parts"]["urgence"], 2)          # pic dans 60 jours : +1
        self.assertEqual(by["Sans date"]["_parts"]["urgence"], 1)
        md = run(VEILLE, "grille", self.d / "idees.json", env=env).stdout
        self.assertIn("pic dans 60 j", md)
        self.assertIn("divertissement", md)

if __name__ == "__main__":
    unittest.main()
