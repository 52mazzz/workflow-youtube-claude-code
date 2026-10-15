# Applications qui appellent l'API Claude

Les tarifs, seuils et noms de paramètres évoluent : pour les chiffres exacts et la syntaxe à jour, charger le skill
`claude-api` avant d'écrire le code. Ici : quoi optimiser et dans quel ordre.

## Leviers, du plus rentable au moins

| Levier | Quand | Gain typique |
|---|---|---|
| **Prompt caching** (`cache_control` sur le préfixe stable) | même long préfixe (système, docs, outils, exemples) réutilisé | lectures du cache facturées une fraction du prix normal |
| **Batch API** | traitements non urgents (classement, extraction, évaluations) | remise importante, résultats en différé |
| **Bon modèle** | Haiku pour tri/extraction/classification, Sonnet par défaut, Opus pour le raisonnement difficile | souvent ×3 à ×10 sur le coût |
| **`max_tokens` serré + sortie structurée** | toute réponse au format connu | évite les réponses longues et les relances pour format invalide |
| **Contexte minimal** | RAG : n'envoyer que les passages pertinents ; historique résumé ou tronqué | proportionnel |
| **Effort / réflexion** | n'activer un budget de réflexion élevé que là où il améliore le résultat | tokens de sortie |
| **Résultats d'outils courts** | les outils renvoient l'essentiel, pas des objets bruts | entrée à chaque tour suivant |

## Prompt caching : règles de structure

- Ordre : contenu **stable** en premier (outils → système → documents → exemples), contenu **variable** à la fin.
- Ne rien mettre de variable (date, ID de requête, nom d'utilisateur) dans le préfixe caché : ça casse le cache.
- Garder la liste d'outils identique et dans le même ordre d'un appel à l'autre.
- Vérifier dans la réponse les compteurs d'usage (tokens écrits / lus dans le cache) pour confirmer que le cache sert.

## Agents et boucles d'outils

- Peu d'outils, descriptions courtes ; outils rares chargés à la demande si l'API le permet.
- Tronquer ou résumer les vieux résultats d'outils dans l'historique ; garder les décisions.
- Arrêter la boucle tôt : nombre max d'itérations, condition de fin claire.
- Sous-tâches mécaniques déléguées à un modèle plus léger.

## Mesurer avant d'optimiser

- Compter les tokens d'une requête type avec l'endpoint de comptage avant de la mettre en production.
- Journaliser l'usage (entrée, sortie, cache) par appel ; optimiser le poste le plus gros, pas le plus visible.

## Anti-patterns

- Renvoyer tout l'historique brut à chaque appel d'un chatbot sans limite.
- Demander du JSON en texte libre puis relancer quand il est invalide (utiliser les sorties structurées).
- Few-shot de 20 exemples quand 3 suffisent.
- Opus en effort max pour classer des tickets.
