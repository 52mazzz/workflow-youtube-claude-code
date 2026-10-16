---
name: economie-tokens
description: Économiser tokens et crédits dans tous les cas — lecture, recherche, shell, éditions, sous-agents, web, navigateur, images, vidéo, MCP, longues sessions, réponses, modèle/effort, configuration (CLAUDE.md, mémoire, skills) et apps API Claude (cache, batch). Inclut un audit chiffré du contexte. À utiliser quand l'utilisateur dit « économise les tokens », « moins de tokens », « ça consomme trop », « mode éco », « audit tokens », « contexte plein », « optimise mon setup », ou avant une tâche lourde (gros dépôt, gros logs, rendu, génération d'images).
---

# Économie de tokens — règles universelles

Réponds en **français**, court. Ce fichier est le cœur : il suffit dans 90 % des cas. Ouvre une référence
**seulement** quand la situation l'exige (table en bas) — les lire toutes d'avance gaspillerait ce qu'elles font gagner.

## Le principe

Un token coûte trois fois : quand il **entre** dans le contexte (lecture, sortie d'outil, image), quand il y **reste**
(relu à chaque tour suivant tant que la session dure) et quand il **sort** (texte écrit, le plus cher à l'unité).
Donc, par ordre d'impact :

1. **Ne pas faire entrer** ce qui ne servira pas (le gros gain : sorties d'outils, fichiers entiers, captures d'écran).
2. **Ne pas faire durer** : ce qui est entré pèse sur tous les tours suivants → session courte et ciblée, sous-agent pour les fouilles.
3. **Ne pas sur-écrire** : réponses, code et commentaires à la taille juste.
4. **Ne pas refaire** : un aller-retour raté (mauvaise commande, mauvais fichier, question évitable) coûte un tour complet.

Ne jamais économiser au prix de la justesse : un bug ou une mauvaise réponse coûte plus cher que les tokens épargnés.
Si l'économie et la qualité s'opposent, choisis la qualité et dis-le.

## Les 20 réflexes (valables partout)

**Entrées**
1. Chercher avant de lire : `Grep`/`Glob` (ou `grep -n`, `rg -l`) pour trouver la ligne, puis `Read` avec `offset`/`limit` sur la zone utile. Jamais un fichier de 2 000 lignes pour 20 lignes.
2. `Grep` en `files_with_matches` ou `count` d'abord ; `content` seulement quand on sait où regarder, avec `head_limit`.
3. Toute commande bavarde est filtrée à la source : `| tail -30`, `| head`, `--quiet`, `-q`, `--silent`, `2>&1 | grep -E "error|fail"`, `--porcelain`, `--oneline`, `-n 20`. Tests : n'afficher que les échecs.
4. Ne jamais relire un fichier qu'on vient d'éditer ou de lire (l'outil le garde en mémoire) ; ne pas relire « pour vérifier ».
5. JSON, CSV, logs géants : extraire avec `jq`, `python -c`, `awk`, `Select-Object -First` — jamais les afficher entiers.
6. Images et captures : uniquement quand le visuel est la question. Pour lire une page, le texte (`get_page_text`, `read_page`) coûte une fraction d'une capture ; `zoom` sur une zone ou `scale` 0.5 plutôt qu'une capture pleine.
7. Web : une recherche bien formulée, puis une page ciblée ; pas dix pages survolées.

**Durée de vie du contexte**
8. Fouille large (beaucoup de fichiers, réponse = une conclusion) → sous-agent `Explore` : seul son résumé entre dans le contexte. Une seule cible connue → recherche directe, pas de sous-agent.
9. Lancer en parallèle (un seul message) les appels indépendants : moins de tours, donc moins de relectures du contexte.
10. Changement de sujet → conseiller `/clear` à l'utilisateur ; longue tâche qui continue → `/compact <ce qu'il faut garder>`.
11. Charger les outils différés en **un seul** `ToolSearch` groupé (`select:A,B,C`), pas un par un.
12. Skills : ne charger que le skill qui couvre la tâche ; dans un skill, n'ouvrir que la référence nécessaire.

**Sorties**
13. Réponse = le résultat, pas le récit. Pas de reformulation de la question, pas de résumé de ce qui vient d'être fait si l'utilisateur l'a vu, pas de « n'hésitez pas ».
14. Éditer avec `Edit` (le morceau qui change), pas réécrire tout le fichier avec `Write`.
15. Code : pas de commentaires évidents, pas de variantes non demandées, pas de fichiers README/docs non demandés.
16. Une recommandation, pas un catalogue d'options. Un tableau ou une liste plutôt que des paragraphes.

**Pas d'allers-retours inutiles**
17. Agir quand on a assez d'informations ; ne demander que ce qui change vraiment la suite, et toutes les questions d'un coup.
18. Connaître le shell avant de taper (PowerShell 5.1 ≠ bash) : une commande en échec = un tour perdu.
19. Ne pas re-dériver ce qui est déjà établi dans la conversation ni re-vérifier ce qui a déjà été vérifié.
20. Effort et modèle à la mesure de la tâche (voir plus bas) : un renommage n'a pas besoin du modèle le plus fort en effort max.

## Choisir le modèle et l'effort

| Tâche | Modèle | Effort |
|---|---|---|
| Renommer, formater, déplacer, question factuelle, petite édition | le plus léger disponible (Haiku / Sonnet) | low |
| Feature normale, bug localisé, script, rédaction | Sonnet | medium |
| Architecture, bug introuvable, revue critique, décision coûteuse à rater | Opus | high |

Pour un sous-agent, passer `model: "haiku"` ou `"sonnet"` quand la tâche est mécanique (fouille, tri, extraction).
Ne pas changer le modèle de la session soi-même : le proposer à l'utilisateur.

## Mode audit (« audit tokens », « optimise mon setup », « pourquoi mon contexte est plein »)

Lance le script, il chiffre ce qui est chargé à **chaque** session sans qu'on le demande :

```bash
python ~/.claude/skills/economie-tokens/scripts/audit_contexte.py
```

(Ajouter un chemin de projet en argument pour inclure ses `CLAUDE.md` et `.claude/`.) Puis lis
[references/configuration.md](references/configuration.md) et rends : un tableau des postes les plus lourds, puis
3 à 5 actions classées par tokens gagnés. Ne modifie aucun fichier de configuration sans accord.

## Quelle référence ouvrir (une seule, quand le cas se présente)

| Situation | Fichier |
|---|---|
| Gros dépôt, gros fichiers, logs, tests, git, builds, recherche de code | [references/code-et-outils.md](references/code-et-outils.md) |
| Session longue, contexte qui sature, sous-agents, workflows, mémoire, CLAUDE.md, skills, MCP, audit | [references/configuration.md](references/configuration.md) |
| Navigateur, captures, images, vidéo, rendu, génération d'images ou de vidéos (crédits) | [references/medias-et-web.md](references/medias-et-web.md) |
| Écrire ou optimiser une app / un script qui appelle l'API Claude (cache, batch, coûts) | [references/api-claude.md](references/api-claude.md) |
| Rédaction : réponses, documents, scripts, prompts pour d'autres modèles | [references/redaction.md](references/redaction.md) |

## Mode éco (actif par défaut dans le dépôt de la chaîne, 2026-10-16)

Actif dans toute session, sauf si l'utilisateur dit « mode normal » ou demande une réponse détaillée.
Applique les 20 réflexes avec rigueur jusqu'à la fin de la session, réponds en 1 à 5 lignes sauf demande contraire,
annonce les étapes coûteuses avant de les lancer (« ça va lire ~40 fichiers via un sous-agent, OK ? ») et propose
`/compact` ou `/clear` aux changements de sujet.
