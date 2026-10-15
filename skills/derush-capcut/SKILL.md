---
name: derush-capcut
description: "Dérusher les rushs d'une vidéo YouTube de l'utilisateur (chaîne TSAR) directement dans son projet CapCut Windows — repérer les prises répétées, garder la dernière prise complète de chaque phrase, couper au mot près et poser le résultat dans la timeline. À utiliser quand l'utilisateur dit « dérushe… », « derush », « dérusher les rushs », « mets les rushs dans CapCut », ou parle de prises à trier dans un projet CapCut. Modes : « priorité basse / low priority » (il joue à côté) ou « priorité normale »."
model: sonnet
effort: medium
---

# Dérushage CapCut — méthode validée avec l'utilisateur (28/09/2026)

Réponds en français, phrases simples. Travaille de façon autonome, mais **confirme le périmètre** (quels rushs,
quel projet, quelle partie) avant un gros lot si ce n'est pas évident : un dérushage fait sur un périmètre
deviné est à refaire.

## Raccord avec la chaîne de production (dépôt unique)

- **Au début** : l'état du dépôt, selon `CLAUDE.md` § « Deux PC ».
- **Racine = `<dépôt>\montage`** (`python ~/.claude/skills/nouvelle-video/scripts/repo.py root` donne `<dépôt>`) ; Claude Code ouvert à la racine du dépôt. Rushs : `Documents\TSAR\Videos\<Nom de la vidéo>\Rush\` ; ailleurs, variable `TSAR_RUSH` (un seul dossier).
- **Le dérushage se fait sur le PC fixe**, où OBS enregistre et où vivent les projets CapCut ; depuis le portable, accéder au fixe à distance. Avant la carte des prises, vérifier la session : lister les rushs (date dans le nom) dans le dossier des rushs, comparer avec le nombre de rushs et les heures de tournage notés dans `resultats.md` (section « Ce qui s'est passé ») ou, s'ils manquent, demander « il y en a combien ? », et contrôler avec `ffprobe` que chacun se lit jusqu'au bout (un enregistrement inachevé ou un fichier encore en cours de copie est tronqué : durée absente ou bien plus courte que prévu). Un rush manquant ou tronqué : le dire et attendre, ne pas dérusher sans lui.
- **Id** = id court de la vidéo (2 ou 3 mots-clés, ex. `pokemon-ia` ; `repo.py list` pour le retrouver). Le nom du projet CapCut est noté en tête de `videos/<id>/suivi.md` (le demander une fois s'il manque).
- **Le script guide le choix des prises** : lire `videos/<id>/script.md` avant la carte des prises. Les phrases du script sont celles qu'on cherche, dans l'ordre du récit du script (pas seulement l'ordre de tournage). Toujours la dernière prise complète, mais signaler : une phrase du script sans aucune prise ; une prise qui dit autre chose que le script sur le fond (vainqueur, chiffre) ; une improvisation absente du script qui vaut peut-être d'être gardée (la proposer, ne pas trancher seul).
- **Fin** : cocher l'étape 5 de `suivi.md`, noter les phrases manquantes ou changées dans « Écarts par rapport au plan », puis, quand l'utilisateur demande l'envoi, lancer `envoi.bat "<id> : dérushage"` à la racine du dépôt (ou `git add -A && git commit -m "<id> : dérushage" && git push`) ; dans `02_ANALYSE`, seuls les textes (`.txt`, `.json`, `.md` : prises, coupes, rapports) partent dans git, les voix nettoyées et autres gros fichiers restent sur le fixe.

## Outils (Windows, déjà installés)

Racine : `<dépôt>\montage`, scripts dans `08_HYPERFRAMES\scripts` : `capcut_bridge.py` (pilote CapCut), `takes_map.py` (carte des prises), `verify_cuts.py`, `capcut_preview.py`. Tableau, rôle de chacun, whisper.cpp (CUDA, Vulkan, processeur, jamais `--vad`) et chemin des projets CapCut : `references/outils.md`.

## Modes de priorité (à demander si l'utilisateur ne l'a pas dit)

**Priorité basse / low priority** — il joue sur le même PC :
- lancer tout calcul lourd (whisper, ffmpeg, preview) avec la priorité BelowNormal :
  `$p = Start-Process python -ArgumentList … -NoNewWindow -PassThru; $p.PriorityClass = 'BelowNormal'; $p.WaitForExit()`
  (les processus enfants ffmpeg / whisper héritent de la priorité) ;
- **aucune** action à l'écran : pas de `shot`, `click`, `key`, `focus`, `launch`, `open` ;
- écriture dans le projet avec `--quit --no-relaunch` (CapCut se ferme en arrière-plan et reste fermé,
  pour ne pas passer devant le jeu) ;
- découper en commandes courtes (< 10 min) ou en arrière-plan pour ne pas bloquer.

**Priorité normale** : priorité normale, CapCut peut être relancé (`--quit` seul) et on peut vérifier à l'écran
(`shot`, ouvrir le projet par double-clic sur sa vignette).

Si l'utilisateur annonce « jeu fini », repasser les processus en cours en priorité Normal.

## Comment il enregistre (à connaître)

- Rushs OBS (`.mkv`, parfois `.mp4` découpé) dans `Documents\TSAR\Videos\<Nom de la vidéo>\Rush\` (ex. `Videos\Pokemon IA\Rush`),
  un dossier par vidéo ; les scripts les cherchent dans tous ces dossiers par leur nom (`commun.rush`), l'ancien
  `Documents\TSAR\Rush` reste lu. Nommés par date-heure (`2026-09-27 17-45-03.mkv`),
  1080p60, une piste audio stéréo. L'ordre des noms ≈ l'ordre de tournage, pas forcément l'ordre du récit.
  Depuis le 2026-10-01, cette piste contient **la voix et le son du jeu**, baissé d'environ 20 dB dans OBS (crêtes
  vers −30 dB). Les seuils de silence (`takes_map.py`, `verify_cuts.py`, `voix.py`, `short.py`) se règlent seuls sur le
  fond de chaque rush (`commun.seuil_silence` : crête du fond + 6 dB ; −40 dB sans fond) ; `SEUIL_SILENCE=-30` force
  une valeur si une coupe tombe mal.
- Trois sortes de rushs :
  - **voix seule, image noire** (luminance ~16) : narration, verdicts, conclusion ;
  - **jeu + voix** (commentaire en direct sur les shaders) : l'image compte aussi, chaque coupe fait un saut visuel ;
  - **plans muets** (Whisper y invente « Sous-titrage Société Radio-Canada ») : illustrations / comparaisons.
  - **long clip sans son (jusqu'à ~1 h) de l'interface ChatGPT / Claude qui génère** : matière à **timelapse très
    accéléré**, pas une erreur d'enregistrement ; aucune prise à y chercher (carte des prises vide, c'est normal).
- **Il refait beaucoup de prises** : la même phrase 2 à 5 fois dans un rush, parfois recommencée dans le rush
  suivant, avec des faux départs (« donc… donc sur ce point… », « les lumières… »). Il se corrige parfois
  sur le fond (ex. « Astra est meilleur » ×2 puis « Claude est meilleur ») → garder la dernière et le signaler.
- Il importe lui-même les rushs à dérusher dans le panneau Médias du projet avant de demander → `unused`
  donne la liste. Sa timeline : tout sur la piste principale, bout à bout.
- Des rushs peuvent contenir un **son de fond** (vidéo, musique avec paroles) : les poser son coupé et le dire.

## Méthode (ce qui a marché)

0. **Pas de projet CapCut pour ces rushs** (Short indépendant, nouvelle session) : ne pas demander à l'utilisateur de le créer, le faire soi-même, CapCut fermé : `python ..\..\07_OUTILS\capcut-bridge-windows\capcut_bridge.py create "<id>" "<rush1>" "<rush2>" … --no-relaunch` (copie du plus court projet existant, vidée, rushs dans le panneau Médias ; `--modele <projet>` pour un autre modèle), puis `check` et `unused`. Première utilisation : site-ennui (2026-10-08), noter ici tout écart.
1. **Périmètre** : `python capcut_bridge.py state <projet>` (où en est la timeline, dernier clip) et
   `unused <projet>` (rushs importés non utilisés). Repérer un éventuel clip brut non dérushé en fin de timeline
   (clip très long, source depuis ~0 s). Confirmer avec l'utilisateur si doute.
2. **Carte des prises** de chaque rush concerné : `takes_map.py`. **Ne jamais se fier à une transcription du
   fichier entier** : Whisper fusionne les prises répétées et fait croire à une seule phrase hésitante.
   Pour les rushs avec image, regarder aussi 4 images par rush (ffmpeg `fps=1/N,tile=4x1`) pour savoir ce
   qu'on voit (vanilla, shader de Claude, d'Astra, Nether, End…).
3. **Choix des prises** (session de plus de 3 rushs ou cartes longues : le confier à l'agent `trieur-prises`, qui lit
   toutes les cartes et le script hors de la conversation et rend seulement les prises retenues et les doutes ;
   relire ses doutes avec l'utilisateur) : pour chaque phrase, **la dernière prise complète**. Ne **jamais recoller des morceaux
   de prises différentes**. On ne réunit deux blocs que s'ils forment la même prise (hésitation au milieu, pas
   de répétition), ou une reprise naturelle de fin de phrase (« …les mouvements sont » / « les mouvements sont
   pas naturels »). Retirer les faux départs, doublons de sens (« c'est beau, c'est beau »), phrases inachevées.
   Ordre du récit : suivre l'ordre de tournage sauf si le sens impose autre chose.
4. **Liste de coupes** JSON (format dans le README du bridge) dans `02_ANALYSE\derush_<projet>_<partie>.json` :
   `rush_dir`, éventuellement `remplace_a_partir_de` (clip brut à remplacer — tout ce qui suit est retiré,
   plans du dessus compris), `groupes` → `clips` [rush, entrée, sortie, "texte exact tel que dit"] et `broll`
   (plans muets posés son coupé au-dessus, pour couvrir le groupe). Le texte doit être **mot pour mot** celui de
   la carte des prises (sinon la vérification échoue).
5. **Vérification mot à mot** : `verify_cuts.py`. Puis **relire chaque correction** :
   - accepter les retraits de « donc », « ouais », fin de prise précédente, début de prise suivante ;
   - refuser quand le script coupe un mot composé (« ChatGPT » → « chat ») ou retire les premiers mots voulus ;
   - « non reconnu » (transcription ratée) → garder la coupe d'origine et le signaler.
5b. **Nettoyage obligatoire avant de poser** (retours du 2026-10-03 sur pokemon-ia : prises ratées gardées, mots
   coupés, blancs trop longs, clip de liaison oublié) : `python scripts\nettoie_derush.py <liste.json>` (dans
   `08_HYPERFRAMES`). Il cale les bords sur les silences (jamais au milieu d'un mot), raccourcit les blancs
   (> 0,3 s en voix seule, > 0,35 s sur un rush de jeu : style WOLF depuis le 2026-10-06), **y compris les passages sans voix où seuls la musique ou
   les clics du jeu sonnent** (VAD ; « 5 s de musique du jeu entre deux phrases, c'est trop »), sauf ceux listés dans
   `"garder": {"<rush>": [[début, fin]]}` (moment de jeu voulu sans parole), signale les **faux départs** dans un
   même bloc (« et en vrai, et en vrai, c'est… », « je vais… je sais pas… je vais lui dire ») et **retranscrit chaque bloc de voix séparément** (pauses dès
   0,12 s : une reprise suit parfois à 0,15 s) pour lister les redites que la transcription d'un clip entier fusionne
   (« il me demande quelle… il me demande quelle direction visuelle… »). Relire la liste (les énumérations voulues
   ressemblent à des redites), écrire les vraies dans `"retirer": {"<rush>": [[début 1re prise, début reprise]]}`,
   puis `--appliquer`. Vérifier aussi que **chaque rush à voix de la session est utilisé ou volontairement écarté**
   (pokemon-ia : `12-42-47`, « je passe à ChatGPT », oublié). Ne jamais juger redites et blancs sur la transcription
   de toute la timeline : elle décale et fusionne les mots.
6. **Test sur une copie** : copier `draft_content.json` + `draft_meta_info.json` du projet dans le scratchpad,
   `apply-cuts <copie> <liste>`, puis `check <copie>` (0 référence cassée, 0 trou, 0 chevauchement).
7. **Application** : `apply-cuts <projet> <liste> --quit` (+ `--no-relaunch` en priorité basse), puis
   `check <projet>`. Sauvegarde automatique dans `<projet>\_sauvegardes_claude\`. En priorité normale,
   ouvrir le projet et faire un `shot` pour confirmer que CapCut l'accepte.
8. **Compte rendu** court : durée avant → après, ce qui a été gardé (tableau par partie, n° de prise), points à
   écouter (contradictions, transcriptions ratées, sons de fond, hésitations possibles), rushs non utilisés, et la
   commande de retour arrière :
   `python "<dépôt>\montage\07_OUTILS\capcut-bridge-windows\capcut_bridge.py" restore <projet>` (chemin complet écrit en clair dans le compte rendu).

## Limites à rappeler honnêtement

Je choisis sur le texte, les silences et l'image : pas sur l'intonation. Les fins de mots de Whisper sont peu
fiables (raisonner sur les débuts de mots) ; les noms propres sont souvent mal transcrits (Claude → « Cloud »,
ChatGPT → « Tchad GPT »). Proposer une page d'écoute des prises en doute si l'utilisateur veut trancher lui-même.
