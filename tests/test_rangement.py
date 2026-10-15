import json, os, subprocess, sys, time, unittest
from datetime import date
from helpers import ROOT, TempDir, run

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import rangement  # noqa: E402
import garde  # noqa: E402

RANGEMENT = ROOT / "rangement.py"
TODAY = date(2026, 10, 8)


def touch(path, data="", age_days=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    if age_days:
        t = time.time() - age_days * 86400
        os.utime(path, (t, t))
    return path


def video(d, vid, statut="en cours", publiee=""):
    touch(d / "videos" / vid / "suivi.md", f"- Statut : {statut}\n- Publiée le : {publiee}\n")


class RulesTest(unittest.TestCase):
    def test_emplacement(self):
        ok = ["CLAUDE.md", "rangement.py", "videos/pokemon-ia/script.md", "videos/mod-minecraft-ia/bilans/x.json",
              "videos/pokemon-ia/miniatures/captures/a.png", "videos/veille-2026-10-08/idees.md",
              "config/youtube/conseils/2026-10-03.md", "config/agents/archiviste.md", "secrets/youtube.enc",
              "tests/test_x.py", "tests/helpers.py", "montage/02_ANALYSE/derush_pokemon-ia_court.json",
              "montage/02_ANALYSE/vue_pokemon-ia - final 3.txt", "montage/02_ANALYSE/prises/2026-10-02 09-40-21.txt",
              "montage/02_ANALYSE/controle_pokemon-ia - final 3/a.png", "montage/08_HYPERFRAMES/videos/x/plan.json",
              ".claude/hooks/garde.py", "skills/yt-script/hookscore.py", "videos/.obsidian/app.json"]
        for rel in ok:
            self.assertIsNone(rangement.emplacement(rel), rel)
        bad = ["notes.md", "brouillon/x.md", "videos/notes.md", "videos/Pokemon IA/script.md",
               "videos/pokemon-ia/capture.png", "videos/pokemon-ia/rushs/a.txt", "config/autre/x.md",
               "config/youtube/conseils/conseil.md", "secrets/token.json", "tests/fixture.json",
               "montage/02_ANALYSE/notes.txt", "montage/02_ANALYSE/divers/x.txt", "montage/09_AUTRE/x",
               "montage/08_HYPERFRAMES/brouillon.html"]
        for rel in bad:
            self.assertIsNotNone(rangement.emplacement(rel), rel)

    def test_forme(self):
        for rel in ("videos/pokemon-ia/script-v2.md", "videos/pokemon-ia/script copie.md", "config/youtube/old_notes.md",
                    "skills/short/SKILL (1).md", "videos/pokemon-ia/Titres.txt", "videos/pokemon-ia/idées.md",
                    "tests/test_tmp.py", "videos/pokemon-ia/script-final-final.md"):
            self.assertIsNotNone(rangement.forme(rel), rel)
        for rel in ("videos/pokemon-ia/script-avant-revision-aywen.md", "skills/short/SKILL.md",
                    "videos/pokemon-ia/bilans/2026-10-06-J3-brouillon.md", "config/youtube/references/2026-10-01-veille-2.json",
                    "skills/youtube/templates/x.md", "montage/02_ANALYSE/vue_pokemon-ia - final 3.txt"):
            self.assertIsNone(rangement.forme(rel), rel)

    def test_interdit_dans_git(self):
        for rel, size in (("x/rush.MKV", 1), ("a.json", 51 * rangement.MO), ("client_secret_123.json", 1),
                          ("config/youtube_oauth_token.json", 1), (".env", 1), ("skills/a/__pycache__/b.pyc", 1),
                          ("montage/08_HYPERFRAMES/build/a.html", 1), ("videos/a-b/x.tmp", 1), ("~$script.docx", 1),
                          ("videos/Thumbs.db", 1), ("montage/02_ANALYSE/voix.wav", 1)):
            self.assertIsNotNone(rangement.interdit_dans_git(rel, size), rel)
        for rel in ("secrets/youtube-oauth-token.enc", "montage/04_RESSOURCES/sfx/synth/impact.wav",
                    "montage/08_HYPERFRAMES/assets/sfx/riser.wav", "videos/pokemon-ia/script.md"):
            self.assertIsNone(rangement.interdit_dans_git(rel, 10), rel)

    def test_real_repo(self):
        """What git holds follows the rules (the CI fails on any drift)."""
        r = run(RANGEMENT, "--git", env={"CLAUDE_REPO": str(ROOT)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class RepoTest(unittest.TestCase):
    def test_structure(self):
        with TempDir() as d:
            v, a = d / "videos", d / "montage" / "02_ANALYSE"
            video(d, "pokemon-ia", "publiée", "2026-10-03")
            for name in ("sans-suivi", "veille-2026-10-07", "veille-2026-09-20"):
                (v / name).mkdir(parents=True)
            (d / "montage" / "08_HYPERFRAMES" / "videos" / "glacon-ia").mkdir(parents=True)
            (d / "skills" / "orphelin").mkdir(parents=True)
            for f in ("derush_pokemon-ia_court.json", "vue_pokemon-ia - final 3.txt", "derush_glacon-ia_short.json",
                      "controle_export_pokemon-ia.txt", "vue_0912 - final.txt", "fond_sonore.json"):
                touch(a / f)
            out = "\n".join(rangement.structure(d, TODAY))
            self.assertIn("videos/sans-suivi : pas de suivi.md", out)
            self.assertIn("videos/veille-2026-09-20 : veille de plus de 3 jours", out)
            self.assertNotIn("veille-2026-10-07", out)                    # veille en cours
            self.assertIn("02_ANALYSE/vue_0912 - final.txt : ne nomme aucune vidéo connue", out)
            self.assertEqual(out.count("02_ANALYSE"), 1)                   # ids des deux dossiers, fichiers communs ignorés
            self.assertIn("skills/orphelin : pas de SKILL.md", out)

    def test_vider_only_safe_caches(self):
        with TempDir() as d:
            video(d, "pokemon-ia", "publiée", "2026-10-03")
            video(d, "sukuna-ia")
            a, hf = d / "montage" / "02_ANALYSE", d / "montage" / "08_HYPERFRAMES"
            gone = [touch(d / "skills" / "x" / "__pycache__" / "a.pyc"),
                    touch(a / "audio_16k" / "capcut_pokemon-ia - final 3.wav", "x" * 1000),
                    touch(a / "capcut_pokemon-ia - final 3_segments.tsv"),
                    touch(a / "controle_pokemon-ia - final 3" / "planche.png"),
                    touch(hf / "build" / "pokemon-ia" / "a.html"),
                    touch(a / "audio_16k" / "rush_2026-09-01 10-00-00.wav", age_days=20)]
            kept = [touch(a / "audio_16k" / "capcut_sukuna-ia - final.wav"),     # pas publiée
                    touch(a / "audio_16k" / "rush_2026-10-07 10-00-00.wav", age_days=1),
                    touch(hf / "build" / "sukuna-ia" / "a.html"),
                    touch(d / "montage" / "06_CAPCUT" / "pokemon-ia" / "__pycache__" / "x.pyc"),  # jamais touché
                    touch(d / "montage" / "06_CAPCUT" / "pokemon-ia" / "rendu" / "m000.mp4"),
                    touch(a / "vue_pokemon-ia - final 3.txt"),
                    touch(d / "videos" / "pokemon-ia" / "veille" / "a.json")]
            stale = touch(a / "capcut_sukuna-ia - final_segments.tsv")
            touch(a / "audio_16k" / "capcut_sukuna-ia - final 2.wav")
            today = date.today()                                          # âges comptés depuis les vraies dates des fichiers
            auto, propose = rangement._caches(d, today)
            proposed = {p.relative_to(d).as_posix() for p, _ in propose}
            self.assertIn("montage/02_ANALYSE/capcut_sukuna-ia - final_segments.tsv", proposed)  # ancien projet
            self.assertIn("videos/pokemon-ia/veille", proposed)
            self.assertIn("montage/06_CAPCUT/pokemon-ia/rendu", proposed)
            freed = rangement.vider(d, today)
            self.assertTrue(freed)
            for f in gone:
                self.assertFalse(f.exists(), f)
            for f in kept + [stale]:
                self.assertTrue(f.exists(), f)

    def test_supprimer_refuses_unproposed(self):
        with TempDir() as d:
            video(d, "pokemon-ia", "publiée", "2026-10-03")
            veille = touch(d / "videos" / "pokemon-ia" / "veille" / "a.json")
            script = touch(d / "videos" / "pokemon-ia" / "script.md")
            env = {"CLAUDE_REPO": str(d)}
            r = run(RANGEMENT, "--supprimer", "videos/pokemon-ia/script.md", env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(script.exists())
            r = run(RANGEMENT, "--supprimer", "videos/pokemon-ia/veille", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(veille.exists())

    def test_ecarts_over_git(self):
        with TempDir() as d:
            git = lambda *a: subprocess.run(["git", "-C", str(d), *a], capture_output=True, check=True)
            git("init", "-q")
            video(d, "pokemon-ia")
            touch(d / "notes.md")
            touch(d / "videos" / "pokemon-ia" / "script-v2.md")
            touch(d / "config" / "youtube" / "a.md", "même contenu, assez long pour compter comme un doublon réel.....")
            touch(d / "config" / "youtube" / "b.md", "même contenu, assez long pour compter comme un doublon réel.....")
            (d / "config" / "youtube" / "latin1.md").write_bytes("café".encode("latin-1"))
            out = "\n".join(rangement.ecarts(d))
            self.assertIn("notes.md : rien d'autre à la racine", out)
            self.assertIn("script-v2.md : nom de version", out)
            self.assertIn("config/youtube/a.md, config/youtube/b.md : même contenu", out)
            self.assertIn("latin1.md : pas en UTF-8", out)


class GardeTest(unittest.TestCase):
    def test_hook(self):
        with TempDir() as d:
            touch(d / "CLAUDE.md")
            ask = lambda rel: garde.verdict({"tool_name": "Write", "tool_input": {"file_path": str(d / rel)}}, repo=d)
            self.assertIsNotNone(ask("brouillon.md"))
            self.assertIsNotNone(ask("videos/pokemon-ia/script-v2.md"))
            self.assertIsNotNone(ask("montage/08_HYPERFRAMES/compositions/a.html"))
            self.assertIsNotNone(ask("secrets/youtube.json"))
            self.assertIsNone(ask("CLAUDE.md"))                           # fichier existant : édition libre
            self.assertIsNone(ask("videos/pokemon-ia/notes.md"))
            self.assertIsNone(garde.verdict({"tool_input": {"file_path": str(d.parent / "ailleurs.md")}}, repo=d))
            edit = lambda rel, t: garde.verdict({"tool_name": "Edit", "tool_input": {"file_path": str(d / rel),
                                                                                    "new_string": t}}, repo=d)
            self.assertIn("règle remplacée", edit("CLAUDE.md", "- *(ancien, remplacé)* pas de whoosh"))
            self.assertIn("contrôle", edit("CLAUDE.md", "a\x08b"))
            self.assertIsNone(edit("CLAUDE.md", "x" * 9000))               # un Edit ne juge pas la taille du fichier
            write = garde.verdict({"tool_name": "Write", "tool_input": {"file_path": str(d / "CLAUDE.md"),
                                                                        "content": "x" * 9000}}, repo=d)
            self.assertIn("budget", write)

    def test_ecriture(self):
        e = rangement.ecriture
        self.assertEqual(e("skills/a/SKILL.md", "outil (ancien = projet) ; short.py (ancien style)"), [])
        self.assertTrue(e("skills/a/references/b.md", "(Avant le 2026-10-03) franches"))
        self.assertTrue(e("config/youtube/preferences.md", "~~Pas de whoosh~~"))
        self.assertEqual(e("videos/pokemon-ia/notes.md", "~~barré~~"), [])            # hors des docs relues
        self.assertTrue(e("skills/a/SKILL.md", "---\ndescription: " + "x" * 1100 + "\n---"))
        with TempDir() as d:
            subprocess.run(["git", "-C", str(d), "init", "-q"], capture_output=True, check=True)
            ligne = "- " + "une règle assez longue pour compter comme une vraie règle de la chaîne " * 3
            for rel, titre in (("skills/a/SKILL.md", "# a\n"), ("skills/b/SKILL.md", "# b\n")):
                touch(d / rel, titre + ligne + "\n")
            out = "\n".join(rangement.ecarts(d))
            self.assertIn("skills/a/SKILL.md, skills/b/SKILL.md : même règle recopiée", out)

    def test_hook_process(self):
        data = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "brouillon-v2.md")}})
        p = subprocess.run([sys.executable, str(ROOT / ".claude" / "hooks" / "garde.py")], input=data.encode("utf-8"),
                           capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("scratchpad", p.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
