---
name: conseil-workflow
description: "Conseil de trois agents indépendants (le spectateur, le producteur, l'analyste) qui jugent le workflow de la chaîne @letsar555 chacun sous son angle, puis un juge qui vérifie leurs preuves et ne garde que 1 à 3 changements mesurables. Mode complet (tout le workflow, une fois par vidéo publiée, après le bilan J+7) ou mode ciblé (un seul livrable : idée, script, titres). À utiliser quand l'utilisateur dit « conseil », « le conseil », « fais juger le workflow », « audit du workflow », « les agents qui jugent », « conseil <id> script », ou quand bilan-video propose l'étape 11b."
model: opus
effort: high
---

# Conseil du workflow

Trois agents lisent le dépôt chacun de leur côté, sans voir le travail des autres, puis tu fais le juge. Le but n'est pas de produire une liste d'idées : c'est de garder **au plus trois changements**, chacun avec un chiffre qui dira s'il a marché. Réponds en français. Les questions se posent avec AskUserQuestion (cases à cocher), option recommandée en premier avec « (Recommandé) ».

## Quand le lancer

- **Mode complet** (défaut) : une fois par vidéo publiée, **après son bilan J+7** (étape 11b de `suivi.md`), dans le créneau atelier de la semaine. Pas plus d'une fois par semaine. Si aucun bilan nouveau n'est arrivé depuis le dernier conseil (`config/youtube/conseils/`), dis-le et propose de ne pas le lancer : il n'y a rien de neuf à juger.
- **Mode ciblé** (« conseil <id> idée | script | titres ») : une seule passe sur un livrable, **avant** de cocher son étape dans `suivi.md`. Pour le script, c'est la seule relecture autorisée avant le tournage : ensuite il est gelé jusqu'au tournage, sauf blocage noté dans « Écarts par rapport au plan ». Une accroche changée par le conseil repasse par `hookscore.py videos/<id>/script.md` (tableau remplacé) et `minutage.py`, puis `relecture.py videos/<id>/script.md` à zéro alerte, avant de cocher l'étape.
- **Coût** : trois sous-agents sur Sonnet qui lisent beaucoup de fichiers, de l'ordre de 100 000 à 150 000 jetons chacun en mode complet, bien moins en ciblé ; la lecture lourde est sur le modèle moins cher, le jugement sur le modèle principal. Annonce-le en une ligne avant de lancer.

## 1. Préparer le contexte

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
REPO=$($PY ~/.claude/skills/nouvelle-video/scripts/repo.py root)
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py etat
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py list
ls "$REPO/config/youtube/conseils/" 2>/dev/null
git -C "$REPO" log --since="<date du dernier conseil, sinon 30 jours>" --date=short --pretty=format:"%ad %s" --name-only
```

Si `repo.py etat` annonce un bilan dû, propose d'abord bilan-video : le conseil juge sur des chiffres à jour.

Prépare un **bloc de contexte** (20 lignes au plus) à coller dans chaque prompt d'agent, avec des faits seulement, sans tes conclusions :
- la racine du dépôt (`$REPO`) et la date du jour ;
- les vidéos : id, statut, date de publication ou visée, étape suivante (`repo.py list`) ;
- les lignes du tableau de `apprentissages.md` et les actions ouvertes ;
- le dernier rapport de `config/youtube/conseils/` : ses changements adoptés et leur date de mesure ;
- le résumé du `git log` : nombre de commits par dossier (`videos/`, `skills/`, `tests/`, `config/`, `montage/`) depuis le dernier conseil ;
- en mode ciblé : l'id, le livrable et son fichier.

## 2. Les trois agents

Les trois rôles sont des **agents nommés** : `spectateur`, `producteur` et `analyste`. Leurs fichiers sont dans `config/agents/` du dépôt, que `setup.py` relie à `~/.claude/agents/` (comme `config/youtube/`) : ils sont donc disponibles dans toutes les conversations Claude Code, sur les deux PC. Ils tournent sur Sonnet (moins cher que la conversation principale) et n'ont que les outils de lecture (Read, Grep, Glob) : ils ne peuvent ni modifier un fichier, ni lancer d'autres agents. Leur rôle et leurs règles sont dans ces fichiers, qui sont la seule source à modifier.

Lance-les **dans le même message** (outil Agent, un appel par rôle, `subagent_type` = `spectateur`, `producteur`, `analyste`) pour qu'ils travaillent en parallèle et sans s'influencer. Le prompt de chacun ne contient que : le mode (complet ou ciblé), la racine du dépôt, la date et le bloc de contexte. Ne leur donne ni ton avis, ni le rapport d'un autre agent.

**Si ces agents n'apparaissent pas** : `~/.claude/agents` n'est pas encore relié (lancer `maj.bat` ou `python setup.py`, puis redémarrer Claude Code). En attendant, lis le fichier du rôle dans `config/agents/` et passe son texte (sous l'en-tête) en prompt à un agent `general-purpose` avec `model: sonnet`.

Toi, tu restes sur le modèle principal : c'est le juge qui demande le plus de jugement, pas le plus de lecture.

## 3. Le juge (toi)

Dans cet ordre :

1. **Vérifie chaque preuve.** Ouvre le fichier cité, retrouve l'extrait, refais les calculs. Un constat que tu ne retrouves pas est écarté, et tu le dis.
2. **Applique les garde-fous de mesure.** Moins de 100 vues dans la fenêtre : « non mesurable », jamais « échec ». Avec moins de 3 vidéos comparables, c'est une tendance, pas une règle. Une hypothèse reste marquée « hypothèse ».
3. **Juge les actions ouvertes** (de `apprentissages.md` et du dernier conseil) : a marché, n'a pas marché, ou non mesurable, chiffres à l'appui. Tant qu'une action ouverte n'est pas mesurée, **aucune nouvelle action sur le même chiffre**.
4. **Arbitre les désaccords** entre agents en une phrase chacun (exemple : le spectateur veut changer le titre, l'analyste dit de ne pas toucher au titre pendant le test).
5. **Garde 1 à 3 changements**, **au plus un par chiffre surveillé**, sinon on ne saura pas lequel a joué. Mets en premier celui qui ne demande aucune donnée pour s'appliquer. Pour chacun : le constat et sa preuve, le changement concret (fichier ou étape), le chiffre, le seuil, et la date de mesure (le bilan J+7 de quelle vidéo).
6. **Liste les écartés**, une ligne chacun avec la raison : preuve introuvable, déjà couvert par une action, pas mesurable, trop coûteux pour le gain, contraire à `preferences.md`.

Ne propose pas de nouvel outil ou de nouveau skill, sauf si une étape a réellement bloqué une vidéo.

## 4. Décision et écriture

1. Présente le verdict en suivant `templates/rapport.md`, puis demande en une question AskUserQuestion (`multiSelect: true`) quels changements adopter.
2. **Mode complet** : écris le rapport dans `config/youtube/conseils/<AAAA-MM-JJ>.md` (crée le dossier s'il manque), avec les choix de l'utilisateur.
3. Les changements adoptés vont dans « Actions pour la prochaine vidéo » de `apprentissages.md` : `- [ ] (conseil, <date>) <constat> ; <changement> ; Mesure : <chiffre, seuil, date>.` Ferme les actions jugées : `- [x] … [fait <date>, <id>] <résultat>`. Cette section reste au-dessus du tableau, qui doit finir le fichier.
4. Un changement qui touche `preferences.md`, un skill ou le kit : seulement avec l'accord de l'utilisateur.
5. **Mode ciblé** : pas de rapport dans `conseils/`. Applique les changements adoptés au livrable, puis ajoute une ligne dans « Écarts par rapport au plan » de `videos/<id>/suivi.md` : `conseil ciblé <date> : <livrable>, <n> changements appliqués`. Le livrable est ensuite gelé.
6. Coche l'étape 11b de `videos/<id>/suivi.md` (mode complet, vidéo dont le bilan J+7 a déclenché le conseil), puis envoie : `envoi.bat "conseil <date>"` à la racine du dépôt (ou `git add -A && git commit -m "conseil <date>" && git push`).

## Règles

- Le conseil ne publie rien et ne modifie aucun fichier pendant le travail des agents. Seul le juge écrit, après l'accord de l'utilisateur.
- Un constat sans fichier cité ne compte pas.
- Pas plus de 3 changements par conseil, même si les agents en proposent 12.
- Aucun emoji, comme partout sur la chaîne.
