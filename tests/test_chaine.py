"""audit.py (skill chaine-youtube) hors ligne, sur une liste de vidéos préparée."""
import json, unittest
from datetime import datetime, timezone

from helpers import SKILLS, TempDir, entry, run, write_json

AUDIT = SKILLS / "chaine-youtube" / "audit.py"
T0 = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()
DAY = 86400


class AuditTest(unittest.TestCase):
    def test_rhythm_themes_drift(self):
        with TempDir() as d:
            vids = [entry(1, "J'ai mis Claude et ChatGPT en duel pour refaire Pokémon de zéro", 500, ts=T0 - 2 * DAY),
                    entry(2, "Claude contre ChatGPT, Pokémon en un prompt", 400, ts=T0 - 9 * DAY),
                    entry(3, "Pokémon recréé par une IA", 300, ts=T0 - 23 * DAY),
                    entry(4, "Pokémon mais c'est l'IA qui joue", 300, ts=T0 - 30 * DAY),
                    entry(5, "Les créatures Pokémon de ChatGPT", 300, ts=T0 - 37 * DAY),
                    entry(6, "J'ai demandé à une IA de créer un mod Minecraft", 564, ts=T0 - 60 * DAY),
                    entry(7, "Minecraft devient réaliste grâce à 2 IA", 100, ts=T0 - 80 * DAY),
                    entry(8, "Mon setup", 50, ts=T0 - 100 * DAY),
                    entry(9, "un short", 900, duration=30, short=True, ts=T0 - 3 * DAY)]
            write_json(d / "ma-chaine.json", {"_type": "playlist", "channel": "tsar rouge555", "entries": vids})
            env = {"YT_CONFIG_DIR": str(d / "cfg"), "SWIPE_NOW": "2026-10-01"}
            r = run(AUDIT, "--chaine", d / "ma-chaine.json", "--json", "--sans-grille", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            a = json.loads(r.stdout)
            self.assertEqual((a["longues"], a["shorts"]), (8, 1))
            self.assertEqual(a["theme_principal"], "Pokémon")
            self.assertTrue(a["derive"])                                   # Pokémon récemment, Minecraft avant
            self.assertEqual(a["depuis_derniere_j"], 2)
            self.assertEqual(a["par_semaine_8s"], 0.62)                    # 5 vidéos en 8 semaines
            self.assertTrue(any("rythme" in p for p in a["points"]))
            self.assertEqual(a["fil_ia"], 0.88)                            # 7 titres sur 8 nomment une IA (pas « Mon setup »)
            self.assertFalse(any(p.startswith("fil conducteur") for p in a["points"]))
            self.assertTrue(any(p.startswith("dérive de thème") for p in a["points"]))
            md = run(AUDIT, "--chaine", d / "ma-chaine.json", "--sans-grille", env=env)
            self.assertIn("Audit de la chaîne du 2026-10-01", md.stdout)
            self.assertTrue((d / "cfg" / "audits" / "2026-10-01.md").exists())


if __name__ == "__main__":
    unittest.main()
