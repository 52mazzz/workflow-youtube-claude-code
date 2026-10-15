"""Mots de la transcription d'une vidéo entre deux secondes, avec leur début (DTW corrigé, temps de la timeline).
usage : python scripts/mots.py <id> a b [a b …]"""
import sys
from commun import ANALYSE, read_json, remap, video

cfg = video(sys.argv[1])
words = read_json(ANALYSE / "transcriptions" / cfg["transcription"])
vals = list(map(float, sys.argv[2:]))
for a, b in zip(vals[::2], vals[1::2]):
    print(" ".join(f"{w['text'].strip()}@{remap(w['startMs'] / 1000 - 0.12, cfg.get('coupes', [])):.2f}"
                   for w in words if a <= w["startMs"] / 1000 - 0.12 < b))
