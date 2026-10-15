"""accroches.py hors ligne : un faux yt-dlp écrit des sous-titres VTT."""
import json, sys, unittest

from helpers import SKILLS, TempDir, run, write_json

ACC = SKILLS / "yt-viral" / "accroches.py"
VTT = """WEBVTT
Kind: captions

00:00:00.000 --> 00:00:02.500
Today I gave Claude and ChatGPT

00:00:02.500 --> 00:00:05.000
Today I gave Claude and ChatGPT
60 minutes to make a horror game

00:00:05.000 --> 00:00:09.000
and only one prompt, let's see who wins

00:00:22.000 --> 00:00:25.000
but first subscribe to the channel

00:00:40.000 --> 00:00:42.000
after thirty seconds
"""
FAKE = r'''
import os, re, sys
out = sys.argv[sys.argv.index("-o") + 1]
url = sys.argv[-1]
vid = re.search(r"v=([\w-]{11})", url).group(1)
if vid == "bbbbbbbbbbb":
    sys.exit(1)
open(out.replace("%(id)s", vid).replace("%(ext)s", "en.vtt"), "w", encoding="utf-8").write(open(os.environ["FAKE_VTT"], encoding="utf-8").read())
'''


class AccrochesTest(unittest.TestCase):
    def test_hooks_measured(self):
        with TempDir() as d:
            (d / "fake.py").write_text(FAKE, encoding="utf-8")
            (d / "s.vtt").write_text(VTT, encoding="utf-8")
            refs = d / "refs.json"
            write_json(refs, {"outliers": [{"url": "https://www.youtube.com/watch?v=aaaaaaaaaaa"},
                                           {"url": "https://www.youtube.com/watch?v=bbbbbbbbbbb"}]})
            env = {"YTDLP": f'"{sys.executable}" "{d / "fake.py"}"', "FAKE_VTT": str(d / "s.vtt")}
            r = run(ACC, "--refs", refs, "--top", "2", "--json", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            v = out["videos"][0]
            self.assertEqual(v["promesse_a"], 0.0)                 # « Today »
            self.assertEqual(v["premier_nombre_a"], 2.5)           # « 60 minutes » (doublon de l'auto-sous-titre retiré)
            self.assertEqual(v["demande_avant_30s"], 22.0)
            self.assertIsNone(v["salutation_a"])
            self.assertEqual(len(v["transcription"]), 4)           # rien après 30 s
            self.assertTrue(v["transcription"][1].endswith("60 minutes to make a horror game"))
            self.assertIn("erreur", out["videos"][1])
            self.assertEqual(out["resume"]["videos"], 1)


if __name__ == "__main__":
    unittest.main()
