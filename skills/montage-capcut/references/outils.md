# Outils et commandes

Racine `<dépôt>\montage` (`repo.py root` donne `<dépôt>`).
**Tout l'outillage est dans `08_HYPERFRAMES` (l'atelier)** : scripts, whisper, kit Hyperframes. Lancer les scripts
depuis `montage\08_HYPERFRAMES\scripts` (`cd` puis `python x.py <id>`). Rushs : `Documents\TSAR\Videos\<Nom de la vidéo>\Rush`
(`.mkv`/`.mp4`, trouvés par leur nom : `commun.rush`) ; ailleurs, variable d'environnement `TSAR_RUSH`.
Remotion (`99_ARCHIVE\remotion`, ex-`03_REMOTION`) est archivé : ne plus l'utiliser. Rushs bruts : `Documents\TSAR\Videos\<Nom de la vidéo>\Rush` (lecture seule).

## Rendu direct (adopté le 2026-10-08) : CapCut ne sert plus qu'au dérush
La timeline dérushée (projet « <id> - final ») est **lue**, jamais ouverte ; `rendu.py` sort le MP4 final. CapCut n'est
plus ouvert ni exporté ; le bridge sert encore à `duplicate` et aux `cut-range` (fichiers, CapCut fermé). La pose dans
CapCut (`place`, `zooms`) reste possible **en option**, seulement s'il demande à retoucher à la main.
- Mesuré sur le fixe (essai glacon-ia, 39 s, 17 éléments, 2 glissements, 3 zooms) : rendu complet 17 s ; une correction
  d'un élément = l'élément + son morceau de 20 s refaits, 11 s.
- Exemple réel complet, rendu et vérifié : `videos/_exemple-direction/` (le dérush du Short glacon-ia monté avec toute la
  direction ; sorties dans `06_CAPCUT/_exemple-direction/`).

## Vitesse (mesurée sur le fixe, 2026-10-03)
- `export_capcut.py` rend 8 éléments en parallèle (`TSAR_RENDUS`, 1 avec `--leger`) : 2,4x plus rapide ; avec
  `--nouveaux`, un élément identique déjà rendu sous un autre nom (sous-titre ou transition renumérotés) est recopié ;
  un export sans changement prend ~10 s.
- Whisper chargé une fois par lot de blocs (`verify_cuts.transcribe_many`) : `controle.py` ~2 min, `nettoie_derush.py`
  ~2 min 15 (au lieu de ~10 min) ; `commun.fond_sonore` en cache (`02_ANALYSE/fond_sonore.json`).
- Essayés le 2026-10-06, **pas adoptés** : `-fa` de whisper (1,5 fois plus rapide, mais aucun début de mot daté : le DTW
  exige `-nfa`) ; mode lot d'Hyperframes (`--batch`, même type et même durée seulement : 8 cartes en 27 s contre 33 s
  en rendus séparés, il relance un rendu par ligne).

## Une vidéo = `08_HYPERFRAMES/videos/<id>/` (copier `videos/_modele/`)
- `video.json` : projet CapCut, transcription, `musiques`, `coupes`, `declics`, `sfx`, `sous_titres` (fix + phrases),
  `transitions`, `zooms`. Exemple réel complet : `videos/_exemple/video.json (la 0927, publiée)`.
- `plan.json` : motion design = `elements` du kit (`{id, type, at, dur, vars, layer?, sfx?}`) + `plans` de jeu
  (`{rush, at, dur, src, vitesse?}` ; `vitesse` 10 = génération en accéléré, rendu direct seulement).
  Modèle de la direction : `videos/_modele/plan.json` ; exemple rendu : `videos/_exemple-direction/`.
- Générés : `debuts_voix.txt` (voix.py), `captions.json` (sous_titres.py), `transitions.json` (transitions.py).

## Scripts (`08_HYPERFRAMES/scripts`, génériques : `python <script> <id>`)
| Script | Rôle |
|---|---|
| `capcut_timeline_audio.py "<projet>"` puis `node scripts/transcribe.ts capcut_<projet>.wav` (depuis 08_HYPERFRAMES) puis `timeline_overview.py "<projet>"` | transcription mot à mot de la timeline → `02_ANALYSE/transcriptions/capcut_<projet>.json` + vue lisible `02_ANALYSE/vue_<projet>.txt` (NOIR / JEU / +PLAN) + `luminance_rushs.json` |
| `timeline_frames.py "<projet>" out.png s1 s2…` | images visibles à ces secondes, grille 8×6 (viser un zoom, reconnaître un shader) |
| `visible_clips.py "<projet>" a b [a b…]` · `rush_sheet.py out.png "rush.mkv@s"…` | plans visibles dans la timeline · planche de rushs avec grille (recadrage 9:16) |
| `rush_index.py out.png "2026-09-27*"` · `rush_scan.py out.png 4 "2026-09-27 16-*"` | index visuel (4 vignettes par rush) · balayage serré (1 vignette / 4 s, « rush@s » écrit dessus) pour retrouver un type de plan (face caméra, dimension…) |
| `voix.py <id>` | voix nettoyée par rush (−14 LUFS) + `voix_segments.json` + `voix_timeline.wav` + `debuts_voix.txt`. **Relancer après une cut-range** |
| `sous_titres.py <id>` | punchlines aux mots exacts, calées sur la voix ; retire celles qui tomberaient sur un élément en bas (plan.json). **Plus utilisé par défaut** : les phrases à l'écran se posent en `soustitre` dans plan.json (sukuna-ia, 2026-10-10) |
| `transitions.py <id>` | `glisse_gauche` / `glisse_droite` / `glisse_haut` / `glisse_bas` (push adouci sans flou ; les sauts de scène automatiques tournent sur les quatre sens, **jamais dans l'accroche, à 0,5 s d'un plein écran ni dans une fenêtre de déclics** ; whoosh), `flash` (son `flash_capcut`), `obturateur`, recalés sur la vraie coupe d'image (±0,8 s), plans de plan.json compris |
| `nettoie_derush.py <liste.json> [--appliquer]` | dérush : bords sur les silences, blancs raccourcis au-delà de 0,3 s (voix) / 0,35 s (jeu) depuis WOLF, redites listées bloc par bloc (`"retirer"` dans la liste) |
| `controle.py <id> [--sans-transcription]` | transcription de contrôle (GPU) → `02_ANALYSE/controle_<projet>.txt` : timeline retranscrite bloc de voix par bloc de voix (cache `capcut_<projet>.blocs.json`) : redites (d'un mot à moins de 3 s, d'une phrase à moins de 90 s), faux départs, mots étirés, blancs > 0,5 s, pauses sans parole > 1 s (`--pause`), coupes dans la voix (avec le creux le plus proche), écran noir non couvert, passages du dérush nettoyé absents, sous-titres décalés, micro-clips < 0,25 s (`--derush <json>` pour un autre dérush). Chaque coupe signalée a son image (`02_ANALYSE/controle_<projet>/coupe_<t>.png` : images autour de la coupe, forme d'onde, mots ; `--sans-images`). L'image hors écran noir n'est pas vérifiée. **Avant la musique et avant l'export**. `controle.py <id> --export <mp4>` : son de l'export final (volume, crête, passages très bas, fond sous la voix par tranche de 30 s avec Demucs, cible WOLF ~9 dB) → `controle_export_<id>.txt`, **après l'export** |
| `recale.py <id> <ancien> <nouveau>` | reporte les temps de plan.json / video.json sur une nouvelle timeline après un dérush corrigé (ancien = projet ou relevé `.tsv`) |
| `zooms.py <id>` | `06_CAPCUT/<id>/zooms.json` : zooms rapides cadrés (écartés avec une ligne d'explication : sous un plein écran, à moins de 2 s du précédent) + respiration (`slow`). Règles de cadrage : `cadrage.py` (rendu direct et bridge) |
| `combler.py <id>` | trous noirs → suite du plan précédent → `plan_comblement.json` (lu par `rendu.py`) |
| `verifie_plan.py <id> [--force]` | **avant tout rendu** (lancé aussi par `export_capcut.py`) : type ou variable inconnus (faute de frappe), variable obligatoire absente (sinon valeur d'exemple du kit à l'écran), image ou logo introuvable, deux éléments au même endroit au même moment, élément après la fin ; avertit sur les durées hors règle, les zooms trop proches ou hors familles, une transition dans l'accroche, un repère de test laissé sur une scène plein écran |
| `synchro.py <id>` | **après verifie_plan, avant tout rendu** : trous courts de jeu entre deux plein écran, vert / rouge d'une pastille sans mot dit juste avant, sous-titres décalés (0 point exigé) ; tableau du mot dit à l'entrée de chaque carte, pastille, flèche, réaction, mot, titre, logos (à lire : entrée sur le mot, écart de −0,3 à +0,3 s) → `02_ANALYSE/synchro_<id>.txt` |
| `export_capcut.py <id> plan.json [captions.json] transitions.json [--nouveaux] [--leger] [--seul REGEX] [--force] [--capcut]` | vérifie le plan, rend chaque élément (les glissements seulement avec `--capcut`, pour une pose dans CapCut : le rendu direct les refait sur les plans cadrés) (scènes MP4, overlays MOV qtrle 60 i/s) → `06_CAPCUT/<id>/` + `plan_capcut.json` (items avec type et couche + bruitages des éléments + fenêtres de déclics de « À venir »). Couches : plans 1, scènes 2, éléments 3, repères (`pastille`, `carte`, `minuteur`, `accelere`) 6, flashs 9. Chemins des JSON : `..\videos\<id>\…` |
| `audio.py <id> [--garder-mix]` | musiques par section (la voix − `musique_sous_voix` (13) dB, coupures sèches, `"coupe": "fondu"` pour les anciens fondus, `musique_lufs` pour un niveau fixe ; bornes recalées après `coupes`), SFX (éléments + déclics des plans rapides + zooms : tick léger, whoosh court de lecture + `flash_camera` à 0 s si `entree` + `sfx`) passés par l'**arbitre** (deux sons d'éléments différents à moins de 0,15 s : le plus fort reste ; au plus 3 moments sonores par seconde), `plan_final.json` ; mesure le mix puis applique seul le gain général (−14 LUFS, crête ≤ −1,1 dBFS) |
| `rendu.py <id> [--de S --a S] [--leger] [--refaire]` | **MP4 final** `06_CAPCUT/<id>/<id> - final.mp4` (1080p 60 i/s, H.264 NVENC, AAC 320 k) : plans visibles recadrés (respiration + zooms rapides, filtre perspective sous-pixel, sans tremblement), glissements refaits sur les plans cadrés, scènes et éléments par couche, entrée « avec éclaircissement » ; morceaux de 20 s en cache (seuls ceux qui changent sont refaits) ; `--de/--a` = extrait |
| `revue.py <id> [mp4] [--sans-images]` | **à lire avant de lui montrer quoi que ce soit** : planches `02_ANALYSE/revue_<id>/` (chaque glissement, zoom, élément : entrée, milieu, sortie) + rapport (à-coups de zoom, respiration qui saute à une coupe, élément sans son, plus de 4 sons en 1 s, noirs, image figée ≥ 2 s, volume, crête, durée) ; code 1 = à corriger |
| `dosage.py <id>` | changements d'image, zooms (dont zooms de lecture, respirations), bruitages, changements et coupures de musique, pauses de voix, par minute, comparés aux cibles de la direction de montage (sur `plan_final.json`, après `audio.py`) → `02_ANALYSE/dosage_<id>.txt` ; code 1 = écart au global. Sur l'export : `controle.py <id> --export <mp4>` (mêmes mesures avec Demucs, la détection de scènes et le suivi des zooms, plus l'image immobile) |
| `mesure_montage.py <video.mp4> [--json f] [--planches dossier] [--sous-titres f.json3]` | mesure le montage d'une vidéo finie (la nôtre ou celle d'une autre chaîne), comme pour WOLF : changements d'image, plan médian, voix présente, pauses, fond sous la voix, changements et coupures du fond, bruitages, volume, débit ; planches de l'accroche et de toute la vidéo. Analyse des 14 chaînes de référence : `config/youtube/references/montage/analyse-2026-10-07.md` |
| `variete.py <id>` | ouverture (`"ouverture"` de video.json, catalogue de recettes dans le script), musiques et transitions comparées aux vidéos d'avant ; code 1 = quelque chose à varier (demande du 2026-10-06). **Après avoir rempli video.json / plan.json, et avant l'export** |
| `musique.py choisir <id> [--short f.json] [--ecrire]` | pour chaque partie de video.json `musiques` (ou de la liste `musique` d'un Short) : le meilleur morceau de `perso/` pour son moment (étiquettes du catalogue, tempo, montée) en évitant ce qui a servi dans les 4 dernières vidéos (au même moment surtout) et deux fois de suite, avec bonus de nouveauté ; départ fort pour hook / verdict / vainqueur, reprise là où on l'avait laissé si le morceau revient ; 2 autres choix et les raisons ; `--ecrire` remplace fichier et départ. Moment déduit du nom de la partie, à forcer avec `"moments_musique": {"partie": "moment"}`. Autres commandes : `catalogue`, `chercher`, `pixabay`, `garder`, `refuser`, `historique` (voir § Musiques) |
| `short.py` · `short_capcut.py` | shorts (voir § Shorts) |
| `calque.py <type> --var k=v -o f.mov` | un élément du kit en fichier vidéo (MOV transparent ou MP4), vertical 1080x1920 par défaut (`--horizontal`), pour le poser à la main dans CapCut ; `--liste` donne types et variables |
| `planche.py out.png type@s type@s@vars.json shorts/x.html@s…` | contrôle visuel du kit (PNG sur gris) |
| `make_compositions.py` · `get_fonts.py` · `make_sfx.py` | régénérer les éléments du kit · polices locales · bruitages de synthèse |
| dérushage : `takes_map.py`, `verify_cuts.py`, `capcut_preview.py`, `prepare_voice.py`, `waveform.py` | voir skill derush-capcut |

Retranscription de contrôle d'un sous-titre : couper la fenêtre dans `voix_timeline.wav` (±0,6 s) puis
`..\.whisper\v1.9.2\Release\whisper-cli.exe -m ..\.whisper\ggml-large-v3-turbo-q5_0.bin -l fr -nt -np -f <wav>`.

## Kit Hyperframes (`08_HYPERFRAMES`, CLI `npx hyperframes`, v0.8.123 épinglée ; HTML + GSAP, 60 i/s)
- `kit/tsar.css` + `kit/tsar.js` : chaque élément = fonction du temps `update(t)` (même calcul qu'en Remotion),
  pilotée par une horloge GSAP en pause → seek-safe. Nouveau type = builder `B.<type>` dans `tsar.js` + entrée
  `SPECS` dans `make_compositions.py` (variables + défauts) + bruitages par défaut dans `export_capcut.py` (`sfx_of`).
- Variables numériques : un 0 est pris tel quel (`num` dans tsar.js) ; un texte trop long est réduit (`fitSize`) au lieu
  de déborder ; jamais de valeur d'exemple à l'écran (`verifie_plan.py`).
- Types : transparents → `chapitre`, `test`, `annotation` (alerte), `etiquette`, `etiquettes` (suite
  Vanilla/Claude/Astra), `point`, `manche` (score), `reaction` (Tsar), `soustitre`, `obturateur`, `flash`,
  `abonnement`, `barres`, style WOLF (2026-10-06, refait comme ses vidéos le 2026-10-07) `pastille` (texte blanc contouré
  en bas à gauche, vert / rouge), `carte` (plein écran `plein` s ; la réduction dans le coin n'est plus utilisée, sukuna-ia), `capture` (zoomée, zone
  surlignée en jaune), `score` ; scènes MP4 → `progression` (frise des tests), `insert` (image plein écran 0,5 à 1 s), `vignette` (transparent : image dans une case propre, liseré blanc, entrée en pop et sortie avec whoosh et pop ; image, largeur, hauteur, x, y, rotation, `cadre` false = l'image seule avec une ombre, pour un gros logo ; les passages à habiller sont listés par `scripts/ennui.py <id>` → `02_ANALYSE/ennui_<id>.txt`),
  `partage` (écran partagé de deux rushs, un côté en gros pixels : rendu FFmpeg dans `export_capcut.py`, vars A et B =
  [rush, seconde], nomA, nomB, flou), direction du 2026-10-07 (transparents) : `duel` (logos des IA qui entrent puis
  « VS »), `titre_jeu` (logo du jeu en image, sinon le nom), `minuteur` (cadran qui défile : de, a — `de` 0 pour un temps qui monte —, position : haut-gauche par défaut),
  `accelere` (pastille ▶▶ ×10, en haut au centre), `a_venir` (bandeau de l'accroche), `note` (carte de note d'une IA : note, points),
  `fleche` (texte et flèche vers x, y), `mot` (mot-clé en énorme légende, remplacé par `soustitre` en phrase entière depuis sukuna-ia),  `scene_mots` (scène plein écran sur le fond de la chaîne, plus l'accroche des Shorts depuis le 2026-10-13 : preferences.md § Shorts ; chaque mot, logo ou icône — `bulle`, `chrono` — arrive quand il est dit, les lignes se recentrent ; items = [{t, texte, logo, icone, couleur, taille, ligne, souligne}]), `scene_fenetre` (lignes, barrées, Tsar), `scene_vs` (écrans
  ciel/galaxie/dégradé), `scene_vainqueur`, `scene_outro`, `scene_fond` ; `short` (vertical, voir § Shorts).
- Règles Hyperframes : `npx hyperframes lint .` = 0 erreur avant rendu ; chemins depuis la racine du projet
  (jamais `../`) ; `@font-face` en ligne vers `assets/fonts` ; la durée racine ne change pas par variable (l'export
  l'injecte dans une copie `build/`). Studio pour l'utilisateur : `npx hyperframes preview --background` puis `--stop`.
- Skills officiels Hyperframes dans `~/.claude/skills` : seulement pour un besoin que le kit ne couvre pas.
  Mise à jour : `npx hyperframes skills update` (pas de git sur le PC : sinon fichiers raw GitHub).

## Bridge CapCut — `07_OUTILS\capcut-bridge-windows\capcut_bridge.py` (README à côté)
Avec le rendu direct : `duplicate`, `cut-range`, `check`, `restore` ; `place` et `zooms` seulement en option (retouche à la
main dans CapCut).
Toute écriture : sauvegarde auto dans `<projet>\_sauvegardes_claude\<date>`, refus si CapCut ouvert
(`--quit` pour fermer proprement), `--no-relaunch` pour ne pas le rouvrir.
| Commande | Rôle |
|---|---|
| `ls` · `state <p>` · `check <p>` · `unused <p>` | lire l'état ; `check` = 0 référence cassée/trou/chevauchement |
| `duplicate <p> <copie>` | copie de projet visible dans CapCut (travailler toujours sur une copie) |
| `place <p> <plan.json>` | pose vidéos/images/audio en une écriture. Item : `file, at, dur?, src?, layer?, mute?, volume?, scale?, x?, y?, opacity?, keyframes?`. Audio → pistes `claude-audio` (layer 1 voix, 2 musique, 3+ SFX). `"mute_main": true` coupe le son des clips principaux |
| `unplace <p> <regex>` | retire les clips dont le **nom de fichier** correspond (remplacement ciblé) |
| `zooms <p> <zooms.json>` | option CapCut : mêmes règles que le rendu direct (`cadrage.plan_zooms`) sur le plan .mkv visible le plus haut |
| `cut-range <p> <a> <b>` | retire [a,b[ sur toutes les pistes et recolle (musiques raccourcies en fin) |
| `restore <p> [date]` | revenir à une sauvegarde |
| `launch` · `quit` · `shot <png>` · `click x y` | écran (priorité normale seulement). Menus déroulants : `ui.py` (clics sans ALT) |

## Shorts : direction en vertical (depuis le 2026-10-08)
Un Short se monte comme une vidéo (SKILL.md § Démarrage rapide, étapes 3 à 9) avec `video.json` `"format": "vertical"` :
`export_capcut.py` rend les éléments du kit en 1080×1920 (la composition est la même, la page prend la taille de la
vidéo ; `kit/tsar.js` place chaque élément pour l'écran vertical), l'écran partagé (`partage`) passe en haut / en bas
(`cxA`, `cxB` : recadrage de chaque moitié), `rendu.py` sort du 1080×1920 en recadrant chaque rush autour de `cx`
(plan de `plan.json`, sinon `recadrage` [[de, a, cx]] de `video.json`, sinon `cx`, 0,5 par défaut), `verifie_plan.py`
contrôle les chevauchements avec les emplacements verticaux, `revue.py` fait des planches verticales.

## Ancienne méthode des Shorts (style LAirHisson, test WOLF) — `python scripts/short.py videos/<id>/<short>.json [étape] [--leger]`
Seulement s'il la demande : elle n'a pas les éléments de la direction (flèche, mot-clé, Tsar, accéléré) ni ses contrôles.
Pour un Short indépendant (sans vidéo longue), `video` et `projet` du JSON sont l'id et le projet CapCut de sa propre mini-session (SKILL.md § Short indépendant) ; les étapes ci-dessous ne changent pas.
Générique, tout est dans le JSON (modèle validé : `videos/_exemple/short1.json (Short 1 de la 0927)`) : `passages` [{a, b, texte exact, plans
(rush+src / sync / image, dur, cx, zoom punch ou [de, à], secousse, flash), surgit (captures en haut), interrupteur}],
`captures` (recadrées depuis les rushs d'écran), `musique` (départ calé pour que la montée tombe au bon moment).
1. Caler les phrases : `python scripts/phrases.py <id> "seconde|phrase dite" …` (a, b) et `mots.py <id> a b` (mots).
2. Trouver les plans : `rush_scan.py` (face caméra = vue F5 de son skin dans les rushs de jeu), `rush_sheet.py`.
3. `short.py … tout` (captures → image → voix → mots → audio → html) ; garde-fous : bornes dans les silences (sinon
   le creux le plus bas juste avant le mot suivant, refus si rien < −26 dB), audio = durée vidéo, aucun trou de son.
4. Contrôle : rendre une fois `--format png-sequence -f 4` et assembler ~24 images (pas une planche par image).
5. `short.py … rendu` → `sortie`. Vérifier −14 LUFS, crête < −1 dBFS, 0 trou de son.
6. **Dans CapCut** (il veut pouvoir retoucher) : `python scripts/short_capcut.py videos/<id>/<short>.json` → pièces dans
   `06_CAPCUT/<id>/shorts/<short>/` (plans MP4 coupés à l'image, calques MOV qtrle transparents : scène, captures,
   interrupteurs, sous-titres par phrase ; voix par passage, musique déjà baissée par morceau, SFX) + projet
   `projet_capcut` (copie vidée du projet de la vidéo, 1080×1920 60 i/s ; zooms/transitions = keyframes d'échelle,
   gain commun → −14 LUFS). `--pieces-seules`, `--projet-seul`, `--plans-seuls`. Puis `capcut_bridge.py check`.
   Refuse d'écraser un projet qu'il a retouché (`--ecraser` seulement s'il le demande). Après ses retouches : lire son
   projet (pistes, débuts, sources, volumes) et en tirer les règles → preferences.md + JSON du short.
   Limites : flou des transitions et éclair blanc non repris (zoom seul) ; texte des sous-titres figé (MOV).
   Style WOLF : un calque par carte titre, pastille (`etiquette_n`), score et noms d'écran partagé (`partage_n`) ;
   aucun calque de sous-titres si `sous_titres: false` ; le floutage `pixel` est déjà dans le plan.
Builder `short_lh` dans `kit/tsar.js` (sous-titres Montserrat 800, minuscules, 2–3 mots, vers 64 % de la hauteur).

## Musiques — `python scripts/musique.py` (demande du 2026-10-08)
Bibliothèque = `04_RESSOURCES/musiques/perso/` (seule source du montage) ; fiche de chaque morceau dans
`musiques/catalogue.json` : `moments` (dans l'ordre de préférence, parmi hook, explication, decouverte, test, comique,
tension, verdict, vainqueur, fin, calme), `humeur`, `avis` (`gardée`, ou `favori` quand il a dit l'aimer sur un montage :
bonus au choix), source, licence, mesure. Un nouveau morceau qu'il dépose lui-même : `musique.py catalogue` le mesure,
**j'écris ses `moments` et `humeur`** dans catalogue.json (d'après son nom, sa mesure et ce qu'il en dit). Ce qu'il
dit d'une musique après un montage (« super sur le hook », « pas pour les verdicts ») va dans le catalogue (`moments`,
`avis`, `note`), pas seulement dans preferences.md.
- **Chercher du neuf** (quand `choisir` dit « rien de vraiment adapté », ou pour varier) — deux sources seulement :
  - StreamBeats (Harris Heller : gratuit, monétisable, sans attribution, protégé du Content ID) :
    `musique.py chercher <moment> [--genre lofi synthwave …] [--nb 3] [--max 12]` (genres : ambient, chiptune, edm, hifi,
    hip-hop, lofi, synthwave ; instrumentaux seulement) ;
  - Pixabay (sans IA ni Content ID) : navigateur intégré, `https://pixabay.com/music/search/<mots>/` (mots donnés par
    `choisir`), refuser les cookies, puis en JS :
    `JSON.stringify((window.__BOOTSTRAP__.page.results||[]).filter(r=>!r.isAiGenerated&&!r.hasYoutubeContentId&&r.duration>=90).map(r=>({nom:r.name,auteur:r.user.username,genre:(r.primaryTag||[])[0],duree:r.duration,src:r.sources.src,page:'https://pixabay.com'+r.href,telech:r.downloadCount,note:r.rating})))`
    → fichier JSON dans le scratchpad → `musique.py pixabay <fichier.json> <moment>` (`isLowQuality` est vrai partout :
    ne pas s'en servir).
  Le script mesure, écarte ce qui est déjà connu ou refusé (les 8 Pixabay de la 0927 compris), classe et montre les
  meilleurs (lien, durée, taille). **Je lui montre la liste et j'attends son oui** avant `--oui` (téléchargement dans
  `musiques/a_ecouter/`, hors git). Pour l'écoute : `musique.py ecoute` (page `a_ecouter/ecoute.html` : un lecteur par
  morceau avec ses passages forts, Garder / Refuser / J'hésite, moments, raison ; ses morceaux de `perso/` en bas pour
  corriger leurs moments), servie par `preview_start` « ecoute-musiques » (`.claude/launch.json`, http://localhost:8765/a_ecouter/ecoute.html ;
  en `file://` les lecteurs ne jouent pas). Quand il dit « c'est fait » : `window.verdicts()` dans la page, puis `musique.py garder <morceau> [--moments a,b]` (→ `perso/` + ligne
  dans LICENCES.md) ou `refuser <morceau> <raison>` (supprimé ; ressemblants pénalisés ensuite). Jamais un morceau
  `a_ecouter/` dans un montage.

## Pixabay (SFX)
Navigateur intégré : `https://pixabay.com/sound-effects/search/<mots>/`, refuser les cookies,
puis en JS : `const b = window.__BOOTSTRAP__ || await fetch(window.__BOOTSTRAP_URL__).then(r=>r.json());`
`b.page.results.filter(r => !r.hasYoutubeContentId && !r.isAiGenerated && r.duration >= <s>)` → `name, duration,
likeCount, sources.src` (mp3 direct). Télécharger : `Invoke-WebRequest <src> -Headers @{Referer="https://pixabay.com/"}`
dans `04_RESSOURCES/sfx/pixabay/`. Passage fort : `astats` RMS par 2 s.
Noter chaque fichier dans `04_RESSOURCES/LICENCES.md`.

## Dossiers
`06_CAPCUT/<id>/` (ce que CapCut utilise : ne rien y supprimer qui soit dans un projet) : `scenes/`, `overlays/`,
`voix/`, `musique/`, `sfx/`, `shorts/`, `plan_*.json`, `zooms.json`, `voix_timeline.wav`, `LISEZ-MOI.md`.
`02_ANALYSE/` : transcriptions, `vue_<projet>.txt`, `luminance_rushs.json`, `prises/`, `voix/` (dérushage).
Vidéo finale (rendu direct) : `06_CAPCUT/<id>/<id> - final.mp4` (`rendu/` : morceaux en cache). Anciens exports CapCut :
`Documents\Infinity Maker\<projet>.mp4`.
