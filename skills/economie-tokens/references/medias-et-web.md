# Navigateur, images, vidéo et crédits de génération

## Navigateur (pane intégré ou Chrome)

| Besoin | Économe | Coûteux |
|---|---|---|
| Lire le contenu | `get_page_text` (avec `max_chars`) | capture d'écran |
| Trouver un bouton/champ | `find "texte"` → `ref` | `read_page` complet |
| Structure d'une zone | `read_page` avec `ref_id` + `depth` faible, `filter: "interactive"` | arbre complet de la page |
| Vérifier un rendu visuel | capture `scale: 0.5`, ou `zoom` sur la zone | capture pleine répétée |
| Plusieurs actions prévisibles | `browser_batch` (un aller-retour) | un appel par clic |
| Valeur précise du DOM | `javascript_tool` qui renvoie juste la valeur | lire la page pour la chercher |
| Erreurs console / réseau | `onlyErrors`, `pattern`, `urlPattern`, `limit` | liste complète |

Outils Chrome différés : les charger tous d'un coup en un seul `ToolSearch`.

## Images

- Lire une image seulement si son contenu visuel est la question.
- Grosse image à analyser : la réduire d'abord (`ffmpeg -i in.png -vf scale=800:-1 out.png`, Pillow) ou la recadrer
  sur la zone utile.
- Comparer deux versions : un script de diff (pixels, histogramme) qui rend un chiffre, puis regarder seulement si le
  chiffre est suspect.
- Pixel art / textures : inspecter via un script (palette, nombre de couleurs, dimensions) plutôt qu'en ouvrant chaque PNG.

## Vidéo et audio

- Ne jamais lire des frames une par une : `ffprobe -v error -show_entries format=duration -of csv=p=0`,
  `ffmpeg ... -vf "select=..."` pour **quelques** vignettes, ou une planche contact (`tile=4x3`) en une image.
- Transcription : travailler sur le texte (horodaté), pas sur l'audio ni les frames.
- Rendus : rendre un extrait court (quelques secondes, basse résolution) pour valider, puis le rendu final une seule fois.
- Logs ffmpeg : `-v error` / `-loglevel error -stats`, ou `2>&1 | tail -5`.

## Crédits de génération (images, vidéo, TTS, musique)

1. **Valider à bas coût d'abord** : prompt relu et accepté, version brouillon / basse résolution / courte, puis la version finale.
2. **Une variante à la fois** quand le prompt est encore incertain ; plusieurs variantes seulement quand le prompt est validé et qu'on veut choisir.
3. **Réutiliser** : assets déjà générés, bibliothèques locales, catalogues gratuits avant toute génération.
4. **Éditer plutôt que régénérer** quand le modèle permet l'édition à partir d'une image de référence.
5. Pré-traiter les entrées (couper, réduire, retirer l'audio inutile) : moins de secondes = moins de crédits.
6. Annoncer le coût estimé avant de lancer une génération chère.

## Web

- `WebSearch` en mode `standard` par défaut ; `extended` seulement si le résultat est maigre, daté ou introuvable.
- Prévoir les recherches d'un coup et les lancer dans le même tour.
- `WebFetch` avec une consigne d'extraction précise (« donne seulement la table des prix ») plutôt que la page entière.
- Documentation : viser la page exacte (référence API, changelog) plutôt que l'accueil.
