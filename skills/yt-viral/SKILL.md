---
name: yt-viral
description: >-
  Find what is actually working in the user's niche on YouTube and rank it
  by how far each video beat its own channel, then name the formula. Use for
  "what's working right now", "find viral videos in my niche", "why did this
  blow up", competitor research, or a swipe file.
---

# yt-viral

Raw view counts rank channel size, not ideas. This ranks by **multiple over each channel's own
median**, which is the only version of the question that is about the video.

For the channel's weekly watch, use **`veille.py`**: it runs the whole collection (followed channels
in `chaines.json`, searches, a second pass on channels found by the searches, a views floor, the
dynamics against earlier collections), archives it and writes a short `veille-resume.md`; `creneau`
checks whether a concept was already done in French, `grille` scores the ideas. Its docstring is the
manual; the workflow is in nouvelle-video's `references/veille.md`.

```bash
python3 veille.py collecte --mode legere --requete "..." --requete "..."   # or --mode complete
python3 veille.py creneau "ia crée un jeu d'horreur"
python3 veille.py grille idees-grille.json
python3 swipe.py collected.json --min 2.0 --min-views 10000
python3 swipe.py veille/*.json --min 2.0 --no-shorts --max-age 365 --exclude @your-own-handle --json > refs.json
python3 refs_history.py save refs.json --slug topic     # keep it; `show` reads what holds over weeks
python3 comments.py URL1 URL2                            # what viewers liked and ask for next
```

## Collecting the input

You need at least **four videos per channel** old enough to count (14 days by default,
`--median-min-age`: a video out this week has not finished its run and would drag the median down)
or a median means nothing, and the tool will skip the channel and tell you it did. Every row says
how many videos its median rests on (`median_n`); under 8 it is marked fragile - say so when you
quote that multiple. Collect them however the user prefers - `yt-dlp --flat-playlist -J`
against a channel URL is the fastest, the public page works, a manual list works.

```json
[{"channel":"...","title":"...","views":412000,"url":"...","duration":613}]
```

The raw `yt-dlp --flat-playlist -J` output (channel, channel tab or `ytsearchN:` query) is read as
is, several files at once, with duplicates counted once. Search results alone give one or two videos
per channel, so use them to find channels, then collect each channel's `/videos` tab for the median.
Keep Shorts apart from long videos (`--no-shorts`), leave the user's own channel out of the ranking
(`--exclude`), and use `--thumbs DIR` to download the top outliers' thumbnails and look at them.
Collect channel tabs with `--extractor-args "youtubetab:approximate_date"`: every entry then has an
approximate date, `--max-age` drops old hits (the median still uses every video old enough to count) and each outlier
shows its age and views per day.

**Read, do not scrape.** Public listings only, never a logged-in session, never the user's own
account credentials.

## Reading the output

The multiple is the signal. The formula line is a judgement about the TITLE, matched against
[the 21 formulas](../yt-script/hooks.json) - it is not a claim about why the video worked, and you
should say so when you present it.

What to hand back: the top five with their multiples, the formula each used, and the ONE structural
thing they share. Then the harder line - which of those the user could actually make this week, in
their voice, with what they have.

## The gate

Nothing here publishes. This skill writes and you publish. Every output ends in a block the user
copies, and the last line of every run is the question: **ship it, or change it?** (inside a
nouvelle-video run, that question waits for the single check at the end of the run: see the stop
points in `nouvelle-video/references/chaine.md`)
