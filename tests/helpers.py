"""Shared helpers for the tests: run a repo script with UTF-8 everywhere (Windows included)."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"


def run(script, *args, env=None, cwd=None):
    e = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf8")
    e.update(env or {})
    return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", env=e, cwd=cwd)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def entry(i, title, views, duration=600, channel=None, channel_id=None, short=False, ts=None, live=None):
    """One yt-dlp --flat-playlist entry."""
    vid = f"{i:011d}"
    return {"_type": "url", "ie_key": "Youtube", "id": vid,
            "url": f"https://www.youtube.com/{'shorts/' if short else 'watch?v='}{vid}",
            "title": title, "view_count": views, "duration": duration, "channel": channel,
            "channel_id": channel_id, "timestamp": ts, "live_status": live,
            "thumbnails": [{"url": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", "width": 480}]}


class TempDir:
    def __enter__(self):
        self._t = tempfile.TemporaryDirectory()
        return Path(self._t.name)

    def __exit__(self, *a):
        self._t.cleanup()
