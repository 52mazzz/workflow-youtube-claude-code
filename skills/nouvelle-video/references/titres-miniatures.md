# Phase 5 : titres et miniatures

Partie du skill nouvelle-video, lue au début de la phase 5.

## Phase 5 : Titres et miniatures (skills youtube-titles-ab, youtube-thumbnail-prompts, nano-banana-pro-prompting)

Charge ces trois skills : ils contiennent la méthode à partir des références. Les préférences de forme sont dans `preferences.md`, les leviers qui ont déjà gagné sur la chaîne dans `apprentissages.md`.

1. **Références d'abord** (étape 1 de youtube-titles-ab) : relis `refs-sujet.json` (la sélection par pertinence de la phase 3), `refs.json` pour le reste de la niche, et la section « Vidéos de référence » de `idees.md`. La veille de la phase 1 portait sur toute la niche ; si elle ne contient pas au moins 5 outliers (2× ou plus) sur le sujet ou le format retenu en phase 2, fais la collecte ciblée décrite dans youtube-titles-ab et complète `refs.json`. Montre le tableau des références et les structures qui reviennent avant de proposer un titre.
2. **Miniatures de référence** : télécharge et analyse celles des meilleurs outliers, fais choisir à l'utilisateur celles qui l'attirent, puis propose corrections et adaptations à la vidéo (youtube-thumbnail-prompts § Références visuelles).
3. **Titres** : chaque titre s'appuie sur une structure de référence (citée), adaptée aux préférences de `preferences.md`. Pour départager deux formulations, regarde ce que les gens tapent (`suggest.py`, skill youtube-titles-ab). Au plus une variante peut être un pari original, présenté comme tel. Pour la paire principale, tiens compte des leviers gagnants de `apprentissages.md`.
4. **Surfaces** : chaque paire vise une surface, notée en 3e colonne de `titres.txt` (`titre | TEXTE MINIATURE | accueil` ou `| recherche`) : **accueil** (fil d'accueil et suggestions : l'émotion ou l'action en tête, la curiosité) ou **recherche** (le mot-clé principal, celui que les gens tapent d'après `suggest.py`, dans les 40 premiers caractères). Au moins une paire de chaque ; la paire principale vise l'accueil, la chaîne vit surtout des suggestions.
5. **Vérification par script** : `check_titles.py titres.txt --refs refs-sujet.json --own ma-chaine.json --mot-cle "<mot-clé principal>"` (skill youtube-titles-ab). Code 1 = au moins une erreur : corrige et relance avant de livrer ; les conseils (dont le sujet hors de l'aperçu mobile d'une paire « accueil ») se lisent et se justifient. **N'écris dans `titres-miniatures.md` que ce que la sortie dit** (par exemple ce que montrent les 40 premiers caractères) : recopie la coupe mobile, ne la décris pas de mémoire.

Livrable : le tableau des références, puis 3 paires titre + miniature sur 3 leviers différents (par exemple humour décalé, affrontement, curiosité), avec nombre de caractères exact (sortie de check_titles.py), la référence de chaque paire, ce que montre la miniature, la paire principale, puis pour la paire principale :
- le prompt Nano Banana complet dans un bloc de code (logo exact avec le code hex, coin bas droit propre),
- une variante « avec captures réelles en référence »,
- 2 ou 3 conseils d'itération.

Écris `titres-miniatures.md`, puis **confirme l'id** (le dossier a déjà été renommé en `videos/<id>/` en phase 2 ; sinon `repo.py id <2 ou 3 mots-clés>`), remplis l'en-tête de `suivi.md` (titre, id, « Publication visée » : propose une date d'après la cadence et les autres vidéos de `repo.py list`) et coche les étapes 1 à 3.

La description n'est plus écrite ici : elle vient après le montage (skill description-video), quand les chapitres et les résultats sont connus.

