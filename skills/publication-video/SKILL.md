---
name: publication-video
description: "Publier une vidéo de la chaîne @letsar555 sans rien oublier (étape 9 de la production) : vérifications avant la mise en ligne (description, miniatures, Test & Compare, écran de fin, sous-titres), programmation, puis après la mise en ligne « Publiée le » et le lien dans suivi.md, rappels de bilan et envoi. À utiliser quand l'utilisateur dit « publie <id> », « on publie », « je mets en ligne », « c'est en ligne », « c'est publié », « vidéo programmée », ou quand description-video vient de finir."
model: sonnet
effort: low
---

# Publication d'une vidéo (étape 9 de la chaîne de production)

Réponds en français. Questions avec AskUserQuestion (cases à cocher), option recommandée en premier. **Rien n'est publié par Claude** : l'utilisateur met en ligne dans YouTube Studio ; ce skill vérifie, guide et note.

## 1. Retrouver la vidéo

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py etat     # non poussé, non récupéré, bilans dus
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py list
```

Lis dans `videos/<id>/` : `suivi.md` (étapes 6 à 8 cochées ? écarts), `titres-miniatures.md` (les 3 paires, la principale), `description.md`, `resultats.md`, et `~/.claude/youtube/preferences.md`. Une étape 6 à 8 non cochée : le dire et proposer de la faire d'abord (le skill correspondant), sans bloquer si l'utilisateur publie quand même ; noter alors l'écart dans `suivi.md`.

## 2. Avant la mise en ligne : vérifier ce qui peut l'être d'ici

```bash
$PY ~/.claude/skills/description-video/check_description.py videos/<id>/description.md --duree <durée du montage final> --mot-cle "<mot-clé principal>"
$PY ~/.claude/skills/youtube-titles-ab/check_titles.py videos/<id>/titres.txt --refs videos/<id>/refs-sujet.json --own videos/<id>/ma-chaine.json --mot-cle "<mot-clé principal>"
ls videos/<id>/miniatures/
```

Le mot-clé principal est celui de `titres-miniatures.md` (paire « recherche »). **Code de sortie** : 1 = au moins une ERREUR (règle de YouTube ou de la chaîne, ou contrôle obligatoire impossible) : on corrige et on relance, on n'avance pas ; 0 = aucune erreur. Les « conseil » s'affichent sans bloquer : lis-les, suis-les ou dis pourquoi pas.

- Description et titres : les deux commandes sortent avec le code 0 ; les conseils sont lus.
- Miniatures : 3 images finales dans `miniatures/` (1280×720, PNG ou JPG, moins de 2 Mo pour YouTube), une par paire de `titres-miniatures.md`, avec les vraies captures. S'il en manque, le dire : étape 7 (youtube-thumbnail-prompts). Si le contrôle `miniature.py` n'a pas été fait à l'étape 7, lance-le (voir youtube-thumbnail-prompts) et regarde la planche.
- **La promesse du titre principal est tenue** par le montage final (`resultats.md`, écarts de `suivi.md`). Sinon, choisir une autre paire principale avant de publier.

## 3. La checklist Studio (l'utilisateur coche, une question AskUserQuestion `multiSelect`)

Présente-la comme une seule question à cocher, puis reviens sur ce qui n'est pas coché :

1. Titre principal et description collés depuis `description.md` (chapitres compris : 0:00 en premier).
2. **Test & Compare** : les 3 paires titre + miniature de `titres-miniatures.md` chargées (la principale en premier).
3. Tags et hashtags de `description.md` ; catégorie **Jeux vidéo** ; langue de la vidéo et des sous-titres : **français**.
4. Sous-titres automatiques relus sur les noms propres (Claude, ChatGPT, nom du jeu) une fois générés.
5. Écran de fin (20 dernières secondes) : la vidéo suivante prévue dans `~/.claude/youtube/chaine.md` (« Écrans de fin » ; sinon la plus proche par le sujet, à y noter) + abonnement ; la vidéo ajoutée à sa playlist (« Playlists » de `chaine.md`) ; rien d'important caché sous l'écran de fin.
6. Visibilité : **programmée** (date et heure) ou publique tout de suite.
7. Shorts : **pas avant** la vidéo longue ; prévus le jour même puis à 2 ou 3 jours d'écart, avec « vidéo associée » vers la longue (étape 10, montage-capcut).

**Heure de publication** : aucune règle n'est fixée dans `preferences.md`. Demande l'heure choisie et, si l'utilisateur veut en faire une règle, propose de l'ajouter à `preferences.md` (seulement avec son accord). N'invente pas une « meilleure heure » : les statistiques d'audience de Studio (« Quand vos spectateurs sont sur YouTube ») sont la seule source.

## 4. Après la mise en ligne (ou la programmation)

1. Demande le lien (ou l'id de 11 caractères) et la date de sortie. Si yt-dlp passe, confirme le titre en ligne : `yt-dlp --flat-playlist -J --playlist-end 5 "https://www.youtube.com/@letsar555/videos"`.
2. En haut de `videos/<id>/suivi.md` :
   - **sortie programmée** : `Statut : programmée`, `Programmée pour : AAAA-MM-JJ HH:MM` (la date et l'heure réglées dans Studio), `Lien : https://youtu.be/<id YouTube>` ; « Publiée le » reste vide. Une fois la date passée, `repo.py etat` compte les bilans à partir d'elle et demande de confirmer la sortie ;
   - **sortie faite** (publique tout de suite, ou programmation passée et vérifiée en ligne) : `Statut : publiée`, `Publiée le : AAAA-MM-JJ` (date de sortie réelle), le lien.
   Coche l'étape 9 dans les deux cas. **C'est la date de sortie effective qui déclenche les rappels de bilan de `repo.py etat`** : sans « Publiée le » ni « Programmée pour », aucun rappel.
3. **Rappels de bilan** : aucun rappel à créer par vidéo. La tâche planifiée « Bilans dus » du portable (chaque jour, toutes les vidéos) et `repo.py etat` (début de chaque session) les annoncent d'après la date de sortie remplie ci-dessus ; voir « Bilans automatiques » dans bilan-video.
4. **Sondage Communauté** (skill chaine-youtube, section 3) : propose le sondage « Quel duel pour la prochaine vidéo ? » (3 ou 4 options tirées des idées restantes et des commentaires), à poster le jour de la sortie ; note-le dans `chaine.md`.
5. Envoie : `envoi.bat "<id> : publication"` à la racine du dépôt (ou `git add -A && git commit -m "<id> : publication" && git push`).
6. **Rangement** : `python rangement.py` à la racine (les caches de la vidéo publiée se vident seuls, `--vider` si besoin), puis l'agent `archiviste` avec la racine du dépôt, l'id et cette sortie. Montre son plan ; n'applique que ce que l'utilisateur valide, après `repo.py etat` (l'autre PC n'a rien envoyé) : les chemins proposés par `rangement.py --supprimer "<chemin>"`, le reste à la main ; puis envoie à nouveau.
7. Suite : « fais-en des shorts » (étape 10, montage-capcut), puis « bilan vidéo » à J+3 (étape 11) et J+28 (étape 12).

Termine par « On valide, ou on change quelque chose ? ».
