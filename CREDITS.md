# Crédits et licences tierces / Third-party notices

Ce dépôt contient du code et des ressources venus d'autres auteurs, chacun sous sa propre licence. La licence du reste
du dépôt ne les remplace pas.

This repository includes code and assets by other authors, each under its own license, listed below.

## Code et méthodes / Code and methods

| Où / Where | Origine / Origin | Licence | Texte / Text |
|---|---|---|---|
| `skills/yt-viral/` : `SKILL.md`, `swipe.py` (modifiés) | yt-viral, Jake Schincariol, https://github.com/Jakeschincariol/youtube-agent-skill | MIT | `skills/yt-viral/licence-mit.txt` |
| `skills/yt-script/` : `SKILL.md`, `hooks.json`, `hookscore.py` (modifiés) | yt-script, Jake Schincariol, même dépôt | MIT | `skills/yt-script/licence-mit.txt` |
| `skills/youtube-titles-ab/` (adapté) | yt-package, Jake Schincariol, même dépôt | MIT | `skills/youtube-titles-ab/licence-yt-package.txt` |
| `skills/youtube-titles-ab/` (adapté) | yt-title-optimizer, Sergey Bulaev, https://github.com/sergebulaev/youtube-skills | MIT | `skills/youtube-titles-ab/licence-yt-title-optimizer.txt` |
| Méthodes reprises dans `chaine-youtube`, `description-video`, `bilan-video`, `youtube-titles-ab`, `youtube-thumbnail-prompts`, `yt-viral` | youtube-seo-skills, Deeploy, https://github.com/deeployCO/youtube-seo-skills | MIT | ci-dessous / below |

Les autres scripts de `yt-viral` et `yt-script` (`veille.py`, `accroches.py`, `selection.py`, `comments.py`,
`refs_history.py`, `minutage.py`, `relecture.py`) ont été écrits pour la chaîne.

## Ressources / Assets

| Où / Where | Origine / Origin | Licence | Texte / Text |
|---|---|---|---|
| `montage/08_HYPERFRAMES/assets/fonts/` | Inter Tight, JetBrains Mono, DM Serif Display, Montserrat (Google Fonts) | SIL Open Font License 1.1 | `OFL-*.txt` dans le même dossier |
| `montage/04_RESSOURCES/sfx/kenney_interface-sounds/` et 5 sons de `montage/08_HYPERFRAMES/assets/sfx/` | Interface Sounds, Kenney | CC0 1.0 | `License.txt` dans le dossier |
| `montage/08_HYPERFRAMES/assets/tsar/` | Mascotte de la chaîne TSAR | Tous droits réservés, hors de la licence du code | — |

Détail des ressources du montage : `montage/04_RESSOURCES/LICENCES.md`.

## Utilisés mais pas inclus / Used but not included

- HyperFrames (HeyGen, Apache-2.0) : lancé par `npx hyperframes@0.8.123`, rien n'est copié ici.
- GSAP 3.14.2 (licence « Standard » de Webflow) : à télécharger dans `montage/08_HYPERFRAMES/assets/vendor/`.
- Skills tiers appelés par le workflow : claude-youtube (AgriciDaniel, MIT), grilling, baoyu-youtube-transcript (JimLiu).
- Outils : FFmpeg, whisper.cpp, yt-dlp, OpenCV, CLIP (open_clip), Python, Node.js.

## youtube-seo-skills : licence MIT

```
MIT License

Copyright (c) 2026 Deeploy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
