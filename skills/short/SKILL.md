---
name: short
description: "Choisir puis proposer un Short (vertical, 20 à 52 s) pour la chaîne @letsar555 : une fenêtre de choix (cases à cocher, comme pour les vidéos longues) présente 3 ou 4 idées appuyées sur les données (Shorts des chaînes suivies, idées restantes, bilans, rushs), mélangeant Shorts filles (tirés d'une vidéo longue) et Shorts indépendants ; l'idée choisie reçoit ensuite accroche dite tout de suite, déroulé minuté, d'où viennent les images, titre de 20 à 40 caractères. Rien n'est fabriqué. À utiliser quand l'utilisateur dit « /short », « une idée de short », « propose un short », « un short pour <id> », « un short fille », « un short indépendant », « un autre short ». Pour fabriquer le Short une fois l'idée validée, voir le skill montage-capcut (« fais-en des shorts », ou « monte le short <id> » pour un Short indépendant)."
model: sonnet
effort: medium
---

# Un Short : le choix, puis l'idée

Réponds en français, phrases simples, vouvoiement collectif pour le spectateur, **aucun emoji**. Ce skill **choisit et propose** ; il ne monte rien. La fabrication (script validé, montage avec la direction en format vertical, MP4) reste dans montage-capcut.

Règles de la chaîne : `~/.claude/youtube/preferences.md` § Shorts et ton ; style de montage : `skills/montage-capcut/references/preferences.md` § Shorts (la direction « duel lisible et nerveux », en vertical) ; voix : `voice.md`.

**Les questions se posent avec AskUserQuestion** (cases à cocher), jamais en texte libre, option recommandée en premier avec « (Recommandé) », 4 questions au plus par tour, comme pour les vidéos longues (nouvelle-video, phase 2, méthode du skill grilling : on pose ce qui est décidable maintenant, on n'attend pas de réponse pour la suite, on ne redemande pas ce qui est déjà tranché : sans visage, ton, voix, style de montage).

## 1. Deux sortes de Short

- **Fille** : tirée d'une vidéo longue (`/short <id>`, « un short pour pokemon-ia »). Elle s'appuie sur des moments réels ou prévus de cette vidéo, et renvoie vers elle (« vidéo associée »).
- **Indépendante** : sans vidéo mère (`/short`, « un short sur <sujet> »). Elle est sa propre mini-vidéo : son tournage, son dérushage, son projet CapCut (montage-capcut § « Short indépendant »).

Sans précision, la fenêtre de choix mélange les deux ; avec un id, seulement les filles de cette vidéo ; avec « indépendant », seulement les indépendantes.

## 2. Lire les données (rien d'inventé)

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py list        # vidéos, statuts, étape en cours
$PY ~/.claude/skills/short/scripts/shorts_refs.py               # Shorts des chaînes suivies (résumé de moins de 14 jours réutilisé)
```

`shorts_refs.py` classe les Shorts des chaînes de référence (et de LAirHisson, la référence de style) par multiple de la médiane de **leurs propres** Shorts, et écrit `config/youtube/references/<date>-shorts.json`. **Limites à annoncer** : l'onglet Shorts n'a pas de date (un Short récent a moins de vues qu'un ancien, le multiple est un indice), et ce sont des vues, pas de la rétention. Moins de 8 Shorts relevés sur une chaîne : « fragile ». `--ajoute @handle` pour une chaîne de plus, `--toutes` pour les 80 chaînes.

Lis ensuite, selon la sorte :

- **Fille** : pour chaque vidéo publiée ou tournée dont l'étape 10 de `suivi.md` n'est pas cochée, `script.md`, `resultats.md`, `shorts.md` (idées déjà proposées, faites ou écartées), `suivi.md` (statut, dates) ; si la vidéo est dérushée, `montage/02_ANALYSE/` (prises, transcriptions, par exemple `transcriptions/capcut_<projet>.txt` pour des phrases et des horodatages réels). Les pics de rétention des bilans (`videos/*/bilans/`, `apprentissages.md`) disent quel moment tient le spectateur.
  - **Pas encore tourné** : le moment est **prévu** par le script ; le dire (« à confirmer au tournage ») et garder une alternative.
  - **Tourné ou monté** : le moment est **réel** (phrase dite, capture, résultat de `resultats.md`), avec son horodatage ou son fichier.
- **Indépendante** : `preferences.md` (fil « IA et création », esprit gaming, sans visage, pas de gaming Roblox), `types-de-videos.md`, `apprentissages.md` (ce qui a tenu ou non), les idées restantes des `videos/*/idees.md`, les formats de Shorts qui ont dépassé leur médiane chez les chaînes suivies (`shorts_refs.py`), et `config/youtube/idees-shorts.md` + les `videos/*/shorts.md` pour ne pas se répéter. Elle n'a pas de rush : dis **ce qu'il faut produire** (une consigne donnée à une IA et son résultat à l'écran, un mini-défi, une capture) et que c'est à tourner ou à générer.

Partout : aucun chiffre, aucun résultat, aucune phrase que la source ne contient pas, et ne pas promettre ce que le Short ne montrera pas (`voice.md`). Une preuve venue d'un autre domaine ou d'une autre chaîne se dit comme telle (un Short de Minecraft sur une chaîne de Minecraft ne prouve pas un Short d'IA).

## 3. La fenêtre de choix

Construis **3 ou 4 candidats**, chacun avec sa sorte, sa preuve et sa faisabilité, puis pose le tour 1 (une seule fois, tout ce qui est décidable) :

- **Q1, Quelle idée ?** 3 ou 4 options, une phrase d'idée en intitulé (précédée de `Fille <id>` ou `Indépendant`), la preuve et le coût en description (« 7,0x la médiane de ses Shorts chez LAirHisson, moment réel à 2:42 de la vidéo, images déjà là »). Au moins une fille et une indépendante quand les deux existent. **Recommandé en premier** : le meilleur rapport preuve / faisabilité ; à preuve égale, une fille d'une vidéo publiée sans Short (images déjà montées, elle fait revenir vers la vidéo). Une fille ne se propose qu'après la publication de sa vidéo mère, jamais avant (`references/chaine.md`).
- **Q2, Production cette semaine ?** images déjà là seulement (filles) / un petit tournage possible / une génération ou une capture suffit. Elle écarte les candidats qui ne tiennent pas.
- **Q3, Le sujet précis**, seulement si le candidat choisi est un format générique (« un jeu absurde en une phrase » : quel jeu, quelle consigne ?). Si Q1 n'est pas encore tranchée, cette question attend le tour 2.

Un candidat « proposée, non choisie » d'une fois précédente peut revenir tel quel ; un candidat « écartée » ne revient jamais.

## 4. L'idée choisie

Une seule, détaillée, après le tour 1. Format :

- **Idée** : une phrase.
- **Accroche** (0 à 3 s) : la phrase dite tout de suite, sujet dans la première phrase, pas de carton titre, pas d'outro (le Short boucle). **Toujours passée par le guide des scripts (skill yt-script, règle du 2026-10-08)** : 3 accroches écrites d'après les 21 formules (`hooks.json`), écrites en blocs `**Version X**` d'une ligne `- **0-3 s** [ON SCREEN : …] : « … »` dans un `.md` (`videos/<id>/shorts.md` pour une fille, sinon le scratchpad), notées avec `$PY ~/.claude/skills/yt-script/hookscore.py <fichier>.md`, **plus `--profil solo` quand le Short n'a qu'une seule IA** (sinon le barème du duel la note bas d'office ; le scoreur le rappelle par une ALERTE) (heuristique : elle repère mission, règle, précision et question ouverte, pas le naturel, le dire), les 2 meilleures montrées avec le tableau qu'il imprime, puis `$PY ~/.claude/skills/yt-script/minutage.py <fichier>.md` sur le déroulé (code 0 obligatoire). Une fille tournée n'utilise que des phrases réellement dites dans les rushs (jamais de mot inventé) : l'accroche se compose en les réordonnant (résultat d'abord, puis retour en arrière), et le Short boucle sur son premier plan.
- **Déroulé minuté** : tableau temps / ce qui est dit / image, une ligne par créneau sous la forme `| 0-3 s | « phrase dite » | image |` (lue par `minutage.py`), (rush, capture, mascotte Tsar) en 5 à 8 lignes ; un changement toutes les 1 à 1,5 s environ. Durée totale 20 à 52 s. Fille tournée : les phrases sont celles de la vidéo, avec leur position.
- **Images** : fille, les fichiers ou moments de `script.md`, `resultats.md`, prises (horodatés) ; indépendante, ce qu'il faut tourner ou générer.
- **Titre** : 20 à 40 caractères, mêmes règles que les titres longs (ton gaming, pas de deux-points, de points de suspension ni de tiret, marques connues). Contrôle : `$PY ~/.claude/skills/youtube-titles-ab/check_titles.py <fichier> --shorts` (un titre par ligne dans un fichier du scratchpad).
- **Publication** : fille, après sa vidéo, avec « vidéo associée » vers elle (`publication-video` § 3, point 7) ; indépendante, sans lien, à la date qui convient à la cadence.
- **Risque** : une ligne (moment non confirmé, spoiler du verdict, musique, droit à l'image d'une capture…).

Puis le tour 2, une question AskUserQuestion : **Garder / Un autre candidat de la fenêtre / Changer quelque chose** (si changer : accroche, durée, titre ou images, en `multiSelect`).

## 5. Après sa réponse

- **Validé, fille** : l'ajouter à `videos/<id>/shorts.md` (créer le fichier s'il manque : idée, accroche, titre, statut « idée validée »), puis proposer de passer à la fabrication (montage-capcut). Ne coche pas l'étape 10 de `suivi.md` : elle se coche quand les Shorts sont faits.
- **Validé, indépendante** : pas de dossier de vidéo ; l'ajouter à `config/youtube/idees-shorts.md` (créer le fichier s'il manque : une section par idée, avec date, accroche, titre, statut). La suite (script minuté validé, tournage, dérushage, montage avec la direction en vertical) est dans montage-capcut § « Short indépendant » ; propose de la lancer et rappelle ce qu'il faut tourner (ligne « Images »).
- **Candidats non choisis** : les noter dans le même fichier avec le statut « proposée, non choisie (date) » et leur preuve, pour qu'ils reviennent dans une prochaine fenêtre. Une idée que l'utilisateur refuse explicitement : « écartée : <raison> ».
- **« Un autre »** : une nouvelle idée sur un autre moment, jamais une variante de la précédente.
- Si l'utilisateur change une règle de Shorts pendant la session, la noter dans `preferences.md` § Shorts (source unique).
- Ne commit pas, ne pousse pas, sauf demande (`envoi.bat`).

## Ce que ce skill ne fait pas

Pas de montage, pas de rendu, pas de publication, pas d'idée détaillée avant le choix, pas d'emoji, pas de visage.
