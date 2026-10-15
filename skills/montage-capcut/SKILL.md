---
name: montage-capcut
description: Monter une vidéo YouTube de l'utilisateur (chaîne TSAR, Minecraft / IA) après le dérushage dans CapCut, en rendu direct (MP4 final sorti par les scripts, CapCut seulement lu) — direction « duel lisible et nerveux » (logos et VS, minuteur, étiquettes, cartes de note, zooms de lecture, phrases clés à l'écran), motion design en « fenêtres » (kit Hyperframes), zooms, transitions, voix nettoyée, ses musiques (perso), SFX, export final, description YouTube et shorts verticaux — avec ses préférences validées et une consommation de crédits maîtrisée. À utiliser quand il dit « passe au motion design », « monte la vidéo », « ajoute musique / SFX / sous-titres / zooms / transitions », « rends-la dynamique », « fais le montage », « exporte », « fais des shorts », « monte le short <id> » (Short indépendant, sans vidéo longue), « description avec timestamps », ou renvoie des retours sur un montage CapCut. Pour le dérushage lui-même, voir le skill derush-capcut.
model: sonnet
effort: medium
---

# Montage CapCut — méthode validée (vidéo 0927 « Claude vs Astra », jugée « parfaite »)

Réponds en **français**, phrases simples. **Rendu direct depuis le 2026-10-08** : il dérushe dans CapCut, puis je
fabrique tout (éléments, zooms, transitions, voix, musique, SFX) et je sors moi-même le MP4 final 1080p60 ; CapCut est
seulement lu (jamais ouvert ni exporté). Ses retouches passent par ses retours horodatés ; la pose dans CapCut reste une
option s'il veut retoucher à la main. **Il veut un montage juste du premier coup** : je ne lui montre rien avant que
`revue.py` soit propre et que j'aie regardé ses planches. Tout l'outillage est dans `08_HYPERFRAMES` (l'atelier).

## Livrable unique (règle du 2026-10-10, sukuna-ia : trop d'allers-retours)

Une demande de montage = **une seule remise** : un MP4 final prêt à poster, puis fin. Je ne montre rien tant que tout ce qui suit n'est pas passé, et je corrige moi-même ce que ces contrôles trouvent (pas à lui de me le faire corriger) :
1. `verifie_plan.py` 0 erreur, **`synchro.py <id>` 0 point** (trous d'une image entre plein écran, états vert / rouge sans mot, sous-titres décalés) **et lecture de son tableau** : chaque carte, logo, titre, flèche, réaction de Tsar entre **sur le mot qui le dit** (écart de −0,3 à +0,3 s), jamais avant (carte « LA TRANCHE » quand il dit « tranche », logos des IA sur « Claude et ChatGPT », titre sur le nom du jeu, vert / rouge après le mot qui le justifie) ;
2. rendu, `revue.py` 0 point (hors image figée justifiée) **et toutes les planches regardées** (pas seulement celles que j'ai touchées au dernier tour) ;
3. `controle.py <id> --export`, agent `relecteur`, `dosage.py` : leurs points sont corrigés ou justifiés **avant** le message ;
4. un seul compte rendu (ci-dessous), qui dit en une ligne ce qui reste à écouter ou à décider par lui (écart au script, phrase mal dite). Il n'a plus qu'à regarder le MP4 et poster (description : skill description-video).

**Retours de sa part : modifier seulement ce qu'il demande.** Avant de toucher quoi que ce soit : lister ses points un par un ; sauvegarder `plan.json` et `video.json` (copie `.avant`) ; corriger **par petites modifications ciblées** de ces deux fichiers, jamais en régénérant le plan ou `video.json` par un script (un script qui réécrit tout efface les musiques, les zooms, l'entrée en flash et tout ce qui avait été validé) ; ne pas relancer `musique.py choisir --ecrire` (il remplace les 5 morceaux) mais changer seulement la partie visée (`musique.py refuser` ne marche que sur `a_ecouter/` : pour un morceau de `perso/`, le retirer du catalogue en Python via `musique.charger/sauver`) ; **comparer avant / après** (`diff` des deux JSON) : seuls les points demandés ont bougé. Ne jamais retirer un élément validé (écran partagé, entrée en flash, musique du hook, zooms…) pour « appliquer » une autre demande : si deux demandes se touchent, choisir la lecture qui garde le plus et le dire. Aucune initiative en plus (« tant que j'y suis »).

**Pièges d'exécution** : `rendu.py` ne lit que la piste principale : un plan posé au-dessus au dérush (`broll`) se redéclare dans `plan.json` `"plans"`, sinon l'image d'en dessous reste (sukuna-ia-short1 : l'écran du script dans l'accroche) ; écrire un script Python dans un fichier (outil Write) plutôt qu'en heredoc dès qu'il contient une apostrophe ; enchaîner les étapes (6 à 8) en un seul bloc en arrière-plan ; appliquer −0,5 dB aux volumes de `plan_final.json` si `revue.py` donne une crête au-dessus de −1 dBFS (`audio.py` vise −1,1 mais l'encodeur remonte d'environ 0,5).

Lire au moment utile, pas avant :
- `references/preferences.md` — le cahier des charges (tout ce qu'il a demandé / refusé). **En entier avant de produire.**
- `references/outils.md` — scripts, kit Hyperframes, bridge, Pixabay pour les SFX (commandes exactes).
- `references/capcut-technique.md` — formats et pièges CapCut 9.5 Windows (déjà vérifiés : ne pas re-tester).

## Raccord avec la chaîne de production (dépôt unique)

L'atelier est dans le dépôt : **racine = `<dépôt>\montage`** (`python ~/.claude/skills/nouvelle-video/scripts/repo.py root` donne `<dépôt>`). Claude Code est ouvert à la racine du dépôt ; les scripts se lancent toujours depuis `montage\08_HYPERFRAMES\scripts`.

- **Id de la vidéo** = id court (2 ou 3 mots-clés, ex. `pokemon-ia`), fixé par nouvelle-video (`repo.py id`). Il nomme `videos/<id>/` (production), `montage/08_HYPERFRAMES/videos/<id>/` (réglages du montage) et `06_CAPCUT/<id>/`. Si l'utilisateur dit « monte la <titre> » ou donne un autre nom, retrouver l'id avec `repo.py video "<titre ou id>"` (il retrouve la vidéo existante par son id ou son titre ; code 2 = plusieurs correspondent : demande laquelle avec AskUserQuestion ; code 1 = aucune : ne crée rien, vérifie avec `repo.py list`). Le **projet CapCut** porte le nom que l'utilisateur lui a donné : il est noté dans l'en-tête de `videos/<id>/suivi.md` (le demander une fois s'il manque).
- **Avant de produire**, en plus de `references/preferences.md` : lire `videos/<id>/script.md` (beats dans l'ordre, accroche, `[ON SCREEN : ...]`, demande finale), `resultats.md` (vainqueur, bugs, versions), `titres-miniatures.md` (promesse du titre principal) et `suivi.md` (écarts déjà notés).
- **Le montage respecte le script** : même ordre des beats ; l'accroche du script dans les 15 premières secondes ; les `[ON SCREEN]` servent de plan aux fenêtres de `plan.json` (mission, règles, tests, score, verdict) ; une seule demande finale, celle du script ; la promesse du titre principal tenue dans les 30 premières secondes. Si le tournage ne permet pas de la tenir (autre vainqueur, résultat raté), le dire **avant l'export** pour changer de titre. Tout écart (beat coupé, ordre changé, plan ajouté) va dans « Écarts par rapport au plan » de `suivi.md`, jamais en silence.
- **Fin de montage** : cocher l'étape 6 de `suivi.md` ; à l'export, garder la transcription horodatée du montage final (02_ANALYSE) : c'est elle qui donne les chapitres à description-video.
- **Préférences** : `references/preferences.md` est dans le dépôt (`~/.claude/skills/montage-capcut` est un lien vers `skills/montage-capcut`), une préférence ajoutée part au prochain commit. Les règles de la chaîne communes à tout (titres, miniatures, mascotte, Shorts) sont dans `~/.claude/youtube/preferences.md` ; en cas de conflit sur le montage lui-même, celles de ce skill priment.
- **Au début** : l'état du dépôt, selon `CLAUDE.md` § « Deux PC ».
- **Envoi** à la fin de chaque grosse étape : `envoi.bat "<id> : montage …"` à la racine du dépôt (il refuse les `.mkv`, `.mp4`, `.mov` et tout fichier de plus de 50 Mo ; à la main : `git status` puis `git add -A && git commit -m "…" && git push`).

## Démarrage rapide : nouvelle vidéo `<id>` (ex. « monte la 1004 »)

Une seule série de questions au début (AskUserQuestion, groupées) : projet CapCut dérushé, priorité (je joue /
normale), périmètre si doute. Puis, dans `montage\08_HYPERFRAMES\scripts` (CapCut fermé pour les étapes 1 et 2b) :

1. `python ..\..\07_OUTILS\capcut-bridge-windows\capcut_bridge.py duplicate "<id>" "<id> - final"` (+ `check`).
2. Transcription : `capcut_timeline_audio.py "<id> - final"` → `node scripts/transcribe.ts …` (depuis 08_HYPERFRAMES)
   → `timeline_overview.py "<id> - final"`. Lire **seulement** `02_ANALYSE/vue_<projet>.txt` (≈ 170 lignes).
2b. **Contrôle de la voix** : `python controle.py <id>` (voir « Contrôle obligatoire » plus bas). Coupes dans un mot,
   pauses où seul le jeu sonne, faux départs, redites : à corriger avant de lui montrer. Les corrections validées =
   `cut-range` du bridge sur « <id> - final » (fichier, CapCut fermé), puis relancer (la timeline a bougé) jusqu'à un
   rapport propre.
3. `xcopy /E /I ..\videos\_modele ..\videos\<id>` puis remplir `video.json` (musiques par moment, transitions, zooms,
   `entree`) et `plan.json` (éléments du kit, plans) **en une passe**, calés au mot près (`phrases.py`) sur la vue **et
   sur `videos/<id>/script.md`** (un beat du script = une fenêtre ou une scène, dans le même ordre). Viser les zooms, les
   flèches et les zones de capture avec `timeline_frames.py` (une planche) ; une flèche vise une chose qui ne bouge pas
   pendant qu'elle est à l'écran. Exemple rendu complet : `videos/_exemple-direction/`.
   **Musiques : je ne les choisis pas à la main.** Je pose les parties (nom, début, fin), puis
   `python musique.py choisir <id>` (meilleur morceau de `perso/` pour chaque moment, sans reprendre ce qui a servi
   récemment) ; si une ligne finit par « rien de vraiment adapté », `musique.py chercher <moment>` (StreamBeats) ou
   Pixabay (outils.md § Musiques) : je lui propose les candidats, je télécharge dans `musiques/a_ecouter/` **après son
   accord**, il écoute, `garder` / `refuser`, puis `choisir <id> --ecrire`.
4. `python voix.py <id>` · `python transitions.py <id>` · `python zooms.py <id>` · `python combler.py <id>`
   (indépendants : les lancer ensemble en arrière-plan). Puis `python variete.py <id>`.
5. `python verifie_plan.py <id>` : 0 erreur (il dit quoi corriger : variable inconnue ou manquante, deux éléments au même
   endroit…) ; chaque avertissement corrigé ou justifié. Puis **`python synchro.py <id>`** (0 point, tableau des mots à
   l'entrée de chaque élément lu : voir « Livrable unique ») et `npx hyperframes lint .`. Caler chaque élément sur
   `mots.py <id> a b` **au moment de l'écrire** (pas sur la vue), pour ne pas le refaire après.
6. `python export_capcut.py <id> ..\videos\<id>\plan.json ..\videos\<id>\transitions.json --nouveaux` (en
   arrière-plan ; `--leger` s'il joue) puis `python audio.py <id>` (niveaux, arbitre des SFX) et `python dosage.py <id>`.
7. `python rendu.py <id>` → `06_CAPCUT/<id>/<id> - final.mp4` (`--leger` s'il joue ; `--de S --a S` pour un extrait).
8. **`python revue.py <id>`** : rapport propre (0 point) **et** je regarde toutes ses planches
   (`02_ANALYSE/revue_<id>/`) : chaque glissement, zoom, élément à l'entrée, au milieu et à la sortie. Tout défaut se
   corrige dans les JSON, puis 6 à 8 de nouveau (seuls les éléments et les morceaux touchés sont refaits).
8b. **`python ennui.py <id>`** (règle du 2026-10-10) : passages où l'image bouge à peine (≥ 2 s) ou où rien ne s'ajoute
   (≥ 6 s). Pour chacun, une `vignette` de ce qui est nommé à ce moment (logo d'une œuvre, d'un jeu, d'un outil,
   personnage, objet, capture), entrée sur le mot : je cherche les images, je lui montre **une seule planche numérotée
   pour tous les passages** dans la même série de questions du début de la revue, il choisit (ou « rien » pour un passage
   de jeu qui tient seul), puis 5 à 8. Jamais une image étrangère à ce qui est dit.
9. `python controle.py <id> --export "06_CAPCUT\<id>\<id> - final.mp4"`, agent `relecteur`, puis je lui envoie le MP4
   (SendUserFile) avec le compte rendu (ci-dessous) et `06_CAPCUT/<id>/LISEZ-MOI.md`. Proposer `/compact`.

**Leçons de pokemon-ia (2026-10-03), à appliquer dès le premier montage :**
- Dérush toujours passé par `nettoie_derush.py` (skill derush-capcut, étape 5b) avant `duplicate`.
- Repères au mot près avec `phrases.py` (jamais la vue approximative) ; vérifier chaque passage d'image fixe (texte
  d'agent, écran titre, fond d'écran, écran noir sous la voix) et le couvrir de plans de jeu qui collent aux mots ou
  d'une fenêtre animée.
- Transitions : `glisse_gauche` / `glisse_droite` (push adouci, sans flou, whoosh), `flash` (son CapCut
  `flash_capcut`), coupes nettes ; **jamais de montée (riser)**. Hook : flash + `flash_camera`.
- Musique : **uniquement** les morceaux de `04_RESSOURCES/musiques/perso/` (les siens, et ceux que j'ai trouvés et qu'il a
  gardés après écoute : règle du 2026-10-08, `musique.py`), choisis par `musique.py choisir`, la voix − 13 dB
  par défaut (direction du 2026-10-07, sans ducking, jamais de blanc entre deux musiques ; `musique_lufs`
  fixe seulement si une vidéo le demande), **aucune musique quand la musique du jeu s'entend** (`commun.fond_sonore` du rush > −60 dB :
  pas de musique sur ce passage).

**Direction « duel lisible et nerveux » (2026-10-07)** : `references/preferences.md` § « Direction de montage » prime sur
tout le reste. En pratique, dans `plan.json` :
- accroche : `partage` **ou** `a_venir` (jamais les deux), sinon plans neutres du jeu, `titre_jeu` ou `vignette`, `duel`,
  `minuteur` ;
- chaque test : `carte` (plein écran 1,2 s seulement), `pastille`, `progression` entre deux tests ;
- partout : `accelere` sur les générations, `capture` pour la consigne et le code, `fleche` sur ce que fait le jeu,
  `insert`, `soustitre` (phrase entière) environ une fois par minute, Tsar en mème de réaction environ une fois par test (`reaction`, ou
  image générée en `insert`) ;
- verdict : une `note` par IA.
Dans `video.json` : le fond qui change 3 à 6 fois par minute, sans blanc entre deux musiques, `sfx`
sur les événements du jeu, des zooms `punch` légers (1,08 à 1,15) et un zoom de lecture fort (1,5 à 3) par minute, la
respiration (`slow`) sur les séquences de jeu. Puis `python variete.py <id>` et **`python dosage.py <id>`** (dosage minute
par minute comparé aux cibles) après `audio.py` ; après le rendu, `controle.py <id> --export <mp4>` (mêmes mesures, plus
l'image immobile). Les cibles sont des contrôles, pas des quotas : jamais un plan ajouté pour un compteur.
- Chaque élément animé a son bruitage (`export_capcut.sfx_of`) ; `audio.py` règle seul le gain général (−14 LUFS,
  crête ≤ −1,1 dBFS).
- **Un seul projet « <id> - final »** (demande du 2026-10-03 : pas de « final 2 / 3 », ils polluent). Option CapCut, s'il l'a retouché à la main :
  corriger dans ce même projet sans perdre ses retouches — `capcut_bridge.py unplace <p> "<regex>" --apres T` (garde ce
  qui commence avant T, ex. son hook), `apply-cuts` avec `remplace_a_partir_de` = premier clip modifié, `place` des seuls
  éléments après T, puis `recale.py <id> "<relevé .tsv d'avant>" "<projet>"`. Lire d'abord ses retouches (pistes,
  sons, animations) et les reporter dans preferences.md.
- **Contrôle obligatoire** : `python scripts/controle.py <id>` (transcription GPU de la timeline) **avant la musique** et
  **avant le rendu final** ; chaque ligne du rapport est corrigée ou justifiée. Puis `revue.py` après chaque rendu.
- Carte graphique : Whisper CUDA (`.whisper/cuda`), NVENC (`commun.h264`), `--gpu --browser-gpu` d'Hyperframes ;
  `TSAR_GPU=0` / `TSAR_WHISPER=cpu` pour revenir au processeur.

## Règles de conduite (ne pas déroger)

1. **Jamais toucher aux rushs** (`Documents\TSAR\Videos\<Nom de la vidéo>\Rush`) ni au projet d'origine : travailler sur la copie
   « - final » (seulement `cut-range` ; le rendu la lit sans l'écrire), et **ne jamais remettre à zéro une copie qu'il a
   retouchée** (date de `draft_content.json`) : en option CapCut, remplacer seulement mes clips (`unplace` + `place`).
2. **CapCut ouvert = pas d'écriture** (`duplicate`, `cut-range`). Lui demander de le fermer, ou demander avant de le fermer.
3. **Priorité basse** (« je joue ») : `--leger`, BelowNormal, aucune action écran/clavier/souris, `--no-relaunch`.
   **Priorité normale** : vérifications à l'écran permises (`launch`, clic vignette, `shot`, `ui.py`).
4. **Téléchargements** : annoncer quoi / d'où / taille ; une demande explicite (« prends du Pixabay ») vaut accord.
5. **Ménage** : jamais supprimer un fichier cité dans `draft_content.json` OU `draft_meta_info.json` d'un projet ;
   corbeille seulement (il la vide lui-même) ; demander avant de supprimer un projet CapCut.
6. **Honnêteté** : je n'entends pas l'audio ; je mesure (LUFS, silences) et je retranscris. Le dire quand ça compte.

## Économie de crédits (sans baisser la qualité)

- **Kit d'abord** : tout le style TSAR existe en éléments paramétrables → remplir `plan.json`, ne pas recoder
  d'animation. Besoin nouveau → ajouter un type au kit (réutilisable), pas un cas unique.
- **Scripts génériques** (`<script> <id>`) : ne jamais copier/adapter de script pour une vidéo ; tout va dans `video.json`.
- **Lire peu** : la vue de la timeline, pas les transcriptions brutes ; Grep / `offset`+`limit` ; ne pas relire un
  fichier qu'on vient d'écrire ; ne pas relire les skills Hyperframes officiels sans besoin nouveau.
- **Rendu final en cache** : `rendu.py` ne refait que les morceaux de 20 s qui ont changé ; un extrait (`--de/--a`) pour
  vérifier une correction. **Rendus ciblés** des éléments : `--nouveaux` (refait ce qui manque **ou a changé** : empreinte de la composition, du kit, des variables et de la durée à côté de chaque rendu ; `voix.py` fait de même pour chaque rush) / `--seul REGEX` (une image d'`assets/` modifiée n'est pas suivie) ; contrôle sur planche d'images, jamais en regardant des vidéos.
- **Longues tâches en arrière-plan** (`run_in_background`), pas de sondage serré ; commandes indépendantes en parallèle.
- **Écritures CapCut groupées** (seulement `cut-range`, et la pose en option) : toutes les coupes d'un contrôle en une fois.
- **Une conversation par vidéo** ; proposer `/compact` après chaque grosse phase et `/clear` entre deux vidéos.
- Pas de recherches web « pour voir ». Un seul sous-agent : `relecteur` (voir « Livrable unique »). Messages d'étape courts.

## Après ses retours

Lister pour soi **tous** les points de son message (horodatés sur le MP4), les corriger **seulement eux** (voir « Livrable
unique » : copie `.avant`, modifications ciblées, comparaison avant / après) dans `plan.json` / `video.json` (ou `cut-range`
pour une coupe), refaire 5 à 9 (seul ce qui a changé est rendu, mais **la synchro et toutes les planches sont relues**),
puis ajouter toute nouvelle préférence à `references/preferences.md` (le skill doit contenir tout ce qu'il a dit).

## Fin de vidéo, shorts

- « C'est bon » → le MP4 de `rendu.py` est déjà l'export final (1080p **60 i/s**) ; `controle.py <id> --export <mp4>`
  (son de l'export : volume, crête ≤ −1 dBFS, fond sous la voix ; pokemon-ia sortait à −0,3 dBFS de crête), transcription horodatée
  du montage final, puis **skill description-video** (préférences § Description : sans emoji, chapitres recalés après
  coupes, vainqueur non révélé ; il vérifie tout avec `check_description.py`).
- **Tout script de Short (fille ou indépendant) passe par le guide des scripts** (skill yt-script : 3 accroches selon les 21 formules en blocs `**Version X**`, `hookscore.py <fichier>.md`, 2 montrées avec son tableau, `minutage.py <fichier>.md` avec le code 0 ; format dans le skill short) avant d'être montré ; règle du 2026-10-08, aucune exception.
- « Fais-en des shorts » → proposer 3–5 idées (accroche, déroulé, durée) tirées de `script.md` et `resultats.md`, il choisit ; lui montrer le **script**
  (tableau temps / ce qu'il dit / image / effets) avant de fabriquer.
- **Un Short se monte avec la direction, comme une vidéo** (2026-10-08) : mêmes étapes 3 à 9 du démarrage rapide, même
  kit (pastille, carte, mot-clé, flèche, Tsar, accéléré, zooms de lecture, respiration, changements de musique), mêmes
  contrôles, en **format vertical** : `video.json` `"format": "vertical"` → `export_capcut.py` rend les éléments en
  1080×1920 (le kit les place dans la zone sûre d'un Short : repères en haut, mot-clé vers 65 % de la hauteur, Tsar
  au-dessus de l'interface), `rendu.py` recadre chaque rush autour de `cx`, en carré sur fond flou (preferences.md § Shorts) (`"cx"` d'un plan de `plan.json`,
  `"recadrage": [[de, a, cx], …]` pour la piste principale, `"cx"` par défaut ; viser ce qui compte avec
  `timeline_frames.py`). Modèle : `videos/_exemple-direction/` + `"format": "vertical"`. La timeline est un projet
  CapCut à lui : Short indépendant, voir ci-dessous ; Short fille, projet `<id>-short<n>` dérushé (skill derush-capcut)
  sur les phrases choisies. `short.py` (ancien style LAirHisson, test WOLF) n'est plus la méthode : seulement s'il le
  demande.

### Short indépendant (pas tiré d'une vidéo longue)

Méthode dans `references/short-independant.md`, à lire seulement dans ce cas (même méthode qu'une vidéo, en miniature : id court, tournage, dérushage, montage avec la direction en vertical).

## Compte rendu final

**Contrôles** (vidéo ou Short) : tous ceux de « Livrable unique », passés avant ce compte rendu ; le tableau de
`dosage.py` (ce montage / cible) y est recopié, chaque ligne « à revoir » corrigée ou justifiée. Écrire « direction
appliquée » seulement s'ils sont tous passés ; sinon dire lesquels manquent et pourquoi. Un élément de la direction volontairement absent
(pas de duel dans un Short à une seule IA…) est nommé avec sa raison.

Par catégorie : ce qui a été ajouté ; ce que je n'ai pas pu vérifier ; points à regarder (horodatés) ; écarts par
rapport au script (aussi notés dans `suivi.md`) ; commande `restore` ; crédits musique si besoin
(`montage/04_RESSOURCES/LICENCES.md`). Court, en français simple.
