---
name: chaine-youtube
description: "Tout ce qui se règle au niveau de la chaîne @letsar555 (tsar rouge555), pas d'une vidéo : playlists qui enchaînent les vidéos, page « À propos » et mots-clés de chaîne, bande-annonce, vidéo à la une, sections, écran de fin qui mène à la vidéo suivante, sondage Communauté, et le mini-audit mensuel (rythme, dérive de thème, grille des miniatures). À utiliser quand l'utilisateur dit « chaîne », « playlist », « bande-annonce », « à propos », « page de la chaîne », « sondage », « communauté », « audit de la chaîne », « audit mensuel », ou quand nouvelle-video fait une veille complète, ou quand publication-video arrive au sondage."
---

# La chaîne (pas une vidéo)

Réponds en français. Questions avec AskUserQuestion (cases à cocher), option recommandée en premier. **Rien n'est publié par Claude** : tu écris les textes et le plan, l'utilisateur les colle dans Studio. Méthode adaptée de youtube-seo-skills (deeployCO, MIT : autorité thématique, chaînes de session, bande-annonce), réécrite pour une chaîne francophone, sans visage, qui démarre (une chaîne de moins de 10 vidéos gagne plus à soigner sa base qu'à optimiser chaque mot).

**L'état de la chaîne vit dans `~/.claude/youtube/chaine.md`** (dans le dépôt, `config/youtube/`) : playlists et leur ordre, texte « À propos », mots-clés, bande-annonce, vidéo à la une, sections, plan d'écrans de fin, journal des sondages. Lis-le au début ; mets-le à jour à la fin de chaque intervention ; puis envoie (`envoi.bat`).

Lis aussi `~/.claude/youtube/preferences.md` (ton, sans emoji, sans visage, vouvoiement), `voice.md`, `apprentissages.md` et `repo.py list` (les vidéos en cours et publiées).

## 1. Mini-audit mensuel (avec chaque veille complète, ou « audit de la chaîne »)

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/chaine-youtube/audit.py --chaine <dossier de veille>/ma-chaine.json   # sans --chaine : yt-dlp
```

Il mesure : le rythme (vidéos longues par semaine sur 8 semaines contre l'objectif de 1, régularité, jours depuis la dernière), Shorts ou non, les thèmes (jeu ou sujet de chaque titre, part du thème principal, **dérive** quand les 5 dernières vidéos changent de thème), le fil conducteur « IA + création », et la **grille des 12 dernières miniatures** (`config/youtube/audits/<date>-miniatures.png`, à ouvrir avec Read : la chaîne a-t-elle l'air d'une seule chaîne ? mêmes couleurs, même typo, mascotte cohérente ?). Il écrit `config/youtube/audits/<date>.md`. Ajoute-y ton jugement sur la grille et les 3 actions du mois, et vérifie la liste « À vérifier à la main » avec l'utilisateur (une question à cases).

Une dérive n'est pas une faute : Minecraft puis Pokémon puis Jujutsu Kaisen reste « IA + création » si les titres et les playlists le disent. La réponse est une playlist qui relie, pas l'abandon d'un sujet qui marche.

## 2. Mise en place (une fois, puis à chaque nouvelle série)

Propose chaque élément, fais valider, note-le dans `chaine.md`.

- **Playlists = chaînes de session** (le levier n°1 du temps passé sur la chaîne) : une playlist de série « Duels d'IA » (toutes les vidéos de duel, dans l'ordre où elles s'enchaînent le mieux, pas l'ordre chronologique), plus une par jeu quand il y en a au moins 3 (« Minecraft par l'IA », « Pokémon par l'IA »…). Titre de 60 caractères au plus avec le mot-clé, description de 100 à 500 caractères (mot-clé dans la 1re ligne), sans emoji.
- **Écran de fin** : chaque vidéo mène à **une** suivante précise (la plus proche par le sujet ou le format), plus l'abonnement ; le plan `vidéo A → vidéo B → playlist` est tenu dans `chaine.md` et repris par description-video et publication-video. Vérifier dans le montage que rien d'important n'est caché sous les 20 dernières secondes.
- **Page « À propos »** : les 150 premiers caractères disent ce qu'est la chaîne (ils s'affichent dans la recherche de chaînes) : « Des IA (Claude, ChatGPT…) s'affrontent pour créer des jeux, des mods et des mondes de zéro. Une vidéo par semaine. » Puis pour qui, le rythme, 5 à 10 noms qui situent le sujet (Claude, ChatGPT, Minecraft, Pokémon, mod, jeu vidéo, IA), une seule invitation à s'abonner. Vouvoiement, pas d'emoji. **Mots-clés de chaîne** (Studio → Paramètres → Chaîne) : 10 au plus, le plus important d'abord, cohérents avec ces noms.
- **Bande-annonce** (pour les non-abonnés, 60 à 90 s, sans visage : voix, mascotte et extraits) : 0-5 s une rupture visuelle (le résultat le plus fou d'un duel) et « Si vous voulez voir ce que les IA font vraiment quand on leur demande de créer un jeu… » ; 5-20 s trois promesses concrètes ; 20-45 s la preuve (les meilleurs moments : les **pics** de rétention des bilans) ; 45-60 s le rythme et l'invitation à s'abonner ; fin sur le moment le plus revu. C'est un script : il passe ensuite par le montage (montage-capcut) comme une petite vidéo.
- **Vidéo à la une** pour les abonnés : la dernière vidéo longue. **Sections** de la page d'accueil : populaires, la playlist « Duels d'IA », récentes, Shorts.
- **Bannière et avatar** : déjà faits (`config/youtube/mascotte/`) ; vérifier seulement que la bannière dit la promesse et le rythme dans la zone visible sur mobile (1546 × 423 au centre).

## 3. Sondage Communauté (à chaque publication, et lecture à la veille suivante)

Le sondage prolonge la demande finale du script et nourrit la prochaine idée : « Quel duel pour la prochaine vidéo ? » avec 3 ou 4 options tirées des idées restantes de `idees.md` (les mieux classées par la grille qui n'ont pas été tournées) et des demandes de commentaires. Options courtes (une ligne chacune), pas d'emoji, vouvoiement. Si l'onglet Communauté n'est pas disponible sur la chaîne, pas de sondage (la chaîne ne fait pas de commentaire épinglé).

Note-le dans `chaine.md` (« Sondages » : date, question, options, vidéo associée). À la veille suivante, demande le résultat (une question à cases, ou une capture) et note-le : l'option gagnante prend `"demande": 2` et `"sondage": true` dans `idees-grille.json` (veille.py grille), et nouvelle-video la cite comme argument (« vous l'avez demandé »).

## Ce que ce skill ne fait pas

Pas de traduction (chaîne en français uniquement), pas de visage, pas d'outil tiers (VidIQ, TubeBuddy…), pas de chiffres inventés : ce qui demande Studio (sources de trafic, abonnés par vidéo) se demande à l'utilisateur. Termine par « On valide, ou on change quelque chose ? ».
