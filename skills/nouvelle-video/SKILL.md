---
name: nouvelle-video
description: "Point d'entrée de la production d'une vidéo de la chaîne YouTube @letsar555 (tsar rouge555) : idée, script, titres et miniatures, puis passage de relais au dérushage, au montage, à la description, aux shorts et au bilan, toutes reliées par videos/<id>/suivi.md. À utiliser dès que l'utilisateur dit \"nouvelle vidéo\", \"nouvelle video\", \"prochaine vidéo\", \"on fait une vidéo\", \"idée de vidéo\", \"je veux faire une vidéo\" ou \"next video\", même sans plus de détails, en particulier dans un nouveau chat. Enchaîne les skills yt-viral, youtube (ideate, metadata, shorts), grilling, yt-script, youtube-titles-ab, youtube-thumbnail-prompts et nano-banana-pro-prompting ; le bilan après publication est le skill bilan-video."
model: sonnet
effort: medium
---

# Nouvelle vidéo : workflow intégral

L'utilisateur lance ce workflow en disant simplement "nouvelle vidéo". Il ne doit rien re-expliquer : le contexte est déjà fixé ci-dessous. **Avant tout** :

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8          # sinon erreurs d'encodage sous Windows
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)   # « python » est souvent un faux lanceur sous Windows
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py etat
```

`etat` dit ce qui n'est pas poussé ou pas récupéré (le régler d'abord, sinon un PC travaille sur une vieille version), les bilans dus et les publications non notées. Ton rôle : dérouler les 5 phases dans l'ordre, sans s'arrêter entre les phases, sauf aux moments où une décision lui appartient (phase 2 et la validation de la phase 2). Ce skill couvre les étapes 1 à 3b de la chaîne de production (tableau complet : `references/chaine.md`) ; les suivantes ont leur skill et reprennent tout depuis `videos/<id>/`. Réponds en français, style normal (pas de style télégraphique).

## Contexte fixe de la chaîne

- Chaîne : @letsar555 (« tsar rouge555 »). Nombre d'abonnés à revérifier en phase 1.
- **Préférences** : lis `~/.claude/youtube/preferences.md` au début du run. C'est la source unique pour la chaîne et pour les règles de titres, miniatures et Shorts. Si l'utilisateur valide une nouvelle préférence pendant le run, ajoute-la dans ce fichier : c'est un lien vers `config/youtube/` du dépôt, elle partira avec le prochain commit.
- **Apprentissages** : lis `~/.claude/youtube/apprentissages.md` : le tableau (une ligne par vidéo publiée : levier gagnant, taux de clics, rétention) et la section **« Actions pour la prochaine vidéo »** (ce que les bilans demandent de changer ; la phase 3 et la phase 5 doivent les appliquer). Si `repo.py etat` annonce un bilan dû, propose d'abord le skill bilan-video (5 minutes), puis reprends le workflow.
- Voix : lis `~/.claude/youtube/voice.md` avant d'écrire un mot du script (vouvoiement collectif, première phrase = la mission, réactions courtes, verdict net, une seule demande finale). S'il manque, demande 3 vidéos de l'utilisateur et recrée-le.
- **Dossier de travail : `videos/` à la racine du dépôt**, pas le dossier courant : c'est ce qui permet de reprendre la vidéo sur l'autre PC. `REPO=$($PY ~/.claude/skills/nouvelle-video/scripts/repo.py root)` le trouve. La phase 1 travaille dans `$REPO/videos/veille-<AAAA-MM-JJ>/` (le sujet n'est pas encore choisi) ; **à la fin de la phase 5, renomme-le en `videos/<id>/`, où l'id est court : 2 ou 3 mots-clés du sujet** (`repo.py id pokemon ia` → `pokemon-ia` ; il refuse un id déjà pris). Pas le titre entier : les ids sont aussi les noms des projets CapCut, et tous les titres de duel commencent pareil. Cet id nomme aussi le dossier de montage et le projet CapCut, et ne change plus ensuite, même si Test & Compare désigne un autre titre. On y trouve `idees.md`, `refs.json`, `ma-chaine.json`, `script.md`, `titres-miniatures.md`, `suivi.md`, puis ce qu'écrivent les étapes suivantes. Les JSON bruts (`veille/`) et les miniatures téléchargées (`miniatures-refs/`) restent hors de git. Si un dossier de veille du jour existe déjà (run interrompu), reprends-le.
- **Suivi** : copie `~/.claude/skills/nouvelle-video/templates/suivi.md` dans le dossier dès la phase 1 et coche chaque étape terminée. `repo.py list` montre où en est chaque vidéo. À la fin de chaque phase, envoie : `envoi.bat "<id> : <étape>"` à la racine du dépôt (ou `git add -A && git commit -m "<id> : <étape>" && git push` depuis `$REPO`), pour reprendre sur l'autre PC.
- **Sources** : les décisions de contenu (idée, accroche, titre, miniature) s'appuient sur des **vidéos de référence d'autres chaînes**, classées par multiple de leur propre médiane. Les vidéos de l'utilisateur servent à ne pas se répéter, à garder sa voix et à lire ses résultats Test & Compare ; elles ne suffisent jamais à justifier un titre ou une idée.

## Règles qui valent pour toute la session

- **Ne rien inventer** : chiffres, résultats, vainqueurs, versions de modèles. Ce qui dépend du tournage reste en `[CROCHETS]`.
- **Rien n'est publié.** Tu écris, l'utilisateur publie.
- **Les questions se posent avec l'outil AskUserQuestion** (cases à cocher), jamais en texte libre. Mets l'option recommandée en premier avec « (Recommandé) ». Une question par décision, 4 questions maximum par tour, `multiSelect: true` quand plusieurs réponses sont possibles.
- « On valide, ou on change quelque chose ? » se pose **aux points d'arrêt seulement** (phase 2, puis une fois à la fin du run) : la liste complète, pour toutes les étapes, est dans `references/chaine.md` (« Quand Claude attend ta décision »). Entre deux points d'arrêt, enchaîne.

## Parcours rapide (par défaut) ou complet

Une vidéo par semaine ne tient que si chaque étape coûte ce qu'elle rapporte. **Le parcours rapide est le défaut** ; le complet se choisit pour une raison dite en une ligne.

| Étape | Rapide (défaut) | Complet (quand) |
|---|---|---|
| Veille | légère (déjà la règle) | complète toutes les 4 semaines |
| Références | `refs-sujet.json` de la vidéo précédente réutilisé si **même format** (duel qui crée un jeu) et moins de 3 semaines ; sinon une sélection | nouveau format, ou moins de 3 chaînes dans la sélection |
| Accroches | 3 écrites dans `script.md`, 2 gardées ; `hookscore.py script.md` + `minutage.py`, puis `relecture.py script.md` à zéro alerte (jamais sautés) | 5 quand un bilan demande de retravailler l'ouverture |
| Titres | 3 paires (Test & Compare en prend 3), tableau des références repris ; `suggest.py` seulement pour départager deux mots | nouveau sujet sans mot-clé connu |
| Montage | **le kit existant** ; un nouvel élément seulement pour un beat qui en a besoin (dis lequel), au plus un par vidéo | nouvelle série, ou demande de l'utilisateur |
| Shorts | 1 ou 2, tirés des pics de la vidéo | — |

Pas de mesure du temps passé (décidé le 2026-10-01) : le parcours se juge sur les bilans. Si un bilan montre qu'une étape allégée a coûté (ouverture, taux de clics), elle repasse en complet pour la vidéo suivante, et c'est noté dans « Actions pour la prochaine vidéo ».

## Tour 0 : longue ou Short, puis le domaine (avant la veille, 2026-10-16)

Avant toute veille, une seule fenêtre AskUserQuestion, deux questions (sautées si la demande les tranche déjà) :
- **Q1, Vidéo longue ou Short ?**
- **Q2, Quel domaine ?** (`multiSelect`) IA seule / IA + gaming / IA + tech / gaming pur (périmètre : `preferences.md` § Chaîne). Tout cocher = peu importe.

Short → passe au skill short avec le ou les domaines : sa fenêtre ne propose que des idées de ces domaines. Longue → la phase 1 vise ces domaines (`references/veille.md` § 3) et la phase 2 ne propose que leurs idées.

## Phase 1 : Veille et idées (skills yt-viral + youtube/ideate)

**Veille légère ou complète.** Légère par défaut chaque semaine (les chaînes qui ont un outlier récent, celles découvertes récemment, et 4 à 6 recherches fraîches que tu écris) ; complète toutes les 4 semaines (toutes les chaînes suivies et les recherches de base). La date de la dernière complète est celle du fichier le plus récent `~/.claude/youtube/references/*-veille-complete.json`. Dis en une ligne laquelle tu fais et pourquoi. Après une **veille complète**, lance aussi le mini-audit mensuel de la chaîne (skill chaine-youtube, section 1). Dans tous les cas, lis le résultat du dernier sondage Communauté (`~/.claude/youtube/chaine.md`) : l'option gagnante prend `"sondage": true` dans la grille. Lis aussi `~/.claude/youtube/idees-videos.md` (idées notées en passant par l'utilisateur) : chacune entre dans la grille comme les autres.

Toute la phase 1 suit **`references/veille.md`** (dans ce skill), à lire en entier au début de la phase : la collecte en une commande (`veille.py collecte`, skill yt-viral : classement par multiple de la médiane avec un plancher de vues, deuxième passage sur les chaînes découvertes, dynamique d'une semaine à l'autre, chaînes suivies dans `chaines.json`), le créneau français (`veille.py creneau`), la grille de classement des idées (`veille.py grille`) et `idees.md`. Ne lis que `veille/veille-resume.md`, pas les JSON bruts.

## Phase 2 : Grilling (skill grilling, en cases à cocher)

Pose les décisions par tours, avec AskUserQuestion. Tour 1 :
- Quelle idée (parmi celles de `idees.md`) ? Mets en premier celle qui a le meilleur rapport preuve / faisabilité. Pour une paire « copie fidèle / version originale », propose les deux comme options distinctes et rappelle la touche d'originalité en une phrase.
- Le jeu ou le sujet précis, si l'idée est une série générique.
- Duel Claude vs ChatGPT, Claude seul ou 3 IA ? (pas posée pour le gaming pur)
- Capacité de production cette semaine (vidéo lourde ou format léger).

Tour 2, selon les réponses : méthode (1 prompt sans correction, prompt + corrections, itérations libres), critères de jugement du gagnant (`multiSelect`), appel final aux commentaires.

Puis un récapitulatif en une question de validation (« on est alignés, j'écris le script ? »). N'agis pas avant cette validation. Une fois validé, renomme le dossier de veille en `videos/<id>/` (`repo.py id <2 ou 3 mots-clés>`, ex. `pokemon-ia`). Si l'idée retenue reprend une demande de commentaire, dis-le dans le récapitulatif (c'est un argument pour la suite). Les décisions déjà tranchées auparavant (voix, cadence, sans visage) ne se redemandent pas, sauf si l'utilisateur les remet en cause.

## Phase 3 : Accroches (skill yt-script)

**Lis `references/accroches-script.md` en entier au début de la phase 3** (il couvre aussi la phase 4).

## Phase 4 : Script (skill yt-script)

Suit `references/accroches-script.md` (lu en phase 3).

## Phase 5 : Titres et miniatures (skills youtube-titles-ab, youtube-thumbnail-prompts, nano-banana-pro-prompting)

**Lis `references/titres-miniatures.md` au début de la phase 5.**

## Préparation du tournage (étape 3b)

Suit `references/tournage.md` : `resultats.md` rempli depuis le template (prompt exact, outils, installations), puis `fiche.py <id>` → `fiche-tournage.md`. C'est l'étape à lancer sur « prépare le tournage <id> ».

## Fin de run

Avant de cocher l'étape 3, propose (sans l'imposer) une passe du conseil en mode ciblé sur le script (skill conseil-workflow, « conseil <id> script ») : c'est la seule relecture prévue avant le tournage, ensuite le script est gelé.

Résume en 6 lignes ce qui a été produit (fichiers, id, idée retenue, titre principal et la référence sur laquelle il s'appuie, ce qu'il reste à tourner). Rappelle la suite en 3 lignes : finir la checklist « Avant de tourner » de `resultats.md`, tourner avec `fiche-tournage.md` sous les yeux, remplir `resultats.md` le jour même (ou le dicter au prochain chat), puis « dérushe <id> ». Envoie (`envoi.bat`) pour que le PC fixe ait le script et la checklist. Dernière ligne : « Ship it, or change it ? »

## La chaîne de production

Le tableau des 13 étapes (qui lit quoi, qui écrit quoi) et les règles de raccord entre étapes sont dans `references/chaine.md` (dans ce skill). Lis-le **quand l'utilisateur reprend une vidéo** (« on en est où sur <id> ? », « reprends <id> ») : lis `suivi.md`, puis lance l'étape suivante d'après ce fichier. Un run « nouvelle vidéo » complet n'en a pas besoin : tout ce qu'il faut pour les étapes 1 à 3b est ci-dessus et dans les `references/` qu'il cite à chaque phase.
