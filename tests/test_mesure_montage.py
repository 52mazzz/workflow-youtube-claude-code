"""mesure_montage.py : dosage d'un montage fini (voix, fond, coupes), comme pour WOLF."""
import importlib.util, json, shutil, subprocess, sys, unittest

from helpers import ROOT, TempDir

sys.path.insert(0, str(ROOT / "montage" / "08_HYPERFRAMES" / "scripts"))
import mesure_montage as mm  # noqa: E402


class MesureMontageTest(unittest.TestCase):
    def test_mesures(self):
        # 60 s : voix qui parle avec une pause de 0,5 s toutes les 10 s ; fond 9 dB sous la voix, coupé 2 s à 30 s
        n = int(60 / mm.W)
        voix = [-60.0 if (i * mm.W) % 10 < 0.5 else -20.0 for i in range(n)]
        fond = [-60.0 if 30 <= i * mm.W < 32 else -29.0 for i in range(n)]
        r = mm.mesures(voix, fond, [5.0, 10.0, 20.0, 40.0])
        self.assertEqual(r["duree_s"], 60.0)
        self.assertEqual(r["images_min"], 4.0)
        self.assertEqual(r["pauses_min"], 5.0)                 # à 10, 20, 30, 40, 50 s (pas celle du tout début)
        self.assertAlmostEqual(r["fond_sous_voix_db"], 9.0, delta=0.1)
        self.assertEqual(r["coupures_fond_min"], 1.0)
        self.assertEqual(r["images_par_minute"], [4])

    @unittest.skipIf(shutil.which("ffmpeg") is None or importlib.util.find_spec("cv2") is None, "ffmpeg ou OpenCV absent")
    def test_zooms(self):
        # image texturée ; 2-2,3 s zoom rapide 1→1,3 ; tenu ; 4-4,3 s retour ; 6-11 s zoom lent 1→1,08
        with TempDir() as d:
            z = ("if(lt(it,2),1,if(lt(it,2.3),1+0.3*(it-2)/0.3,if(lt(it,4),1.3,if(lt(it,4.3),1.3-0.3*(it-4)/0.3,"
                 "if(lt(it,6),1,1+0.08*min((it-6)/5,1))))))")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:d=1,trim=end_frame=1",
                            "-frames:v", "1", str(d / "img.png")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "12", "-i", str(d / "img.png"), "-vf",
                            f"scale=2560:1440,zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1280x720:fps=30",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "z.mp4")], check=True)
            r = mm.mouvements(d / "z.mp4")
            got = [(z["sens"], z["facteur"]) for z in r["zooms"]]
            self.assertEqual(len(got), 3, r["zooms"])
            self.assertEqual([s for s, _ in got], ["avant", "arrière", "avant"])
            self.assertAlmostEqual(got[0][1], 1.3, delta=0.04)
            self.assertAlmostEqual(got[2][1], 1.08, delta=0.03)
            self.assertEqual([z["duree"] <= 0.5 for z in r["zooms"]], [True, True, False])   # deux rapides, un lent

    def test_debit(self):
        with TempDir() as d:
            f = d / "s.json3"
            f.write_text(json.dumps({"events": [
                {"tStartMs": 0, "segs": [{"utf8": "Salut"}, {"utf8": " à", "tOffsetMs": 300}, {"utf8": " tous", "tOffsetMs": 600}]},
                {"tStartMs": 40000, "segs": [{"utf8": "[Musique]"}]},
                {"tStartMs": 60000, "segs": [{"utf8": "fin"}]}]}), encoding="utf-8")
            r = mm.debit(f)
            self.assertEqual(r["mots_min"], 4)
            self.assertEqual(r["debut_30s"], "Salut à tous")


if __name__ == "__main__":
    unittest.main()
