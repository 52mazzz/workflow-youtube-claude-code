import json, shutil, unittest
from helpers import ROOT, TempDir, run

try:
    import cryptography  # noqa: F401
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


@unittest.skipUnless(HAVE_CRYPTO, "cryptography not installed")
class VaultTest(unittest.TestCase):
    def test_finds_gitignored_files_round_trip(self):
        with TempDir() as d:
            repo, home = d / "repo", d / "home"
            repo.mkdir(); (home / ".claude").mkdir(parents=True)
            shutil.copy(ROOT / "secrets_vault.py", repo)
            env = {"HOME": str(home), "USERPROFILE": str(home), "VAULT_PASSPHRASE": "correct horse"}
            key = {"api_key": "AIzaTEST"}
            client = {"installed": {"client_id": "x.apps.googleusercontent.com", "client_secret": "s"}}
            token = {"refresh_token": "r", "token": "t"}
            # where the user may really have them: API key in ~/.claude, the rest git-ignored in the repo
            (home / ".claude" / "youtube-credentials.json").write_text(json.dumps(key), encoding="utf-8")
            (repo / "client_secret_123-abc.apps.googleusercontent.com.json").write_text(json.dumps(client), encoding="utf-8")
            (repo / ".tmp").mkdir()
            (repo / ".tmp" / "youtube_oauth_token.json").write_text(json.dumps(token), encoding="utf-8")
            (repo / "youtube_client_secrets.json").write_text("{not json", encoding="utf-8")

            st = run(repo / "secrets_vault.py", "status", env=env)
            self.assertEqual(st.returncode, 0, st.stderr)
            self.assertIn("client_secret_123", st.stdout)
            self.assertIn("not valid JSON", st.stdout)

            r = run(repo / "secrets_vault.py", "encrypt", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            for n in ("youtube-credentials.enc", "youtube-client-secrets.enc", "youtube-oauth-token.enc"):
                self.assertTrue((repo / "secrets" / n).exists(), n)
            # copied where the skills read them on this machine
            self.assertEqual(json.loads((home / ".claude" / "youtube_client_secrets.json").read_text()), client)
            self.assertEqual(json.loads((home / ".claude" / ".tmp" / "youtube_oauth_token.json").read_text()), token)

            # another machine: nothing in ~/.claude, decrypt from the repo
            shutil.rmtree(home / ".claude")
            bad = run(repo / "secrets_vault.py", "decrypt", env=dict(env, VAULT_PASSPHRASE="wrong"))
            self.assertNotEqual(bad.returncode, 0)
            r = run(repo / "secrets_vault.py", "decrypt", env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads((home / ".claude" / "youtube-credentials.json").read_text()), key)
            self.assertEqual(json.loads((home / ".claude" / "youtube_client_secrets.json").read_text()), client)
            self.assertEqual(json.loads((home / ".claude" / ".tmp" / "youtube_oauth_token.json").read_text()), token)


if __name__ == "__main__":
    unittest.main()
