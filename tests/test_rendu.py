"""Rendu direct (rendu.py, 2026-10-08) : timeline, glissements, morceaux, et un vrai mini-rendu FFmpeg de synthèse."""
import contextlib, io, json, re, shutil, subprocess, sys, unittest
from pathlib import Path

from helpers import ROOT, TempDir

sys.path.insert(0, str(ROOT / "montage" / "08_HYPERFRAMES" / "scripts"))
import cadrage  # noqa: E402
import rendu  # noqa: E402

F = rendu.FPS


def seg(file, a, b, src=0.0, niveau=0, speed=1.0):
    return {"file": file, "a": a * F, "b": b * F, "src": src, "speed": speed, "niveau": niveau}


class TimelineTest(unittest.TestCase):
    def test_visibles_prend_le_plan_le_plus_haut_et_bouche_les_trous(self):
        segs = [seg("a", 0, 10, 5.0), seg("p", 4, 6, 100.0, niveau=100)]
        v = rendu.visibles(segs + [seg("b", 12, 14)])
        self.assertEqual([(p["file"], p["a"] / F, p["b"] / F) for p in v],
                         [("a", 0, 4), ("p", 4, 6), ("a", 6, 10), (None, 10, 12), ("b", 12, 14)])
        self.assertAlmostEqual(v[2]["src"], 11.0)          # la suite du rush reprend au bon endroit

    def test_vitesse_avance_la_source(self):
        v = rendu.visibles([seg("g", 0, 2, 40.0, speed=10.0), seg("a", 0, 4, niveau=-1)])
        self.assertEqual(v[0]["file"], "g")
        self.assertEqual(v[1]["src"], 2.0)

    def test_glissement_garde_les_deux_plans_et_coupe_autour(self):
        pieces = rendu.visibles([seg("a", 0, 5, 10.0), seg("b", 5, 10, 50.0)])
        for p in pieces:
            p["points"], p["t0"] = [], 0.0
        out = rendu.avec_glissements(pieces, [{"a": int(4.75 * F), "b": int(5.25 * F), "sens": "gauche"}])
        self.assertEqual([p.get("kind") or p["file"] for p in out], ["a", "glisse", "b"])
        self.assertEqual(out[0]["b"], out[1]["a"])
        self.assertEqual(out[1]["b"], out[2]["a"])
        self.assertAlmostEqual(out[2]["src"], 50.25)
        self.assertAlmostEqual(out[2]["t0"], 0.25)          # le cadrage du plan b continue au bon instant
        self.assertEqual(out[1]["A"]["file"], "a")

    def test_bornes_morceaux_hors_des_glissements(self):
        b = rendu.bornes_morceaux(50 * F, [{"a": 19 * F, "b": 21 * F}])
        self.assertEqual(b[0], 0)
        self.assertEqual(b[1], 21 * F)
        self.assertEqual(b[-1], 50 * F)
        self.assertTrue(all(y > x for x, y in zip(b, b[1:])))

    def test_expression_de_zoom_suit_les_points(self):
        pts = [{"t": 0.0, "scale": 1.0}, {"t": 1.0, "scale": 1.2}, {"t": 2.0, "scale": 1.1}]
        e = rendu.expr_lin(pts, "scale", "T")
        clip = lambda x, a, b: max(a, min(b, x))  # noqa: E731
        for t in (0, 0.5, 1, 1.5, 2, 3):
            self.assertAlmostEqual(eval(e.replace("T", str(t)), {"clip": clip}),
                                   cadrage.echelle([{**p, "x": 0, "y": 0} for p in pts], t)[0], places=4)


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg absent")
class MiniRenduTest(unittest.TestCase):
    """Un morceau de 3 s : deux plans de synthèse, un glissement, un zoom, une scène par-dessus, l'éclaircissement."""
    def test_morceau(self):
        with TempDir() as d:
            d = Path(d)
            for nom, couleur in (("a", "red"), ("b", "blue")):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=1920x1080:r=60:d=6",
                                "-vf", f"drawbox=c={couleur}:t=40", "-c:v", "libx264", "-preset", "ultrafast", str(d / f"{nom}.mp4")], check=True)
            (d / "scenes").mkdir()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=green:s=1920x1080:r=60:d=0.5",
                            "-c:v", "libx264", "-preset", "ultrafast", str(d / "scenes" / "s.mp4")], check=True)
            pieces = rendu.visibles([seg(str(d / "a.mp4"), 0, 1.5, 1.0), seg(str(d / "b.mp4"), 1.5, 3, 2.0)])
            with contextlib.redirect_stdout(io.StringIO()):
                z = cadrage.plan_zooms([{"id": i, "start": p["a"] / F, "length": (p["b"] - p["a"]) / F, "path": p["file"], "level": 1,
                                         "src": p["src"]} for i, p in enumerate(pieces)],
                                       [{"at": 0.2, "dur": 0.8, "scale": 1.12, "x": 0.05, "y": 0.0}], None)
            for i, p in enumerate(pieces):
                p["points"], p["t0"] = (z.get(i) or {}).get("points", []), 0.0
            r = object.__new__(rendu.Rendu)
            r.out, r.dir, r.leger, r.entree = d, d / "rendu", False, "eclaircissement"
            r.dir.mkdir()
            r.glisses = [{"a": int(1.25 * F), "b": int(1.75 * F), "sens": "haut"}]
            r.pieces = rendu.avec_glissements(pieces, r.glisses)
            r.calques = [{"file": "scenes/s.mp4", "at": 2.4, "dur": 0.5, "layer": 2}]
            with contextlib.redirect_stdout(io.StringIO()):
                m = r.morceau(0, 0, 3 * F)
                r.morceau(0, 0, 3 * F)                      # deuxième fois : repris du cache
            n = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                "stream=nb_read_packets", "-of", "csv=p=0", str(m)], capture_output=True, text=True).stdout.strip()
            self.assertEqual(int(n), 3 * F)
            def couleur(t):
                out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(m), "-frames:v", "1", "-vf", "scale=1:1",
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
                return tuple(out[:3])
            vert = couleur(2.6)
            self.assertGreater(vert[1], 100)                 # la scène est bien par-dessus
            self.assertLess(vert[0], 80)

    def test_short_vertical_recadre_autour_de_cx(self):
        """Short (1080×1920) : un rush 16:9 moitié rouge (gauche), moitié bleue (droite), recadré à gauche puis à droite."""
        with TempDir() as d:
            d = Path(d)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=960x1080:r=60:d=3", "-f", "lavfi",
                            "-i", "color=c=blue:s=960x1080:r=60:d=3", "-filter_complex", "[0][1]hstack", "-c:v", "libx264",
                            "-preset", "ultrafast", str(d / "r.mp4")], check=True)
            ancien = rendu.W, rendu.H
            rendu.W, rendu.H = 1080, 1920
            try:
                pieces = [{**seg(str(d / "r.mp4"), 0, 1), "cx": 0.0, "points": [], "t0": 0.0},
                          {**seg(str(d / "r.mp4"), 1, 2, 1.0), "cx": 1.0, "points": [], "t0": 0.0}]
                r = object.__new__(rendu.Rendu)
                r.out, r.dir, r.leger, r.entree = d, d / "rendu", False, ""
                r.dir.mkdir()
                r.glisses, r.pieces, r.calques = [], pieces, []
                with contextlib.redirect_stdout(io.StringIO()):
                    m = r.morceau(0, 0, 2 * F)
            finally:
                rendu.W, rendu.H = ancien
            taille = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                     "-of", "csv=p=0", str(m)], capture_output=True, text=True).stdout.strip()
            self.assertEqual(taille, "1080,1920")
            def couleur(t):
                out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(m), "-frames:v", "1", "-vf", "scale=1:1",
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
                return tuple(out[:3])
            gauche, droite = couleur(0.5), couleur(1.5)
            self.assertGreater(gauche[0], 150); self.assertLess(gauche[2], 80)
            self.assertGreater(droite[2], 150); self.assertLess(droite[0], 80)


class RecadrageTest(unittest.TestCase):
    def test_recadrage_coupe_la_piste_principale_et_donne_cx(self):
        d = {"materials": {"videos": [{"id": "m", "path": "r.mkv"}]},
             "tracks": [{"type": "video", "flag": 0, "segments": [
                 {"material_id": "m", "target_timerange": {"start": 0, "duration": 10_000_000},
                  "source_timerange": {"start": 5_000_000, "duration": 10_000_000}}]}]}
        plan = {"items": [{"file": "p.mkv", "at": 1.0, "dur": 1.0, "src": 0.0, "layer": 1, "cx": 0.9}]}
        segs = rendu.segments_base(d, plan, {"items": []}, [[4.0, 6.0, 0.2]], 0.5)
        principale = [(s["a"] / F, s["b"] / F, s["src"], s["cx"]) for s in segs if s["niveau"] == 0]
        self.assertEqual(principale, [(0, 4, 5.0, 0.5), (4, 6, 9.0, 0.2), (6, 10, 11.0, 0.5)])
        self.assertEqual(next(s["cx"] for s in segs if s["niveau"] == 100), 0.9)
        self.assertEqual([p["cx"] for p in rendu.visibles(segs)], [0.5, 0.9, 0.5, 0.2, 0.5])

    def test_borne_de_recadrage_arrondie_a_l_image(self):
        """Un clip qui commence à l'image 694 (11,5667 s) prend la plage [11.567, …] (site-ennui, 2026-10-08)."""
        d = {"materials": {"videos": [{"id": "m", "path": "r.mkv"}]},
             "tracks": [{"type": "video", "flag": 0, "segments": [
                 {"material_id": "m", "target_timerange": {"start": 11_566_667, "duration": 4_566_667}}]}]}
        segs = rendu.segments_base(d, {"items": []}, {"items": []}, [[8.8, 11.567, 0.5], [11.567, 16.133, 0.3]], 0.5)
        self.assertEqual([s["cx"] for s in segs], [0.3])


if __name__ == "__main__":
    unittest.main()
