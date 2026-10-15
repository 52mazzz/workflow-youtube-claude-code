# Licences des ressources externes

Version publique de ce fichier : elle ne liste que les ressources présentes dans ce dépôt. Le dépôt de travail de la
chaîne garde en plus des musiques, des sons et des images qu'on ne peut pas republier ici (voir le README, « Ce qui
n'est pas publié »).

## Musiques

Aucune musique n'est publiée. `08_HYPERFRAMES/scripts/musique.py` range les morceaux dans `musiques/perso/` (fiches dans
`musiques/catalogue.json`) et ajoute ci-dessous une ligne par morceau gardé après écoute.

| Fichier | Titre | Auteur (source) | Licence | Lien | Gardée le |
|---|---|---|---|---|---|

## Sound effects

| Fichier | Nom | Auteur | Source | Licence | Lien original | Attribution requise |
|---|---|---|---|---|---|---|
| `sfx/kenney_interface-sounds/` → `08_HYPERFRAMES/assets/sfx/` tick, clic, clic_2, croix, valide | Interface Sounds 1.0 | Kenney | kenney.nl | CC0 1.0 (domaine public), texte dans `License.txt` | https://kenney.nl/assets/interface-sounds | Non (crédit apprécié) |
| `sfx/synth/` → `08_HYPERFRAMES/assets/sfx/` whoosh, whoosh_court, impact, sub_drop, riser | Sons synthétisés pour ce projet | Créés avec FFmpeg (`08_HYPERFRAMES/scripts/make_sfx.py`) | — | Création originale | — | Non |

Non publiés : `pop` et `pop_sortie` (tirés de « Bubble Pop 06 » d'Universfield sur Pixabay), `declic` et `declic_2`
(déclics d'appareil photo Pixabay) : la licence Pixabay interdit de redistribuer ces fichiers tels quels ;
`flash_camera` (source non précisée) et `flash_capcut` (bibliothèque de sons de CapCut). `make_sfx.py` refait les sons
synthétisés et ceux de Kenney ; pour `pop` et `pop_sortie`, il attend le fichier Pixabay dans `sfx/pixabay/`.

## Polices et assets graphiques

| Élément | Nom | Auteur | Source | Licence | Lien original | Attribution requise |
|---|---|---|---|---|---|---|
| Police titres / textes | Inter Tight | Rasmus Andersson | Google Fonts | SIL Open Font License 1.1 | https://fonts.google.com/specimen/Inter+Tight | Non |
| Police labels / code | JetBrains Mono | JetBrains | Google Fonts | SIL Open Font License 1.1 | https://fonts.google.com/specimen/JetBrains+Mono | Non |
| Police « OPUS 5.5 » (fenêtre Claude) | DM Serif Display | Colophon Foundry | Google Fonts | SIL Open Font License 1.1 | https://fonts.google.com/specimen/DM+Serif+Display | Non |
| Police sous-titres | Montserrat | Julieta Ulanovsky | Google Fonts | SIL Open Font License 1.1 | https://fonts.google.com/specimen/Montserrat | Non |
| Mascotte Tsar (avatar et 6 expressions, `08_HYPERFRAMES/assets/tsar/`) | Tsar | Chaîne TSAR | Fichiers de la chaîne | Propriété de la chaîne, tous droits réservés : hors de la licence du code | — | — |
| Pastilles `08_HYPERFRAMES/assets/logos/claude.svg` et `chatgpt.svg` | Pastilles neutres | Copie publique | — | Comme le code du dépôt | — | Non |

Les textes des licences des polices sont dans `08_HYPERFRAMES/assets/fonts/OFL-*.txt`. Les vrais logos des IA, que le
kit affiche dans les duels, ne sont pas publiés (marques d'Anthropic et d'OpenAI) : deux pastilles neutres les
remplacent. Pour les retrouver, déposer les SVG dans `08_HYPERFRAMES/assets/logos/` sous le nom utilisé par les plans.
