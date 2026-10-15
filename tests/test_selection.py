"""selection.py : les références choisies par pertinence (sujet, format) avant leur multiple."""
import json, unittest

from helpers import SKILLS, TempDir, run, write_json

SEL = SKILLS / "yt-viral" / "selection.py"


def o(title, channel, multiple, views=100000):
    return {"title": title, "channel": channel, "multiple": multiple, "views": views, "url": "u"}


class SelectionTest(unittest.TestCase):
    def test_relevance_before_score(self):
        refs = {"collected_at": "2026-10-01", "outliers": [
            o("I Let ChatGPT Play Pokémon Fire Red!", "Poepeo", 1833),
            o("Can ChatGPT Beat a Pokémon Nuzlocke?", "Poepeo", 600),
            o("Claude Plays Pokemon Song", "Kurukkoo", 249, views=3984),
            o("ChatGPT vs Claude Make Minecraft From Scratch", "Wxter", 48),
            o("ChatGPT vs Gemini Make FNAF From Scratch", "mxks", 24),
            o("ChatGPT vs Gemini Make FIFA From Scratch", "mxks", 11),
            o("ChatGPT vs Claude Make Horror From Scratch", "mxks", 35),
            o("AI Makes Pokémon", "tef", 1.9),
            o("Survivre 100 jours", "Autre", 90)]}
        with TempDir() as d:
            write_json(d / "refs.json", refs)
            r = run(SEL, d / "refs.json", "--sujet", r"\bpok[eé]mon", "--format", r"\b(make|makes|from scratch)\b",
                    "--exclure", r"\b(plays?|nuzlocke)\b")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout)
            titles = [x["title"] for x in res["outliers"]]
            self.assertEqual(titles[0], "AI Makes Pokémon")                          # même sujet ET même format d'abord
            self.assertEqual(res["outliers"][0]["pertinence"], "sujet+format")
            self.assertEqual(sum(1 for x in res["outliers"] if x["channel"] == "mxks"), 2)   # 2 par chaîne au plus
            self.assertNotIn("Survivre 100 jours", titles)
            self.assertEqual([x["channel"] for x in res["secondaires"]], ["Poepeo", "Poepeo"])   # l'IA qui joue : secondaire
            self.assertNotIn("Kurukkoo", json.dumps(res))                             # sous le plancher de vues
            self.assertTrue(any("moins de 3 références" in n for n in res["notes"]))
            self.assertEqual(res["collected_at"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
