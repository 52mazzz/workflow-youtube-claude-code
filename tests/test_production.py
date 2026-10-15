import os, re, subprocess, sys, unittest
from datetime import date, timedelta
from helpers import ROOT, SKILLS, TempDir, run

REPO_PY = SKILLS / "nouvelle-video" / "scripts" / "repo.py"
CHECK = SKILLS / "description-video" / "check_description.py"
ENVOI = ROOT / "envoi.py"
FICHE = SKILLS / "nouvelle-video" / "scripts" / "fiche.py"
sys.path.insert(0, str(REPO_PY.parent))
import repo  # noqa: E402

GOOD = """# Description : J'ai mis Claude et ChatGPT en duel sur Roblox

## Description
```text
Deux IA, une seule consigne : créer un jeu Roblox de zéro. Une seule a tenu jusqu'au bout.

Le prompt exact : « Crée un obby complet ». Modèles : Claude Opus 5.5, ChatGPT 6.

Chapitres
0:00 Le défi
0:42 Les règles
2:10 Claude
5:30 ChatGPT
8:05 Le verdict

Et vous, quel jeu je leur fais créer la prochaine fois ?

#roblox #ia #claude
```

## Tags
```text
roblox, ia roblox, claude vs chatgpt, ia jeu vidéo, créer un jeu avec une ia, chatgpt roblox
```
"""


class RepoTest(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(repo.slug("J'ai mis Claude et ChatGPT en duel sur Roblox"),
                         "j-ai-mis-claude-et-chatgpt-en-duel-sur-roblox")
        self.assertEqual(repo.slug("Minecraft devient RÉALISTE grâce à 2 IA !"), "minecraft-devient-realiste-grace-a-2-ia")
        long = repo.slug("mot " * 40)
        self.assertLessEqual(len(long), 60)
        self.assertFalse(long.endswith("-"))
        self.assertEqual(repo.slug("!!!"), "video")

    def test_root_and_video_and_list(self):
        with TempDir() as d:
            (d / "setup.py").write_text("", encoding="utf-8")
            env = {"CLAUDE_REPO": str(d)}
            self.assertEqual(run(REPO_PY, "root", env=env).stdout.strip(), str(d))
            r = run(REPO_PY, "video", "Mon Titre Génial", env=env)
            self.assertEqual(r.returncode, 1)                                   # ne crée plus rien en devinant
            self.assertFalse((d / "videos" / "mon-titre-genial").exists())
            out = run(REPO_PY, "video", "--creer", "titre genial", env=env).stdout.strip()
            self.assertTrue(out.endswith(os.path.join("videos", "titre-genial")))
            self.assertEqual(run(REPO_PY, "video", "titre-genial", env=env).stdout.strip(), out)
            (d / "videos" / "titre-genial" / "suivi.md").write_text(
                "# Suivi : Mon Titre Génial\n\n- [x] 1. Idée\n- [ ] 2. Accroches et script\n", encoding="utf-8")
            self.assertIn("2. Accroches et script", run(REPO_PY, "list", env=env).stdout)
            self.assertEqual(run(REPO_PY, "video", "Mon Titre Génial", env=env).stdout.strip(), out)   # par le titre

    def test_find_by_title_and_ambiguity(self):
        with TempDir() as d:
            env = {"CLAUDE_REPO": str(d)}
            for vid, title, alt in (("pokemon-ia", "J'ai mis Claude et ChatGPT en duel pour refaire Pokémon de zéro",
                                     "Claude et ChatGPT refont Pokémon avec 1 seul prompt | FACILE | recherche"),
                                    ("sukuna-ia", "J'ai fait coder Sukuna dans Minecraft à Claude et ChatGPT", "")):
                (d / "videos" / vid).mkdir(parents=True)
                (d / "videos" / vid / "suivi.md").write_text(f"# Suivi : {title}\n", encoding="utf-8")
                if alt: (d / "videos" / vid / "titres.txt").write_text(alt + "\n", encoding="utf-8")
            (d / "videos" / "veille-2026-10-01").mkdir()
            got = lambda *q: run(REPO_PY, "video", *q, env=env)
            self.assertTrue(got("J'ai mis Claude et ChatGPT en duel pour refaire Pokémon de zéro").stdout.strip().endswith("pokemon-ia"))
            self.assertTrue(got("Claude et ChatGPT refont Pokémon avec 1 seul prompt").stdout.strip().endswith("pokemon-ia"))
            self.assertTrue(got("pokemon").stdout.strip().endswith("pokemon-ia"))
            self.assertTrue(got("sukuna").stdout.strip().endswith("sukuna-ia"))
            amb = got("ia")
            self.assertEqual(amb.returncode, 2)
            self.assertIn("pokemon-ia", amb.stderr); self.assertIn("sukuna-ia", amb.stderr)
            self.assertEqual(got("roblox").returncode, 1)
            self.assertEqual(len(list((d / "videos").iterdir())), 3)            # rien créé

    def test_scheduled_release(self):
        today = date.today()
        with TempDir() as d:
            v = d / "videos" / "prog-ia"
            v.mkdir(parents=True)
            (v / "suivi.md").write_text(f"# Suivi : x\n\n- Statut : programmée\n- Programmée pour : {today - timedelta(days=4)} 18:00\n"
                                        "- Publiée le : [AAAA-MM-JJ]\n\n- [ ] 11. Bilan\n", encoding="utf-8")
            infos = repo.videos_info(d / "videos")
            self.assertEqual(infos[0]["status"], "programmée")
            due = repo.bilans_dus(infos, today)
            self.assertEqual(len(due), 1)
            self.assertIn("à confirmer", due[0])
            notes = repo.publications_oubliees(d / "videos", infos, today, online=False)
            self.assertTrue(any("sortie programmée" in n and "passée" in n for n in notes), notes)
            self.assertIn("programmée", run(REPO_PY, "list", env={"CLAUDE_REPO": str(d)}).stdout)
            (v / "suivi.md").write_text(f"- Statut : programmée\n- Programmée pour : {today + timedelta(days=2)} 18:00\n", encoding="utf-8")
            infos = repo.videos_info(d / "videos")
            self.assertEqual(repo.bilans_dus(infos, today), [])
            self.assertEqual(repo.publications_oubliees(d / "videos", infos, today, online=False), [])

    def test_short_id(self):
        with TempDir() as d:
            env = {"CLAUDE_REPO": str(d)}
            (d / "videos").mkdir()
            self.assertEqual(run(REPO_PY, "id", "Pokémon", "IA", env=env).stdout.strip(), "pokemon-ia")
            (d / "videos" / "pokemon-ia").mkdir()
            taken = run(REPO_PY, "id", "pokemon ia", env=env)
            self.assertNotEqual(taken.returncode, 0)
            self.assertIn("existe déjà", taken.stderr)
            self.assertNotEqual(run(REPO_PY, "id", "j'ai mis claude et chatgpt en duel", env=env).returncode, 0)

    def test_list_status_dates_and_bilans_due(self):
        today = date.today()
        def suivi(statut, visee="[AAAA-MM-JJ]", publiee="[AAAA-MM-JJ]", done=()):
            steps = "\n".join(f"- [{'x' if n in done else ' '}] {n}. Étape {n} (skill) : détail"
                              for n in ("1", "2", "3", "3b", "4", "11", "12"))
            return (f"# Suivi : x\n\n- Id : `x`\n- Statut : {statut}\n- Publication visée : {visee}\n"
                    f"- Publiée le : {publiee}\n\n{steps}\n")
        with TempDir() as d:
            v = d / "videos"
            for name, text in {
                "course-ia": suivi("mis de côté (à reprendre)", visee=str(today + timedelta(days=12)), done=("1", "2", "3")),
                "pokemon-ia": suivi("en cours", visee=str(today + timedelta(days=5)), done=("1", "2", "3")),
                "shader-ia": suivi("publiée", publiee=str(today - timedelta(days=30)), done=("1", "2", "3", "3b", "4", "11")),
                "mod-ia": suivi("publiée", publiee=str(today - timedelta(days=1)), done=("1", "2", "3", "3b", "4")),
            }.items():
                (v / name).mkdir(parents=True)
                (v / name / "suivi.md").write_text(text, encoding="utf-8")
            lines = repo.videos_info(v)
            self.assertEqual([x["id"] for x in lines], ["shader-ia", "mod-ia", "pokemon-ia", "course-ia"])
            self.assertEqual(lines[3]["status"], "mis de côté")
            out = run(REPO_PY, "list", env={"CLAUDE_REPO": str(d)}).stdout
            self.assertIn("visée", out)
            self.assertIn("3b. Étape 3b", out)
            self.assertNotIn("(skill)", out)
            due = repo.bilans_dus(lines, today)
            self.assertEqual(len(due), 1)                      # J+28 du shader ; le mod n'est qu'à J+1
            self.assertIn("shader-ia : bilan J+28", due[0])
            self.assertEqual(len(repo.bilans_dus(lines, today + timedelta(days=3))), 2)
            (v / "mod-ia" / "bilans").mkdir()                  # J+3 fait : on attend la fenêtre J+7 complète (J+9)
            (v / "mod-ia" / "bilans" / "2026-10-06-J3-brouillon.md").write_text("x", encoding="utf-8")
            lines = repo.videos_info(v)
            self.assertEqual(len(repo.bilans_dus(lines, today + timedelta(days=7))), 1)
            due = repo.bilans_dus(lines, today + timedelta(days=8))
            self.assertIn("mod-ia : bilan J+7 dû", due[-1])

    def test_fiche_de_tournage(self):
        script = """# Script : Duel test

## Décisions
> « pas une phrase de beat »

## Beat 1. Accroche (0:00 à 0:15)

> « Un seul prompt, deux IA. »

[ON SCREEN : le titre ; « sous-titre [DURÉE] »]

## Beat 2. Partie Claude

- **Lancement** [ON SCREEN : le jeu, « [DURÉE] »] : « Ça se lance : [OUI / NON]. »

```
Crée un jeu.
```

**Cas « aucun ne marche »** : on le dit.

## Notes de tournage

- **Même machine** pour les deux.
"""
        with TempDir() as d:
            v = d / "videos" / "duel-ia"
            v.mkdir(parents=True)
            (v / "script.md").write_text(script, encoding="utf-8")
            (v / "resultats.md").write_text("## Avant de tourner (étape 3b)\n\n- [ ] OBS prêt\n\n## Prompt\n", encoding="utf-8")
            r = run(FICHE, "duel-ia", env={"CLAUDE_REPO": str(d)})
            self.assertEqual(r.returncode, 0, r.stderr)
            fiche = (v / "fiche-tournage.md").read_text(encoding="utf-8")
            self.assertIn("- [ ] OBS prêt", fiche)
            self.assertIn("- [ ] « Un seul prompt, deux IA. »", fiche)
            self.assertIn("  - **Lancement** : « Ça se lance : [OUI / NON]. »", fiche)
            self.assertIn("```text\nCrée un jeu.\n```", fiche)
            self.assertIn("**Cas « aucun ne marche »**", fiche)
            self.assertIn("- [ ] **Même machine** pour les deux.", fiche)
            self.assertNotIn("ON SCREEN", fiche)
            self.assertNotIn("pas une phrase de beat", fiche)
            self.assertLess(fiche.index("Beat 1"), fiche.index("Beat 2"))

    def test_fiche_prompt_dans_sa_section(self):
        script = """# Script : Duel test

## Le prompt en mode plan (deux messages)

Message 1 (à coller mot pour mot) :

```text
Crée un mod.
```

Message 2 (après le plan) :

```text
Plan validé tel quel.
```

## Beat 1. Le prompt

Le texte complet est dans la section « Le prompt en mode plan » ci-dessus.

> « Voilà le prompt. »
"""
        with TempDir() as d:
            v = d / "videos" / "duel-ia"
            v.mkdir(parents=True)
            (v / "script.md").write_text(script, encoding="utf-8")
            r = run(FICHE, "duel-ia", env={"CLAUDE_REPO": str(d)})
            self.assertEqual(r.returncode, 0, r.stderr)
            fiche = (v / "fiche-tournage.md").read_text(encoding="utf-8")
            self.assertIn("Message 1 (à coller mot pour mot) :\n```text\nCrée un mod.\n```", fiche)
            self.assertIn("Message 2 (après le plan) :\n```text\nPlan validé tel quel.\n```", fiche)
            self.assertLess(fiche.index("Plan validé tel quel."), fiche.index("Beat 1"))
            self.assertIn("- [ ] « Voilà le prompt. »", fiche)

    def test_forgotten_publication(self):
        today = date.today()
        with TempDir() as d:
            v = d / "videos"
            for name, title, visee in (("pokemon-ia", "J'ai mis Claude et ChatGPT en duel pour refaire Pokémon de zéro", "[AAAA-MM-JJ]"),
                                       ("mod-ia", "Un mod Minecraft", str(today - timedelta(days=2))),
                                       ("course-ia", "Jeu de course", str(today - timedelta(days=2)))):
                (v / name).mkdir(parents=True)
                statut = "mis de côté" if name == "course-ia" else "en cours"
                (v / name / "suivi.md").write_text(f"# Suivi : {title}\n\n- Statut : {statut}\n- Publication visée : {visee}\n"
                                                   "- Publiée le : [AAAA-MM-JJ]\n\n- [ ] 9. Publication\n", encoding="utf-8")
            # publiée sous un titre de variante (titres.txt), pas sous le titre de suivi.md
            (v / "pokemon-ia" / "titres.txt").write_text("Titre A | QUI GAGNE ?\nPokémon mais c'est Claude et ChatGPT qui inventent tout | ÇA MARCHE ?\n", encoding="utf-8")
            chaine = d / "chaine.json"
            chaine.write_text('{"entries": [{"title": "Pokémon mais c\'est Claude et ChatGPT qui inventent tout", "id": "abcdefghijk"},'
                              ' {"title": "Une autre vidéo", "id": "zzzzzzzzzzz"}]}', encoding="utf-8")
            os.environ["YT_CHAINE_JSON"] = str(chaine)
            try:
                out = repo.publications_oubliees(v, repo.videos_info(v), today)
            finally:
                del os.environ["YT_CHAINE_JSON"]
            self.assertEqual(len(out), 2, out)
            self.assertTrue(any("pokemon-ia" in l and "youtu.be/abcdefghijk" in l for l in out))
            self.assertTrue(any(l.startswith("mod-ia : publication visée") for l in out))   # date dépassée
            self.assertFalse(any("course-ia" in l for l in out))                            # mise de côté
            self.assertEqual(repo.publications_oubliees(v, repo.videos_info(v), today, online=False),
                             [l for l in out if l.startswith("mod-ia")])

    def test_etat_reports_unpushed_work(self):
        with TempDir() as d:
            remote, work = d / "remote.git", d / "work"
            git = lambda *a, cwd=None: subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True)
            git("init", "-q", "--bare", str(remote))
            git("clone", "-q", str(remote), str(work))
            for k, val in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
                git("config", k, val, cwd=work)
            (work / "videos").mkdir()
            (work / "config" / "youtube").mkdir(parents=True)
            (work / "config" / "youtube" / "a.md").write_text("a", encoding="utf-8")
            env = {"CLAUDE_REPO": str(work)}
            self.assertIn("non commité", run(REPO_PY, "etat", env=env).stdout)
            r = run(ENVOI, "test : premier envoi", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("rien en attente", run(REPO_PY, "etat", env=env).stdout)
            self.assertIn("rien en attente", run(REPO_PY, "etat", "--hors-ligne", env=env).stdout)
            (work / "rush.mkv").write_bytes(b"x")
            r = run(ENVOI, env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("rush.mkv", r.stderr)
            self.assertEqual(git("diff", "--cached", "--name-only", cwd=work).stdout, "")  # rien laissé indexé
            (work / "rush.mkv").unlink()
            for bad in ("client_secret_1.json", "notes.tmp"):                               # secret en clair, temporaire
                (work / bad).write_text("x", encoding="utf-8")
                r = run(ENVOI, env=env)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(bad, r.stderr)
                (work / bad).unlink()
            (work / "config" / "youtube" / "b.md").write_text("b", encoding="utf-8")
            git("add", "config/youtube/b.md", cwd=work); git("commit", "-qm", "local", cwd=work)
            self.assertIn("non poussé", run(REPO_PY, "etat", env=env).stdout)
            self.assertEqual(run(ENVOI, env=env).returncode, 0)
            self.assertIn("config/youtube/b.md", git("ls-tree", "-r", "--name-only", "HEAD", cwd=remote).stdout)
            other = d / "autre-pc"
            git("clone", "-q", str(remote), str(other))
            for k, val in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
                git("config", k, val, cwd=other)
            (other / "config" / "youtube" / "c.md").write_text("c", encoding="utf-8")
            git("add", "config/youtube/c.md", cwd=other); git("commit", "-qm", "autre", cwd=other); git("push", "-q", cwd=other)
            self.assertIn("lance maj.bat", run(REPO_PY, "etat", env=env).stdout)            # git fetch le voit

    def test_root_through_link(self):
        if os.name == "nt":
            self.skipTest("covered by setup tests on Windows")
        with TempDir() as d:
            repo_dir, home = d / "repo", d / "home"
            (repo_dir / "config" / "youtube").mkdir(parents=True)
            (repo_dir / "setup.py").write_text("", encoding="utf-8")
            (home / ".claude").mkdir(parents=True)
            os.symlink(repo_dir / "config" / "youtube", home / ".claude" / "youtube")
            r = run(REPO_PY, "root", env={"HOME": str(home), "CLAUDE_REPO": ""})
            self.assertEqual(r.stdout.strip(), str(repo_dir.resolve()))
            r = run(REPO_PY, "root", env={"HOME": str(d / "vide"), "CLAUDE_REPO": ""})
            self.assertNotEqual(r.returncode, 0)


class DescriptionTest(unittest.TestCase):
    def check(self, text, *args):
        with TempDir() as d:
            (d / "description.md").write_text(text, encoding="utf-8")
            return run(CHECK, d / "description.md", *args)

    def test_good(self):
        r = self.check(GOOD, "--duree", "9:41")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("5 chapitres", r.stdout)

    def test_problems(self):
        bad = (GOOD.replace("0:00 Le défi", "0:05 Le défi").replace("0:42 Les règles", "0:10 Les règles <3")
               .replace("Et vous,", "[DEMANDE FINALE] Et vous, 🔥"))
        r = self.check(bad, "--duree", "8:00")
        self.assertEqual(r.returncode, 1)
        for flag in ("doit être à 0:00", "< ou >", "emoji", "crochets à remplir", "dépasse la durée"):
            self.assertIn(flag, r.stdout)

    def test_short_chapter_and_tags(self):
        bad = GOOD.replace("0:42 Les règles", "0:05 Les règles").replace(
            "roblox, ia roblox", "roblox, Roblox, " + ", ".join(f"tag numero {i} assez long" for i in range(25)))
        r = self.check(bad)
        self.assertIn("moins de 10 s", r.stdout)
        self.assertIn("500 maximum", r.stdout)
        self.assertIn("en double", r.stdout)

    def test_keyword_entities_and_vague_chapters(self):
        md = GOOD.replace("0:42 Les règles", "0:42 Partie 2") + "\n## Entités\n```text\nClaude Opus 5.5, ChatGPT 6, Roblox Studio, Fortnite\n```\n"
        r = self.check(md, "--mot-cle", "claude chatgpt roblox")
        self.assertEqual(r.returncode, 1)
        self.assertIn("mot-clé « claude chatgpt roblox » absent des 150 premiers caractères (claude, chatgpt)", r.stdout)
        self.assertIn("entités non citées dans la description : Roblox Studio, Fortnite", r.stdout)
        self.assertIn("chapitres sans contenu (Partie 2)", r.stdout)
        self.assertIn("le premier tag (« roblox ») n'est pas le mot-clé principal", r.stdout)
        ok = self.check(GOOD + "\n## Entités\n```text\nClaude Opus 5.5, ChatGPT 6\n```\n")
        self.assertEqual(ok.returncode, 0, ok.stdout)                # mot-clé par défaut : le 1er tag, « roblox »
        self.assertIn("les 2 sont citées", ok.stdout)

    def test_no_chapters_is_an_error(self):
        lines = [l for l in GOOD.splitlines() if not re.match(r"\s*\d+:\d{2}\s", l)]
        r = self.check("\n".join(lines) + "\n", "--duree", "9:41")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ERREUR : aucun chapitre", r.stdout)
        self.assertEqual(self.check("\n".join(lines) + "\n", "--sans-chapitres").returncode, 0)
        r = self.check(GOOD)                                          # sans --duree : conseil seulement
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("conseil : --duree absent", r.stdout)

    def test_missing_sections(self):
        r = self.check("# rien\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("## Description", r.stdout)


if __name__ == "__main__":
    unittest.main()
