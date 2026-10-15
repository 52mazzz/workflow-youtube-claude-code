"""Règles du montage « duel lisible et nerveux » (2026-10-08) : cadrage (respiration, zooms rapides), sans CapCut."""
import contextlib, io, sys, unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT / "montage" / "08_HYPERFRAMES" / "scripts"))
import cadrage  # noqa: E402
import audio  # noqa: E402
import export_capcut  # noqa: E402
import verifie_plan as vp  # noqa: E402
import zooms  # noqa: E402

SLOW = {"scale": 1.08, "periode": 14.0, "min_dur": 5.0}


def seg(i, st, ln, path="a.mkv", src=None):
    return {"id": i, "start": st, "length": ln, "path": path, "level": 1, "src": st if src is None else src}


def plan(segs, punch=()):
    with contextlib.redirect_stdout(io.StringIO()):
        return cadrage.plan_zooms(segs, list(punch), SLOW)


def courbe(z, segs, pas=1 / 60):
    """échelle image par image sur toute la timeline : [(t, échelle, id du plan)]"""
    out = []
    for s in sorted(segs, key=lambda s: s["start"]):
        pts = (z.get(s["id"]) or {}).get("points", [])
        n = int(s["length"] / pas)
        for k in range(n):
            out.append((s["start"] + k * pas, cadrage.echelle(pts, k * pas)[0], s["id"]))
    return out


class CadrageTest(unittest.TestCase):
    def test_respiration_continue_sur_les_jump_cuts(self):
        # 30 s de jump cuts du même moment (0,4 s sautée à chaque coupe) : une seule séquence
        segs = [seg(f"s{i}", 3 * i, 3, src=3 * i + 0.4 * i) for i in range(10)]
        with contextlib.redirect_stdout(io.StringIO()):
            z = cadrage.plan_zooms(segs, [], {**SLOW, "mode": "vague"})   # ancien mode, gardé en option
        c = courbe(z, segs)
        sauts = [abs(b[1] - a[1]) for a, b in zip(c, c[1:])]
        self.assertLess(max(sauts), 0.002)                      # aucun à-coup, même aux coupes
        self.assertAlmostEqual(max(e for _, e, _ in c), 1.08, places=3)
        self.assertGreater(min(e for t, e, _ in c if 6 < t < 8), 1.075)     # au plus haut vers 7 s et 21 s,
        self.assertLess(max(e for t, e, _ in c if 13.5 < t < 14.5), 1.005)  # revenu tout doucement vers 14 s
        self.assertAlmostEqual(cadrage.echelle(z["s0"]["points"], 0)[0], 1.0)

    def test_pousse_lente_puis_retour_net_au_debut_de_phrase(self):
        """Mode par défaut (retour du 2026-10-08) : 1 → 1,08 en T/2, tenu, retour à 1 en une image au début d'une phrase."""
        slow = {**SLOW, "remises": [4.0, 4.3, 9.0]}            # 4,3 : trop près de 4,0, ignorée
        segs = [seg("p", 0, 12)]
        with contextlib.redirect_stdout(io.StringIO()):
            pts = cadrage.plan_zooms(segs, [], slow)["p"]["points"]
        e = lambda t: cadrage.echelle(pts, t)[0]  # noqa: E731
        self.assertAlmostEqual(e(3.98), 1 + 0.08 * 3.98 / 7, places=3)
        self.assertAlmostEqual(e(4.0), 1.0, places=4)          # retour net
        self.assertGreater(e(4.0 - 1 / 60), 1.04)              # une image avant : encore zoomé
        self.assertAlmostEqual(e(8.9), 1 + 0.08 * 4.9 / 7, places=3)
        self.assertAlmostEqual(e(9.0), 1.0, places=4)
        c = [e(k / 60) for k in range(12 * 60 - 3)]
        sauts = [i / 60 for i, (a, b) in enumerate(zip(c, c[1:])) if abs(b - a) > 0.002]
        self.assertTrue(all(abs(t - 4.0) < 0.02 or abs(t - 9.0) < 0.02 for t in sauts), sauts)

    def test_nouvelle_sequence_repart_de_1(self):
        segs = [seg("a", 0, 8), seg("b", 8, 8, src=60.0), seg("c", 16, 3, "b.mkv")]
        z = plan(segs)
        self.assertAlmostEqual(z["b"]["points"][0]["scale"], 1.0)
        self.assertNotIn("c", z)                               # plan court seul : immobile, pas de mouvement inventé

    def test_zoom_rapide_part_de_l_echelle_en_cours_et_sort_par_la_coupe(self):
        segs = [seg("s1", 0, 4), seg("s2", 4, 4, src=4.3), seg("s3", 8, 4, src=8.6)]
        z = plan(segs, [{"at": 5.0, "dur": 1.2, "scale": 1.12}])
        avant = cadrage.echelle(z["s2"]["points"], 0.99)[0]
        haut = cadrage.echelle(z["s2"]["points"], 1.5)[0]
        self.assertGreater(avant, 1.0)
        self.assertAlmostEqual(haut / cadrage.respiration(5.5, 12, SLOW), 1.12, places=2)
        self.assertGreater(cadrage.echelle(z["s2"]["points"], 3.9)[0], 1.12)   # tenu jusqu'à la coupe (< 3 s)
        self.assertTrue(z["s2"]["ease"])
        # entrée adoucie : pas plus de 0,03 d'échelle par image
        c = [cadrage.echelle(z["s2"]["points"], k / 60)[0] for k in range(60, 80)]
        self.assertLess(max(abs(b - a) for a, b in zip(c, c[1:])), 0.03)

    def test_zoom_de_lecture_loin_de_la_coupe_revient_en_douceur(self):
        segs = [seg("y", 0, 12)]
        z = plan(segs, [{"at": 2.0, "dur": 1.5, "scale": 1.8, "x": 0.4, "y": -0.2}])
        pts = z["y"]["points"]
        self.assertGreater(cadrage.echelle(pts, 3.0)[0], 1.75)
        apres = cadrage.echelle(pts, 4.0)
        self.assertAlmostEqual(apres[0], cadrage.respiration(4.0, 12, SLOW), places=3)
        self.assertEqual(apres[1:], (0.0, 0.0))
        c = [cadrage.echelle(pts, k / 60)[0] for k in range(0, 600)]
        self.assertLess(max(abs(b - a) for a, b in zip(c, c[1:])), 0.06)
        d = [b - a for a, b in zip(c, c[1:])]
        self.assertLess(max(abs(y - x) for x, y in zip(d, d[1:])), 0.012)   # aucun à-coup (revue.py : même seuil)

    def test_zoom_colle_a_une_coupe_passe_au_plan_suivant_ou_est_ecarte(self):
        segs = [seg("s1", 0, 4), seg("s2", 4, 4, src=4.2), seg("x", 8, 4, "b.mkv")]
        z = plan(segs, [{"at": 3.9, "dur": 1.0, "scale": 1.1}, {"at": 11.9, "dur": 1.0, "scale": 1.1}])
        self.assertTrue(z["s2"]["ease"])
        self.assertFalse(z["s1"]["ease"])
        self.assertNotIn("x", z)

    def test_zoom_sans_plan_de_jeu_ecarte(self):
        z = plan([seg("a", 0, 3)], [{"at": 10.0, "dur": 1.0, "scale": 1.1}])
        self.assertEqual(z, {})



def el(i, t, at, dur, **v):
    return {"id": i, "type": t, "at": at, "dur": dur, "vars": v}


DUEL = dict(nomA="CLAUDE", nomB="CHATGPT", logoA="claude", logoB="chatgpt")


class VerifiePlanTest(unittest.TestCase):
    def erreurs(self, els, cfg=None, fin=None):
        return [x for _, x in vp.verifier(els, cfg, fin)[0]]

    def test_plan_propre(self):
        els = [el("d", "duel", 3, 2.5, **DUEL), el("c", "carte", 10, 12, texte="CLAUDE", logo="claude", plein=1.2),
               el("p", "pastille", 11.5, 10, texte="Le combat", etat=[[5, "ok"]]), el("m", "minuteur", 12, 4, de=60),
               el("r", "reaction", 14, 1.9, humeur="rire"), el("x", "accelere", 12, 4, texte="×10")]
        self.assertEqual(self.erreurs(els, fin=30), [])

    def test_faute_de_frappe_et_valeur_d_exemple(self):
        e = self.erreurs([el("n", "note", 0, 3, nom="CLAUDE", logo="claude", note="7/10", point=[["+", "x"]])])
        self.assertTrue(any("« point » inconnue" in x for x in e))
        self.assertTrue(any("« points » à donner" in x for x in e))

    def test_variable_lue_par_le_kit_sans_etre_declaree(self):
        e = self.erreurs([el("f", "scene_fenetre", 0, 3, titre="T", lignes=[], tsarDe=1)])
        self.assertFalse(any("tsarDe" in x for x in e))

    def test_deux_elements_au_meme_endroit(self):
        # minuteur en haut à droite pendant la carte réduite : refusé ; Tsar et l'accéléré : plus en conflit (2026-10-08)
        els = [el("c", "carte", 0, 10, texte="CLAUDE", plein=1.2), el("m", "minuteur", 3, 3, de=60, position="haut-droite")]
        self.assertTrue(any("au même endroit" in x for x in self.erreurs(els)))
        self.assertFalse(self.erreurs([el("r", "reaction", 0, 1.9, humeur="rire"), el("x", "accelere", 0, 4, texte="×10")]))

    def test_image_et_fin(self):
        e = self.erreurs([el("i", "insert", 50, 0.8, image="videos/rien.png")], fin=40)
        self.assertTrue(any("introuvable" in x for x in e))
        self.assertTrue(any("après la fin" in x for x in e))

    def test_transitions_et_zooms_de_l_accroche(self):
        els = [el("a", "a_venir", 10, 3)]
        cfg = {"transitions": [[8.0, "flash", ""], [20.0, "flash", ""]],
               "zooms": {"punch": [[30, 1, 1.12, .5, .5, ""], [31, 1, 1.3, .5, .5, ""]]}}
        w = [x for _, x in vp.verifier(els, cfg)[1]]
        self.assertTrue(any("dans l'accroche" in x and "8.0" in x for x in w))
        self.assertFalse(any("20.0 s dans l'accroche" in x for x in w))
        self.assertTrue(any("jamais deux de suite" in x for x in w))
        self.assertTrue(any("hors des familles" in x for x in w))

    def test_pleins_ecrans_et_accroche(self):
        els = [el("c", "carte", 10, 12, texte="X", plein=1.2), el("p", "progression", 30, 2.5), el("d", "duel", 3, 2, **DUEL)]
        f = vp.plein_ecran(els)
        self.assertEqual([i for _, _, i in f], ["c", "p"])
        self.assertLess(f[0][1], 11.5)                       # la carte n'est plein écran que pendant `plein`
        self.assertEqual(vp.fin_accroche(els), 5)


class ZoomsChoixTest(unittest.TestCase):
    def test_zooms_ecartes(self):
        els = [el("p", "progression", 10, 2.5)]
        with contextlib.redirect_stdout(io.StringIO()):
            garde = zooms.choisir([[5, 1, 1.1, .5, .5, ""], [6, 1, 1.1, .5, .5, ""], [11, 1, 1.1, .5, .5, ""], [20, 1, 1.6, .5, .5, ""]], els)
        self.assertEqual([z[0] for z in garde], [5, 20])


class BruitagesTest(unittest.TestCase):
    def test_arbitre(self):
        cues = [(10.0, "whoosh_court", "carte"), (10.05, "impact", "carte"), (10.02, "pop", "pastille"), (10.1, "whoosh", "tr"),
                (10.5, "tick", "zoom"), (10.6, "tick", "cap"), (10.7, "pop", "fl"), (12, "pop", "x")]
        g, r = audio.arbitre(cues)
        self.assertIn((10.05, "impact", "carte"), g)          # la paire voulue d'un même élément reste
        self.assertIn((10.0, "whoosh_court", "carte"), g)
        self.assertIn((10.02, "pop", "pastille"), r)          # deux éléments au même instant : un seul son
        self.assertIn((12, "pop", "x"), g)
        for t, *_ in g:                                        # au plus 3 moments sonores par seconde
            self.assertLessEqual(len({c[2] for c in g if t <= c[0] < t + 1}), 3)

    def test_carte_sans_reduction_sans_whoosh(self):
        self.assertEqual(len(export_capcut.sfx_of(el("c", "carte", 0, 1.2, plein=1.2))), 2)
        self.assertEqual(len(export_capcut.sfx_of(el("c", "carte", 0, 8, plein=1.2))), 3)

    def test_couches(self):
        self.assertEqual(export_capcut.couche({"type": "pastille"}, False, False), 6)
        self.assertEqual(export_capcut.couche({"type": "flash"}, False, False), 9)
        self.assertEqual(export_capcut.couche({"type": "progression"}, True, False), 2)


if __name__ == "__main__":
    unittest.main()
