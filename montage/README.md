# Montage TSAR — atelier Claude

Dossier `montage/` de ce dépôt. Mode d'emploi complet et mise en place sur un PC : `WORKFLOW.md`.

L'atelier tourne sur le **PC fixe** (OBS, Whisper, CapCut, Hyperframes, export). Le portable sert à écrire et à accéder au fixe à distance ; les projets et médias de montage restent sur le fixe.

Rushs bruts : `Documents\TSAR\Videos\<Nom de la vidéo>\Rush` sur le fixe (lecture seule, hors dépôt), ou le dossier désigné par `TSAR_RUSH`. L'ancien dossier `Documents\TSAR\Rush` reste reconnu.

## Structure

| Dossier | Contenu | Règle |
|---|---|---|
| `01_RUSHS/` | Vide (les rushs sont dans `Documents\TSAR\Videos\<Nom de la vidéo>\Rush`) | — |
| `02_ANALYSE/` | Dérushage (`derush_*.json`, rapports), transcriptions mot à mot, prises, voix nettoyées, vues de timeline | Claude ; régénérable |
| `04_RESSOURCES/` | Originaux : `musiques/perso/` (ses musiques et celles qu'il a gardées après écoute, fiches dans `musiques/catalogue.json` : `musique.py`, règle du 2026-10-08), `sfx/` (Kenney, synth, pixabay), `assets/` (mascotte Tsar), `images/` | **Licences : `04_RESSOURCES/LICENCES.md`** |
| `05_EXPORTS/` | Exports finaux | — |
| `06_CAPCUT/<id>/` | **Fichiers utilisés par les projets CapCut** (overlays, scènes, voix, musique, SFX, shorts) + `LISEZ-MOI.md` | **Ne rien déplacer ni supprimer** : CapCut perd le lien |
| `07_OUTILS/capcut-bridge-windows/` | Pilotage de CapCut (lire/modifier un projet, poser overlays, coupes) — voir son README | — |
| `08_HYPERFRAMES/` | **L'atelier** : kit TSAR (`kit/`), compositions, scripts génériques, whisper, `videos/<id>/` (réglages par vidéo) | Voir `08_HYPERFRAMES/CLAUDE.md` |

## Nouvelle vidéo

Tout se règle dans `08_HYPERFRAMES/videos/<id>/video.json` + `plan.json` (modèle : `videos/_modele/`, exemple réel :
`videos/_exemple/`, la 0927). Les scripts se lancent depuis `08_HYPERFRAMES\scripts` : `python <script>.py <id>`.
On ne copie jamais un script pour une vidéo.
