---
name: "youtube-thumbnail-prompts"
description: "Concevoir des miniatures YouTube à fort CTR et rédiger leurs prompts image (Nano Banana, etc.) : lisibilité mobile, curiosity gap, mascotte, gaming."
model: opus
effort: high
---

# Miniatures YouTube : concepts et prompts image

À utiliser avec le skill nano-banana-pro-prompting pour la syntaxe des prompts, et youtube-titles-ab pour le titre associé.

## Contexte de la chaîne
Lire `~/.claude/youtube/preferences.md`, section « Miniatures » : chaîne sans visage, mascotte optionnelle, texte de 3 à 4 mots. Si l'utilisateur valide une nouvelle préférence, l'ajouter dans ce fichier, pas ici.
- **Mascotte (le Tsar)** : lire `~/.claude/youtube/mascotte.md` (description, couleurs, tableau des expressions). Choisir l'image de `~/.claude/youtube/mascotte/` dont l'expression raconte le concept (surprise, doute, gêne, rire, réflexion, explication, tête, en pied), la passer en image 1 dans le prompt (« Use image 1 as the mascot, keep its exact design, colors and proportions ») et nommer le fichier dans le livrable pour que l'utilisateur la joigne. Ne pas la poser sur le rouge de la chaîne (elle disparaît). S'il faut une expression qui n'existe pas, partir de la plus proche et demander une variation, sans réinventer le personnage.
- `~/.claude/youtube/apprentissages.md` dit quels leviers de miniature ont gagné les Test & Compare précédents (pas à relire s'il a déjà été lu dans la conversation).

## Miniature finale d'une vidéo de la chaîne (étape 7 de la production)
Après le montage, avec les vraies captures (`videos/<id>/resultats.md`, section « Captures à garder ») : les 3 miniatures finales du Test & Compare, et les captures réelles utilisées en référence, vont dans **`videos/<id>/miniatures/`** (`1-<levier>.png`, `2-<levier>.png`, `3-<levier>.png`, `captures/`). Ce dossier est versionné : la miniature est ainsi sur les deux PC. Images de plus de 50 Mo : non (`envoi.bat` les refuse) ; exporter en PNG ou JPG 1280×720, moins de 2 Mo (limite de YouTube).

**Contrôle avant Test & Compare** (`miniature.py`, dans ce skill ; OpenCV, et CLIP s'il est installé avec `python setup.py --vision`) :

```bash
$PY ~/.claude/skills/youtube-thumbnail-prompts/miniature.py videos/<id>/miniatures/[123]-*.png \
    --refs videos/<id>/refs-sujet.json --chaine videos/<id>/ma-chaine.json
```

Pour chaque miniature : format et poids, contraste, luminosité, couleurs dominantes, densité de détails, **coin bas droit** (la durée s'y affiche), aperçus à 120, 246 et 480 px ; une **planche** où la miniature est posée au milieu des miniatures des meilleures références, comme dans le fil, avec sa version 120 px ; la **similarité CLIP** contre les concurrents (moins de 0,55 : elle se démarque ; plus de 0,70 : elle se fond dans la masse) et contre les 11 dernières de la chaîne (moins de 0,60 : le style dérive). **Ouvre la planche avec l'outil Read et regarde-la vraiment** : à 120 px, comprend-on le sujet, lit-on le texte, voit-on l'émotion de la mascotte ? Si une réponse est non, c'est un défaut à corriger avant de charger les 3 paires. Les mesures décrivent l'image, elles ne prédisent pas le taux de clics : Test & Compare tranche. Sans OpenCV, le script le dit ; fais alors le contrôle à l'œil sur les miniatures des références (`--thumbs`).

Coche l'étape 7 de `suivi.md`.

## Références visuelles (avant de proposer un concept)
Comme les titres, les concepts partent des miniatures de vidéos qui ont dépassé leur médiane sur le même sujet ou le même format, pas seulement des miniatures de la chaîne.
- Reprendre la même sélection `refs-sujet.json` que pour les titres et télécharger ses miniatures dans cet ordre : `$PY ~/.claude/skills/yt-viral/swipe.py --refs-selection videos/<id>/refs-sujet.json --top 8 --thumbs videos/<id>/miniatures-refs/`. Les ouvrir et les regarder vraiment. Si la sélection manque, la créer avec `selection.py` avant ce contrôle ; le classement global ne la remplace pas.
- **Analyse** (2026-10-16) : `$PY ~/.claude/skills/youtube-thumbnail-prompts/miniature.py videos/<id>/miniatures-refs/*.jpg --grille` → mesures de chaque miniature (contraste, texte, coin de la durée, aperçus) et une grille numérotée à 246 et 120 px. Regarde la grille 120 px avec Read. Pour chacune, un tableau d'une ligne : n°, multiple de la médiane, sujet principal, nombre d'éléments, texte (mots exacts), couleurs, logo / avant-après / personnage, **levier** (ce qui donne envie de cliquer), **à changer** (ce qui est faible : illisible à 120 px, trop d'éléments, texte qui répète le titre, coin de la durée chargé, ou « rien »). Puis les 2 ou 3 constantes parmi les outliers.
- **Choix de l'utilisateur** : envoie la grille (SendUserFile, `render`) avec le tableau, puis AskUserQuestion `multiSelect: true` : « Lesquelles t'attirent le plus ? » (4 options par question, 2 questions pour 8 miniatures ; libellé = n° + 3 mots, multiple en description). Ne conseille pas avant ce choix : c'est son œil de spectateur qu'on mesure.
- **Adaptations** : pour chaque miniature choisie, propose (1) ce qu'on garde (le principe : composition, levier, contraste), (2) ce qu'on corrige de ses défauts relevés plus haut, (3) l'adaptation à la vidéo : le sujet et les éléments de `script.md`, la mascotte, le logo, le texte de 3 à 4 mots qui complète le titre, (4) si besoin, ce que **la vidéo** doit changer pour tenir la promesse de la miniature : un plan ou un résultat à tourner ou capturer (à noter dans `resultats.md`, « Captures à garder »), une scène à mettre plus tôt. Les concepts de miniature partent de ces choix ; une miniature non choisie ne sert de base qu'en pari, signalé.
- Chaque concept proposé indique la miniature de référence dont il reprend le principe (ou « pari original ») et ce qui le distingue : ne jamais reproduire une miniature existante, ni ses personnages, ni son texte.
- Si le téléchargement échoue (réseau bloqué), le dire et s'appuyer sur la description des titres de référence et les formats validés de `preferences.md`, en le signalant.
- Les formats validés de `preferences.md` restent des préférences de forme ; si les références montrent un autre principe qui marche nettement mieux sur ce sujet, le proposer comme variante de test plutôt que de l'écarter.

## Règles de lisibilité (vérifier chaque concept)
- Compréhensible en moins d'une seconde, à la taille d'une miniature mobile (~2 cm de large).
- Un sujet principal évident ; 3 éléments visuels maximum.
- Texte : nombre de mots et mot-clé mis en valeur selon les préférences (section « Miniatures ») ; très gros, contraste fort, jamais dans le coin bas droit (durée de la vidéo).
- Le texte complète le titre, ne le répète pas.
- Montrer le résultat spectaculaire plutôt que le processus ; pas d'interfaces logicielles inutiles.
- Contraste de couleurs fort entre le sujet et le fond (chaud contre froid).

## Formats validés par la chaîne
Voir `preferences.md` § Miniatures.

## Leviers de clic
- Transformation / avant-après (même objet, même angle, écart maximal).
- Curiosity gap : montrer une partie seulement, masquer le vainqueur, porte entrouverte.
- Incrédulité : « ceci est X » sur une image qui ne ressemble pas à X.
- Affrontement : A vs B, même scène, deux résultats visiblement différents.
- Menace / tension : élément inquiétant à moitié caché.

## Format du prompt miniature
Toujours inclure :
- « YouTube thumbnail, 16:9, 1280x720 (ou 2K/4K), ultra sharp, high contrast, readable on a phone. »
- La hiérarchie visuelle (ce que l'œil voit en premier, puis ensuite).
- La composition en positions précises (left third, top center, straddling the center line…).
- Premier plan / arrière-plan / effets / couleurs dominantes.
- Le texte exact entre guillemets, avec police, couleur, contour et position.
- « Keep the bottom right corner clean. No watermark, no other text. Spell the text exactly as written. »

## Logos
Nano Banana Pro sait retrouver les logos connus : nommer le logo officiel et le décrire précisément (forme, couleur de fond avec code hex, symbole, position, taille) plutôt que d'exiger une image de référence. Ajouter « Reproduce the official logo exactly, flat, without stylization. » Si le logo sort déformé : « Search for the official … icon and reproduce it exactly », sinon l'ajouter en post-production.
- ChatGPT : rounded square, teal-green background (#10A37F), white OpenAI hexagonal interlaced knot symbol.
- Claude : rounded square, terracotta-orange background (#D97757), white starburst of short rounded rays.

## Fidélité aux résultats réels
Quand la vidéo compare des résultats réels (shaders, mods, builds, IA…), proposer aussi une version **avec captures en référence** : « Use image 1 as … keep it faithful, do not change lighting, colors or content; only crop, align and slightly boost contrast. » Une miniature entièrement inventée qui ne correspond pas à la vidéo nuit à la confiance ; la version générée sert à valider la mise en page. Si l'utilisateur préfère la version générée, la donner en principal et la version captures en une ligne.

## Spécifique Minecraft / gaming
- Garder les formes cubiques reconnaissables même en rendu réaliste (« everything keeps its Minecraft cube shapes »).
- Éléments iconiques qui marchent : bloc d'herbe, creeper, cochon, porte, épée en diamant.
- Scènes qui vendent le réalisme : eau et reflets, brume volumétrique, coucher de soleil, lumière entre les arbres, pluie.
- Captures en jeu : F1 (masquer l'interface), /time set, /weather clear, /gamerule doDaylightCycle false, /tp avec yaw/pitch identiques pour des angles comparables.

## Livrable attendu
- Pour des concepts : une description courte par concept (1 à 2 phrases) par défaut ; le détail complet (composition, premier plan, arrière-plan, positions, texte, effets, couleurs, raison du clic, titre) seulement sur demande. Puis un top 3 CTR.
- Pour un prompt : bloc de code prêt à copier, puis 2 ou 3 conseils d'itération.
- Pour un A/B test : 3 paires miniature + titre (voir youtube-titles-ab), trois leviers différents, chacune avec sa miniature de référence.
