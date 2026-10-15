import json, re, unittest
from helpers import SKILLS, TempDir, run, write_json

CHECK = SKILLS / "youtube-titles-ab" / "check_titles.py"
HOOKSCORE = SKILLS / "yt-script" / "hookscore.py"


class CheckTitlesTest(unittest.TestCase):
    def check(self, lines, *args, code=0):
        with TempDir() as d:
            (d / "t.txt").write_text("\n".join(lines), encoding="utf-8")
            refs = d / "refs.json"
            write_json(refs, {"outliers": [{"title": "Minecraft mais 2 IA s'affrontent pour le rendre réaliste",
                                            "channel": "Aywen", "multiple": 7.8}]})
            own = d / "own.json"
            write_json(own, {"entries": [{"title": "J'ai demandé à 2 IA de créer des shaders Minecraft"}]})
            r = run(CHECK, d / "t.txt", "--refs", refs, "--own", own, *args)
            self.assertEqual(r.returncode, code, r.stdout + r.stderr)
            return r.stdout

    def test_clean_title(self):
        out = self.check(["J'ai mis Claude et ChatGPT en duel sur Roblox | QUI GAGNE ?"])
        self.assertIn("aucune erreur sur les contrôles effectués", out)
        self.assertIn("référence la plus proche", out)

    def test_surfaces(self):
        out = self.check(["J'ai mis Claude et ChatGPT en duel pour refaire Pokémon | QUI GAGNE ? | accueil",
                          "Pokémon recréé par 2 IA, Claude contre ChatGPT | FACILE | recherche",
                          "Deux IA inventent leurs propres créatures Pokémon et Claude | ÇA MARCHE ? | recherche"],
                         "--mot-cle", "claude pokemon", code=1)
        self.assertIn("[recherche]", out)
        self.assertEqual(out.count("ERREUR : paire « recherche » : mot-clé absent des 40 premiers caractères"), 1)   # la 3e
        # paire « accueil » dont l'aperçu mobile ne montre pas le sujet : conseil, pas erreur
        self.assertIn("conseil : aperçu mobile « J'ai mis Claude et ChatGPT en duel pour  » : le sujet (pokemon)", out)
        one_side = self.check(["Titre un sur Roblox avec Claude | A B | accueil", "Titre deux sur Roblox avec ChatGPT | C D | accueil"], code=1)
        self.assertIn("toutes les paires visent « accueil »", one_side)
        no_kw = self.check(["Pokémon recréé par 2 IA, Claude contre ChatGPT | FACILE | recherche",
                            "J'ai mis Claude et ChatGPT en duel sur Pokémon | QUI GAGNE ? | accueil"], code=1)
        self.assertIn("sans --mot-cle", no_kw)
        none = self.check(["Pokémon recréé par 2 IA, Claude contre ChatGPT | FACILE", "Deux IA refont Roblox | ÇA MARCHE ?"], code=1)
        self.assertIn("aucune surface indiquée", none)
        self.check(["Pokémon recréé par 2 IA", "Deux IA refont Roblox"], "--shorts")

    def test_flags(self):
        out = self.check(["J'ai demandé à Claude Opus 5.5 de coder un jeu : c'est INCROYABLE... | Claude a codé un jeu entier tout seul"], code=1)
        for flag in ("deux-points", "points de suspension", "numéro de version", "adjectif vague",
                     "texte miniature de 8 mots", "mot(s) répété(s)"):
            self.assertIn(flag, out)

    def test_dash_but_not_hyphen(self):
        self.assertIn("tiret interdit", self.check(["2 IA créent un jeu Roblox de zéro - le résultat"], code=1))
        self.assertNotIn("tiret interdit", self.check(["Est-ce que 2 IA peuvent créer un jeu Roblox"]))

    def test_copy_and_repeat(self):
        out = self.check(["Minecraft mais 2 IA s'affrontent pour le rendre réaliste",
                          "J'ai demandé à 2 IA de créer des shaders Minecraft"], "--shorts", code=1)
        self.assertIn("quasi copie", out)
        self.assertIn("déjà publié", out)

    def test_same_start(self):
        out = self.check(["2 IA s'affrontent sur Roblox", "2 IA s'affrontent sur Fortnite"], "--shorts")
        self.assertIn("commencent par", out)

    def test_accents_count_once(self):
        import unicodedata
        decomposed = unicodedata.normalize("NFD", "Réaliste é")
        out = self.check([decomposed])
        self.assertIn("10 caractères", out)


class HooksTest(unittest.TestCase):
    def test_hooks_json_is_valid(self):
        d = json.loads((SKILLS / "yt-script" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d["hooks"]), 21)
        self.assertEqual(len({h["id"] for h in d["hooks"]}), 21)
        for h in d["hooks"]:
            for p in h["match"]:
                re.compile(p)

    def score(self, hook, *opts):
        r = run(HOOKSCORE, "--json", *opts, "--hook", hook)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)[0]

    def test_french_scores_discriminate(self):
        vague = self.score("Bon alors aujourd'hui on fait une vidéo vraiment incroyable.", "--profil", "generique")
        sharp = self.score("Vous pensez qu'une IA peut coder Minecraft en 10 minutes ? Claude va essayer, et s'il rate, il perd tout.", "--profil", "generique")
        self.assertGreater(sharp["verdict"], vague["verdict"] + 10)
        self.assertGreater(sharp["properties"]["ADDRESS"], vague["properties"]["ADDRESS"])

    def test_profil_chaine_note_un_duel_sans_adresse(self):
        duel = self.score("J'ai demandé à Claude et ChatGPT de refaire Pokémon. Ils doivent inventer leurs créatures et fabriquer tout le jeu. Est-ce qu'on aura vraiment envie d'y jouer ?")
        vague = self.score("Bon alors aujourd'hui on fait une vidéo vraiment incroyable.")
        self.assertIn("DEFI", duel["properties"])
        self.assertEqual(duel["properties"]["DEFI"], 100)
        self.assertGreater(duel["verdict"], vague["verdict"] + 20)

    def test_profil_solo_short_a_une_ia(self):
        # un Short à une seule IA n'a pas de duel : le profil chaîne le notait bas d'office (2026-10-08)
        solo = lambda h: self.score(h, "--profil", "solo")
        defi = solo("Une phrase, dix minutes : Claude peut-il guérir mon ennui ?")
        ordre = solo("Claude, fais-moi un site contre l'ennui.")
        vague = solo("Bon alors aujourd'hui on fait une vidéo vraiment incroyable.")
        self.assertEqual(defi["properties"]["DEFI"], 100)                 # l'IA nommée + le défi en question
        self.assertEqual(ordre["properties"]["DEFI"], 100)                # l'ordre donné à l'IA
        self.assertGreater(defi["properties"]["ENJEU"], ordre["properties"]["ENJEU"] + 40)  # contrainte et risque
        self.assertGreater(defi["verdict"], self.score("Une phrase, dix minutes : Claude peut-il guérir mon ennui ?")["verdict"])
        self.assertGreater(defi["verdict"], ordre["verdict"] + 15)
        self.assertGreater(ordre["verdict"], vague["verdict"] + 15)
        anonyme = solo("Peut-on guérir l'ennui avec une seule phrase ?")
        self.assertLess(anonyme["properties"]["DEFI"], defi["properties"]["DEFI"])  # dire quelle IA tente
        long = "Claude a codé un site contre l'ennui et franchement c'est vraiment incroyable, regardez bien"
        self.assertEqual(self.score(long)["properties"]["BREVITY"], 100)  # 14 mots : bien pour 10 s
        self.assertLess(solo(long)["properties"]["BREVITY"], 75)          # trop pour 3 s

    def test_contre_sans_adversaire_n_est_pas_un_duel(self):
        self.assertLess(self.score("Claude, fais-moi un site contre l'ennui.")["properties"]["DEFI"], 75)
        self.assertGreaterEqual(self.score("Moi contre ChatGPT : qui code le meilleur Snake ?")["properties"]["DEFI"], 50)
        self.assertIn("--profil solo", " ".join(self.score("Claude, fais-moi un site contre l'ennui.")["alertes"]))
        self.assertEqual(self.score("J'ai demandé à Claude et ChatGPT de refaire Pokémon.")["alertes"], [])

    def test_ouverture_de_15_s_pas_penalisee(self):
        # une ouverture de plusieurs phrases se mesure en temps (mission en 4 s, tout en 15 s), pas en 9-24 mots
        o = self.score("J'ai fait coder Sukuna à Claude et ChatGPT. Dans Minecraft, avec un seul prompt chacun. "
                       "Lequel me donne un vrai Dismantle ? Et à la fin, le domaine.")
        self.assertGreaterEqual(o["properties"]["BREVITY"], 70)
        self.assertEqual(o["band"], "STRONG")
        long_first = self.score("Minecraft de base ressemble à ça et aujourd'hui je vais demander à deux IA de le transformer "
                                "complètement pour voir ce que ça donne vraiment. Claude contre ChatGPT.")
        self.assertLess(long_first["properties"]["BREVITY"], o["properties"]["BREVITY"])

    def test_vocabulaire_conjugue(self):
        self.assertGreaterEqual(self.score("Claude et ChatGPT codent chacun Sukuna dans Minecraft.")["properties"]["DEFI"], 75)
        duel = self.score("Deux IA recréent Zelda, un seul prompt.")
        self.assertGreaterEqual(duel["properties"]["DEFI"], 75)
        self.assertGreater(duel["properties"]["SPECIFICITY"], 34)

    def test_bourrage_de_mots_cles(self):
        r = self.score("J'ai demandé à Claude et ChatGPT de coder Sukuna incroyable fou dingue mission défi créer "
                       "construire sans aucun un seul seulement zéro")
        self.assertLess(r["properties"]["DEFI"], 100)
        self.assertLess(r["properties"]["ENJEU"], 100)
        self.assertLess(r["verdict"], 60)

    def test_gagnant_annonce_ferme_la_question(self):
        ouvert = self.score("Claude et ChatGPT codent Sukuna. Lequel gagne ?")
        ferme = self.score("Claude et ChatGPT codent Sukuna. Claude gagne.")
        self.assertGreater(ouvert["properties"]["CURIOSITY"], ferme["properties"]["CURIOSITY"])

    def test_alertes(self):
        r = self.score("Salut tout le monde, tu vas voir Claude coder Minecraft.", "--profil", "solo")
        self.assertEqual(len(r["alertes"]), 2)
        self.assertEqual(self.score("J'ai demandé à Claude de coder Minecraft.", "--profil", "solo")["alertes"], [])

    def test_lit_les_versions_d_un_script(self):
        with TempDir() as d:
            (d / "script.md").write_text(
                "## Beat 1. Accroche (0:00 à 0:13)\n\n**Version A (principale)**\n\n"
                "- **0-3 s** [ON SCREEN : le jeu] : « J'ai fait coder Sukuna à Claude et ChatGPT. »\n"
                "- **3-6 s** [ON SCREEN : VS] : « Lequel me donne un vrai Dismantle ? »\n\n"
                "**Version B**\n\n- **0-3 s** [ON SCREEN : le jeu] : « Deux IA, un seul prompt. »\n\n"
                "## Beat 2. Les règles (0:13 à 0:35)\n\n> « Un seul prompt. »\n", encoding="utf-8")
            r = run(HOOKSCORE, "--json", d / "script.md")
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual([x["version"] for x in out], ["A", "B"])
            self.assertTrue(out[0]["hook"].startswith("J'ai fait coder"))
            self.assertEqual(out[0]["minutage"], "ok")
            r = run(HOOKSCORE, d / "script.md")
            self.assertIn("| A |", r.stdout)

    def test_short_versions_et_tableau_minutes(self):
        with TempDir() as d:
            (d / "short.md").write_text(
                "**Version A**\n\n- **0-3 s** [ON SCREEN : le domaine] : « Claude a codé le domaine de Sukuna. »\n\n"
                "**Version B**\n\n- **0-3 s** : « Deux IA, un seul prompt, un seul domaine. »\n\n"
                "| Temps | Dit | Image |\n|---|---|---|\n"
                "| 0-3 s | « Claude a codé le domaine de Sukuna. » | domaine |\n"
                "| 3-5 s | « Mais ChatGPT a fait ça. » | écran partagé |\n", encoding="utf-8")
            r = run(HOOKSCORE, "--json", d / "short.md")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual([x["version"] for x in json.loads(r.stdout)], ["A", "B"])
            r = run(SKILLS / "yt-script" / "minutage.py", d / "short.md", "--json")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("déroulé 3-5 s", [x["creneau"] for x in json.loads(r.stdout)])

    def test_le_workflow_passe_par_le_scoreur(self):
        # chaque endroit qui écrit une accroche ou un script la note et la minute (règle du 2026-10-08)
        for f in ["yt-script/SKILL.md", "nouvelle-video/SKILL.md", "nouvelle-video/references/accroches-script.md",
                  "short/SKILL.md", "montage-capcut/SKILL.md", "montage-capcut/references/short-independant.md",
                  "conseil-workflow/SKILL.md"]:
            text = (SKILLS / f).read_text(encoding="utf-8")
            self.assertIn("hookscore.py", text, f)
            self.assertIn("minutage.py", text, f)
        # un script long se relit en entier avant d'être montré (2026-10-08)
        for f in ["yt-script/SKILL.md", "nouvelle-video/SKILL.md", "nouvelle-video/references/accroches-script.md",
                  "conseil-workflow/SKILL.md"]:
            self.assertIn("relecture.py", (SKILLS / f).read_text(encoding="utf-8"), f)
        self.assertNotIn("0-4 / 4-9 / 9-15", (SKILLS / "nouvelle-video/SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("calibration.json", (SKILLS / "bilan-video/SKILL.md").read_text(encoding="utf-8"))

    def test_calibrer(self):
        d = json.loads((SKILLS / "yt-script" / "calibration.json").read_text(encoding="utf-8"))
        for v in d["videos"]:
            self.assertTrue({"id", "retention_30s", "ouverture", "source"} <= set(v))
        r = run(HOOKSCORE, "--calibrer", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreaterEqual(len(json.loads(r.stdout)["videos"]), 2)

    def test_french_formula(self):
        self.assertEqual(self.score("J'ai demandé à Claude de créer Minecraft de zéro")["formula"], "I Tried It")
        self.assertEqual(self.score("Je vais demander à deux IA de recréer Zelda")["formula"], "I Tried It")

    def test_reads_utf8_file(self):
        with TempDir() as d:
            (d / "h.txt").write_text("Pourquoi personne n'a réussi à faire ça avant ?\nÇa marche.\n", encoding="utf-8")
            r = run(HOOKSCORE, d / "h.txt")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("winner", r.stdout)


if __name__ == "__main__":
    unittest.main()
