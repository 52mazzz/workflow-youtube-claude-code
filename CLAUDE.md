# Dépôt de la chaîne @letsar555 (TSAR)

Toute la production de la chaîne, de l'idée au bilan, plus les skills et la config de Claude Code. Le dépôt est la seule copie : `~/.claude/skills/`, `~/.claude/youtube` et `~/.claude/agents` sont des liens vers lui (`setup.py`). Mode d'emploi : `README.md` ; tableau de bord de l'utilisateur : `atelier.bat` (`atelier.py`). Montage : `montage/WORKFLOW.md` et `montage/08_HYPERFRAMES/CLAUDE.md`. Chantiers en cours : `config/youtube/chantiers.md` (à lire seulement quand on en parle ou qu'on prépare une vidéo).

Tout en français. Règles de la chaîne (ton, titres, miniatures, montage) : `config/youtube/preferences.md`, source unique.

## Deux PC

- **Fixe = atelier** (RTX 3070 Ti) : tournage, transcription, dérush (CapCut), montage et export en rendu direct (`rendu.py`, CapCut seulement lu). **Portable** : écriture (idées, script, titres, description, bilans) et accès au fixe à distance. Installation : `INSTALLATION_CLAUDE.md`.
- Le montage d'une vidéo vit sur un seul PC : projet CapCut et `06_CAPCUT/` hors git (chemins absolus). Les rushs ne passent **jamais par git** : `Documents\TSAR\Videos\<Nom de la vidéo>\Rush`.
- Envoi vers l'autre PC : `envoi.bat` (ou `python envoi.py "<id> : <étape>"`). Pas de commit ni de push sans demande. « push » depuis une session sur une branche (web) = pousser **et** fusionner la pull request dans `main`, sinon l'autre PC ne reçoit rien.
- Avant de déplacer ou supprimer un fichier suivi : `repo.py etat` (l'autre PC n'a rien envoyé ?), sinon conflit.
- Au début d'une étape de production (dérush, montage, publication…) : relire l'état donné par le hook (`repo.py etat`) ; travail non envoyé sur ce PC → l'envoyer d'abord ; bilan dû → le signaler en une ligne ; `maj.bat` si l'autre PC a pu envoyer depuis.

## Où va quoi

| Quoi | Où |
|---|---|
| Une vidéo (idée, script, titres, résultats, description, shorts, `bilans/`) | `videos/<id>/`, avec un `suivi.md` obligatoire (sinon invisible pour `repo.py list` et `etat`) |
| Veille en cours | `videos/veille-<AAAA-MM-JJ>/`, **renommée** en `videos/<id>/` à la fin de la phase 5 (un `veille-*` restant est un doublon : vérifier puis supprimer) |
| Dérushage (prises, coupes, rapports, transcriptions) | `montage/02_ANALYSE/` (chemins fixés par les scripts) |
| Réglages de montage | `montage/08_HYPERFRAMES/videos/<id>/` |
| Fichiers de CapCut | `montage/06_CAPCUT/<id>/` (**ne rien déplacer ni supprimer** : CapCut perd le lien) |
| Musiques, SFX, images (licences : `LICENCES.md`) | `montage/04_RESSOURCES/` |
| Apprentissages, préférences, conseils (`conseils/<date>.md`) | `config/youtube/` |
| Agents nommés | `config/agents/` |
| Brouillons jetables | scratchpad de la session, jamais le dépôt |

Id d'une vidéo : 2 ou 3 mots-clés (`repo.py id`), ne change plus, nomme aussi le dossier de montage et les projets CapCut (`<id>`, puis `<id> - final`).

Rangement : règles détaillées dans `rangement.py` (source unique : emplacements, noms, jamais dans git, caches), appliquées par le hook `garde.py`. Éditer avec Write/Edit (contrôlés par le hook) et ranger là où il dit ; un script qui écrit les fichiers, seulement pour un remplacement mécanique sur beaucoup de fichiers, suivi tout de suite de `python rangement.py`. Caches sans risque vidés seuls (`repo.py etat`) ; le reste supprimé seulement après accord (`rangement.py --supprimer`).

## Conventions obligatoires

- **Une règle, un seul endroit** ; ailleurs un renvoi (« voir X § Y »). Sources : chaîne → `config/youtube/preferences.md` ; script → `nouvelle-video/references/accroches-script.md` ; montage → `montage-capcut/references/preferences.md` ; rangement → `rangement.py` ; dépôt et deux PC → ici.
- **Règle remplacée = supprimée** (jamais barrée ni marquée ancienne : git garde l'historique), la nouvelle datée. Une contradiction se corrige partout, dans le même tour.
- **Budgets** (caractères) : ce fichier 6 000, un autre `CLAUDE.md` 3 000, un `SKILL.md` 26 000, une autre doc 40 000, une description de skill 1 024. Dépassé → raccourcir, sans exception.
- Contrôlé par `rangement.py` (chaque session), `garde.py` (chaque écriture) et les tests : un écart se corrige avant de continuer.

## Installer des outils

Permis sans demander (paquet Python, outil en ligne de commande, version GPU…) : source officielle, une ligne pour dire quoi et pourquoi, et noter dans `INSTALLATION_CLAUDE.md` de quoi refaire l'installation sur l'autre PC. Annoncer avant les gros téléchargements (plus de quelques centaines de Mo) et les logiciels lourds.

## Économie de tokens (obligatoire)

- **Mode éco actif par défaut** (skill `economie-tokens` § Mode éco), sans attendre qu'on le demande ; « mode normal » le coupe. Le charger avant une tâche lourde (dérush, montage, veille, audit) ; lancer son audit (`scripts/audit_contexte.py .`) après un changement de skills ou de `CLAUDE.md`.
- Un script avant le modèle : ce qui est mécanique (état, rangement, contrôles, mesures) passe par `repo.py`, `controle.py`, `dosage.py`, etc.
- Lire le strict nécessaire : chemin exact, et pour les gros fichiers (transcriptions, `derush_*.json`, bilans `.json`) la partie utile avec `Grep` ou une plage de lignes, jamais tout par défaut. Exception : un fichier qu'un skill dit de lire « en entier » (ex. `montage-capcut/references/preferences.md` avant de monter) se lit en entier, sans économie.
- Pas de sous-agent pour une recherche de quelques fichiers ; les agents nommés seulement aux étapes qui les prévoient.
- Les fichiers de `config/youtube/` ne se lisent qu'à l'étape qui les demande dans son skill ; les `references/` d'un skill, seulement à l'étape qui y renvoie.
