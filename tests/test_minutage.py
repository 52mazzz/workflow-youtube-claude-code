"""minutage.py (les phrases tiennent dans leur créneau) et le seuil de silence du montage (son du jeu sous la voix)."""
import json, shutil, subprocess, sys, unittest
from unittest import mock

from helpers import ROOT, SKILLS, TempDir, run

MINUTAGE = SKILLS / "yt-script" / "minutage.py"
SCRIPTS = ROOT / "montage" / "08_HYPERFRAMES" / "scripts"

SCRIPT = """# Script

## Beat 1. Accroche (0:00 à 0:15)

**Version A**

- **0-2 s** [ON SCREEN : le plan [FORT]] : « Claude et ChatGPT refont Pokémon de zéro, avec un seul prompt. »
- **2-6 s** : « Si vous partez, vous ratez [LE CONTRASTE, 4 mots au plus]. »
- **6-10 s** : « Alors, qui gagne ? »

## Beat 2. Le défi (0:15 à 0:25)

> « Voilà le défi : la même consigne pour les deux. »
"""


class MinutageTest(unittest.TestCase):
    def test_slots(self):
        with TempDir() as d:
            p = d / "script.md"
            p.write_text(SCRIPT, encoding="utf-8")
            r = run(MINUTAGE, p, "--json")
            self.assertEqual(r.returncode, 1)                                  # 11 mots en 2 s : déborde
            res = {x["creneau"]: x for x in json.loads(r.stdout)}
            a = res["version A 0-2 s"]
            self.assertEqual((a["mots"], a["verdict"], a["mots_max"]), (11, "dépasse", 6))   # 200 mots / min depuis le 2026-10-07
            self.assertEqual(res["version A 2-6 s"]["mots"], 9)                 # 5 dits + budget de 4 du crochet
            self.assertEqual(res["version A 6-10 s"]["verdict"], "ok")
            self.assertEqual(res["Beat 2. Le défi"]["mots"], 9)
            self.assertNotIn("FORT", a["texte"])                                # le [ON SCREEN] n'est pas dit
            p.write_text(SCRIPT.replace("Claude et ChatGPT refont Pokémon de zéro, avec un seul prompt.", "Pokémon de zéro."),
                         encoding="utf-8")
            r = run(MINUTAGE, p)
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("voix haute", r.stdout)


@unittest.skipIf(shutil.which("ffmpeg") is None, "ffmpeg absent")
class SeuilSilenceTest(unittest.TestCase):
    def test_game_sound_raises_threshold(self):
        sys.path.insert(0, str(SCRIPTS))
        import commun
        with TempDir() as d, mock.patch.object(commun, "ANALYSE", d):   # cache hors du vrai 02_ANALYSE
            voice ="sine=f=300:d=10,volume=0.3,volume='if(lt(mod(t,2),1),1,0)':eval=frame"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", voice, "-f", "lavfi", "-i",
                            "anoisesrc=c=pink:a=0.025:d=10", "-filter_complex", "amix=inputs=2:normalize=0",
                            str(d / "jeu.wav")], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", voice, str(d / "calme.wav")], check=True)
            self.assertEqual(commun.seuil_silence(d / "calme.wav"), -40.0)
            seuil = commun.seuil_silence(d / "jeu.wav")
            self.assertTrue(-36 < seuil < -26, seuil)
            err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(d / "jeu.wav"), "-af",
                                  f"silencedetect=n={seuil}dB:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
            self.assertEqual(err.count("silence_end"), 5)                       # les 5 pauses de la voix


class TakesMapTest(unittest.TestCase):
    def test_long_blocks_split_on_voice(self):
        sys.path.insert(0, str(SCRIPTS))
        import takes_map as tm
        # bloc long redécoupé aux pauses du VAD (morceaux d'au plus MAX_BLOC = 20 s) ; bloc court ou sans VAD : inchangé
        self.assertEqual(tm.decouper(0, 100, [(1, 5), (5.3, 9), (20, 35), (40, 45)]), [(1, 9), (20, 35), (40, 45)])
        self.assertEqual(tm.decouper(0, 10, [(1, 5)]), [(0, 10)])
        self.assertEqual(tm.decouper(0, 100, None), [(0, 100)])

class ControleTest(unittest.TestCase):
    def test_erreurs_du_rendu(self):
        sys.path.insert(0, str(SCRIPTS))
        import controle as vr
        m = lambda texte, t0=0.0: [(w, t0 + k * 0.4, t0 + k * 0.4 + 0.3) for k, w in enumerate(texte.split())]
        # même phrase deux fois : une seule redite ; trois fois d'affilée : boucle de Whisper, ignorée
        phrase = "il a mis vingt deux creatures dans le jeu "
        mots = m("alors " + phrase + "bon " + phrase + "et voila")
        red = vr.redites_longues(mots)
        self.assertEqual(len(red), 1)
        self.assertEqual(red[0][2], phrase.strip())
        self.assertEqual(vr.redites_longues(m("on y va " + phrase * 3)), [])
        self.assertEqual(vr.redites_longues(m(phrase) + m(phrase, 200.0)), [])               # trop loin : pas une redite
        # passage du dérush absent ; sous-titre qui ne colle pas
        clips = [("Beat 1", "On va voir lequel s'en sort le mieux"), ("Beat 5", "il est parti sur créaturia"),
                 ("Beat 5", "(suite)"), ("Beat 6", "je passe à ChatGPT maintenant")]
        dit = m("on va voir lequel sen sort le mieux il est parti sur creaturia")
        self.assertEqual(vr.absents(clips, dit), [("Beat 6", "je passe à ChatGPT maintenant")])
        self.assertEqual(vr.sous_titres_faux([[0.0, "On va voir"], [2.8, "Il est parti"], [10.0, "C'est stylé"]], dit),
                         [(10.0, "C'est stylé", "(rien)")])
        self.assertEqual(vr.micro_clips([(0, 5.0, "a.mkv"), (5.0, 0.1, "a.mkv"), (5.1, 0.1, "(clip combiné)")]),
                         [(5.0, 0.1, "a.mkv")])


    def test_pauses_coupes_et_faux_departs(self):
        sys.path.insert(0, str(SCRIPTS))
        import controle as c
        import nettoie_derush as n
        m = lambda texte: [(w, k * 0.3, k * 0.3 + 0.2) for k, w in enumerate(texte.split())]
        # musique du jeu seule entre deux phrases : pause signalée au-delà de 1 s
        self.assertEqual(c.pauses([(0, 3), (3.4, 6), (11, 14)], 1.0), [(6, 11)])
        # coupe au milieu d'un mot (voix des deux côtés) ; coupe dans un creux ou hors voix : rien
        db = lambda t0, t1: -60.0 if 9.9 <= t0 <= 10.0 else -20.0
        self.assertEqual(c.coupes_dans_la_voix([5.0, 10.0, 20.0], db, -40, [(0, 12)]), [(5.0, -20.0, -20.0)])
        # coupe dans la fermeture d'une consonne (« descri|ption ») : 100 ms de silence, voix autour
        db = lambda t0, t1: -60.0 if 4.95 <= t0 and t1 <= 5.05 + 1e-9 else -20.0
        self.assertEqual(len(c.coupes_dans_la_voix([5.0], db, -40, [(0, 12)])), 1)
        # voix forte jusqu'à la coupe, puis 90 ms de silence numérique, puis reprise (« description », 12,07 s de pokemon-ia)
        db = lambda t0, t1: -120.0 if 5.0 <= t0 < 5.09 else -20.0
        self.assertEqual(len(c.coupes_dans_la_voix([5.0], db, -40, [(0, 12)])), 1)
        self.assertEqual(c.coupes_dans_la_voix([5.0], db, -40, [(6, 12)]), [])         # hors d'un passage parlé
        # « et en vrai, et en vrai » et « je vais… je sais pas… je vais » ; « il a… il a » n'en est pas un
        self.assertEqual(n.faux_departs(m("et en vrai et en vrai cest nul"))[0][2], "et en vrai")
        self.assertEqual(n.faux_departs(m("je vais euh je sais pas je vais lui dire"))[0][2], "je vais euh je sais pas")
        self.assertEqual(n.faux_departs(m("il a fait un truc il a vu")), [])
        self.assertEqual(n.fusion([(0, 1), (0.5, 2), (3, 4)]), [(0, 2), (3, 4)])

class EmpreinteTest(unittest.TestCase):
    def test_stale_output_is_detected(self):
        sys.path.insert(0, str(SCRIPTS))
        import commun
        with TempDir() as d:
            src, dst = d / "compo.html", d / "rendu.mov"
            src.write_text("<div>v1</div>", encoding="utf-8")
            e1 = commun.empreinte("etiquette", 2.0, {"texte": "A"}, fichiers=[src])
            self.assertFalse(commun.a_jour(dst, e1))                          # rien de rendu
            dst.write_bytes(b"x"); commun.marquer(dst, e1)
            self.assertTrue(commun.a_jour(dst, e1))
            self.assertFalse(commun.a_jour(dst, commun.empreinte("etiquette", 2.0, {"texte": "B"}, fichiers=[src])))   # variable
            self.assertFalse(commun.a_jour(dst, commun.empreinte("etiquette", 2.5, {"texte": "A"}, fichiers=[src])))   # durée
            src.write_text("<div>v2</div>", encoding="utf-8")
            self.assertFalse(commun.a_jour(dst, commun.empreinte("etiquette", 2.0, {"texte": "A"}, fichiers=[src])))   # composition


if __name__ == "__main__":
    unittest.main()
