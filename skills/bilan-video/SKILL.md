---
name: bilan-video
description: "Bilan d'une vidéo publiée de la chaîne @letsar555, 3 à 7 jours après sa sortie (et à 28 jours) : statistiques YouTube Analytics (rétention à 30 s, % regardé, vues des jours 0-1 et 0-6, abonnés, sources de trafic), résultat du Test & Compare, comparaison avec les vidéos précédentes et les références, puis une ligne dans apprentissages.md que le workflow nouvelle-video relit. À utiliser quand l'utilisateur dit \"bilan vidéo\", \"bilan de la vidéo\", \"comment marche ma vidéo\", \"résultats de la vidéo\", \"stats de la vidéo\", \"le test A/B est fini\" ou \"Test & Compare terminé\"."
model: sonnet
effort: medium
---

# Bilan vidéo

Le workflow nouvelle-video s'appuie sur des vidéos de référence d'autres chaînes. Ce bilan ajoute la deuxième source : ce que les vidéos de la chaîne ont réellement appris. Réponds en français. Les questions se posent avec AskUserQuestion (cases à cocher), option recommandée en premier.

## 1. Quelle vidéo

Commence par `$PY ~/.claude/skills/nouvelle-video/scripts/repo.py etat` : il liste les bilans dus (J+3/J+7 et J+28 après la date « Publiée le » de chaque `suivi.md`) et ce qui n'est pas poussé. Si l'utilisateur ne précise pas la vidéo : prends celle dont le bilan est dû, sinon la dernière vidéo de la chaîne (`yt-dlp --flat-playlist -J --playlist-end 5 "https://www.youtube.com/@letsar555/videos"`) qui n'a pas encore de ligne dans `~/.claude/youtube/apprentissages.md`, et confirme-la en une question. Moins de 3 jours après la publication, préviens : YouTube Analytics a environ 2 jours de retard, le bilan sera partiel.

## 2. Les chiffres

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/bilan-video/scripts/bilan.py VIDEO_ID --id <id> --age <3, 7 ou 28> --vue "<dépôt>/montage/02_ANALYSE/vue_<projet - final>.txt"
```

- `--age N` arrête tous les chiffres au jour N-1 : c'est ce qui permet de comparer deux vidéos **au même âge** (bilan J+7 de l'une contre bilan J+7 de l'autre), quel que soit le jour où le bilan est lancé. Prends 3 ou 7 pour l'étape 11 (selon le jour où il est fait), 28 pour l'étape 12.
- `--id <id>` garde chaque collecte dans `videos/<id>/bilans/<instant-UTC>-J<fenêtre-demandée>.json` (ou `-cumul` sans `--age`). L'âge actuel reste une donnée distincte. Les relances au même instant ont un suffixe et n'écrasent rien. La courbe brute, ses unités et sa provenance sont conservées pour refaire l'analyse hors ligne. `apprentissages.md` garde une ligne par vidéo.
- **Périodes** : YouTube Analytics compte en **jours entiers, à l'heure du Pacifique** (Los Angeles), pas en heures depuis la sortie. Le jour 0 est le jour de sortie (souvent partiel : une sortie à 18 h en France tombe le matin à Los Angeles). Dis « vues des jours 0 à 6 », jamais « vues en 48 h » ou « en 7 jours pile ».

`--vue` (la transcription horodatée du montage final, faite par montage-capcut sur le fixe, puis partagée dans `montage/02_ANALYSE/` par git) relie chaque chute et chaque pic de la courbe à la phrase dite à ce moment ; sans elle, les temps seuls s'affichent. Le bilan peut se faire sur le portable après récupération de ces textes.

Le script donne, depuis la publication (ou jusqu'au jour N-1 avec `--age N`) : vues, vues des jours 0-1 et des jours 0-6, durée moyenne, % moyen regardé, rétention à 30 s, 25 %, 50 % et 75 %, abonnés gagnés et perdus, j'aime, commentaires, partages, sources de trafic, et les impressions et le taux de clics quand l'API les expose. Il termine par une ligne pour `apprentissages.md`.

Si l'accès OAuth n'est pas configuré (le script le dit) : lance `bilan.py VIDEO_ID --public` pour les chiffres publics, explique la configuration de la section 6 (`references/configuration-analytics.md`), et demande les chiffres de Studio à la place. Pour la courbe de rétention sans OAuth : Studio → la vidéo → Statistiques → Mode avancé → Rétention de l'audience → exporter en CSV, puis `bilan.py --csv <fichier> --duree <durée réelle, secondes ou m:ss> --vue <vue>`. Le script lit l'unité de la position (pourcentage, ratio ou secondes) sur l'en-tête ou les valeurs et l'affiche ; s'il ne peut pas trancher, il s'arrête et demande `--unite-position` : ouvre le CSV, regarde la colonne, ne devine pas. Un export partiel (une partie de la vidéo seulement) est signalé : ne conclus rien en dehors de la plage couverte.

**La courbe** (API ou CSV) : le script donne le niveau à 0:15 (accroche) et à 1:00 (promesse, repère ≥ 60 %), les **chutes** (10 % ou plus du public perdu en moins de 10 s, après les 30 premières secondes) et les **pics** (le public revient en arrière : moments forts, à réutiliser en Shorts, chapitres, miniature). Pour chaque chute, dis ce qui se passe à l'écran et dans la phrase (`--vue`, `script.md`, écarts de `suivi.md`) : digression, plan fixe trop long, promesse du titre pas encore tenue, longue génération… comme une **hypothèse**, jamais comme un fait.

Pour archiver un CSV, ajouter `--id <id>` et, si l'export couvre bien cette fenêtre, `--age N`. Cette option étiquette l'export ; elle ne filtre pas sa période. L'archive contient le CSV original et la courbe normalisée en ratios. L'en-tête détermine l'unité de rétention ; si elle est ambiguë, fournir `--unite-retention pourcentage|ratio`. Un ratio peut dépasser 1 ou 2 avec les relectures, selon la [définition officielle d'audienceWatchRatio](https://developers.google.com/youtube/analytics/metrics#audienceWatchRatio).

## 3. Ce que l'API ne donne pas (à demander)

En une question AskUserQuestion à la fois :
- **Test & Compare** : quel est le **statut exact** affiché par Studio ? « en cours », « gagnant » (quelle variante, avec quelle part du temps de visionnage), « performances similaires » ou « non concluant ». YouTube départage sur la **part du temps de visionnage**, pas sur le taux de clics. Proposer les 3 paires de `titres-miniatures.md`. Si le test tourne encore, le noter et revenir plus tard.
- **Taux de clics et impressions** si le script ne les a pas : Studio → la vidéo → Statistiques → Audience/Portée → « Taux de clics des impressions ». Une capture d'écran suffit ; lis-la.

## 4. Lecture

Compare avec les lignes précédentes de `apprentissages.md`, puis avec la sélection pertinente de la vidéo (`refs-sujet.json` et `idees.md` dans `videos/<id>/`). Si elle manque, la créer avec `selection.py` à partir de `refs.json` ; le classement global ne remplace pas cette sélection. Le script affiche aussi des **repères gaming** (rétention à 30 s ≥ 70 %, part regardée 45 à 55 % pour une vidéo longue, sous 35 % c'est bas pour la niche, taux de clics 5 à 10 %) : des repères de niche (suite youtube-seo-skills), pas une loi ; la comparaison avec les vidéos précédentes de la chaîne prime. Repères pour une petite chaîne, à nuancer :
- Rétention à 30 s : sous 60 %, l'accroche ou la promesse du titre est en cause (relire les 15 premières secondes du script). Au-dessus de 70 %, l'ouverture fait son travail. Au bilan J+7, ajoute la vidéo à `~/.claude/skills/yt-script/calibration.json` (ouverture dite dans les 15 premières secondes, prise dans `montage/02_ANALYSE/vue_<id> - final*.txt`, et rétention à 30 s ; remplace une valeur J+3 déjà notée), puis lance `hookscore.py --calibrer` et note dans le bilan si le scoreur classe les ouvertures dans le même ordre que leur rétention.
- % regardé : comparer surtout aux vidéos précédentes de la chaîne, la valeur absolue dépend de la durée.
- Taux de clics : 2 à 10 % est la plage habituelle ; il baisse normalement quand YouTube montre la vidéo à un public plus large. Un taux élevé avec peu d'impressions dit peu.
- Sources de trafic : beaucoup de « Parcourir » et de « Vidéos suggérées » veut dire que l'algorithme teste la vidéo ; beaucoup de « Recherche YouTube » veut dire que le titre et les tags sont bien trouvés.
- **Test & Compare** : une variante gagnante dit que **cette paire** (titre + miniature, qui changent ensemble) a retenu plus de temps de visionnage, pas pourquoi. N'écris pas « l'humour gagne » : écris « la paire A (humour, miniature conversation) a gagné ; hypothèse : le ton » ; seule une série de tests où **un seul** élément change peut isoler une cause. « Performances similaires » ou « non concluant » est un résultat à noter tel quel (« aucune paire ne se détache »), pas un échec à interpréter. Avec moins de 3 tests, c'est une tendance, pas une règle.
- **Un repère n'est pas un mécanisme** : « 30 % regardé, sous le repère gaming » est un constat ; « YouTube freine la vidéo » n'en est pas un (on ne le mesure pas).

Sépare toujours trois choses, dans cet ordre : **constats** (chiffres mesurés, avec leur période), **hypothèses** (ce qui pourrait l'expliquer, marqué comme tel, avec ce qui permettrait de le vérifier), **statut du test A/B** (le libellé exact de Studio). Donne 3 constats chiffrés, 1 chose à refaire, 1 chose à changer. **La chose à changer devient une action concrète** pour la vidéo suivante : ce qu'on fait autrement, où (accroche, beat, titre, miniature, montage), et son **plan de mesure** : le chiffre à surveiller, la fenêtre et le seuil de réussite. Format :

| Changement | Chiffre à surveiller | Fenêtre | Réussi si |
|---|---|---|---|
| accroche : résultat montré avant 0:05 | rétention à 30 s | bilan J+3 de la vidéo suivante | ≥ 60 % (puis 70 %) |
| chute à 2:10 (génération trop longue) : couper la génération à 20 s | chute à cet endroit | même bilan | plus de chute au même beat |
| miniature principale changée | taux de clics des impressions | 14 jours | +1 point | Relis aussi les actions ouvertes de `apprentissages.md` : si la vidéo mesurée en appliquait une, dis si elle a marché, chiffres à l'appui. N'invente aucune cause : « la rétention a chuté à 1:40 » est un fait, « parce que le passage était ennuyeux » est une hypothèse, à présenter comme telle.

## 5. Ce qui reste

1. Ajoute la ligne complète (sans `[à compléter]` si l'information est connue) à la fin du tableau de `~/.claude/youtube/apprentissages.md` (le tableau finit le fichier). Ajoute l'action concrète dans « Actions pour la prochaine vidéo » (`- [ ] (bilan de <id>, <date>) …`) et ferme celles que ce bilan a jugées (`- [x] … [fait <date>, <id>] résultat`). Une vidéo, une ligne : si la ligne existe déjà (bilan à 28 jours), mets-la à jour au lieu d'en ajouter une ; les bilans précédents restent dans `videos/<id>/bilans/` (option `--id`), rien n'est perdu. Dans la colonne « Leçon », écris le constat puis l'hypothèse marquée (« hypothèse : … »), jamais une cause présentée comme sûre. Le « levier gagnant » vaut « paire A (humour) » ou « aucune paire ne se détache », jamais un levier présenté comme prouvé.
2. Si un constat confirme ou contredit une préférence de `preferences.md`, propose la modification à l'utilisateur ; ne change le fichier qu'avec son accord.
3. `~/.claude/youtube` est un lien vers le dépôt : la ligne est déjà dans `config/youtube/apprentissages.md`. Coche l'étape 11 de `videos/<id>/suivi.md` (12 pour le bilan à 28 jours), puis envoie : `envoi.bat "<id> : bilan"` à la racine du dépôt (ou `git add -A && git commit -m "<id> : bilan" && git push`).
4. Le bilan à 28 jours (étape 12) est annoncé par `repo.py etat` et collecté par la tâche quotidienne du fixe (voir « Bilans automatiques ») : pas de rappel à créer.
5. Après un bilan **J+7** (étape 11), propose le conseil (skill conseil-workflow, étape 11b de `suivi.md`) : trois agents jugent tout le workflow avec ces chiffres neufs, puis un juge garde 1 à 3 changements mesurables. Rien à proposer après un J+3 ou un J+28.

## Bilans automatiques

- **Rappel** : le hook `SessionStart` de `.claude/settings.json` du dépôt lance `repo.py etat` au début de chaque session, sur les deux PC ; si un bilan est dû, le proposer dans la première réponse.
- **Annonce quotidienne** (portable, tâche planifiée « Bilans dus » de l'app Claude, chaque jour à 11 h, tant que l'app est ouverte) : lance `repo.py etat` et notifie les bilans dus de toutes les vidéos, avec ce que le fixe a déjà collecté. Lecture seule : ne récupère, n'écrit ni n'envoie rien. Remplace les rappels par vidéo.
- **Collecte seule** (PC fixe, tâche planifiée « Bilan automatique des vidéos TSAR » de l'app Claude, chaque jour à 10 h, tant que l'app est ouverte) : `bilan_auto.py` collecte les bilans J+7 et J+28 dus deux jours après la fin de leur fenêtre (retard d'Analytics), jamais le J+3, et jamais deux fois la même fenêtre. Sortie dans `videos/<id>/bilans/<date>-J<N>-auto.txt`, puis la tâche écrit `<date>-J<N>-brouillon.md`, envoie seulement `videos/<id>/bilans/` et notifie. Elle ne touche ni `apprentissages.md` ni `suivi.md`.
- Quand un `*-auto.txt` existe : partir de lui et du brouillon (pas besoin de relancer `bilan.py`), demander seulement ce qui vient de Studio (section 3), puis faire la section 5 comme d'habitude.

## 6. Configuration de l'accès YouTube Analytics (une seule fois)

À lire seulement si `bilan.py` dit que l'accès OAuth manque : `references/configuration-analytics.md` (`secrets_vault.py status` / `encrypt`, sinon création du client OAuth en 5 étapes). Le script ne lit que les statistiques et ne publie rien.
