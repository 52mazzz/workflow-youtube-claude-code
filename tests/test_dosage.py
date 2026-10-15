"""dosage.py : le montage posé compté minute par minute et comparé aux cibles de la direction de montage (2026-10-07)."""
import sys, unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "montage" / "08_HYPERFRAMES" / "scripts"))
import dosage  # noqa: E402


class DosageTest(unittest.TestCase):
    def test_regrouper(self):
        self.assertEqual(dosage.regrouper([1.0, 1.2, 1.5, 3.0, 0.0]), [0.0, 1.0, 1.5, 3.0])

    def test_rapport_cible_et_pokemon(self):
        cible = [{"minute": k, "images": 12, "zooms": 6, "zooms_forts": 1, "sfx": 15, "musique": 4.5, "coupures": 0,
                  "pauses": 2} for k in range(5)]
        texte, ecart = dosage.rapport(cible)
        self.assertFalse(ecart, "\n".join(texte))
        self.assertNotIn("à revoir", "\n".join(texte))
        poke = [{"minute": k, "images": 6, "zooms": 2, "zooms_forts": 0, "sfx": 13, "musique": 1, "coupures": 1, "pauses": 14}
                for k in range(5)]
        texte, ecart = dosage.rapport(poke)
        self.assertTrue(ecart)
        t = "\n".join(texte)
        self.assertIn("changements d'image / min", t)
        self.assertEqual(t.count("à revoir"), 6)          # images, zooms, zooms de lecture, musique, coupures, pauses
        self.assertIn("images, zooms, pauses", t)                             # minutes loin des cibles listées


if __name__ == "__main__":
    unittest.main()
