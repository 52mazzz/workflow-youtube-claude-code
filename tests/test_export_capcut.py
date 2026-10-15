"""Réutilisation des rendus : les noms peuvent changer sans altérer leur contenu."""
import importlib.util
import json
import os
import shutil
import unittest
from unittest.mock import patch

from helpers import ROOT, TempDir, run

SCRIPTS = ROOT / "montage" / "08_HYPERFRAMES" / "scripts"


class ExportCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TempDir()
        self.base = self.tmp.__enter__()
        self.hf = self.base / "montage" / "08_HYPERFRAMES"
        scripts = self.hf / "scripts"
        scripts.mkdir(parents=True)
        for name in ("commun.py", "export_capcut.py", "make_compositions.py", "verifie_plan.py"):  # SCENES vient des SPECS du kit
            shutil.copy2(SCRIPTS / name, scripts / name)
        (self.hf / "compositions").mkdir()
        (self.hf / "kit").mkdir()
        self.sources = [self.hf / "compositions" / "etiquette.html",
                        self.hf / "kit" / "tsar.js", self.hf / "kit" / "tsar.css"]
        for source in self.sources:
            source.write_text("fixture", encoding="utf-8")
        (self.hf / "package.json").write_text(
            json.dumps({"scripts": {"render": "npx hyperframes@0.8.123 render"}}), encoding="utf-8")
        self.out = self.base / "montage" / "06_CAPCUT" / "test" / "overlays"
        self.out.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location("export_test_commun", scripts / "commun.py")
        self.commun = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, TSAR_GPU="0"):
            spec.loader.exec_module(self.commun)

    def tearDown(self):
        self.tmp.__exit__()

    def fingerprint(self, text):
        return self.commun.empreinte("etiquette", 1.0, {"texte": text}, fichiers=self.sources)

    def export(self, previous, requested):
        for ident, text in previous.items():
            dst = self.out / f"{ident}.mov"
            dst.write_text(text, encoding="utf-8")
            self.commun.marquer(dst, self.fingerprint(text))
        plan = self.hf / "plan.json"
        plan.write_text(json.dumps({"elements": [
            {"id": ident, "type": "etiquette", "at": n, "dur": 1, "vars": {"texte": text}}
            for n, (ident, text) in enumerate(requested.items())
        ]}), encoding="utf-8")
        result = run(self.hf / "scripts" / "export_capcut.py", "test", plan, "--nouveaux",
                     env={"TSAR_GPU": "0"}, cwd=self.hf)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 rendu(s)", result.stdout)  # aucune dépendance à Chrome, npx ou FFmpeg
        for ident, text in requested.items():
            dst = self.out / f"{ident}.mov"
            self.assertEqual(dst.read_text(encoding="utf-8"), text, ident)
            self.assertTrue(self.commun.a_jour(dst, self.fingerprint(text)), ident)

    def test_swap_cached_renders(self):
        self.export({"st01": "A", "st02": "B"}, {"st01": "B", "st02": "A"})

    def test_rotate_three_cached_renders(self):
        self.export({"st01": "A", "st02": "B", "st03": "C"},
                    {"st01": "B", "st02": "C", "st03": "A"})

    def test_reuse_overwritten_source_more_than_once(self):
        self.export({"st01": "A", "st02": "B"}, {"st01": "B", "st02": "A", "st03": "A"})

    def test_unchanged_and_renamed_renders(self):
        self.export({"st01": "A", "st02": "B"}, {"st01": "A", "st03": "B"})


if __name__ == "__main__":
    unittest.main()
