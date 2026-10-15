"""variete.py : ouverture, musiques et transitions comparées aux vidéos d'avant (demande du 2026-10-06)."""
import sys, unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "montage" / "08_HYPERFRAMES" / "scripts"))
import variete  # noqa: E402


def m(id_, ouverture="", musiques=(), transitions=()):
    return {"id": id_, "ouverture": ouverture, "musiques": list(musiques), "transitions": list(transitions)}


class VarieteTest(unittest.TestCase):
    def test_repeats_are_flagged(self):
        avant = [m("pokemon-ia", "flash_plans", [("hook", "hook.mp3")], ["flash"] * 5),
                 m("0927", "avant_apres")]
        cur = m("sukuna-ia", "flash_plans", [("hook", "hook.mp3"), ("a", "x.mp3"), ("b", "x.mp3"), ("c", "x.mp3")],
                ["flash", "flash", "flash", "glisse_gauche"])
        lignes = variete.rapport(cur, avant)
        texte = "\n".join(lignes)
        self.assertIn("« flash_plans » déjà prise par pokemon-ia", texte)
        self.assertNotIn("avant_apres,", texte.split("Pas utilisées récemment : ")[1].split("\n")[0])  # 0927 : récente
        self.assertIn("« hook.mp3 » déjà sur la partie « hook »", texte)
        self.assertIn("« x.mp3 » revient 3 fois", texte)
        self.assertIn("« flash » fait 3 sur 4", texte)
        self.assertIn("« flash » domine déjà pokemon-ia", texte)
        self.assertIn("glisse_haut", texte)                                   # types jamais utilisés proposés

    @unittest.skipUnless(variete.PERSO.exists(), "copie publique : musiques/perso/ n'y est pas")
    def test_varied_video_passes(self):
        avant = [m("pokemon-ia", "flash_plans", [("hook", "hook.mp3")], ["flash"] * 5)]
        cur = m("sukuna-ia", "pire_moment", [("hook", "quirky.mp3")],
                ["carte", "glisse_haut", "flash", "glisse_gauche"])
        self.assertEqual([l for l in variete.rapport(cur, avant) if "(info)" not in l], [])

    def test_missing_opening_lists_free_recipes(self):
        lignes = variete.rapport(m("x"), [m("pokemon-ia", "flash_plans")])
        self.assertTrue(lignes[0].startswith("ouverture : non choisie"))
        self.assertNotIn("flash_plans", lignes[0])


if __name__ == "__main__":
    unittest.main()
