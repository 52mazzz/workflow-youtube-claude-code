#!/usr/bin/env python3
"""repo.py - where the repo is on this PC, the id of a video, and what is waiting, for every production skill.

    python repo.py root                   # path of the repo (videos/, montage/ live there)
    python repo.py id pokemon ia          # -> pokemon-ia : a short id from 2 or 3 key words
    python repo.py slug "J'ai mis Claude et ChatGPT en duel sur Roblox"
                                          # -> j-ai-mis-claude-et-chatgpt-en-duel-sur-roblox
    python repo.py trouve "<titre ou id>" # the existing video it names (id, title of suivi.md, titres.txt)
    python repo.py video "<titre ou id>"  # path of that existing video; refuses to guess (code 2 if several match,
                                          # 1 if none); --creer <id> creates videos/<id>/ only when nothing matches
    python repo.py list                   # every video: status, date, next stage (from suivi.md)
    python repo.py etat                   # what is waiting: not pushed, not pulled, reviews due, publication not noted,
                                          # and the tidying of rangement.py (safe caches emptied, the rest reported)
    python repo.py etat --hors-ligne      # same, without asking GitHub and YouTube

The id of a video is short: 2 or 3 key words of the subject, e.g. pokemon-ia, sukuna-ia, fixed
at the end of the titles phase (`repo.py id`, which refuses an id already taken). The same id names
videos/<id>/, the montage folder montage/08_HYPERFRAMES/videos/<id>/ and the CapCut projects "<id>" and
"<id> - final". It never changes afterwards, even if Test & Compare picks another title.

suivi.md carries in its header "Statut" (en cours, mis de côté, abandonnée, programmée, publiée, terminée),
"Publication visée", "Programmée pour" (the date set in Studio for a scheduled release) and "Publiée le"
(AAAA-MM-JJ): `list` sorts by those dates, and `etat` announces the reviews due at J+3 (stage 11; J+9 once a
J+3 is in bilans/, when the J+7 window is complete) and J+28 (stage 12), counted from the actual release:
"Publiée le", or a scheduled date already passed (YouTube released it; `etat` then asks to confirm it in suivi.md).
`etat` also asks GitHub (git fetch) what the other PC sent, and looks at the channel's latest videos
(yt-dlp, public data) for a video already online whose suivi.md has no "Publiée le" yet: without that
date, no review reminder would ever come.

The repo is found through ~/.claude/youtube, which setup.py links to config/youtube of the repo
(or $CLAUDE_REPO if set).
"""
import difflib, json, os, re, shutil, subprocess, sys, unicodedata
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

MAX = 60      # plain slugs
ID_MAX = 30   # ids
# reviews: (stage number in suivi.md, days after publication, label)
BILANS = [("11", 3, "bilan J+3/J+7"), ("12", 28, "bilan J+28")]
# once the J+3 is in bilans/, stage 11 waits for the full J+7 window: Analytics lags 2 days (bilan_auto.py)
J7_COMPLET = 9
CHAINE = "https://www.youtube.com/@letsar555/videos"


def root():
    env = os.environ.get("CLAUDE_REPO")
    if env:
        return Path(env)
    yt = Path.home() / ".claude" / "youtube"
    real = Path(os.path.realpath(yt))
    if real != yt.absolute() and (real.parent.parent / "setup.py").exists():
        return real.parent.parent
    sys.exit("repo introuvable : ~/.claude/youtube n'est pas un lien vers le dépôt. "
             "Lance `python setup.py` depuis le dépôt (mode lien), ou définis CLAUDE_REPO.")


def slug(title, limit=MAX):
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0]
    return s or "video"


def new_id(words, videos):
    """A short id from key words; refuses an id that already names a folder in videos/."""
    i = slug(words, ID_MAX)
    if i.count("-") > 3:
        sys.exit(f"id trop long : « {i} ». 2 ou 3 mots-clés suffisent (ex. pokemon-ia).")
    if (videos / i).exists():
        sys.exit(f"l'id « {i} » existe déjà (videos/{i}/) : ajoute un mot pour le distinguer.")
    return i


def field(text, name):
    """Value of '- <name> : value' in the header of suivi.md ('' if absent or still a [placeholder])."""
    m = re.search(rf"^\s*-\s*{re.escape(name)}\s*:\s*(.+)$", text, re.M | re.I)
    v = m.group(1).strip() if m else ""
    return "" if v.startswith("[") else v


def a_date(text):
    m = re.search(r"\d{4}-\d{2}-\d{2}", text or "")
    return date.fromisoformat(m.group(0)) if m else None


def paris_zone(day):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Paris")
    except ImportError:
        pass
    except KeyError:
        pass
    # Windows without tzdata: EU summer time, last Sunday of March to last Sunday of October.
    def last_sunday(month):
        end = date(day.year, month + 1, 1) - timedelta(days=1)
        return end - timedelta(days=(end.weekday() - 6) % 7)
    start, end = last_sunday(3), last_sunday(10)
    if isinstance(day, datetime) and day.tzinfo:
        utc = day.astimezone(timezone.utc)
        summer = datetime.combine(start, time(1), timezone.utc) <= utc < datetime.combine(end, time(1), timezone.utc)
    else:
        local = day if isinstance(day, datetime) else datetime.combine(day, time.min)
        summer = datetime.combine(start, time(2)) <= local < datetime.combine(end, time(3))
    return timezone(timedelta(hours=2 if summer else 1), "Europe/Paris")


def scheduled_at(text):
    """ISO date + time + offset or IANA zone; Paris by default. Date alone expires at end of day."""
    m = re.search(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?", text or "")
    if not m: return None
    value = m.group(0)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if len(value) == 10: dt = datetime.combine(dt.date(), time.max)
    if dt.tzinfo: return dt
    zone = re.search(r"\b([A-Za-z_]+/[A-Za-z_]+)\b", text)
    if zone and zone.group(1) != "Europe/Paris":
        from zoneinfo import ZoneInfo
        return dt.replace(tzinfo=ZoneInfo(zone.group(1)))
    return dt.replace(tzinfo=paris_zone(dt))


def as_moment(value):
    dt = value if isinstance(value, datetime) else datetime.combine(value, time.min)
    return dt if dt.tzinfo else dt.replace(tzinfo=paris_zone(dt))


def paris_date(value):
    dt = as_moment(value)
    return dt.astimezone(paris_zone(dt)).date()


def video_dirs(vids, require_suivi=True):
    return [p for p in sorted(vids.iterdir()) if p.is_dir() and not p.name.startswith((".", "_", "veille-"))
            and (not require_suivi or (p / "suivi.md").is_file())] if vids.exists() else []


def stage_line(text):
    """The first unchecked stage of suivi.md, or 'terminé'."""
    for line in text.splitlines():
        m = re.match(r"\s*- \[ \] (.+)", line)
        if m:
            return m.group(1)
    return "terminé"


def checked(text, number):
    return re.search(rf"^\s*- \[[xX]\] {number}\.", text, re.M) is not None


def video_info(d):
    s = d / "suivi.md"
    text = s.read_text(encoding="utf-8") if s.exists() else ""
    published = a_date(field(text, "Publiée le"))
    target = a_date(field(text, "Publication visée"))
    scheduled = scheduled_at(field(text, "Programmée pour"))
    status = field(text, "Statut").split(" (")[0] or ("publiée" if published else "programmée" if scheduled else "en cours")
    return {"id": d.name, "text": text, "status": status, "published": published, "target": target,
            "scheduled": scheduled, "next": stage_line(text) if text else "(pas de suivi.md)",
            "j3_fait": any((d / "bilans").glob("*-J3*")) if (d / "bilans").is_dir() else False}


def released(v, today):
    """(date of the actual release, confirmed?) : "Publiée le", else a scheduled date already passed."""
    if v["published"]:
        return v["published"], True
    if v.get("scheduled") and as_moment(v["scheduled"]) <= as_moment(today) and v["status"] == "programmée":
        return paris_date(v["scheduled"]), False
    return None, False


def videos_info(vids):
    infos = [video_info(d) for d in video_dirs(vids)]
    return sorted(infos, key=lambda v: (v["published"] or (paris_date(v["scheduled"]) if v.get("scheduled") else None)
                                       or v["target"] or date.max, v["id"]))


def echeances(v, today):
    """The reviews of a released video: (stage number, due date, label, release confirmed?); [] before release."""
    out_d, sure = released(v, today)
    if not out_d:
        return []
    out = []
    for number, days, label in BILANS:
        if number == "11" and v.get("j3_fait"):
            days, label = J7_COMPLET, "bilan J+7"
        out.append((number, out_d + timedelta(days=days), label, sure))
    return out


def bilans_dus(infos, today):
    out = []
    for v in infos:
        for number, due, label, sure in echeances(v, today):
            if paris_date(today) >= due and not checked(v["text"], number):
                out.append(f"{v['id']} : {label} dû depuis le {due.isoformat()} (skill bilan-video)"
                           + ("" if sure else " ; sortie programmée, à confirmer dans « Publiée le »"))
    return out


def git(r, *args, timeout=60):
    try:
        p = subprocess.run(["git", "-C", str(r), *args], capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout if p.returncode == 0 else None


def git_waiting(r, online=True):
    """Lines saying what is not pushed yet, or not pulled yet; [] when both PCs are in step."""
    out = []
    if online and git(r, "fetch", "-q", timeout=30) is None:
        out.append("GitHub injoignable : ce que l'autre PC a envoyé n'a pas pu être vérifié")
    status = git(r, "status", "--porcelain")
    if status is None:
        return ["git indisponible ici : impossible de vérifier ce qui n'est pas poussé"]
    changed = [l for l in status.splitlines() if l.strip()]
    if changed:
        out.append(f"{len(changed)} fichier(s) modifié(s) non commité(s) : lance envoi.bat (ou git add -A, commit, push)")
    ahead = git(r, "rev-list", "--count", "@{u}..HEAD")
    if ahead is None:
        out.append("la branche n'a pas de branche distante : git push -u origin <branche>")
    else:
        if int(ahead.strip() or 0):
            out.append(f"{ahead.strip()} commit(s) non poussé(s) : lance envoi.bat (ou git push)")
        behind = git(r, "rev-list", "--count", "HEAD..@{u}")
        if behind and int(behind.strip() or 0):
            out.append(f"{behind.strip()} commit(s) envoyé(s) par l'autre PC pas encore récupéré(s) : lance maj.bat")
    return out


def titles_of(v, d):
    """Every title this video may have been published under: suivi.md, then titres.txt (title | thumbnail text)."""
    titles = []
    m = re.search(r"^# Suivi : (.+)$", v["text"], re.M)
    if m and not m.group(1).startswith("["):
        titles.append(m.group(1))
    t = d / "titres.txt"
    if t.exists():
        titles += [l.split("|")[0] for l in t.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {slug(x) for x in titles}


def channel_titles():
    """Titles of the channel's latest videos (yt-dlp, public); None when yt-dlp is missing or offline."""
    if os.environ.get("YT_CHAINE_JSON"):  # tests
        data = json.loads(Path(os.environ["YT_CHAINE_JSON"]).read_text(encoding="utf-8"))
    else:
        cmd = ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]
        try:
            p = subprocess.run(cmd + ["--flat-playlist", "-J", "--playlist-end", "10", CHAINE],
                               capture_output=True, text=True, encoding="utf-8", timeout=60)
            data = json.loads(p.stdout) if p.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, ValueError):
            data = None
    if not data:
        return None
    return [(e.get("title") or "", e.get("id") or "") for e in data.get("entries") or []]


def publications_oubliees(vids, infos, today, online=True):
    """Videos probably online whose suivi.md has no 'Publiée le': review reminders depend on that date."""
    out, pending = [], [v for v in infos if not v["published"] and v["status"] not in ("terminée", "abandonnée")]
    for v in pending:
        if v["status"] == "programmée" and v.get("scheduled") and as_moment(v["scheduled"]) <= as_moment(today):
            out.append(f"{v['id']} : sortie programmée le {v['scheduled'].isoformat()}, passée : vérifie qu'elle est en ligne, "
                       "puis « Statut : publiée », « Publiée le » et le lien dans suivi.md")
    pending = [v for v in pending if not (v["status"] == "programmée" and v.get("scheduled"))]
    online_titles = channel_titles() if online and pending else None
    for v in pending:
        hit = None
        if online_titles:
            mine = titles_of(v, vids / v["id"])
            hit = next(((t, i) for t, i in online_titles if slug(t) in mine), None)
        if hit:
            out.append(f"{v['id']} : « {hit[0]} » est en ligne sur la chaîne mais « Publiée le » est vide dans "
                       f"suivi.md : remplis-le (date de publication, lien https://youtu.be/{hit[1]}), sinon aucun rappel de bilan")
        elif v["target"] and v["target"] < paris_date(today) and v["status"] != "mis de côté":
            out.append(f"{v['id']} : publication visée le {v['target'].isoformat()} dépassée : si elle est en ligne, "
                       f"remplis « Publiée le » et le lien dans suivi.md ; sinon, change la date visée")
    if online and pending and online_titles is None:
        out.append("chaîne YouTube non consultée (yt-dlp absent ou hors ligne) : publications oubliées non vérifiées")
    return out


def rangement(r, today):
    """Vide les caches sans risque, puis rend les écarts aux règles de rangement : rangement.py à la racine du dépôt
    (la règle, une seule source), cherché à côté de ce script puis dans le dépôt des données."""
    import importlib.util
    here = Path(os.path.realpath(__file__)).parents[3]
    src = next((d / "rangement.py" for d in (here, r) if (d / "rangement.py").is_file()), None)
    if src is None:
        return ["rangement.py introuvable : règles de rangement non vérifiées"]
    spec = importlib.util.spec_from_file_location("rangement", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    freed = mod.vider(r, today)
    total = sum(n for _, n in freed) / mod.MO
    out = [f"caches vidés : {total:.0f} Mo ({len(freed)} élément(s), refaits à la demande)"] if freed else []
    return out + mod.rapport(r, today)


def find(vids, text):
    """Existing videos named by an id or a title: exact id, then titles (suivi.md heading, titres.txt), then
    close ids or titles. [] when nothing matches; several entries when it is ambiguous."""
    if not vids.exists():
        return []
    dirs = video_dirs(vids, require_suivi=False)  # allow resuming a folder just created, before its suivi.md
    want = slug(text)
    exact = [d for d in dirs if d.name == want or d.name == text.strip()]
    if exact:
        return exact
    by_title = [d for d in dirs if want in titles_of(video_info(d), d)]
    if by_title:
        return by_title
    words = set(want.split("-")) - {"", "de", "la", "le", "les", "et", "a", "j", "ai", "en", "un", "une", "pour", "sur", "du", "des"}
    scored = []
    for d in dirs:
        names = {d.name} | titles_of(video_info(d), d)
        best = max(difflib.SequenceMatcher(None, want, n).ratio() for n in names)
        overlap = max(len(words & set(n.split("-"))) / max(1, len(words)) for n in names)
        if best >= 0.75 or overlap >= 0.6:
            scored.append((max(best, overlap), d))
    scored.sort(key=lambda x: -x[0])
    if len(scored) > 1 and scored[0][0] - scored[1][0] >= 0.2:
        scored = scored[:1]
    return [d for _, d in scored]


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("root", "id", "slug", "video", "trouve", "list", "etat"):
        print(__doc__); sys.exit(1)
    if a[0] == "slug":
        print(slug(" ".join(a[1:])))
    elif a[0] == "root":
        print(root())
    elif a[0] == "id":
        print(new_id(" ".join(a[1:]), root() / "videos"))
    elif a[0] in ("video", "trouve"):
        create = a[a.index("--creer") + 1] if "--creer" in a and a.index("--creer") + 1 < len(a) else None
        words = [x for i, x in enumerate(a[1:], 1) if x != "--creer" and a[i - 1] != "--creer"]
        vids = root() / "videos"
        hits = find(vids, " ".join(words)) if words else []
        if len(hits) == 1:
            print(hits[0]); return
        if len(hits) > 1:
            print("plusieurs vidéos correspondent, demande laquelle (AskUserQuestion) :\n"
                  + "\n".join(f"  {d.name}  ({video_info(d)['status']})" for d in hits), file=sys.stderr)
            sys.exit(2)
        if a[0] == "video" and create:
            d = vids / new_id(create, vids)
            d.mkdir(parents=True)
            print(d); return
        print(f"aucune vidéo ne correspond à « {' '.join(words)} » dans videos/ ; `repo.py list` les montre toutes"
              + (" ; pour en créer une : repo.py video --creer <2 ou 3 mots-clés>" if a[0] == "video" else ""), file=sys.stderr)
        sys.exit(1)
    elif a[0] == "list":
        for v in videos_info(root() / "videos"):
            when = (f"publiée {v['published']}" if v["published"]
                    else f"programmée {v['scheduled']}" if v.get("scheduled")
                    else f"visée {v['target']}" if v["target"] else "")
            print(f"{v['id']:<30}  {v['status']:<12}  {when:<20}  {v['next'].split(' (')[0]}")
    else:
        r, online = root(), "--hors-ligne" not in a
        local = datetime.now()
        infos, today = videos_info(r / "videos"), datetime.now(paris_zone(local))
        lines = (git_waiting(r, online) + bilans_dus(infos, today)
                 + publications_oubliees(r / "videos", infos, today, online) + rangement(r, paris_date(today)))
        print("\n".join(lines) if lines else "rien en attente : les deux PC sont à jour, aucun bilan dû, aucune publication oubliée")


if __name__ == "__main__":
    main()
