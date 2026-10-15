#!/usr/bin/env python3
"""secrets_vault.py - keep the YouTube credentials in git, encrypted with a passphrase.

    python secrets_vault.py status      # what is found on this machine and what is in secrets/ (no passphrase)
    python secrets_vault.py encrypt     # every credential found -> secrets/<name>.enc
    python secrets_vault.py decrypt     # secrets/<name>.enc -> the place the skills read it from

Credentials, each looked for in several places (the plaintext files are git-ignored, so they may
sit in ~/.claude/ or in this repo folder, under their usual name or Google's download name):
  - the API key            youtube-credentials.json        -> ~/.claude/youtube-credentials.json
  - the OAuth client       youtube_client_secrets.json     -> ~/.claude/youtube_client_secrets.json
                           (or client_secret_*.json as downloaded from Google Cloud Console)
  - the OAuth token        youtube_oauth_token.json        -> ~/.claude/.tmp/youtube_oauth_token.json
                           (read-only YouTube Analytics access; with it, another machine does not
                           need the browser sign-in. Delete secrets/youtube-oauth-token.enc if you
                           would rather sign in on each machine.)

Fernet (AES-128-CBC + HMAC) with a key derived from your passphrase by PBKDF2-SHA256 (600k rounds)
and a random salt. The passphrase is asked for interactively (or read from $VAULT_PASSPHRASE) and
is never stored. Without it the .enc files are useless, so commit them freely; never commit the
plaintext json.
"""
import base64, getpass, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ITERATIONS = 600_000


def claude():
    return Path.home() / ".claude"


def secrets():
    """name in secrets/ -> (destination on the machine, candidate locations, validator)."""
    c = claude()
    downloads = Path.home() / "Downloads"
    return {
        "youtube-credentials.enc": (
            c / "youtube-credentials.json",
            [c / "youtube-credentials.json", HERE / "youtube-credentials.json"],
            lambda d: isinstance(d, dict) and bool(d.get("api_key")),
        ),
        "youtube-client-secrets.enc": (
            c / "youtube_client_secrets.json",
            [c / "youtube_client_secrets.json", HERE / "youtube_client_secrets.json",
             *sorted(c.glob("client_secret*.json")), *sorted(HERE.glob("client_secret*.json")),
             *sorted(downloads.glob("client_secret*.apps.googleusercontent.com.json"))],
            lambda d: isinstance(d, dict) and ("installed" in d or "web" in d),
        ),
        "youtube-oauth-token.enc": (
            c / ".tmp" / "youtube_oauth_token.json",
            [c / ".tmp" / "youtube_oauth_token.json", HERE / ".tmp" / "youtube_oauth_token.json",
             HERE / "youtube_oauth_token.json", c / "youtube_oauth_token.json"],
            lambda d: isinstance(d, dict) and bool(d.get("refresh_token")),
        ),
    }


def find(candidates, valid):
    """First candidate that exists and holds the expected JSON; also the rejected ones, for status."""
    rejected = []
    for p in candidates:
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            rejected.append((p, "not valid JSON"))
            continue
        if valid(data):
            return p, data, rejected
        rejected.append((p, "not the expected content"))
    return None, None, rejected


def derive(passphrase, salt):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))


def ask(confirm=False):
    p = os.environ.get("VAULT_PASSPHRASE") or getpass.getpass("Passphrase: ")
    if confirm and "VAULT_PASSPHRASE" not in os.environ and getpass.getpass("Repeat: ") != p:
        sys.exit("Passphrases differ.")
    if not p:
        sys.exit("Empty passphrase.")
    return p


def status():
    for name, (dest, candidates, valid) in secrets().items():
        found, data, rejected = find(candidates, valid)
        enc = HERE / "secrets" / name
        print(f"{name}")
        print(f"    on this machine : {found if found else 'not found'}")
        for p, why in rejected:
            print(f"    ignored         : {p} ({why})")
        if found and name == "youtube-client-secrets.enc" and "web" in data:
            print("    ! client of type 'Web application': bilan.py needs a 'Desktop app' client")
        print(f"    in the repo     : {'secrets/' + name if enc.exists() else 'no'}")


def encrypt():
    from cryptography.fernet import Fernet
    todo = {}
    for name, (dest, candidates, valid) in secrets().items():
        found, _, _ = find(candidates, valid)
        if found:
            todo[name] = found
    if not todo:
        sys.exit("Nothing to encrypt. Run `python secrets_vault.py status` to see where files are looked for.")
    passphrase = ask(confirm=True)
    for name, src in todo.items():
        salt = os.urandom(16)
        enc = HERE / "secrets" / name
        enc.parent.mkdir(exist_ok=True)
        enc.write_bytes(salt + Fernet(derive(passphrase, salt)).encrypt(src.read_bytes()))
        print(f"Wrote {enc}  (from {src})")
        dest = secrets()[name][0]
        if src != dest and not dest.exists():  # put it where the skills read it on this machine too
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
            try:
                dest.chmod(0o600)
            except OSError:
                pass
            print(f"Copied to {dest}")
    print("\nNow: git add secrets && git commit -m \"Update encrypted YouTube credentials\" && git push")


def decrypt():
    from cryptography.fernet import Fernet, InvalidToken
    todo = {name: dest for name, (dest, _, _) in secrets().items() if (HERE / "secrets" / name).exists()}
    if not todo:
        sys.exit("No .enc file in secrets/.")
    passphrase = ask()
    for name, dest in todo.items():
        raw = (HERE / "secrets" / name).read_bytes()
        try:
            data = Fernet(derive(passphrase, raw[:16])).decrypt(raw[16:])
        except InvalidToken:
            sys.exit(f"Wrong passphrase for {name}.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        try:
            dest.chmod(0o600)
        except OSError:
            pass
        print(f"Wrote {dest}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"status": status, "encrypt": encrypt, "decrypt": decrypt}.get(cmd, lambda: sys.exit(__doc__))()
