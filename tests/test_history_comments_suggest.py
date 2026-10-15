import json, sys, unittest
from helpers import SKILLS, TempDir, run, write_json

HISTORY = SKILLS / "yt-viral" / "refs_history.py"
COMMENTS = SKILLS / "yt-viral" / "comments.py"
sys.path.insert(0, str(SKILLS / "youtube-titles-ab"))
import suggest  # noqa: E402


def refs(date, formulas, median):
    return {"collected_at": date, "outliers": [
        {"id": f"vid{date}{i}", "title": f"t{i}", "channel": "Aywen", "multiple": 3 + i, "formula": f}
        for i, f in enumerate(formulas)],
        "channels": [{"channel": "Aywen", "channel_id": "UCa", "handle": "@aywen", "videos": 30, "median": median}]}


class HistoryTest(unittest.TestCase):
    def test_save_and_show(self):
        with TempDir() as d:
            env = {"YT_REFS_DIR": str(d / "hist"), "SWIPE_NOW": "2026-10-01"}
            for date, fs, med in [("2026-09-10", ["The Comparison", "I Tried It"], 100000),
                                  ("2026-09-28", ["The Comparison"], 120000)]:
                write_json(d / "refs.json", refs(date, fs, med))
                r = run(HISTORY, "save", d / "refs.json", "--slug", "Minecraft Shaders", env=env)
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((d / "hist" / "2026-09-28-minecraft-shaders.json").exists())
            r = run(HISTORY, "show", "--json", env=env)
            out = json.loads(r.stdout)
            self.assertEqual(len(out["collections"]), 2)
            self.assertEqual([f["formula"] for f in out["lasting_formulas"]], ["The Comparison"])
            ch = out["channels"][0]
            self.assertEqual(ch["days_since"], 3)
            self.assertEqual([m for _, m in ch["seen"]], [100000, 120000])
            text = run(HISTORY, "show", env=env).stdout
            self.assertIn("à jour", text)
            # older than the window
            out = json.loads(run(HISTORY, "show", "--weeks", "1", "--json", env=env).stdout)
            self.assertEqual(len(out["collections"]), 1)

    def test_rejects_non_swipe_file(self):
        with TempDir() as d:
            write_json(d / "x.json", [1, 2])
            r = run(HISTORY, "save", d / "x.json", env={"YT_REFS_DIR": str(d)})
            self.assertNotEqual(r.returncode, 0)


class CommentsTest(unittest.TestCase):
    def test_requests_and_mentions(self):
        info = {"title": "Claude vs ChatGPT Minecraft", "channel": "Aywen", "webpage_url": "u", "comments": [
            {"text": "Fais-le sur Roblox stp !", "like_count": 500, "parent": "root"},
            {"text": "Trop bien la vidéo", "like_count": 900, "parent": "root"},
            {"text": "Et si tu testais avec Gemini ? Roblox aussi", "like_count": 120, "parent": "root"},
            {"text": "réponse ignorée fais Roblox", "like_count": 9999, "parent": "abc"},
            {"text": "try it with Gemini next time", "like_count": 40, "parent": "root"}]}
        with TempDir() as d:
            write_json(d / "i.json", info)
            r = run(COMMENTS, "--from-file", d / "i.json", "--json")
            self.assertEqual(r.returncode, 0, r.stderr)
            v = json.loads(r.stdout)["videos"][0]
            self.assertEqual(v["comments_read"], 4)  # replies skipped
            self.assertEqual(v["top"][0]["likes"], 900)
            self.assertEqual([c["likes"] for c in v["requests"]], [500, 120, 40])
            mentions = {m["name"]: m["count"] for m in v["mentions"]}
            self.assertEqual(mentions.get("Roblox"), 2)
            self.assertEqual(mentions.get("Gemini"), 2)


class SuggestTest(unittest.TestCase):
    def test_parse_both_formats(self):
        self.assertEqual(suggest.parse('["ia", ["ia minecraft", "ia roblox"]]'), ["ia minecraft", "ia roblox"])
        jsonp = 'window.google.ac.h(["ia",[["ia minecraft",0,[512]],["ia gta",0]],{"k":1}])'
        self.assertEqual(suggest.parse(jsonp), ["ia minecraft", "ia gta"])

    def test_rank(self):
        ranked = suggest.rank({"a": ["x", "y"], "b": ["y", "z"]})
        self.assertEqual(ranked[0][0], "y")
        self.assertEqual(ranked[0][2], 2)


if __name__ == "__main__":
    unittest.main()
