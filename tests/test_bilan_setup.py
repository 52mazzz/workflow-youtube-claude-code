import os, shutil, sys, unittest
from datetime import date
from helpers import ROOT, SKILLS, TempDir, run, write_json

sys.path.insert(0, str(SKILLS / "bilan-video" / "scripts"))
import bilan  # noqa: E402


class BilanTest(unittest.TestCase):
    def test_retention_drops_peaks_and_csv(self):
        dur = 600.0
        def aud(t):                      # 100 -> 60 % en 30 s, plateau, chute à 2:00, pic à 5:00
            if t < 30: return 1 - 0.4 * t / 30
            a = 0.6 - 0.0002 * (t - 30)
            if t >= 120: a -= 0.12
            if 300 <= t < 312: a += 0.05 * (1 - abs(t - 306) / 6)
            return a
        curve = [(i / 100, aud(i * dur / 100)) for i in range(101)]
        c = bilan.analyse_curve(curve, dur)
        self.assertEqual(len(c["chutes"]), 1)
        self.assertTrue(110 <= c["chutes"][0]["t"] <= 120, c["chutes"])
        self.assertEqual(len(c["pics"]), 1)
        self.assertTrue(290 <= c["pics"][0]["t"] <= 306, c["pics"])
        self.assertAlmostEqual(c["intro_15s"], 80.0, delta=1)
        self.assertEqual(bilan.bench("retention_30s", 50.0), "à retravailler : accroche ou promesse du titre")
        self.assertEqual(bilan.bench("averageViewPercentage", 30.0), "bas pour du gaming (repère de niche, pas une règle de YouTube)")
        with TempDir() as d:
            vue = d / "vue.txt"
            vue.write_text("   0.0 NOIR      Un seul prompt.\n 112.4 JEU       Et là, ça plante.\n 130.0 JEU       Bon.\n", encoding="utf-8")
            self.assertEqual(bilan.said_at(bilan.read_vue(vue), c["chutes"][0]["t"]), "Et là, ça plante.")
            csvf = d / "retention.csv"
            csvf.write_text("Position de la vidéo (%);Rétention de l'audience absolue (%)\n"
                            + "".join(f"{i};{aud(i * 6) * 100:.1f}\n".replace(".", ",") for i in range(101)), encoding="utf-8")
            pts, info = bilan.read_studio_csv(csvf, 600)
            self.assertEqual(len(pts), 101)
            self.assertEqual((info["unite_position"], info["unite_retention"]), ("pourcentage", "pourcentage"))
            self.assertAlmostEqual(pts[50][1], aud(300), places=2)
            r = run(SKILLS / "bilan-video" / "scripts" / "bilan.py", "--csv", csvf, "--duree", "600", "--vue", vue)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("« Et là, ça plante. »", r.stdout)

    def test_csv_units_and_partial_exports(self):
        with TempDir() as d:
            f = d / "r.csv"
            # ratio sans indication d'unité : 0,5 reste 0,5 (et non 0,005)
            f.write_text("Video position,Audience retention\n" + "".join(f"{i / 10},{1 - i / 20}\n" for i in range(11)), encoding="utf-8")
            pts, info = bilan.read_studio_csv(f, 600, unite_retention="ratio")
            self.assertEqual(info["unite_position"], "ratio")
            self.assertAlmostEqual(dict(pts)[0.5], 0.75)
            # secondes, export partiel (les 2 premières minutes d'une vidéo de 10 min) : pas étiré sur toute la vidéo
            f.write_text("Temps (s);Rétention (%)\n" + "".join(f"{t};{100 - t / 4:.1f}\n" for t in range(0, 121, 5)), encoding="utf-8")
            pts, info = bilan.read_studio_csv(f, 600)
            self.assertEqual(info["unite_position"], "secondes")
            self.assertAlmostEqual(max(p for p, _ in pts), 0.2)
            self.assertIn("export partiel", info["alerte"])
            c = bilan.analyse_curve(pts, 600)
            self.assertAlmostEqual(c["premisse_60s"], 85.0, delta=0.5)
            self.assertEqual(c["couverture"], 20)
            f.write_text("Temps (s);Rétention (%)\n" + "".join(f"{t};{100 - t / 4:.1f}\n" for t in range(300, 601, 5)), encoding="utf-8")
            c = bilan.analyse_curve(bilan.read_studio_csv(f, 600)[0], 600)
            self.assertIsNone(c["intro_15s"])                                      # hors de l'export : pas de valeur inventée
            # m:ss
            f.write_text("Position (temps);Rétention de l'audience absolue (%)\n0:00;100\n1:30;70\n10:00;20\n", encoding="utf-8")
            pts, info = bilan.read_studio_csv(f, 600)
            self.assertAlmostEqual(pts[1][0], 0.15)
            # entre 1 et 100 sans en-tête parlant : on ne devine pas
            f.write_text("Video position;Audience retention\n" + "".join(f"{i};{100 - i}\n" for i in range(0, 61, 10)), encoding="utf-8")
            with self.assertRaises(ValueError) as e:
                bilan.read_studio_csv(f, 600)
            self.assertIn("--unite-position", str(e.exception))
            pts, info = bilan.read_studio_csv(f, 60, "secondes", "pourcentage")
            self.assertAlmostEqual(pts[-1][0], 1.0)
            # durée fausse : positions au-delà de la fin
            with self.assertRaises(ValueError):
                bilan.read_studio_csv(f, 30, "secondes")
            r = run(SKILLS / "bilan-video" / "scripts" / "bilan.py", "--csv", f, "--duree", "1:00")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("--unite-position", r.stderr)
            r = run(SKILLS / "bilan-video" / "scripts" / "bilan.py", "--csv", f, "--duree", "1:00", "--unite-position", "secondes", "--unite-retention", "pourcentage")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("position en secondes", r.stdout)

    def test_pacific_days(self):
        from datetime import datetime, timezone
        # 2026-10-06 03:00 UTC = 2026-10-05 20:00 à Los Angeles (heure d'été)
        self.assertEqual(bilan.pacific(datetime(2026, 10, 6, 3, tzinfo=timezone.utc)), date(2026, 10, 5))
        self.assertEqual(bilan.pacific(datetime(2026, 12, 6, 7, 59, tzinfo=timezone.utc)), date(2026, 12, 5))   # hiver : UTC-8
        self.assertEqual(bilan.pacific(datetime(2026, 12, 6, 8, 0, tzinfo=timezone.utc)), date(2026, 12, 6))

    def test_helpers(self):
        self.assertEqual(bilan.iso_duration("PT9M41S"), 581)
        self.assertEqual(bilan.iso_duration("PT1H"), 3600)
        self.assertIsNone(bilan.iso_duration("nope"))
        self.assertEqual(bilan.video_id("https://www.youtube.com/watch?v=abcdefghijk&t=3"), "abcdefghijk")
        self.assertEqual(bilan.video_id("https://youtu.be/abcdefghijk"), "abcdefghijk")
        self.assertIsNone(bilan.video_id("pas une vidéo"))
        curve = [(0.0, 1.0), (0.1, 0.6), (0.5, 0.4), (1.0, 0.1)]
        self.assertAlmostEqual(bilan.retention_at(curve, 0.05), 0.8)
        self.assertAlmostEqual(bilan.retention_at(curve, 0.5), 0.4)
        self.assertEqual(bilan.retention_at(curve, 2), 0.1)
        pub = date(2026, 9, 1)
        daily = [(date(2026, 9, d), 100 * d) for d in range(1, 6)]
        self.assertEqual(bilan.first_days(daily, pub, 2), 300)
        self.assertIsNone(bilan.first_days(daily, pub, 7))

    def test_row(self):
        row = bilan.row({"published": "2026-09-01", "title": "T", "retention_30s": 64.2,
                         "averageViewPercentage": 38.5, "views_7d": 1200, "subscribersGained": 14})
        self.assertTrue(row.startswith("| 2026-09-01 | T |"))
        self.assertIn("64.2 %", row)
        self.assertIn("[à compléter]", row)  # CTR comes from Studio
        self.assertEqual(row.count("|"), 11)

    def test_bilan_auto_due(self):
        auto = SKILLS / "bilan-video" / "scripts" / "bilan_auto.py"
        with TempDir() as d:
            v = d / "videos" / "pokemon-ia"
            (v / "bilans").mkdir(parents=True)
            (d / "montage" / "02_ANALYSE").mkdir(parents=True)
            (d / "montage" / "02_ANALYSE" / "vue_pokemon-ia - final 3.txt").write_text("  0.0 JEU  Salut.\n", encoding="utf-8")
            suivi = ("- Statut : publiée\n- Publiée le : 2026-10-03 (vers 23:45)\n- Lien : https://youtu.be/h59yw1ofKqo\n"
                     "- [ ] 11. Bilan à J+3/J+7\n- [ ] 12. Bilan à J+28\n")
            (v / "suivi.md").write_text(suivi, encoding="utf-8")
            (d / "videos" / "sans-lien").mkdir()
            (d / "videos" / "sans-lien" / "suivi.md").write_text("- Publiée le : 2026-09-01\n- [ ] 11. Bilan\n", encoding="utf-8")
            liste = lambda day: run(auto, "--liste", "--aujourdhui", day, env={"CLAUDE_REPO": str(d)}).stdout
            self.assertIn("aucun bilan", liste("2026-10-11"))          # J+7 window not complete yet (2 days of lag)
            self.assertEqual(liste("2026-10-12"), "pokemon-ia : bilan J+7 à collecter\n")
            # a J+7 archive collected too early (age 7) does not count, one at age 9 does
            write_json(v / "bilans" / "2026-10-10T000000.000000Z-J7.json", {"requested_age": 7, "age_days": 7})
            self.assertIn("J+7", liste("2026-10-12"))
            write_json(v / "bilans" / "2026-10-12T000000.000000Z-J7.json", {"requested_age": 7, "age_days": 9})
            self.assertIn("aucun bilan", liste("2026-10-12"))
            self.assertEqual(liste("2026-11-02"), "pokemon-ia : bilan J+28 à collecter\n")
            (v / "suivi.md").write_text(suivi.replace("[ ] 12.", "[x] 12."), encoding="utf-8")
            self.assertIn("aucun bilan", liste("2026-11-02"))           # stage checked by hand


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.t = TempDir(); self.d = self.t.__enter__()
        self.repo = self.d / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests", "videos"))
        cfg = self.repo / "config" / "youtube"   # public copy: the channel data is not published
        if not cfg.exists():
            (cfg / "mascotte").mkdir(parents=True)
            for name in ("apprentissages.md", "preferences.md", "voice.md"):
                (cfg / name).write_text(f"# {name}\n", encoding="utf-8")
            (cfg / "mascotte" / "tsar_tete.png").write_bytes(b"")
        self.home = self.d / "home"; self.home.mkdir()
        self.env = {"HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CLAUDE_DOCUMENTS": str(self.home / "Documents")}
        self.claude = self.home / ".claude"

    def tearDown(self):
        self.t.__exit__()

    def setup_py(self, *args):
        r = run(self.repo / "setup.py", "--ici", "--skip-deps", "--skip-secrets", *args, env=self.env, cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_orphan_links_removed(self):
        def link(target, at):
            try:
                os.symlink(target, at, target_is_directory=True)
            except OSError:
                import _winapi
                _winapi.CreateJunction(str(target), str(at))
        skills = self.claude / "skills"; skills.mkdir(parents=True)
        ghost, ailleurs = self.repo / "skills" / "supprime", self.d / "ailleurs" / "autre"
        for target in (ghost, ailleurs):
            target.mkdir(parents=True)
        link(ghost, skills / "supprime"); link(ailleurs, skills / "autre")
        shutil.rmtree(ghost); shutil.rmtree(ailleurs)                       # deux liens morts
        out = self.setup_py()
        self.assertIn("liens retirés (skill supprimé du dépôt) : supprime", out)
        names = {p.name for p in skills.iterdir()}
        self.assertNotIn("supprime", names)
        self.assertIn("autre", names)                                        # pas un lien vers ce dépôt : laissé

    def test_link_mode_repo_is_the_only_copy(self):
        # this machine already has an old copy-mode install, with things the repo does not have
        yt = self.claude / "youtube"; yt.mkdir(parents=True)
        (yt / "voice.md").write_text("voix réglée sur cette machine\n", encoding="utf-8")
        (yt / "apprentissages.md").write_text(
            (self.repo / "config" / "youtube" / "apprentissages.md").read_text(encoding="utf-8")
            + "| 2026-09-01 | Vidéo A | humour | 5 % | 70 % | 40 % | 900 | 10 | ref | leçon A |\n", encoding="utf-8")
        (yt / "references").mkdir()
        (yt / "references" / "2026-09-28-veille.json").write_text("{}", encoding="utf-8")
        out = self.setup_py()
        self.assertIn("(linked)", out)
        cfg = self.repo / "config" / "youtube"
        # merged into the repo, nothing lost
        self.assertIn("Vidéo A", (cfg / "apprentissages.md").read_text(encoding="utf-8"))
        self.assertTrue((cfg / "references" / "2026-09-28-veille.json").exists())
        # differing file: repo kept, machine's copy backed up
        self.assertNotEqual((cfg / "voice.md").read_text(encoding="utf-8"), "voix réglée sur cette machine\n")
        backups = list(self.claude.glob(".sauvegarde-*/config/youtube/voice.md"))
        self.assertEqual(len(backups), 1)
        # writing through ~/.claude now writes into the repo
        (self.claude / "youtube" / "preferences.md").write_text("nouvelle préférence\n", encoding="utf-8")
        self.assertEqual((cfg / "preferences.md").read_text(encoding="utf-8"), "nouvelle préférence\n")
        (self.claude / "skills" / "bilan-video" / "note.md").write_text("x", encoding="utf-8")
        self.assertTrue((self.repo / "skills" / "bilan-video" / "note.md").exists())
        self.assertTrue((self.claude / "youtube" / "mascotte" / "tsar_tete.png").exists())
        # running again is a no-op
        self.assertIn("(ok)", self.setup_py())

    def test_location_and_repoint_old_copy(self):
        # an old clone installed first (forced), then the real one in Documents/TSAR/Claude workflow youtube
        self.setup_py()
        new = self.home / "Documents" / "TSAR" / "Claude workflow youtube"
        new.parent.mkdir(parents=True)
        shutil.copytree(self.repo, new)
        refused = run(self.repo / "setup.py", "--skip-deps", "--skip-secrets", env=self.env, cwd=self.repo)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("Claude workflow youtube", refused.stdout)
        r = run(new / "setup.py", "--skip-deps", "--skip-secrets", env=self.env, cwd=new)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pointait vers", r.stdout)
        (self.claude / "youtube" / "preferences.md").write_text("depuis la nouvelle copie\n", encoding="utf-8")
        self.assertEqual((new / "config" / "youtube" / "preferences.md").read_text(encoding="utf-8"),
                         "depuis la nouvelle copie\n")
        self.assertNotEqual((self.repo / "config" / "youtube" / "preferences.md").read_text(encoding="utf-8"),
                            "depuis la nouvelle copie\n")

    def test_adopt_skill_from_machine(self):
        local = self.claude / "skills" / "skill-perso"
        (local / "references").mkdir(parents=True)
        (local / "SKILL.md").write_text("---\nname: skill-perso\n---\n", encoding="utf-8")
        (local / "references" / "preferences.md").write_text("pref\n", encoding="utf-8")
        out = self.setup_py("--adopt", "skill-perso", "absent")
        self.assertIn("2 file(s) copied into the repo", out)
        self.assertIn("absent: no SKILL.md", out)
        self.assertTrue((self.repo / "skills" / "skill-perso" / "references" / "preferences.md").exists())
        (local / "references" / "preferences.md").write_text("pref modifiée\n", encoding="utf-8")
        self.assertEqual((self.repo / "skills" / "skill-perso" / "references" / "preferences.md")
                         .read_text(encoding="utf-8"), "pref modifiée\n")

    def test_copy_mode_and_save(self):
        self.setup_py("--copy")
        yt = self.claude / "youtube"
        self.assertFalse(yt.is_symlink())
        app_local, app_repo = yt / "apprentissages.md", self.repo / "config" / "youtube" / "apprentissages.md"
        with open(app_local, "a", encoding="utf-8") as f:
            f.write("| 2026-09-01 | Vidéo A | humour | 5 % | 70 % | 40 % | 900 | 10 | ref | leçon A |\n")
        with open(app_repo, "a", encoding="utf-8") as f:
            f.write("| 2026-09-08 | Vidéo B | curiosité | 4 % | 65 % | 35 % | 700 | 6 | ref | leçon B |\n")
        self.setup_py("--copy")
        local = app_local.read_text(encoding="utf-8")
        self.assertIn("Vidéo A", local); self.assertIn("Vidéo B", local)
        app_local.write_text(local.replace("leçon A", "leçon A à 28 jours"), encoding="utf-8")
        r = run(self.repo / "setup.py", "--save", env=self.env, cwd=self.repo)
        saved = app_repo.read_text(encoding="utf-8")
        self.assertIn("leçon A à 28 jours", saved)
        self.assertEqual(saved.count("Vidéo A"), 1)

    def test_setup_propagates_vault_failure(self):
        secrets = self.repo / "secrets"
        secrets.mkdir(exist_ok=True)
        (secrets / "test.enc").write_bytes(b"fixture")
        (self.repo / "secrets_vault.py").write_text(
            'import sys\nprint("coffre indisponible", file=sys.stderr)\nsys.exit(7)\n', encoding="utf-8")
        r = run(self.repo / "setup.py", "--ici", "--skip-deps", env=self.env, cwd=self.repo)
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertIn("coffre indisponible", r.stderr)
        self.assertIn("Installation incomplète", r.stderr)

    def test_setup_accepts_vault_success_and_explicit_skip(self):
        secrets = self.repo / "secrets"
        secrets.mkdir(exist_ok=True)
        (secrets / "test.enc").write_bytes(b"fixture")
        (self.repo / "secrets_vault.py").write_text('print("coffre déchiffré")\n', encoding="utf-8")
        r = run(self.repo / "setup.py", "--ici", "--skip-deps", env=self.env, cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("coffre déchiffré", r.stdout)
        (self.repo / "secrets_vault.py").write_text('raise SystemExit(7)\n', encoding="utf-8")
        self.setup_py()  # --skip-secrets reste un choix explicite valable


if __name__ == "__main__":
    unittest.main()
