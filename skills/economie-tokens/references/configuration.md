# Session, contexte et configuration

## Ce qui est chargé à chaque session (coût fixe, payé à chaque tour)

| Poste | Pourquoi ça coûte | Remède |
|---|---|---|
| `CLAUDE.md` (global `~/.claude/`, projet, sous-dossiers) | lu en entier à chaque session | garder les règles, sortir les détails dans des fichiers lus à la demande ; viser < 200 lignes |
| `MEMORY.md` | index injecté à chaque session | une ligne par mémoire ; fusionner les doublons (skill `consolidate-memory`) ; supprimer les faits périmés |
| Descriptions des skills | **toutes** les descriptions sont listées à chaque session | descriptions courtes et précises ; désinstaller/archiver les skills jamais utilisés ; pas de doublons (ex. deux copies du même skill) |
| Corps d'un skill (`SKILL.md`) | chargé quand le skill se déclenche | cœur court, détails dans `references/` lus à la demande |
| Serveurs MCP | leurs outils (ou noms d'outils différés) apparaissent dans le contexte | désactiver les serveurs inutiles pour ce projet |
| Instructions de style de sortie, hooks qui injectent du texte | ajoutés à chaque tour | vérifier qu'ils restent courts |

L'audit (`scripts/audit_contexte.py`) chiffre ces postes. Estimation : ~4 caractères = 1 token en anglais, ~3,5 en
français ; c'est un ordre de grandeur, pas une mesure exacte. `/context` (dans un terminal `claude`) donne la
répartition réelle.

## Pendant une session

- **Une session = un sujet.** Nouveau sujet → `/clear` (la mémoire et CLAUDE.md restent).
- **Session longue qui continue** → `/compact garde : décisions, fichiers modifiés, prochaine étape`. Compacter
  avant la saturation, à un point de transition propre (après un commit, une étape validée).
- **Passer le relais** : avant un `/clear` sur une tâche inachevée, écrire 10 lignes d'état dans un fichier
  (ou dans `suivi.md` du projet) ; la session suivante lit ces 10 lignes au lieu de tout redécouvrir.
- Ne pas coller de gros logs ou fichiers dans le chat : donner le chemin, l'agent lira la partie utile.

## Sous-agents et workflows

| Situation | Choix |
|---|---|
| Fouille large, réponse = conclusion | sous-agent `Explore` (lecture seule) |
| Plusieurs fouilles indépendantes | plusieurs sous-agents dans un seul message |
| Tâche mécanique (tri, extraction, conversion) | sous-agent avec `model: "haiku"` ou `"sonnet"` |
| Cible connue (un fichier, un symbole) | recherche directe, pas de sous-agent (le lancer coûte son propre contexte) |
| Workflow multi-agents | seulement sur demande explicite ; garder peu d'agents, schéma de sortie strict et court |

Rédiger le prompt d'un sous-agent pour qu'il rende **peu** : « réponds en ≤ 15 lignes : fichiers:lignes + conclusion ».
Ne pas refaire soi-même la recherche qu'on lui a confiée.

## Mémoire

- Ne mémoriser que le non-déductible (préférences, décisions, contraintes) : pas ce que le code ou git disent déjà.
- Un fait par fichier, mise à jour plutôt que doublon, suppression des faits faux.

## Écrire des skills économes

- Description : déclencheurs précis, sans paragraphe marketing (elle est payée à chaque session).
- `SKILL.md` court (~100–200 lignes) avec une table « quelle référence ouvrir » ; le détail dans `references/`.
- Scripts dans `scripts/` qui rendent un résumé, plutôt que des procédures que l'agent exécute pas à pas.
- `model:` / `effort:` dans le frontmatter quand le skill n'a pas besoin du modèle le plus fort.

## Permissions et allers-retours

Chaque demande de permission refusée/acceptée ajoute un tour. Le skill `fewer-permission-prompts` ajoute une liste
d'autorisations pour les commandes en lecture seule les plus fréquentes.

## Rendu de l'audit

```
| Poste | Fichiers | ~Tokens | Action |
|---|---|---|---|
| Descriptions de skills | 34 | 9 800 | archiver hyperframes-* si inutilisés ici (−4 100) |
...
Gain estimé : ~X tokens par session, ~Y par tour.
```
