# La chaîne de production d'une vidéo

Référence du skill nouvelle-video, lue quand on reprend une vidéo en cours.

Une vidéo = un dossier `videos/<id>/` et un `suivi.md`. Chaque étape **lit tout ce que les étapes précédentes ont écrit** et le respecte ; un écart au plan est permis s'il est noté dans « Écarts par rapport au plan » de `suivi.md`, jamais en silence. Quand l'utilisateur reprend une vidéo (« on en est où sur <titre> ? », « reprends la vidéo <titre> »), lis `suivi.md` et lance l'étape suivante.

| # | Étape | Skill | Lit | Écrit |
|---|---|---|---|---|
| 1-3 | Idée, script, titres et miniatures | nouvelle-video | références, `apprentissages.md`, `preferences.md`, `voice.md` | `idees.md`, `script.md`, `titres-miniatures.md`, `suivi.md` |
| 3b | Préparation du tournage | nouvelle-video | `script.md`, `titres-miniatures.md` | `resultats.md` (checklist « Avant », prompt exact) |
| 4 | Tournage et rangement des rushs sur le PC fixe | (l'utilisateur) | `fiche-tournage.md` (générée par `fiche.py`), `resultats.md` | `resultats.md` (rempli le jour même) |
| 5 | Dérushage (PC fixe, accessible à distance) | derush-capcut | `script.md` : les phrases attendues, dans l'ordre | projet CapCut `<id>` |
| 6 | Montage (PC fixe, accessible à distance) | montage-capcut | `script.md` (beats, `[ON SCREEN]`, accroche, demande finale), `resultats.md`, `titres-miniatures.md` (promesse du titre) | `<id> - final`, export, écarts dans `suivi.md` |
| 7 | Miniature finale | youtube-thumbnail-prompts | `titres-miniatures.md`, captures réelles (`resultats.md`), mascotte | 3 paires pour Test & Compare, images dans `videos/<id>/miniatures/` |
| 8 | Description | description-video | tout ce qui précède + le montage final | `description.md` |
| 9 | Publication | publication-video (l'utilisateur met en ligne) | `description.md`, `titres-miniatures.md`, `miniatures/` | « Statut », « Publiée le » et lien dans `suivi.md` |
| 10 | Shorts | montage-capcut | `script.md`, `resultats.md`, `preferences.md` (section Shorts) | `shorts.md` |
| 11 | Bilan J+3/J+7 | bilan-video | `suivi.md`, `titres-miniatures.md`, `refs-sujet.json` | `apprentissages.md` (ligne + action pour la prochaine vidéo) |
| — | Chaîne (mensuel, avec la veille complète ; sondage à chaque publication) | chaine-youtube | `chaine.md`, `ma-chaine.json`, bilans | `chaine.md`, `audits/<date>.md` |
| 12 | Bilan J+28 | bilan-video | idem + Test & Compare terminé | ligne de `apprentissages.md` mise à jour |

Règles de raccord :
- **Le montage respecte le script** : même ordre des beats, l'accroche du script dans les 15 premières secondes, les `[ON SCREEN]` comme plan des fenêtres de motion design, une seule demande finale (celle du script). Le dérushage cherche les prises des phrases du script ; une phrase du script sans prise, ou une improvisation qui vaut d'être gardée, est signalée.
- **La promesse du titre** principal doit être tenue dans les 30 premières secondes du montage ; si le tournage ne la tient pas (autre vainqueur, résultat raté), le signaler avant l'export pour changer de titre.
- **Shorts** : fabriqués par montage-capcut (style validé dans ses préférences) ; titres de 20 à 40 caractères selon `preferences.md`, vérifiés avec `check_titles.py --shorts` ; publiés après la vidéo longue (le jour même puis à 2 ou 3 jours d'écart), jamais avant : un Short qui donne le vainqueur ne doit pas tuer la curiosité de la vidéo. Lien « vidéo associée » vers la vidéo longue.
- **Envoi** (`envoi.bat`, ou commit et push) à la fin de chaque étape, depuis la racine du dépôt, pour reprendre sur l'autre PC. Chaque skill de la chaîne commence par `repo.py etat` : rien de non poussé ne doit traîner d'un PC à l'autre.
- **Reprendre une vidéo** : `repo.py video "<titre ou id>"` retrouve le dossier existant (par l'id ou un titre) ; plusieurs correspondances (code 2) : demander laquelle ; aucune (code 1) : ne rien créer.
- **Rappels de bilan** : `repo.py etat` annonce les bilans dus (J+3 et J+28 après la sortie effective : « Publiée le », ou « Programmée pour » une fois passée). La tâche planifiée « Bilans dus » du portable fait la même vérification chaque jour pour toutes les vidéos : pas de rappel à créer par vidéo.

## Quand Claude attend ta décision (points d'arrêt, 2026-10-01)

C'est la seule liste qui fait foi : entre deux points d'arrêt, Claude enchaîne sans demander. Les « On valide, ou on change quelque chose ? » des skills se posent **à ces moments-là seulement**, pas après chaque fichier.

| Étape | Claude s'arrête pour | Sans réponse |
|---|---|---|
| 0 Départ | vidéo longue ou Short, et le domaine (avant la veille) | rien n'est lancé |
| 1-2 Idée | le choix de l'idée et du format (phase 2), puis la validation du récapitulatif | rien n'est écrit |
| 3-5 Accroches, script, titres | **une seule** validation, à la fin du run (accroches, script, titres et miniatures ensemble) | les fichiers restent en brouillon, non cochés |
| 3b Préparation | les décisions matérielles qui te reviennent (outil, version, modèle) | la ligne reste à cocher dans `resultats.md` |
| 5 Dérushage | les questions de départ (projet, priorité), puis un rush manquant ou tronqué | rien n'est dérushé sans le rush |
| 6 Montage | les questions de départ groupées ; supprimer un projet CapCut | le MP4 final est rendu (`rendu.py`) et contrôlé |
| 7 Miniature finale | le choix des 3 paires | — |
| 8-9 Description, publication | une validation du texte ; c'est toi qui publies | rien n'est publié |
| 10 Shorts | le choix des idées de Shorts, puis la validation de chaque Short | — |
| 11-12 Bilan | la validation de la leçon et de l'action pour la prochaine vidéo | la ligne reste « à confirmer » |

Hors de ces points, une question n'est posée que si une règle est réellement ambiguë (deux règles qui se contredisent sans que la portée ou la date tranche, voir le cahier des charges du montage).
