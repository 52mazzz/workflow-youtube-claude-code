# HyperFrames Composition Project

## Projet TSAR — lire d'abord

Atelier de montage de la chaîne : kit du style (validé sur la vidéo 0927) `kit/tsar.js` + `kit/tsar.css` ;
éléments `compositions/*.html` **générés** par `python scripts/make_compositions.py` (ne pas les éditer à la main) ;
une vidéo = `videos/<id>/video.json` + `plan.json` (modèle `videos/_modele/`) ; scripts génériques
`python scripts/<script>.py <id>` (voix, transitions, zooms, combler, verifie_plan, export_capcut, audio, rendu, revue :
**rendu direct** du MP4 final depuis le 2026-10-08, CapCut seulement lu) ; exemple rendu complet : `videos/_exemple-direction/` ;
whisper dans `.whisper/`. Méthode complète et préférences : skill `montage-capcut`
(`~/.claude/skills/montage-capcut/`, SKILL.md § Démarrage rapide + references/outils.md). Écrire des plans JSON,
ne pas recoder d'animation ; les skills Hyperframes servent seulement pour un besoin que le kit ne couvre pas.

Guide Hyperframes générique (skills `/hyperframes…`, commandes, règles des compositions) : `AGENTS.md`, à ouvrir
seulement pour un besoin hors kit. Règles utiles au kit (lint, preview, mise à jour) : `references/outils.md` du skill.
