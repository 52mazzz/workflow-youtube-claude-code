# Quel modèle et quel effort pour quelle tâche

À regarder au démarrage d'une session. On change de modèle avec `/model <nom>` et d'effort avec `/effort <niveau>` (`low`, `medium`, `high`, `xhigh`, `max`), même en cours de conversation. Règle simple : **Sonnet en `medium` par défaut**, Opus en `high` quand la qualité du texte se verra à l'écran, Haiku en `low` pour le mécanique.

| Tâche | Modèle | Effort | Commandes |
|---|---|---|---|
| Script : accroches et script (nouvelle-video, phases 3-4) | Opus | high | `/model claude-opus-5-5` puis `/effort high` |
| Titres et miniatures (phase 5) | Opus | high | `/model claude-opus-5-5` puis `/effort high` |
| Conseil (conseil-workflow), lecture d'un bilan (bilan-video, section 4) | Opus | high | `/model claude-opus-5-5` puis `/effort high` |
| Changer l'architecture ou la manière de faire (méthode de montage, workflow, skills, scripts sur plusieurs fichiers) | Opus | high (xhigh pour un gros chantier) | `/model claude-opus-5-5` puis `/effort high` ; démarrer en mode plan (Maj+Tab) pour valider le plan avant toute modification |
| Bug difficile dans un script du dépôt | Sonnet | high | `/model claude-sonnet-5-5` puis `/effort high` |
| Veille et idées (phase 1), grilling (phase 2) | Sonnet | medium | `/model claude-sonnet-5-5` puis `/effort medium` |
| Dérush, montage, shorts | Sonnet | medium | `/model claude-sonnet-5-5` puis `/effort medium` |
| Description, publication, collecte d'un bilan, petite modif de code | Sonnet | low | `/model claude-sonnet-5-5` puis `/effort low` |
| État du dépôt, rangement, envoi, petites questions | Haiku | low | `/model claude-haiku-5-5` puis `/effort low` |

## Automatique (depuis le 2026-10-07)

Les skills règlent eux-mêmes modèle et effort (champs `model` et `effort` de leur en-tête), dès qu'ils se lancent :

| Skill | Modèle | Effort |
|---|---|---|
| yt-script, youtube-titles-ab, youtube-thumbnail-prompts, conseil-workflow | Opus | high |
| nouvelle-video, derush-capcut, montage-capcut, short, bilan-video | Sonnet | medium |
| description-video, publication-video | Sonnet | low |

Limite : le modèle choisi par un skill ne dure que jusqu'à la fin de la réponse en cours ; à ton message suivant, la session reprend son propre modèle. Pour une étape longue sur plusieurs messages (retravailler le script), mets le modèle du tableau ci-dessus à la main. Les autres skills et les petites questions gardent le modèle de la session.

## À la main

L'effort, c'est le temps de réflexion avant de répondre : plus il est haut, mieux c'est sur les tâches difficiles, mais plus ça consomme et plus c'est lent. Opus, Sonnet et Haiku 5.5 sont en `medium` si on ne choisit rien.

Astuces :
- **Enregistrer ou non** : taper `/effort high` (ou valider le curseur avec Entrée) l'enregistre comme défaut de ce modèle pour les sessions suivantes. Dans le curseur `/effort` (sans niveau), la touche `s` l'applique à cette session seulement. `/effort auto` revient au défaut du modèle.
- `xhigh` et `max` : seulement si `high` a raté (un script qui ne tient pas, un bug introuvable). `max` ne dure que la session.
- Pour une seule question difficile, écrire `ultrathink` dans le message : réflexion plus poussée pour ce tour seulement, sans changer le réglage.
- Run « nouvelle vidéo » complet : Sonnet `medium` pour la veille et le grilling, Opus `high` pour le script et les titres, puis retour en Sonnet `medium`.
- Les agents nommés (`config/agents/`) ont leur propre modèle (Sonnet), quel que soit celui de la conversation.
- `/clear` entre deux tâches sans rapport : c'est souvent plus d'économie que le choix du modèle.
