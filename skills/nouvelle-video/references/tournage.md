# Étape 3b : préparation du tournage

Partie du skill nouvelle-video, lue à l'étape 3b ou sur « prépare le tournage <id> ».

## Préparation du tournage (étape 3b)

Copie `~/.claude/skills/nouvelle-video/templates/resultats.md` dans `videos/<id>/` et remplis tout ce qui est déjà connu : le prompt exact (celui de `script.md`, mot pour mot), l'outil et l'environnement prévus pour chaque IA, ce qu'il faut installer ou tester avant (version du jeu, loader, moteur, navigateur). Ce qui dépend d'une décision de l'utilisateur (outil, version du jeu) se pose en AskUserQuestion, pas en devinette. Coche l'étape 3b de `suivi.md` quand la checklist « Avant de tourner » ne contient plus que ce qui se fait devant l'écran le jour même. Si l'utilisateur reprend une vidéo mise de côté (« prépare le tournage <id> »), c'est cette étape qu'il faut lancer.

Puis génère la **fiche de tournage**, à garder sur le téléphone pendant le tournage (beats dans l'ordre, phrases-cadres, prompt exact, notes de tournage et checklist en cases à cocher) : `$PY ~/.claude/skills/nouvelle-video/scripts/fiche.py <id>` → `videos/<id>/fiche-tournage.md` (lisible dans l'appli GitHub après l'envoi). À refaire après toute modification de `script.md`.

