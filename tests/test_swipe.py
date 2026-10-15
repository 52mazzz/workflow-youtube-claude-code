import json, unittest
from datetime import datetime, timezone
from helpers import SKILLS, TempDir, entry, run, write_json

SWIPE = SKILLS / "yt-viral" / "swipe.py"
NOW = "2026-10-01"
DAY = 86400
T0 = datetime(2026, 10, 1, tzinfo=timezone.utc).timestamp()


def fixtures(d):
    v = d / "veille"; v.mkdir()
    write_json(v / "aywen.json", {
        "_type": "playlist", "channel": "Aywen", "channel_id": "UCa", "uploader_id": "@aywen",
        "extractor_key": "YoutubeTab", "entries": [
            entry(1, "Minecraft mais 2 IA s'affrontent pour le rendre réaliste", 900000, ts=T0 - 30 * DAY),
            entry(2, "J'ai testé le pire mod", 100000, ts=T0 - 40 * DAY),
            entry(3, "Survivre 100 jours", 120000, ts=T0 - 50 * DAY),
            entry(4, "Vidéo normale", 110000, ts=T0 - 60 * DAY),
            entry(5, "Première bientôt", None, live="is_upcoming"),
            entry(6, "Vieux succès de 2023", 800000, ts=T0 - 900 * DAY)]})
    # channel page without /videos: nested tabs, dated videos
    write_json(v / "petite.json", {
        "_type": "playlist", "channel": "Petite Chaîne", "channel_id": "UCb", "extractor_key": "YoutubeTab",
        "entries": [{"_type": "playlist", "title": "Videos", "entries": [
            entry(10, "Claude contre ChatGPT qui code le mieux Minecraft de zéro ?", 50000, ts=T0 - 30 * DAY),
            entry(11, "a", 2000, ts=T0 - 40 * DAY), entry(12, "b", 3000, ts=T0 - 40 * DAY), entry(13, "c", 2500, ts=T0 - 40 * DAY)]}]})
    write_json(v / "search.json", {
        "_type": "playlist", "id": "claude vs chatgpt", "extractor_key": "YoutubeSearch", "entries": [
            entry(1, "Minecraft mais 2 IA s'affrontent pour le rendre réaliste", 900000, channel="Aywen", channel_id="UCa"),
            entry(20, "short viral", 5000000, 30, "Shorty", "UCs", short=True),
            entry(21, "ChatGPT vs Claude Make Minecraft From Scratch", 400000, channel="Can It Code?", channel_id="UCc", ts=T0 - 30 * DAY)]})
    write_json(v / "own.json", {
        "_type": "playlist", "channel": "tsar rouge555", "channel_id": "UCown", "uploader_id": "@letsar555",
        "extractor_key": "YoutubeTab", "entries": [entry(30 + i, "x", n) for i, n in enumerate([10, 20, 30, 400])]})
    (v / "vide.json").write_text("null", encoding="utf-8")
    return v


class FloorFlopsTest(unittest.TestCase):
    def test_min_views_weak_signals_flops_thin(self):
        with TempDir() as d:
            v = d / "veille"; v.mkdir()
            vids = [entry(i, f"Video {i}", 20000, ts=T0 - (20 + i) * DAY) for i in range(1, 9)]
            vids += [entry(9, "Le flop de la semaine", 4000, ts=T0 - 15 * DAY), entry(10, "Gros succès", 400000, ts=T0 - 25 * DAY)]
            write_json(v / "a.json", {"_type": "playlist", "channel": "Grande", "channel_id": "UCg", "entries": vids})
            write_json(v / "p.json", {"_type": "playlist", "channel": "Minuscule", "channel_id": "UCm", "entries": [
                entry(30, "Petit buzz", 4000, ts=T0 - 20 * DAY)] + [entry(31 + i, "x", 300, ts=T0 - 40 * DAY) for i in range(4)]})
            write_json(v / "s.json", {"_type": "playlist", "id": "ytsearch25:q", "extractor_key": "YoutubeSearch", "entries": [
                dict(entry(50, "Trouvée en recherche", 90000, channel="Inconnue", channel_id="UCi", ts=T0 - 10 * DAY),
                     channel_url="https://www.youtube.com/channel/UCi")]})
            r = run(SWIPE, *sorted(v.glob("*.json")), "--min-views", "10000", "--json", env={"SWIPE_NOW": NOW, "SWIPE_OFFLINE": "1"})
            out = json.loads(r.stdout)
            titles = [o["title"] for o in out["outliers"]]
            self.assertIn("Gros succès", titles)
            self.assertNotIn("Petit buzz", titles)                                   # sous le plancher
            self.assertEqual([w["title"] for w in out["weak_signals"]], ["Petit buzz"])  # 13x sur une petite chaîne
            self.assertEqual([f["title"] for f in out["flops"]], ["Le flop de la semaine"])
            self.assertEqual(out["thin_candidates"][0]["url"], "https://www.youtube.com/channel/UCi")
            self.assertEqual(out["thin_candidates"][0]["best_views"], 90000)


class SwipeTest(unittest.TestCase):
    def go(self, d, *args):
        r = run(SWIPE, *sorted((d / "veille").glob("*.json")), *args, "--json", env={"SWIPE_NOW": NOW, "SWIPE_OFFLINE": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_reads_ytdlp_and_ranks_by_channel_median(self):
        with TempDir() as d:
            fixtures(d)
            out = self.go(d, "--min", "2", "--exclude", "@letsar555")
            titles = [o["title"] for o in out["outliers"]]
            self.assertEqual(titles[0], "Claude contre ChatGPT qui code le mieux Minecraft de zéro ?")
            self.assertIn("Minecraft mais 2 IA s'affrontent pour le rendre réaliste", titles)
            self.assertNotIn("x", titles)  # own channel excluded by handle
            self.assertEqual(out["dropped_no_views"], 1)  # upcoming premiere not counted as 0
            self.assertEqual(out["empty_files"], ["vide.json"])
            thin = dict((c, n) for c, n in out["skipped_thin_channels"])
            self.assertEqual(thin.get("Can It Code?"), 1)
            # the video seen in the channel tab and in the search is counted once
            aywen = next(c for c in out["channels"] if c["channel"] == "Aywen")
            self.assertEqual(aywen["videos"], 5)

    def test_french_title_gets_a_formula(self):
        with TempDir() as d:
            fixtures(d)
            out = self.go(d, "--min", "2")
            f = {o["title"]: o["formula"] for o in out["outliers"]}
            self.assertEqual(f["Minecraft mais 2 IA s'affrontent pour le rendre réaliste"], "The Comparison")

    def test_no_shorts(self):
        with TempDir() as d:
            fixtures(d)
            self.assertEqual(self.go(d, "--no-shorts")["dropped_shorts"], 1)

    def test_age_and_max_age(self):
        with TempDir() as d:
            fixtures(d)
            out = self.go(d, "--min", "2")
            by = {o["title"]: o for o in out["outliers"]}
            m = by["Minecraft mais 2 IA s'affrontent pour le rendre réaliste"]
            self.assertEqual(m["age_days"], 30)
            self.assertEqual(m["views_per_day"], 30000)
            self.assertIn("Vieux succès de 2023", by)
            out = self.go(d, "--min", "2", "--max-age", "365")
            titles = [o["title"] for o in out["outliers"]]
            self.assertNotIn("Vieux succès de 2023", titles)
            self.assertEqual(out["dropped_too_old"], 1)
            # dated recent outliers remain
            self.assertIn("Claude contre ChatGPT qui code le mieux Minecraft de zéro ?", titles)

    def test_min_age(self):
        with TempDir() as d:
            fixtures(d)
            out = self.go(d, "--min", "2", "--min-age", "35")
            self.assertNotIn("Minecraft mais 2 IA s'affrontent pour le rendre réaliste",
                             [o["title"] for o in out["outliers"]])

    def test_text_output(self):
        with TempDir() as d:
            fixtures(d)
            r = run(SWIPE, *sorted((d / "veille").glob("*.json")), "--min", "2", env={"SWIPE_NOW": NOW, "SWIPE_OFFLINE": "1"})
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("outliers at 2.0x", r.stdout)
            self.assertIn("formulas among the outliers", r.stdout)

    def test_missing_file(self):
        r = run(SWIPE, "nope.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stdout)


if __name__ == "__main__":
    unittest.main()


class MedianTest(unittest.TestCase):
    def test_young_videos_do_not_lower_the_median(self):
        with TempDir() as d:
            vids = [entry(100 + i, f"vidéo {i}", 1000, ts=T0 - (40 + i) * DAY) for i in range(6)]
            vids.append(entry(110, "la vieille qui marche", 2500, ts=T0 - 30 * DAY))
            vids += [entry(120 + i, f"sortie ce matin {i}", 10, ts=T0 - 3600) for i in range(2)]
            write_json(d / "c.json", {"_type": "playlist", "channel": "C", "channel_id": "UCm", "extractor_key": "YoutubeTab",
                                      "entries": vids})
            r = run(SWIPE, d / "c.json", "--json", env={"SWIPE_NOW": NOW})
            out = json.loads(r.stdout)
            best = out["outliers"][0]
            self.assertEqual((best["median"], best["median_n"], best["fragile"]), (1000, 7, True))   # sans les 2 du jour
            self.assertEqual(best["multiple"], 2.5)
            r = run(SWIPE, d / "c.json", "--json", "--median-min-age", "0", env={"SWIPE_NOW": NOW})
            self.assertEqual(json.loads(r.stdout)["outliers"][0]["median_n"], 9)                     # l'ancien calcul
            txt = run(SWIPE, d / "c.json", env={"SWIPE_NOW": NOW}).stdout
            self.assertIn("median of 7 (fragile)", txt)
