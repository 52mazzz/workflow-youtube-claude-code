"""miniature.py : contrôle des miniatures (OpenCV), planche et similarité (sans CLIP : histogramme)."""
import json, os, sys, unittest

from helpers import ROOT, SKILLS, TempDir, run

MINI = SKILLS / "youtube-thumbnail-prompts" / "miniature.py"
try:
    import cv2, numpy as np  # noqa: F401
except ImportError:
    cv2 = None


@unittest.skipIf(cv2 is None, "OpenCV absent (pip install opencv-python-headless numpy)")
class MiniatureTest(unittest.TestCase):
    def img(self, path, color, w=1280, h=720, busy_corner=False):
        im = np.full((h, w, 3), color, np.uint8)
        cv2.putText(im, "FACILE", (80, 300), cv2.FONT_HERSHEY_SIMPLEX, 6, (255, 255, 255), 18)
        if busy_corner:
            for i in range(0, 260, 12):
                cv2.line(im, (w - 260 + i, h - 120), (w - 260 + i, h), (255, 255, 255), 3)
        cv2.imwrite(str(path), im)
        return path

    def test_analyse_planche_similarity(self):
        with TempDir() as d:
            comps = d / "concurrents"; comps.mkdir()
            for i, c in enumerate([(200, 60, 40), (190, 70, 50), (210, 50, 30)]):   # tout bleu chez les concurrents
                self.img(comps / f"{i}.jpg", c)
            own = d / "chaine"; own.mkdir()
            for i in range(3):
                self.img(own / f"{i}.jpg", (40, 40, 220))                            # la chaîne : rouge
            mine = self.img(d / "1-duel.png", (40, 40, 225))
            bad = self.img(d / "2-petite.png", (12, 12, 12), w=640, h=360, busy_corner=True)
            env = {"MINIATURE_SANS_CLIP": "1"}
            r = run(MINI, mine, bad, "--concurrents", comps, "--chaine", own, "--dossier", d / "out", "--json", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = json.loads(r.stdout)
            a, b = rep["miniatures"]
            self.assertTrue(a["format_ok"]); self.assertFalse(b["format_ok"])
            self.assertEqual(a["coin_duree"], "libre"); self.assertEqual(b["coin_duree"], "chargé")
            self.assertTrue(any("1280x720" in m for m in b["remarques"]))
            self.assertEqual(a["couleurs"][0]["hex"], "#E12828")                     # BGR (40,40,225) -> rouge
            self.assertTrue(os.path.exists(a["planche"]))
            self.assertTrue(all(os.path.exists(p) for p in a["apercus"].values()))
            self.assertEqual(a["vs_chaine"]["verdict"], "plus proche de la chaîne que des concurrents")
            self.assertEqual(a["vs_concurrents"]["verdict"], "non calibré (sans CLIP)")
            self.assertGreater(a["vs_chaine"]["moyenne"], a["vs_concurrents"]["moyenne"])
            self.assertIn("approximative", rep["methode_similarite"])
            txt = run(MINI, mine, "--concurrents", comps, "--dossier", d / "out2", env=env).stdout
            self.assertIn("planche à regarder", txt)

    def test_thumb_urls_from_refs_and_channel(self):
        sys.path.insert(0, str(MINI.parent))
        import miniature
        with TempDir() as d:
            refs = d / "refs.json"
            refs.write_text(json.dumps({"outliers": [{"id": "abcdefghijk", "thumbnail": "https://i.ytimg.com/vi/abcdefghijk/hq720.jpg"},
                                                     {"id": "bcdefghijkl", "url": "https://www.youtube.com/watch?v=bcdefghijkl"}]}), encoding="utf-8")
            self.assertEqual(miniature.thumb_urls(refs, 5), ["https://i.ytimg.com/vi/abcdefghijk/hq720.jpg",
                                                             "https://i.ytimg.com/vi/bcdefghijkl/hqdefault.jpg"])
            chaine = d / "ma-chaine.json"
            chaine.write_text(json.dumps({"entries": [{"id": "cdefghijklm", "url": "https://www.youtube.com/shorts/cdefghijklm"},
                                                      {"id": "defghijklmn", "thumbnails": [{"url": "a", "width": 1}, {"url": "b", "width": 9}]}]}),
                              encoding="utf-8")
            self.assertEqual(miniature.thumb_urls(chaine, 5), ["b"])                  # Shorts écartés


if __name__ == "__main__":
    unittest.main()
