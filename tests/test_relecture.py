"""relecture.py (un script.md relu d'un coup : accroches, minutage, beats, voix) et ce que hookscore.py vérifie
de l'ouverture (titre confirmé avant 6 s, première image), depuis le 2026-10-08."""
import json, unittest
from helpers import SKILLS, TempDir, run

RELECTURE = SKILLS / "yt-script" / "relecture.py"
HOOKSCORE = SKILLS / "yt-script" / "hookscore.py"
MINUTAGE = SKILLS / "yt-script" / "minutage.py"

OUVERTURE = """# Script : test

## Accroches

{tableau}

## Beat 1. Accroche (0:00 à 0:13)

**Version A**

- **0-3 s** [ON SCREEN : le domaine en jeu, écran partagé] : « J'ai fait coder Sukuna à Claude et ChatGPT. »
- **3-6 s** [ON SCREEN : VS] : « Dans Minecraft, un seul prompt, aucune retouche. »
- **6-10 s** [ON SCREEN : enjeu] : « Lequel me donne un vrai Dismantle ? »

**Version B**

- **0-3 s** [ON SCREEN : le plus beau plan] : « Deux IA, un seul prompt, un seul pouvoir. »
- **3-6 s** [ON SCREEN : VS] : « Claude et ChatGPT codent Sukuna dans Minecraft. »
- **6-10 s** [ON SCREEN : domaine] : « Lequel ira jusqu'au domaine ? »
"""

CORPS = """
## Beat 2. Les règles (0:13 à 0:35)

> « Un seul prompt, très détaillé. Si ça plante, je colle l'erreur une fois. »

[ON SCREEN : les règles en cartes]

## Beat 3. Le prompt (0:35 à 0:45)

```
Crée un mod Minecraft.
```

> « Voilà le prompt, il est dans la description. »

[ON SCREEN : le prompt]

## Beat 4. Test 1 : Dismantle (0:45 à 1:25)

[ON SCREEN : carte titre]

- **Claude** : « [CE QU'ON VOIT] ». [RÉACTION]
- **Point** : « Le point va à [GAGNANT], parce que [RAISON]. »

## Beat 5. Verdict (1:25 à 1:45)

> « Le gagnant, c'est [CLAUDE / CHATGPT], parce que [RAISON]. »

**Cas « aucun des deux ne marche »** :

> « Ni l'un ni l'autre ne se lance, même après ma seule correction, donc pas de pouvoir à regarder du tout ce soir. »

[ON SCREEN : les cartes de note]

## Beat 6. Demande finale (1:45 à 1:55)

> « Dites-moi dans les commentaires quel concept je leur fais coder ensuite. Merci d'avoir regardé, salut. »

[ON SCREEN : la question]
"""


class RelectureTest(unittest.TestCase):
    def relire(self, text, title=None, code=None):
        with TempDir() as d:
            (d / "script.md").write_text(text, encoding="utf-8")
            if title:
                (d / "suivi.md").write_text(f"# Suivi : {title}\n", encoding="utf-8")
            r = run(RELECTURE, d / "script.md", "--json")
            out = json.loads(r.stdout)
            if code is not None:
                self.assertEqual(r.returncode, code, out)
            return out

    def table(self, title=None):
        with TempDir() as d:
            (d / "script.md").write_text(OUVERTURE.format(tableau="") + CORPS, encoding="utf-8")
            if title:
                (d / "suivi.md").write_text(f"# Suivi : {title}\n", encoding="utf-8")
            return self.relire_table(d)

    def relire_table(self, d):
        return json.loads(run(RELECTURE, d / "script.md", "--json").stdout)["tableau"]

    def test_script_propre(self):
        title = "J'ai fait coder Sukuna dans Minecraft à Claude et ChatGPT"
        out = self.relire(OUVERTURE.format(tableau=self.table(title)) + CORPS, title, code=0)
        self.assertEqual(out["alertes"], [])
        self.assertTrue(any("voix écrite" in x for x in out["a_verifier"]))
        self.assertIn("| A |", out["tableau"])
        self.assertIn("4/4", out["tableau"])                      # les 4 noms du titre dits avant 6 s

    def test_tableau_absent_ou_perime(self):
        out = self.relire(OUVERTURE.format(tableau="") + CORPS, code=1)
        self.assertTrue(any("tableau de hookscore.py absent" in x for x in out["alertes"]))
        old = "| Version | Score /100 | Formule |\n|---|---:|---|\n| A, retenue | 12 | x |\n| B | 13 | y |"
        out = self.relire(OUVERTURE.format(tableau=old) + CORPS, code=1)
        self.assertTrue(any("tableau des accroches périmé" in x and "A 12 au lieu de" in x for x in out["alertes"]))

    def test_defauts_de_structure_et_de_voix(self):
        bad = (CORPS.replace("(0:35 à 0:45)", "(0:36 à 0:45)")                       # trou d'une seconde
                    .replace("[ON SCREEN : le prompt]", "")                          # beat sans image
                    .replace("il est dans la description", "je le lis")              # prompt jamais renvoyé
                    .replace("Si ça plante", "Abonnez-vous, et si tu vois un bug")   # demande au milieu + « tu »
                    .replace("(1:25 à 1:45)", "(1:25 à 2:10)").replace("## Beat 6. Demande finale (1:45", "## Beat 6. Demande finale (2:10")
                    .replace("> « Le gagnant, c'est [CLAUDE / CHATGPT], parce que [RAISON]. »", "> « Le gagnant, c'est Claude. »"))
        out = self.relire(OUVERTURE.format(tableau=self.table()) + bad, code=1)
        text = "\n".join(out["alertes"])
        for expected in ("trou entre", "« Beat 3. Le prompt » sans [ON SCREEN]", "dans la description",
                         "demande au spectateur dans « Beat 2. Les règles »", "abonnement demandé",
                         "« tu » dit au spectateur", "verdict en 45 s", "verdict sans sa raison"):
            self.assertIn(expected, text)

    def test_mise_en_place_trop_longue_et_deux_demandes(self):
        late = (CORPS.replace("(0:35 à 0:45)", "(0:35 à 1:05)").replace("(0:45 à 1:25)", "(1:05 à 1:25)")
                     .replace("quel concept je leur fais coder ensuite.", "quel concept je leur fais coder ensuite, et abonnez-vous."))
        out = self.relire(OUVERTURE.format(tableau=self.table()) + late, code=1)
        text = "\n".join(out["alertes"])
        self.assertIn("mise en place finie à 1:05", text)
        self.assertIn("2 demandes dans « Beat 6. Demande finale »", text)
        self.assertTrue(any("premier test à 1:05" in x for x in out["a_verifier"]))

    def test_short_sans_beats(self):
        short = OUVERTURE.format(tableau="").replace("## Beat 1. Accroche (0:00 à 0:13)", "") + "\n| Temps | Dit | Image |\n|---|---|---|\n| 0-3 s | « Claude a codé le domaine. » | domaine |\n"
        out = self.relire(short)
        self.assertTrue(any("contrôles des beats sautés" in x for x in out["a_verifier"]))


class OuvertureTest(unittest.TestCase):
    def score(self, hook, *opts):
        r = run(HOOKSCORE, "--json", *opts, "--hook", hook)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)[0]

    def test_titre_confirme_ou_non(self):
        title = "J'ai demandé à Claude et ChatGPT de refaire Pokémon"
        bad = self.score("Deux IA, un seul prompt, un seul jeu. Lequel tiendra jusqu'à la fin ?", "--titre", title)
        self.assertTrue(any("titre pas confirmé avant 6 s" in a for a in bad["alertes"]))
        good = self.score("J'ai demandé à Claude et ChatGPT de refaire Pokemon. Lequel tiendra ?", "--titre", title)
        self.assertEqual(good["alertes"], [])                    # Pokemon sans accent compte
        self.assertEqual(good["titre"], "3/3")

    def test_premiere_image(self):
        with TempDir() as d:
            (d / "s.md").write_text("**Version A**\n\n- **0-3 s** : « J'ai fait coder Sukuna à Claude. »\n\n"
                                    "**Version B**\n\n- **0-3 s** [ON SCREEN : ma facecam qui sourit] : « Deux IA codent Sukuna. »\n",
                                    encoding="utf-8")
            out = {x["version"]: x for x in json.loads(run(HOOKSCORE, "--json", d / "s.md").stdout)}
            self.assertTrue(any("sans [ON SCREEN]" in a for a in out["A"]["alertes"]))
            self.assertTrue(any("la première image doit être le résultat" in a for a in out["B"]["alertes"]))

    def test_curiosite_est_une_forme_pas_un_compte(self):
        liste = self.score("Pourquoi comment quoi quel lequel qui mais sauf presque personne ?")
        vraie = self.score("J'ai fait coder Sukuna à Claude et ChatGPT. Lequel me donne un vrai Dismantle ? Et à la fin, le domaine.")
        self.assertLess(liste["properties"]["CURIOSITY"], 60)
        self.assertGreater(vraie["properties"]["CURIOSITY"], liste["properties"]["CURIOSITY"] + 30)
        nommee = self.score("Claude et ChatGPT codent Sukuna. Lequel me donne un vrai Dismantle ?")
        floue = self.score("Claude et ChatGPT codent Sukuna. Lequel va réussir ?")
        self.assertGreater(nommee["properties"]["CURIOSITY"], floue["properties"]["CURIOSITY"])
        # « on va voir lequel… » est une question, même sans point d'interrogation ; « jusqu'au » une promesse
        indirecte = self.score("J'ai demandé à Claude et ChatGPT de refaire Pokémon. On va voir lequel s'en sort.")
        self.assertGreaterEqual(indirecte["properties"]["CURIOSITY"], 54)
        self.assertGreater(self.score("Deux IA, un seul prompt. Jusqu'au domaine.")["properties"]["CURIOSITY"], 24)

    def test_noms_propres_en_debut_de_phrase(self):
        # « Minecraft de base… » : un nom en tête de phrase est un nom ; « Dans », « J'ai » n'en sont pas
        a = self.score("Minecraft de base ressemble à ça.")
        b = self.score("Dans le jeu de base, ça ressemble à ça.")
        self.assertGreater(a["properties"]["SPECIFICITY"], b["properties"]["SPECIFICITY"])
        # des chiffres en liste sans aucun nom ne font pas 100
        self.assertLess(self.score("Deux IA, un seul prompt, une seule règle, trois essais.")["properties"]["SPECIFICITY"], 100)


class MinutageBeatsTest(unittest.TestCase):
    def test_puces_comptees_variantes_non(self):
        with TempDir() as d:
            (d / "s.md").write_text(CORPS, encoding="utf-8")
            res = {x["creneau"]: x for x in json.loads(run(MINUTAGE, d / "s.md", "--json").stdout)}
            self.assertEqual(res["Beat 4. Test 1 : Dismantle"]["mots"], 6)    # « Le point va à , parce que . »
            self.assertEqual(res["Beat 5. Verdict"]["mots"], 5)               # le cas « aucun ne marche » est une variante


if __name__ == "__main__":
    unittest.main()
