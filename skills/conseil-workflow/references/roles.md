# Rôles des agents du conseil

Les trois rôles vivent dans les agents nommés du dépôt, dans `config/agents/` (relié à `~/.claude/agents/` par `setup.py`), qui sont la seule source à modifier :

- `config/agents/spectateur.md` : sujet, titre, miniature, accroche, rythme, Shorts, page de chaîne
- `config/agents/producteur.md` : temps et crédits perdus, cadence
- `config/agents/analyste.md` : chiffres, goulot, boucle de mesure

Chaque fichier contient le texte commun (règles de preuve, 450 mots au maximum), le mode complet et le mode ciblé. Modèle : Sonnet. Outils : Read, Grep, Glob (lecture seule, pas d'agents en cascade).
