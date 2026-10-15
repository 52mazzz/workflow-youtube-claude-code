"""Régressions des dix problèmes signalés le 2026-10-02, sans réseau."""
import contextlib, importlib.util, io, json, os, sys, unittest
from datetime import datetime, timezone
from unittest.mock import patch
from helpers import ROOT, SKILLS, TempDir, entry, run, write_json


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


BILAN = SKILLS / "bilan-video/scripts/bilan.py"
TITLES = SKILLS / "youtube-titles-ab/check_titles.py"
MINUTAGE = SKILLS / "yt-script/minutage.py"
SWIPE = SKILLS / "yt-viral/swipe.py"
bilan = module("bilan_regression", BILAN)
accroches = module("accroches_regression", SKILLS / "yt-viral/accroches.py")
swipe = module("swipe_regression", SWIPE)
repo = module("repo_regression", SKILLS / "nouvelle-video/scripts/repo.py")


class ArchiveTest(unittest.TestCase):
    def test_windows_and_identical_instant_never_overwrite(self):
        with TempDir() as d, patch.dict(os.environ, CLAUDE_REPO=str(d)):
            stamp = "2026-10-02T12:00:00.123456+00:00"
            paths = [bilan.keep("test", {"requested_age": age, "age_days": 28, "collected_at": stamp})
                     for age in (3, 7, 28, 7)]
            self.assertEqual(len(set(paths)), 4)
            self.assertEqual(len(list((d / "videos/test/bilans").glob("*.json"))), 4)
            self.assertEqual([json.loads(p.read_text())["requested_age"] for p in paths], [3, 7, 28, 7])
            self.assertIn("-J3", paths[0].name)

    def test_api_raw_curve_survives_main_and_offline_reanalysis(self):
        raw = {"id": "abcdefghijk", "title": "test", "duration": 60, "age_days": 28,
               "curve": [(0, 1), (.5, .6), (1, .4)],
               "curve_units": {"position": "ratio", "audience": "ratio"},
               "curve_source": {"type": "youtube_analytics", "startDate": "2026-09-01"}}
        with TempDir() as d, patch.dict(os.environ, CLAUDE_REPO=str(d)), patch.object(bilan, "private", return_value=(raw, None)), \
                patch.object(sys, "argv", [str(BILAN), "abcdefghijk", "--age", "7", "--id", "test", "--json"]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            bilan.main()
            saved = json.loads(next((d / "videos/test/bilans").glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(saved["requested_age"], 7)
            self.assertEqual(saved["curve_units"]["audience"], "ratio")
            self.assertEqual(saved["curve_source"]["type"], "youtube_analytics")
            self.assertEqual(saved["analyse"], bilan.analyse_curve(saved["curve"], saved["duration"]))

    def test_csv_ratio_above_two_archive_and_ambiguity(self):
        with TempDir() as d:
            f = d / "raw.csv"
            text = "Video position (ratio),Audience ratio\n0,2.5\n0.5,1.2\n1,0.5\n"
            f.write_text(text, encoding="utf-8")
            curve, info = bilan.read_studio_csv(f, 60)
            self.assertEqual(curve[0][1], 2.5)
            self.assertEqual(info["unite_retention"], "ratio")
            r = run(BILAN, "--csv", f, "--duree", "60", "--age", "7", "--id", "test", "--json",
                    env={"CLAUDE_REPO": str(d)})
            self.assertEqual(r.returncode, 0, r.stderr)
            saved = json.loads(next((d / "videos/test/bilans").glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(saved["curve_source"]["raw_csv"], text)
            self.assertEqual(saved["analyse"], bilan.analyse_curve(saved["curve"], 60))
            f.write_text(text.replace("Audience ratio", "Audience retention"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "--unite-retention"):
                bilan.read_studio_csv(f, 60)
            self.assertEqual(bilan.read_studio_csv(f, 60, unite_retention="ratio")[0], curve)
            f.write_text(text.replace("Audience ratio", "Audience retention (%)"), encoding="utf-8")
            self.assertEqual(bilan.read_studio_csv(f, 60)[0][0][1], .025)


class ValidationTest(unittest.TestCase):
    def test_empty_titles_missing_or_empty_refs_fail(self):
        with TempDir() as d:
            titles = d / "titres.txt"
            titles.write_text("# commentaire\n", encoding="utf-8")
            r = run(TITLES, titles)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("contrôle impossible", r.stdout + r.stderr)
            titles.write_text("Claude et ChatGPT inventent un jeu\n", encoding="utf-8")
            for content in (None, "{}", "not json"):
                refs = d / "refs.json"
                if content is not None: refs.write_text(content, encoding="utf-8")
                r = run(TITLES, titles, "--refs", refs)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("contrôle impossible", r.stdout + r.stderr)

    def test_no_recognized_spoken_timing_fails(self):
        with TempDir() as d:
            script = d / "script.md"
            script.write_text("# Script\nVoici une phrase sans créneau reconnu.\n", encoding="utf-8")
            for args in ((), ("--json",)):
                r = run(MINUTAGE, script, *args)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("contrôle impossible", r.stdout + r.stderr)

    def test_promises_and_manual_review(self):
        for phrase in ("I want to make Pokémon", "Voyons lequel crée le meilleur jeu"):
            self.assertEqual(accroches.analyse([(1, phrase)])["promesse_a"], 1)
        r = accroches.analyse([(0, "Regardez ces petites créatures.")])
        self.assertIsNone(r["promesse_a"])
        self.assertEqual(r["promesse_statut"], "promesse non détectée, à vérifier")


class ReferencesTest(unittest.TestCase):
    def test_unknown_dates_cannot_supply_median_or_age_filtered_outliers(self):
        with TempDir() as d:
            old = datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()
            rows = [entry(i, str(i), n, ts=old) for i, n in enumerate([100, 100, 100, 1000])]
            rows += [entry(10 + i, "unknown", 1) for i in range(8)]
            rows += [entry(30, "unknown hit", 1000000)]
            write_json(d / "c.json", {"channel": "C", "entries": rows})
            r = run(SWIPE, d / "c.json", "--json", "--max-age", "90", env={"SWIPE_NOW": "2026-10-02"})
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["channels"][0]["median_n"], 4)
            self.assertTrue(data["channels"][0]["fragile"])
            self.assertEqual(data["channels"][0]["median"], 100)
            self.assertEqual(data["dropped_unknown_date"], 9)
            self.assertEqual(data["usable_dated_videos"], 4)
            self.assertEqual([v["title"] for v in data["outliers"]], ["3"])
            write_json(d / "c.json", {"channel": "C", "entries": [entry(i, str(i), 100) for i in range(10)]})
            r = run(SWIPE, d / "c.json", "--json", env={"SWIPE_NOW": "2026-10-02"})
            data = json.loads(r.stdout)
            self.assertEqual(data["channels"], [])
            self.assertEqual(data["outliers"], [])
            self.assertEqual(data["skipped_thin_channels"], [["C", 0]])

    def test_selected_thumbnail_order_survives_without_ranking(self):
        with TempDir() as d:
            rows = [dict(entry(2, "subject", 100), channel="C", multiple=2),
                    dict(entry(1, "format", 1000000), channel="D", multiple=100)]
            write_json(d / "refs-sujet.json", {"outliers": rows})
            stream = io.StringIO()
            with patch.object(swipe, "download", return_value=True) as download, \
                    patch.object(sys, "argv", [str(SWIPE), "--refs-selection", str(d / "refs-sujet.json"),
                                               "--thumbs", str(d / "thumbs"), "--json"]), contextlib.redirect_stdout(stream):
                with self.assertRaises(SystemExit) as result: swipe.main()
            self.assertEqual(result.exception.code, 0)
            data = json.loads(stream.getvalue())
            self.assertEqual([v["title"] for v in data["outliers"]], ["subject", "format"])
            self.assertIn("00000000002", download.call_args_list[0].args[0])
            self.assertIn("00000000001", download.call_args_list[1].args[0])


class ScheduleTest(unittest.TestCase):
    def test_technical_folders_and_evening_release(self):
        with TempDir() as d:
            for name in (".obsidian", "_cache", "veille-2026-10-02", "junk", "video"):
                (d / name).mkdir()
            (d / "video/suivi.md").write_text("- Statut : programmée\n- Programmée pour : 2026-10-02 18:00 Europe/Paris\n",
                                             encoding="utf-8")
            infos = repo.videos_info(d)
            self.assertEqual([v["id"] for v in infos], ["video"])
            morning = datetime.fromisoformat("2026-10-02T10:00:00+02:00")
            evening = datetime.fromisoformat("2026-10-02T18:01:00+02:00")
            self.assertEqual(repo.publications_oubliees(d, infos, morning, False), [])
            self.assertIsNone(repo.released(infos[0], morning)[0])
            self.assertTrue(repo.publications_oubliees(d, infos, evening, False))
            self.assertEqual(infos[0]["scheduled"].utcoffset().total_seconds(), 7200)
            self.assertEqual(repo.scheduled_at("2026-12-02 18:00 Europe/Paris").utcoffset().total_seconds(), 3600)
            self.assertEqual(repo.scheduled_at("2026-10-02 16:00+00:00"), infos[0]["scheduled"])
            self.assertEqual(repo.paris_date(datetime.fromisoformat("2026-10-01T23:30:00+00:00")).isoformat(), "2026-10-02")
            with patch("zoneinfo.ZoneInfo", side_effect=KeyError("no tzdata")):
                self.assertEqual(repo.paris_zone(datetime.fromisoformat("2026-10-25T00:59:00+00:00")).utcoffset(None).total_seconds(), 7200)
                self.assertEqual(repo.paris_zone(datetime.fromisoformat("2026-10-25T01:00:00+00:00")).utcoffset(None).total_seconds(), 3600)


if __name__ == "__main__": unittest.main()
