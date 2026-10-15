# Cahier des charges — tout ce que l'utilisateur a demandé ou refusé (vidéo 0927, 27–29/09/2026)

Chaîne **TSAR** (Minecraft, IA). Mascotte : **Tsar**, petit diable chibi noir aux cornes rouges, 6 expressions
(`08_HYPERFRAMES/assets/tsar/tsar_*.png` pour le kit : doute, explication, gene_goutte, reflexion, rire_larmes,
surprise ; jeu complet avec la tête seule et la pose en pied, avatar et bannière : `config/youtube/mascotte/`, décrit
dans `config/youtube/mascotte.md`).
Couleurs : rouge chaîne `#E5383B`, noir profond ; Claude `#E07A5A` (orange), Astra/ChatGPT `#3CCFB0` (vert),
or `#F5B942` pour le vainqueur. Polices : Inter Tight (titres), JetBrains Mono (labels/code), DM Serif Display ponctuel.

## Comment lire ce cahier (règles de portée, 2026-10-01)
- **Portée** : chaque règle vaut pour la **vidéo longue**, sauf celles de la section « Shorts », qui ne valent que
  pour les Shorts (et y priment sur le reste). Une règle d'une autre section qui ne s'applique pas aux Shorts le dit.
- **Exception** : toujours datée, avec sa portée (« Shorts uniquement, 30/09 »). Sans portée, elle ne vaut que pour la
  vidéo où elle a été décidée.
- **Deux règles qui se contredisent** : la plus précise l'emporte (Shorts sur général), puis la plus récente ; si le
  doute reste, je pose la question au lieu de choisir.
- **Quand j'attends sa décision** : uniquement aux points d'arrêt de `skills/nouvelle-video/references/chaine.md`
  (section « Quand Claude attend ta décision ») ; entre eux, je travaille seul.

## Direction de montage : « duel lisible et nerveux » (2026-10-07) — prime sur toutes les sections plus anciennes ci-dessous
Adoptée par l'utilisateur le 2026-10-07 après la mesure de 27 vidéos des 14 chaînes de référence et des zooms des 8 qui
performent le mieux (`config/youtube/references/montage/analyse-2026-10-07.md`, rapport visuel « Direction de montage
TSAR »). Elle garde de WOLF (testé sur le Short glacon-ia, `config/youtube/references/wolf/style.md`) ce que toute la
niche confirme (une voix qui ne s'arrête pas, beaucoup de bruitages, des éléments clairs à l'écran), prend aux duels
d'IA qui marchent leur emballage (logos, titre du jeu, minuteur, notes) et laisse les dosages extrêmes de WOLF. Vaut
pour les **vidéos longues** comme pour les Shorts. Vérifiée par `dosage.py <id>` (montage posé) et
`controle.py <id> --export <mp4>` (export) : tout écart se corrige ou se justifie.

**Dosages, par minute** (entre parenthèses : pokemon-ia, médiane des chaînes qui performent, WOLF)

| | Cible |
|---|---|
| Pauses de voix de 0,3 s ou plus | **moins de 3** (14,1 ; 6,8 ; 2,7) : `nettoie_derush.py` coupe dès 0,3 s, mêmes marges sur le jeu ; voix présente 90 % du temps ou plus (83 ; 83 ; 93) |
| Débit de parole | **190 à 210 mots** : déjà bon (pokemon-ia 201, shaders 237) ; les scripts sont minutés à 200 (`minutage.py`) |
| Changements d'image | **10 à 15**, pointes à 20 dans l'accroche et les tests (8,1 ; 9,3 ; 15 à 23) ; des résultats lisibles plutôt que des coupes pour le chiffre. **Les cibles sont des contrôles, pas des quotas** (retour du 2026-10-08) : jamais un plan ajouté pour le compteur ; un plan d'illustration montre ce que la voix dit à ce moment, avec ce que la vidéo a déjà montré ou le test en cours (capture de la consigne, de l'annonce de l'IA, type `capture` avec `zones`), **jamais un moment à venir** (seul « À venir » en montre) ; une cible manquée honnêtement se justifie |
| Image immobile | **moins de 35 % du temps** (66 ; 54 ; 25) |
| Zooms | **5 à 7** (2,1 ; 3,8 ; 4,8) : 3 à 5 **légers** (1,08 à 1,15) calés sur un mot ou un événement, jamais deux de suite ; **un zoom de lecture fort** (1,5× à 3×) environ une fois par minute sur un texte, un bouton, un chiffre du jeu, tenu pendant la phrase, sorti par une coupe ; **respiration** (choisie le 2026-10-08 : une poussée de 1,07 étalée sur 30 s était invisible, image immobile 83 %) sur chaque **séquence** de jeu : **une seule poussée lente par plan, tenue jusqu'à la coupe, jamais de dézoom lent ni de retour à chaque phrase** (retour du 2026-10-13 sur gojo-ia : « zoom, revient, re-zoom » se voyait trop ; `"slow": {"scale": 1.08, "periode": 10.0, "min_dur": 0.6, "mode": "unique"}` ; l'ancien mode « pousse » remettait l'image à 1 à chaque début de phrase, l'aller-retour doux = `"mode": "vague"`) ; les jump cuts d'un même moment du rush (moins de 1 s sautée) forment une seule séquence, l'échelle continue d'une coupe à l'autre ; elle ne repart de 1 qu'à un vrai changement de plan, caché par la coupe (`cadrage.py`). Un zoom rapide part de l'échelle en cours (montée adoucie de 0,2 s, jusqu'à 0,45 s pour un zoom de lecture de 2× et plus) et sort par la coupe suivante (retour en douceur seulement si elle est à plus de 3 s) : **jamais « lent, retour à la normale, rapide »** (retour du 2026-10-08) ; jamais deux à moins de 2 s, jamais sous un plein écran (`zooms.py` les écarte). Adoucis, jamais de tremblement (filtre perspective sous-pixel) ni de flou |
| Musique | **la voix − 13 dB** (`audio.py`, `musique_sous_voix` ; 22,6 ; 28 ; 9), jamais baissée sous la voix ; le fond change 3 à 6 fois par minute (morceau, coupure, reprise) ; **jamais de blanc entre deux musiques** : un changement de morceau enchaîne directement sur le suivant, sur le mot du moment fort (retour du 2026-10-13 sur gojo-ia : « pas de blanc, ça fait bizarre » ; remplace les coupures franches d'1 s) ; toujours **aucune musique quand celle du jeu s'entend** |
| Bruitages | **12 à 18** (19 ; 16 ; 15), sur chaque élément et chaque événement du jeu, groupés sur les moments forts, pas un whoosh à chaque coupe. **Arbitre** (`audio.py`, 2026-10-08) : deux éléments au même instant (moins de 0,15 s) = un seul son, le plus fort ; au plus 3 moments sonores par seconde ; les sons voulus ensemble d'un même élément restent (whoosh + impact de la carte). Zoom léger = tick, zoom de lecture = whoosh court |

**L'accroche** (0 à 45 s ; script : skill nouvelle-video, phase 4)
1. **Les résultats se montrent une seule fois dans l'accroche : soit l'écran partagé à 0-3 s (type `partage`), soit
   « À venir » (étape 4), jamais les deux** (2026-10-10) ; sans écran partagé, 0-3 s = plans neutres du jeu.
2. 3 à 6 s : **titre du jeu** dans sa propre police (type `titre_jeu` : son logo en image, sinon le nom en gros), puis
   les **deux IA qui entrent l'une après l'autre avec « VS »** (type `duel`).
3. 6 à 10 s : **l'enjeu en une image** : minuteur (type `minuteur`, ex. 45:00) ou règle choc.
4. 10 à 13 s, seulement sans écran partagé : **« À venir »** : 2 à 3 s des meilleurs moments de la vidéo (plans de jeu, bandeau type `a_venir`), sans le
   résultat final ni le gagnant ; c'est le seul endroit où la vidéo montre ce qui vient.
5. Mise en place finie avant 0:45, premier résultat jouable à l'écran avant 1:00.

**Le corps, en deux temps** (décision du 2026-10-09 : la première IA en entier, puis la seconde ; détail dans
`skills/nouvelle-video/references/accroches-script.md`)
- **Partie 1 (Claude)** : chaque test avec sa **carte titre courte** (type `carte`, plein écran 1,2 s, jamais réduite
  dans le coin) et son **étiquette** en bas à gauche tout le test (type `pastille`, verte ou rouge à la fin), sans
  point ; transition de 2 s sur le récapitulatif de ses étiquettes.
- **Partie 2 (ChatGPT)** : mêmes cartes et étiquettes, dans le même ordre ; chaque test finit par l'**écran partagé** de
  3 s (type `partage`, Claude à gauche) puis le point, et la **frise** (type `progression`) avec le score se met à jour.
  Aucun gagnant avant le dernier test.
- **Générations jamais montrées telles quelles** : accéléré avec la pastille ▶▶ (type `accelere`) et le minuteur qui
  défile, 10 s au plus, une réaction ou un gag pendant l'attente.
- **Consigne et code** toujours en capture zoomée, la ligne surlignée (type `capture`).
- **Étiquettes avec flèche** sur ce que fait le jeu (type `fleche`) ; **inserts** de 0,5 à 1 s (type `insert`).
- **Tsar en mème de réaction**, environ une fois par test (décision du 2026-10-07, remplace « Tsar rare ») : sur les
  moments drôles ou ratés, en réaction (type `reaction`) ou dans une image générée posée en `insert` (comme la mascotte
  de Prompt Potato).
- **Une phrase à l'écran** environ une fois par minute (type `soustitre`, la phrase entière qui frappe, voir
  sukuna-ia en bas) ; **jamais de sous-titrage intégral** de la voix.

**Le verdict et la fin**
- **Une carte de note par IA** (type `note` : « 7/10 », deux ou trois points forts ou faibles), puis la frise finale.
- **Fin courte** qui demande le prochain jeu à faire refaire.

**Au tournage** (fiche de tournage) : une caméra qui bouge souvent dans le jeu ; 10 à 20 s de **plans « beauté »** par
résultat (survol, tour autour, interface masquée) pour l'accroche et « À venir » ; lancer un vrai minuteur visible quand
le temps compte.

**Propreté, pour qu'il n'ait pas à réitérer (2026-10-08, « je veux pas devoir réitérer, parfait, utilisable direct »)**
- **Rendu direct** : CapCut ne sert plus qu'au dérush ; je sors le MP4 final (`rendu.py`) et je ne lui montre rien avant
  que `revue.py` soit propre et que j'aie regardé toutes ses planches (chaque glissement, zoom, élément).
- **Plan vérifié avant tout rendu** (`verifie_plan.py`) : aucune variable inconnue ou manquante (jamais une valeur
  d'exemple du kit à l'écran), aucun texte qui déborde (réduit tout seul), aucun élément sur un autre.
- **Places fixes** : étiquette (`pastille`) en bas à gauche, minuteur en haut à gauche (ou au centre dans l'accroche),
  accéléré en haut au centre, Tsar en bas à droite, phrase à l'écran en bas au centre, flèche près de ce qu'elle vise.
  Les repères tenus pendant un test (étiquette, minuteur, accéléré) passent au-dessus des éléments ponctuels ; les
  flashs passent devant tout.
- **Transitions** : jamais de glissement automatique dans l'accroche (plans rapides, « À venir »), à 0,5 s d'un plein
  écran (scène, insert, frise, carte en plein écran) ni dans une fenêtre de déclics ; un glissement part des images déjà
  zoomées (aucun saut d'échelle).
- **Flèche** : elle vise une chose qui ne bouge pas pendant qu'elle est à l'écran (interface, objet posé), relevée sur
  une planche à l'instant de son entrée ; sur un personnage qui court, préférer un zoom.
- **Hook** : entrée « avec éclaircissement » (l'image sort d'un éclat de lumière) et son `flash_camera` à 0 s
  (`video.json` `"entree"`) ; plans rapides de « À venir » avec un déclic chacun (automatique).
- **Générations** : plans en accéléré réel (`"vitesse": 10` dans les plans), pastille ▶▶ ×10, minuteur (`de` 0 pour un
  temps qui monte).

Garde-fous inchangés : −14 LUFS, crête ≤ −1 dBFS (contrôler l'export), son jamais coupé dans un mot,
aucun écran noir, aucun plan statique, contrôle (`controle.py`) avant la musique et avant l'export, relecteur avant
l'export. Les sections ci-dessous restent valables pour tout ce que cette direction ne change pas (transitions, flashs,
clics, motion design en fenêtres, export).

## Façon de travailler
- **Rendu direct** : CapCut sert au dérush ; je sors le MP4 final (`rendu.py`). Une pose dans son projet CapCut seulement
  s'il veut retoucher à la main.
- Il n'attend pas devant l'écran : « ça doit être prêt quand je reviens » → **autonome**, mais **efficace,
  rigoureux, sans dépenser de crédits pour rien**. Les questions de départ groupées, puis rien jusqu'au MP4 contrôlé.
- Ne jamais toucher aux rushs bruts ; toujours une copie de projet ; sauvegardes.
- Ne pas partir sur un périmètre deviné : confirmer le périmètre si doute.
- Quand il joue : priorité basse, rien à l'écran. « Priorité normale » = je peux utiliser le PC.
- Tout recevoir en **français simple**. Il apprécie un compte rendu clair de ce qui a été fait.

## Style visuel (motion design)
- **Kit d'abord** (parcours rapide, 2026-10-01) : chaque vidéo se monte avec les éléments existants du kit ; un nouvel
  élément ou effet seulement pour un beat qui en bénéficie vraiment (le dire : quel beat, pourquoi), un par vidéo au plus,
  sauf demande de sa part.
- Références : **Fuze** (@FuzePlays), **Aywen** (@Aywen), **LanceyPoo** (@LanceyPooAi) — fluide, clean, dynamique.
  Inspiration musique/ton : **LAirHisson** (YouTubeur Minecraft).
- **Fond de la chaîne** : lignes ondulées diagonales qui montent vers la droite, sur noir
  (`04_RESSOURCES/assets/fond_pinterest.jpg`), animé, **couleur selon la scène** (rouge chaîne, or pour le vainqueur…).
  (rouge chaîne, or pour le vainqueur…).
- **Style « fenêtres »** (sa capture de référence) : fenêtres d'app sombres (`#15171C`), barre de titre avec
  pastille de couleur + titre + icônes − □ ×, coins arrondis, grosse ombre ; **étiquette en pilule** sous la
  fenêtre (icône carrée colorée + texte gras) ; **pastille « VS » rouge** cerclée de blanc entre deux fenêtres.
  Fenêtre Claude = ciel + logo + nom du modèle en serif ; fenêtre ChatGPT = galaxie étoilée + nom du modèle. **Les noms viennent de `videos/<id>/resultats.md`** (versions réellement utilisées), jamais de la 0927 (« OPUS 5.5 », « GPT-6 · Astra » à l'époque).
  Toute info (mission, règles, tests, score, classement, temps, conclusion, vainqueur, outro) = une fenêtre.
- Utiliser **Tsar** en réaction (bas droite) et **le footage** du jeu sous les scènes rapides.
- **AUCUN EMOJI nulle part** (motion design, sous-titres, boutons). Uniquement des **icônes dessinées (SVG)** :
  check, alerte, interdit, trophée, bulle, cloche…
- Rappel d'abonnement (décidé le 2026-10-01) : **pas de question** (plus de « Tu aimes ce genre de vidéos ? »).
  Élément `abonnement` du kit : une **fenêtre de la chaîne** (même style que les autres fenêtres, barre
  « youtube.com/@letsar555 ») avec **à gauche la photo de profil** (`assets/tsar/avatar_chaine.png`, ronde, liseré
  rouge), le nom et le @, **à droite les boutons** façon YouTube. Le curseur clique « S'abonner » (fondu doux vers
  « Abonné » gris), puis la **cloche** (elle se remplit et sonne), puis l'étiquette « Notifications activées » apparaît
  sous la fenêtre. Smooth et clean, sans emoji. **Posé uniquement au moment où le script demande explicitement de
  s'abonner**, calé sur ces mots ; si le script ne le demande pas, pas d'élément d'abonnement.
- Les étiquettes de comparaison (Vanilla / Claude / Astra) doivent tomber **sur les changements de plan réels**
  (vérifier à l'image quel shader est montré), pas seulement sur la voix.

## Sous-titres (phrases à l'écran)
- Pas de sous-titrage intégral : la phrase qui frappe, en entier (élément `soustitre`, règle de sukuna-ia en bas).
- **Tout en blanc**, aucune couleur, aucun emoji ; **ses mots exacts**, fautes de transcription corrigées
  (retranscrire le passage à part) ; chaque mot apparaît quand il est dit ; rien sur un passage à transcription incertaine.

## Musique
- **Règle du 2026-10-08, prime sur tout le reste de ce fichier** (remplace celle du 2026-10-05, « seulement ce qu'il
  donne ») : un montage ne prend que des morceaux de `04_RESSOURCES/musiques/perso/` (à plat) : les siens, et ceux que
  j'ai trouvés et qu'**il a gardés après écoute**. Les musiques varient d'une vidéo à l'autre sans qu'il y pense : pour
  chaque moment, la meilleure parmi celles qui restent (`musique.py choisir`) ; on réutilise ce qui marche, mais pas
  au même moment que la vidéo d'avant. Quand rien ne convient, ou pour apporter du neuf, je cherche **seulement** sur
  StreamBeats et Pixabay (sans IA ni Content ID) et je retiens les meilleurs ; je lui montre la liste avant de
  télécharger, ils vont dans `musiques/a_ecouter/` et il les écoute avant qu'ils servent (`garder` / `refuser`).
  Toujours pas de YouTube Studio, CapCut ni CC BY ; pas d'OST dans une vidéo longue. **Dans un Short, ses OST sont
  permis** (2026-10-13 ; Content ID donne les revenus aux ayants droit) :
  marqués `shorts_seulement` dans `catalogue.json`, `musique.py choisir` ne les propose qu'en vertical. Il en fournit
  et me laisse choisir le moment de chacun (étiqueter `moments` et `humeur` d'après le morceau). Méthode : outils.md §
  Musiques. Les SFX ne sont pas concernés.
- **Ses goûts, mesurés à l'écoute du 2026-10-08** (18 candidats, 5 gardés ; `musique.py` en tient compte : genres gardés /
  refusés, profils des moments) :
  - **verdict et hook → vraies batteries** (percussions, stomp, batterie rock : 2 sur 2 gardés, et il les voit aussi au
    hook) ; **jamais de beats hip-hop / edm** (0 sur 3) ni de bande-annonce orchestrale ;
  - **test → synthwave ou aventure jeu vidéo pas trop rapide** (106 et 116 BPM gardés ; les 4 au-dessus de 120 BPM et le
    chiptune pur refusés) ;
  - **fin → pas de « joyeux » corporate** (cheerful, uplifting, positive : 0 sur 3) ; un lofi posé gardé sur trois, et
    les percussions lui vont aussi en fin ;
  - pas de préférence de source (Pixabay 3 sur 9, StreamBeats 2 sur 9) ; ne pas juger un auteur sur un morceau
    (Spencer Y.K. refusé en 2026-10-05, gardé ce jour).
- **2026-10-09 : « Percussion and Stomp » (fugu_vibes, Pixabay, 116 BPM) refusée** après publication : il l'a entendue
  au hook du Short site-ennui (départ 102 s) et ne l'aime pas. Supprimée de `perso/`, notée refusée dans `catalogue.json`
  (plus jamais proposée, ce qui lui ressemble perd des points). Des deux « vraies batteries » gardées le 2026-10-08, il ne
  reste que Drums Epic Action : la règle « hook → vraies batteries » tient sur un seul morceau, à revérifier avec lui
  à la prochaine recherche de musique de hook. Leçon : un morceau gardé à l'écoute seule peut déplaire une fois monté ;
  ce qu'il dit d'une musique après publication se note ici et dans le catalogue, comme un refus à l'écoute.
- Ses références de style = musiques de son projet CapCut **0912** (Curious Footsteps, Whimsical, Curious
  Documentary, Pizzicato Panic Parade, Synthwave / Retro-future games, Dark Epic Cinematic Percussion Groove) :
  **s'en inspirer, ne pas les réutiliser**.
- **Une musique adaptée à chaque moment** : **hook fort** (épique/énergique, un peu plus haut), explication →
  pizzicato malicieux, découverte → curieux/tech, tests → synthwave / chiptune, passage comique → pizzicato comique,
  **verdict → percussions épiques**, vainqueur → retour du thème fort du hook (fin : voir ses goûts ci-dessus).
- Mix final ≈ −14 LUFS, crête ≤ −1 dBFS (YouTube ne remonte jamais une vidéo trop basse) ; niveau de la musique : la direction.

## Retours de pokemon-ia (2026-10-03) — priment sur les règles plus anciennes ci-dessous
- **Transitions variées** : glissements latéraux gauche / droite (push) **adoucis (accélèrent puis ralentissent),
  jamais linéaires, sans aucun flou**, avec whoosh ; ou **coupes nettes** ; flashs. **Pas de transition en montée
  (riser)** (essayée puis refusée le 2026-10-03). Remplace « pas de whoosh » et « pas de glissement ».
- **Flashs** : hook = son `flash_camera` (son fichier) ; tous les autres flashs = le son CapCut « click (camera shutter
  sound single shot) » de LEOPARD, qu'il a mis en favori (`assets/sfx/flash_capcut.wav`).
- **Hook** : entrée en flash caméra (image + `flash_camera`) sur la première phrase.
- **Clics (2026-10-05, vidéos et Shorts)** : tout clic, déclic ou obturateur = **uniquement** le son CapCut « click (camera
  shutter sound single shot) » (`assets/sfx/flash_capcut.wav`, volume 1) ; plus jamais `declic`, `declic_2`, `clic`. Il a
  remplacé à la main les déclics du Short glacon-ia ; `short.py` (`CLIC`) et `export_capcut.py` le font maintenant.
- **Musique** (niveau : voir la direction) ; **aucune musique quand la musique du jeu
  s'entend** (partie Claude de pokemon-ia), mais **de la musique quand celle du jeu est très basse** (partie ChatGPT) ;
  il n'a pas aimé les 8 morceaux Pixabay en stock : il fournit ses musiques (pokemon-ia : hook, quirky, chill jazz,
  tribal jazz, `04_RESSOURCES/musiques/perso/`).
- **Tout ce qui bouge a un SFX** : chaque ligne qui apparaît dans une fenêtre, chaque mot barré, chaque IA qui entre
  dans le VS, l'étiquette de la description… (pas seulement l'ouverture).
- **3e série (2026-10-03)** :
  - **Un seul projet** « <id> - final » : corriger dans ce projet (remplacer mes clips, garder ses retouches), jamais
    « final 2 / final 3 » ; supprimer (corbeille) les projets de travail en trop.
  - **Ses retouches du hook** à garder et à reproduire d'emblée : premier plan avec l'animation d'entrée CapCut
    « Entrée avec éclaircissement » (pas de flash blanc par-dessus), son `flash_camera` à 0 s, **ses clics CapCut
    « click (camera shutter sound single shot) » (1111055) sur les plans rapides** (`flash_capcut.wav`), musique du hook
    un peu plus basse (+1,35 dB au lieu de +3).
  - **Encore plus dynamique** : blancs coupés au-delà de 0,35 s (voix seule) / 0,5 s (jeu) ; pas d'attente pendant
    qu'il choisit dans un menu (choix du starter, Créadex) : seulement la musique du jeu = à couper.
  - **Sauts de scène dans le jeu** (inventaire puis combat…) : jamais une coupe sèche, un glissement (automatique dans
    `transitions.py`).
  - **Quand la musique du jeu s'arrête** (bug, fin du jeu) : remettre une musique en fondu progressif.
  - **Aucun écran noir**, même 1 s (9:43 de pokemon-ia).
  - **Transcription de contrôle** (`controle.py`) avant la musique et avant l'export : redites (« ChatGPT… ChatGPT »,
    « il a utilisé… il a utilisé »), blancs, écran noir, et ce qui manque : réponse coupée au nettoyage du dérush
    (« je vais lui dire… » sans la réponse, final 3 de pokemon-ia), sous-titre décalé, bout de clip oublié.
  - **Retours du 2026-10-03 (final 3)** : coupes au milieu d'un mot ; **5 s de musique du jeu sans parole** entre deux
    phrases (navigation dans l'interface) = trop, à couper ; **faux départs** (« et en vrai, et en vrai, c'est… »,
    début de phrase, hésitation, phrase redite) ; « ChatGPT… ChatGPT a fait » à 0:13 gardé. Tout ça doit être
    trouvé par `nettoie_derush.py` et `controle.py`, pas par lui.
- **Réactions de Tsar** (sa retouche du 2026-10-03, final 3) : posées sur le mot qui réagit (« Super stylé »), pas
  avant, et courtes (~1,9 s au lieu de 2,8 s).
- **Petits défauts** : une prise ratée peut être suivie de la bonne à 0,15 s (« il me demande… il me demande quelle
  direction visuelle ») : `nettoie_derush.py` retranscrit bloc par bloc pour la trouver.
- **Aucun plan statique** longtemps à l'écran (texte d'agent, écran titre, fond d'écran, notes dites sur un écran fixe) :
  le couvrir avec des plans de jeu qui collent à ce qu'il dit, ou une fenêtre animée.
- **Dérush** : jamais la prise ratée avant la bonne (même phrase redite, faux départ, « c'est… ça dépend des… ») ; ne
  pas se fier à la transcription de toute la timeline pour repérer redites et blancs (elle décale les mots) : vérifier
  au son et par retranscription du passage ; couper les blancs ; jamais une coupe au milieu d'un mot (bords calés sur
  les silences).
- **Éléments calés au mot près** (phrases.py), pas sur la vue approximative.
- **Ne jamais sauter un clip qui fait le lien** (ex. « je passe à ChatGPT », ses questions et son plan) : vérifier que
  chaque rush à voix de la session est utilisé ou volontairement écarté.
- Visuel de « le prompt est dans la description » : une **maquette de la description YouTube** (`scene_description`).

## SFX
- **Pop (2026-10-06, vidéos et Shorts)** : un vrai pop de bulle, « Bubble Pop 06 » d'Universfield (Pixabay), choisi
  par lui (`assets/sfx/pop.wav` ; `pop_sortie.wav` = le même, plus grave). L'ancien pop (son d'interface Kenney
  `select_006`) est refusé : « j'aime pas du tout, je veux vraiment un pop ». Un nouveau son choisi par lui passe par
  `make_sfx.py` (`PIXABAY`), jamais par un remplacement à la main du WAV.
- **Déclics d'appareil photo** sur les plans rapides ; whoosh permis (levé le 2026-10-03).
- Plans rapides qui s'enchaînent au début : un **déclic d'appareil photo sur chaque plan**.
- **Vignettes (2026-10-13) : pas de pop**, seulement le whoosh du glissement, à l'entrée et à la sortie
  (`export_capcut.sfx_of`).
- Discrets ailleurs : pop à l'ouverture des fenêtres, tick sur étiquettes/zooms rapides, croix sur les règles
  barrées, validation sur les points marqués, frappes clavier sur le texte tapé, montée + impact avant le vainqueur.

## Transitions
- **Seulement entre deux scènes qui n'ont rien à voir** (changement de partie, de dimension, arrivée du vainqueur),
  **sans en abuser** (~10 pour 8 min).
- **Pas de transition au début** sur les plans rapides.

## Flous
- Quand c'est utile : ex. **flou « teaser »** léger sur les comparaisons rapides du début (« dans cette vidéo… »
  sans l'écrire).

## Zooms
- Dosage et types : la direction (tableau, ligne Zooms). Un zoom rapide est **cadré sur la chose** dont il parle
  (regarder l'image) ; keyframes **adoucies**, jamais linéaires.

## Rythme / propreté
- **Aucun plan noir** laissé à l'écran sous la voix : combler (suite du plan précédent, scène…).
- **Du jeu à l'écran dans la première minute** (2026-10-02, vidéo shaders : chute à 0:56) : règles, scores et réglages se
  disent sur des extraits du résultat, pas sur un fond uni ni un terminal ; génération accélérée 10 s au plus ; passage
  d'une IA à l'autre en 15 s au plus jusqu'à la première image de son jeu.
- **Couper les blancs** dans la voix (ex. pause entre « très très propre » et « pour une IA ») en recollant toute
  la timeline.
- Voix **nettoyée** (bruit réduit, sifflantes adoucies, niveau constant). Quand le son du jeu est sous la voix (rushs OBS
  depuis le 2026-10-01, jeu ≈ 20 dB plus bas), `voix.py` le détecte et passe en **réduction de bruit douce** : la
  musique et les sons du jeu restent, seul le souffle part. **Écoute humaine obligatoire de l'export** (casque, en
  entier, en accéléré seulement sur les parties de génération) : coupes, volumes du jeu, voix qui « pompe » ; les
  défauts trouvés vont dans « Écarts » de `suivi.md`.

## Export
- **Rendu direct (2026-10-08)** : `rendu.py` sort le MP4 final 1080p 60 i/s, H.264 à qualité constante élevée, AAC 320 k,
  −14 LUFS, crête ≤ −1 dBFS ; il n'y a plus d'export CapCut à faire. Une pose dans CapCut seulement s'il veut retoucher à
  la main (option).

## Shorts
- **La direction « duel lisible et nerveux » (section plus haut) s'applique aussi aux Shorts et prime sur tout ce qui suit.** Depuis le 2026-10-08, un Short se monte avec la chaîne de la direction en format vertical (`video.json` `"format": "vertical"`, modèle `08_HYPERFRAMES/videos/_exemple-direction/`, SKILL.md § Fin de vidéo, shorts), avec les mêmes contrôles avant le compte rendu (`dosage.py`, `revue.py`, `relecteur`). `short.py` et ses réglages (`_exemple/short1.json`, `glacon-ia/short1.json`) sont l'ancien style : ne plus les prendre comme modèle. Les règles ci-dessous (son jamais coupé, plein écran recadré…) restent valables quand elles ne contredisent pas la direction.
- **Retours du 2026-10-08 sur le Short site-ennui (vaut pour tous les Shorts)** :
  - **pas de « À venir »** dans un Short ;
- **Accroche d'un Short (demande du 2026-10-13, gojo-ia ; remplace la scène de mots sur fond rouge)** : son plan de jeu reste
  à l'écran ; **les premiers plans sont des plans face caméra de son skin en troisième personne** (demande du 2026-10-13,
  sukuna-ia-short1 : à prendre dans les rushs, ex. « mon apparence a bien changé ») ; **chaque chose nommée
  s'illustre en gros au milieu** sur son mot : logo d'une IA (`vignette` `"cadre": false`), personnage ou œuvre
  (`vignette`), deux IA (`duel`).
- **Sous-titres d'un Short (2026-10-13, sukuna-ia-short1 ; remplace le mot à mot de gojo-ia)** : sur **tout le Short**
  (exception à « jamais de sous-titrage intégral »), comme sa référence (Short de LAirHisson
  https://www.youtube.com/shorts/mnhYIR1v9xk) : ses mots exacts par **groupes de 1 à 3 mots**, **minuscules** sauf les
  noms propres, **sans ponctuation**, Montserrat 900 blanc **sans contour**, halo sombre flou autour des lettres, lettres
  serrées (ses captures du 2026-10-13) ; le groupe **pope** d'un bloc (surgit à 60 %, rebondit à sa taille en 9 images,
  sans glisser) et disparaît net quand le suivant arrive (`soustitre` `"style": "reference"`, mots à `t` 0,
  `taille` 92, `bas` 600 : vers 65 % de la hauteur ; plus haut quand Tsar est à l'écran) ; **pas de sous-titre sur un
  juron** (« putain »).
- **Étiquette du test centrée en haut, au-dessus du jeu** (`pastille` `"place": "haut"`, 2026-10-13).
- **Transitions entre les parties** (accroche, chaque IA, verdict), à l'image et au son : glissement avec whoosh, ou
  flash devant un plein écran (2026-10-13).
- **Une seule musique sur tout le Short**, calée sur ses temps forts (départ choisi pour que les attaques du morceau
  tombent sur l'ouverture et les changements de partie) ; sukuna-ia-short1 : Cuphead, départ 0,4 s (2026-10-13).
- **Noms des IA sur l'écran partagé = exactement le texte du VS** (2026-10-13, « là c'est moche » avec l'Arial de
  FFmpeg) : `partage` avec `nomA` / `nomB` à " " et un élément `noms_partage` (même `wolfText` que `duel`) par-dessus,
  même début et même durée.
  - **pastille jamais verte ni rouge sur une réaction** (« Wow » n'est pas une validation) : la couleur seulement si un
    test réussit ou rate, dit comme tel ;
  - **aucun élément ne disparaît en plein plan** : un repère (minuteur, mot, capture, Tsar, pastille) finit sur une coupe
    d'image ou une transition, jamais avant ;
  - **Tsar jamais coupé au milieu de l'écran** : en vertical, il surgit dans son cadre arrondi (le buste est coupé par le
    bord du cadre) ;
  - respiration : voir la direction (une poussée lente par plan, sans retour à chaque phrase).
- Il veut que je **trouve les idées** à partir de la vidéo longue et que je les propose ; il choisit.
- **Un Short n'est pas forcément tiré d'une vidéo longue** (2026-10-04) : un Short indépendant se monte comme une vidéo
  (tournage OBS, dérush dans CapCut, montage avec la direction en vertical, SKILL.md § Short indépendant).
- **Jeu en carré au milieu sur fond flou** (sa capture du 2026-10-13, gojo-ia) : les plans de jeu en carré 1080×1080
  pleine largeur au centre, au-dessus et en dessous le même plan agrandi, flouté et assombri (`video.json`
  `"cadre_vertical": "carre_flou"`, `rendu.py`) ; zooms et respiration dans le carré (`fx`, `fy` relevés dans le carré) ;
  le texte affiché par le jeu sur les côtés est coupé. MP4 1080×1920 60 i/s prêt à publier.
- **Son JAMAIS coupé** (bug du Short 1, 30/09) : chaque passage commence et finit dans un silence, la piste audio fait
  exactement la durée de la vidéo, aucun trou de son.
- Accroche **dite tout de suite** (pas de carton titre), sujet dans la 1re phrase ; pas de fin « dites en commentaire »,
  ça boucle. **Vrais logos** des IA (`assets/logos/`), jamais redessinés. Jamais de secousse ou vibration artificielle.

## Description YouTube
- Description courte + chapitres horodatés (0:00 en premier, ≥ 10 s chacun), calés sur le montage final (après
  coupes), sans révéler le vainqueur. **Aucun emoji** dans la description non plus.

## Ménage
- « Clean tout ce qui sert à rien » : corbeille, jamais suppression définitive ; lister ce qui part et ce qui reste ;
  demander avant de supprimer un **projet CapCut** ; vérifier le panneau Médias de tous les projets avant.

## Retours de sukuna-ia (2026-10-10) : primes sur les sections plus anciennes
- **Un seul nom de test à l'écran** : l'étiquette en bas à gauche (`pastille`, « IA : nom du test », ou le nom seul dans un Short à une seule IA, couleur vert / rouge) ; la `carte` ne fait que son plein écran (1,2 s), jamais de carte réduite en haut à droite en plus.
- **Accroche : peu de plans de résultats.** Les résultats (domaine, flèche, coupes) se voient une seule fois : écran partagé ou « À VENIR », pas les deux (précisé le 2026-10-10) ; le reste, et pendant les règles, des plans neutres du jeu (début de partie, interface, objets).
- **Séparer l'accroche de l'explication du plan** par une transition (glissement à la fin de l'accroche, `video.json` `transitions`), pas une coupe sèche.
- **Jamais un trou de quelques images** entre deux éléments plein écran (scène, carte, progression) : le jeu ne doit pas apparaître 1 à 10 images (« 1 frame de jeu, puis l'écran ChatGPT en gros, puis le jeu »). Un plein écran commence pile sur la coupe d'image et le suivant pile à sa fin.
- **Pas de barre sous « À VENIR »** (retirée du kit).
- **Pas de mot isolé** (« DINGUERIE », « BUGUÉ », « COPIÉ ») : la **phrase entière**, ses mots exacts (fautes de transcription corrigées), mot à mot sur la voix (`soustitre`, `bas` 190 pour ne pas toucher l'étiquette). Vaut aussi pour les rappels de règles (« Je valide le plan tel quel »). Remplace « un mot-clé en énorme légende » de la direction.
- **Musique refusée** : « Castle of Athanasius » (Spencer Y.K.) sur la partie test de Claude, refusée et supprimée de `perso/` (`catalogue.json`, `refuses`).
- **Quand il cite l'œuvre ou le personnage** (« Sukuna », « Jujutsu Kaisen ») : une image par mot, dans une **case propre** (`vignette` : fond sombre, liseré blanc, coins arrondis), qui entre en pop sur le mot et ressort, avec ses bruitages ; pas de titre texte (`titre_jeu`) en plus. Il choisit les images sur une planche numérotée ; logo **occidental** de l'œuvre.
- **Écran ennuyeux = vignette** (2026-10-10) : quand l'image bouge à peine ou que rien ne s'ajoute (`ennui.py`, étape 8b), on habille le passage d'une `vignette` de ce qui est nommé à ce moment, comme Sukuna et le logo de Jujutsu Kaisen dans l'accroche de sukuna-ia. Il choisit les images sur une planche numérotée ; un passage de jeu qui tient seul peut rester tel quel.

## Retours de gojo-ia (2026-10-13) : priment sur les sections plus anciennes
- **Laisser voir chaque action en entier** : un pouvoir, un sort, une explosion se montre du lancement à l'effet tant qu'il est à l'écran, même sans parole (« le Bleu pas visible ») : au dérush, ces passages vont dans `"garder"` de `nettoie_derush.py`, repérés sur une planche à 1 image par seconde ; la règle des blancs coupés ne s'y applique pas.
- **Garder les phrases de passage** (« Ok donc, nous voilà enfin sur Minecraft ») : elles marquent la transition entre l'accroche et le jeu.
- **Logo d'une IA nommée seule** : même style que dans le VS (`duel` avec `"seul": true` : logo rond et nom dessous), pas le logo nu.
- **Short à une seule IA** : l'étiquette donne seulement le nom du test (« Le Bleu »), sans « Claude : » devant.
- **Étalonnage** propre, coloré et attirant, sans excès (1,35 de saturation jugé trop saturé) : `video.json` `"etalonnage"` : saturation 1,12, contraste 1,06, gamma 1,01, vibrance 0,12, netteté 0,4 (`rendu.py`).
- **Musique refusée** : « Neon Vibes » (StreamBeats) sur la partie test du Short gojo-ia (à la corbeille, refusée dans `catalogue.json`) ; à la place, sa musique « Lost Woods » (Zelda, reprise de Sylvurr, départ 6 s) ; « Color Your Night » (Lotus Juice), essayée entre les deux, reste dans `perso/` mais pas sur ce Short.
