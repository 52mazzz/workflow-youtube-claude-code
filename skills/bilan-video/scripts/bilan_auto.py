#!/usr/bin/env python3
"""bilan_auto.py - collect the reviews that are due, with nobody at the keyboard (daily task on the desktop PC).

    python bilan_auto.py                         # collect every due review, one text file per review
    python bilan_auto.py --liste                 # only say which reviews would be collected
    python bilan_auto.py --aujourdhui 2026-10-12 # pretend today is that day (tests)

A review J+N (N = 7 for stage 11, 28 for stage 12 of suivi.md) is collected when:
- suivi.md has "Publiée le" and a YouTube link ("Lien :"), and the stage is not checked;
- the video is at least N + 2 days old: Analytics lags about 2 days, so days 0 to N-1 are complete;
- no archive in videos/<id>/bilans/ already holds that window (requested_age N) at that age or later.
J+3 is never collected here: two days after it, the J+7 window is almost there, and a J+3 curve is
too thin to act on (a few dozen viewers at most).

Each collection runs bilan.py <video> --id <id> --age N [--vue <latest vue_<id>*.txt>]: the JSON archive
lands in videos/<id>/bilans/ as usual, and the printed review in videos/<id>/bilans/<date>-J<N>-auto.txt.
Nothing else is written: apprentissages.md, suivi.md and Studio numbers (Test & Compare, impressions,
click-through rate) stay for the bilan-video skill, with the user. Exit code 1 if a collection failed
(OAuth token expired, no network), 0 otherwise, even with nothing to do.
"""
import json, os, re, subprocess, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "nouvelle-video" / "scripts"))
import repo  # noqa: E402

LAG = 2
WINDOWS = [("11", 7), ("12", 28)]


def video_link(text):
    m = re.search(r"(?:youtu\.be/|v=|/shorts/)([\w-]{11})", repo.field(text, "Lien"))
    return m.group(1) if m else None


def collected(bilans, n):
    """True if an archive already holds window J+n, collected once that window was complete."""
    for p in bilans.glob(f"*-J{n}*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if r.get("requested_age") == n and (r.get("age_days") or 0) >= n + LAG:
            return True
    return False


def latest_vue(r, vid_id):
    vues = sorted((r / "montage" / "02_ANALYSE").glob(f"vue_{vid_id}*.txt"), key=lambda p: p.stat().st_mtime)
    return vues[-1] if vues else None


def due(r, today):
    out = []
    for d in repo.video_dirs(r / "videos"):
        text = (d / "suivi.md").read_text(encoding="utf-8")
        published, link = repo.a_date(repo.field(text, "Publiée le")), video_link(text)
        if not published or not link:
            continue
        for stage, n in WINDOWS:
            if (today - published).days >= n + LAG and not repo.checked(text, stage) and not collected(d / "bilans", n):
                out.append({"id": d.name, "video": link, "age": n, "vue": latest_vue(r, d.name)})
    return out


def main():
    a = sys.argv[1:]
    today = date.fromisoformat(a[a.index("--aujourdhui") + 1]) if "--aujourdhui" in a else date.today()
    r = repo.root()
    todo = due(r, today)
    if not todo:
        print("aucun bilan à collecter"); return
    failed = False
    for b in todo:
        label = f"{b['id']} : bilan J+{b['age']}"
        if "--liste" in a:
            print(f"{label} à collecter" + ("" if b["vue"] else " (sans transcription du montage final)")); continue
        args = [sys.executable, str(HERE / "bilan.py"), b["video"], "--id", b["id"], "--age", str(b["age"])]
        if b["vue"]:
            args += ["--vue", str(b["vue"])]
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf8"))
        if p.returncode != 0:
            failed = True
            print(f"{label} : échec de la collecte\n{(p.stderr or p.stdout).strip()}"); continue
        out = r / "videos" / b["id"] / "bilans" / f"{today.isoformat()}-J{b['age']}-auto.txt"
        out.write_text(p.stdout + ("\n" + p.stderr if p.stderr else ""), encoding="utf-8")
        print(f"{label} collecté : {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
