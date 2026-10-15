---
name: "youtube-titles-ab"
description: "Écrire les titres YouTube (FR) à partir de vidéos de référence qui ont dépassé leur médiane, et les associer aux miniatures en paires pour un A/B test Test & Compare : références, formules, longueurs, non-répétition titre/miniature."
model: opus
effort: high
---

# Titres YouTube et paires titre + miniature pour A/B test

Complète youtube-thumbnail-prompts (la miniature) : ici on écrit le titre et on vérifie la paire. Adapté de deux skills MIT : yt-package (Jake Schincariol) et yt-title-optimizer (Sergey Bulaev).

## Principe
Le titre et la miniature forment UNE unité. Ils portent la même promesse avec des mots différents : la miniature montre ce que le titre ne dit pas, et inversement.

**Les titres partent des vidéos de référence, pas des vidéos de l'utilisateur.** Tant que la chaîne est petite, ses propres vidéos sont trop peu nombreuses et trop peu vues pour prouver qu'une formule marche. Elles servent à ne pas se répéter et à garder la cohérence de ton ; la preuve qu'une structure de titre fait cliquer vient des vidéos d'autres chaînes qui ont largement dépassé leur propre médiane sur le même sujet ou le même format. Les préférences de la chaîne fixent la forme (ponctuation, ton, marques), pas la structure.

**Avant tout : lire `~/.claude/youtube/preferences.md`** (préférences validées, source unique) et `~/.claude/youtube/apprentissages.md` (ce que les vidéos de la chaîne ont déjà appris). Déjà lus plus tôt dans la même conversation (run nouvelle-video) : ne pas les relire. S'ils manquent, le signaler et demander à l'utilisateur de lancer `python setup.py` depuis son dépôt.

## Étape 1 : les vidéos de référence (obligatoire, avant d'écrire un titre)

1. **Récupérer les références déjà collectées.** Dans le workflow nouvelle-video, la phase 1 a écrit `refs.json` (sortie `--json` de swipe.py) et la section « Vidéos de référence » de `idees.md` dans le dossier de la vidéo. Les relire, ainsi que `refs_history.py show` (skill yt-viral) : les formules qui reviennent sur plusieurs semaines pèsent plus qu'un succès isolé.
2. **Sélectionner par pertinence, puis vérifier qu'elles couvrent le sujet retenu.** `selection.py` (skill yt-viral) classe d'abord par pertinence (même sujet et même format, puis même format), 2 vidéos par chaîne au plus, et écrit `refs-sujet.json` ; c'est elle qui sert de base, `refs.json` reste la niche entière. Il faut au moins 5 vidéos de référence à 2× leur médiane ou plus, sur le même sujet (le jeu, le type de création) ou le même format (duel d'IA, « l'IA crée X de zéro », « Minecraft mais… »). Des outliers sur un autre jeu ou un autre format ne prouvent rien pour ce titre.
3. **Sinon, collecte ciblée** (aussi quand ce skill est utilisé seul, hors workflow) :
   - Tous les JSON bruts vont dans le dossier `veille/` de la vidéo (le créer s'il manque), à côté de ceux de la phase 1.
   - 4 recherches au moins, en français et en anglais, sur le sujet exact et le format (`yt-dlp --flat-playlist -J "ytsearch25:requête" > veille/s-sujet-1.json`) : par exemple `ytsearch25:claude vs chatgpt minecraft`, `ytsearch25:ia crée un jeu de zéro`, `ytsearch25:ai builds minecraft from scratch`, `ytsearch25:minecraft mais ia`.
   - Les résultats de recherche ne donnent qu'une ou deux vidéos par chaîne, donc pas de médiane : relever les chaînes qui reviennent, puis récupérer 30 vidéos de chacune (`yt-dlp --flat-playlist -J --playlist-end 30 --extractor-args "youtubetab:approximate_date" "https://www.youtube.com/@HANDLE/videos" > veille/c-handle.json`), petites chaînes comprises.
   - Classer : `$PY ~/.claude/skills/yt-viral/swipe.py veille/*.json --min 2 --no-shorts --max-age 365 --min-age 5 --exclude <chaîne de l'utilisateur> --json > refs.json`, puis archiver : `$PY ~/.claude/skills/yt-viral/refs_history.py save refs.json --slug <sujet>`. swipe.py lit directement les JSON de yt-dlp et dédoublonne ; relancé sur tout `veille/`, il refait un `refs.json` qui contient la veille de la phase 1 et la collecte ciblée. Ne pas mélanger Shorts et vidéos longues : un titre de vidéo longue se compare à des vidéos longues.
   - Exclure la chaîne de l'utilisateur du classement (`--exclude`) : sa médiane sur quelques vidéos ne veut rien dire. Garder ses titres à part (`ma-chaine.json`) pour éviter les répétitions.
4. **Si la collecte est impossible** (yt-dlp absent, réseau bloqué, résultats vides) : le dire clairement, utiliser l'instantané de veille plus bas en le présentant comme daté, et proposer de relancer la collecte. Ne jamais présenter des titres comme « appuyés sur des références » sans références réelles.
5. **Tableau des références** (5 à 10 lignes) à montrer avant les titres : titre exact, chaîne, multiple de la médiane, vues, âge, formule (colonne `formula` de swipe.py, en sachant que c'est un jugement sur les mots, pas une explication du succès), et la **structure** réduite à son squelette (ex. « [Jeu] mais [N] IA s'affrontent pour [résultat] », « J'ai demandé à [IA] de [créer X] de zéro »).
6. **Nommer les 2 ou 3 structures qui reviennent** parmi les outliers, et ce qu'ils ont en commun (place du nom du jeu, chiffre, première personne, longueur). Si une seule vidéo porte une structure, c'est un indice, pas une preuve : le dire.
7. **Regarder aussi ce qui ne marche pas** : les titres des mêmes chaînes sous leur médiane (`--min 0 --json`, puis les vidéos sous 0,7× de leur médiane) montrent les formulations à éviter.

## Étape 2 : écrire les titres à partir des références
- **Chaque titre cite la ou les références sur lesquelles il s'appuie** (titre de la vidéo, chaîne, multiple) et ce qui a été adapté : langue, sujet, ponctuation, ton.
- Au moins 2 des 3 variantes reposent sur une structure prouvée par une référence à 2× ou plus sur ce sujet ou ce format. La troisième peut être un pari original, à présenter comme tel.
- **Adapter, ne pas copier** : reprendre le squelette, jamais la phrase. Un titre presque identique à celui d'une autre chaîne passe pour une copie et se retrouve en concurrence directe avec l'original.
- Une référence anglaise se traduit par sa structure, pas mot pour mot (« from scratch » devient « de zéro »).
- **Les préférences de la chaîne priment sur la forme** : si la référence utilise deux-points, tiret ou numéros de version, garder sa structure et la reformuler selon les préférences de la chaîne. Si les références contredisent nettement une préférence (par exemple tous les outliers mettent la version du modèle), le signaler à l'utilisateur en une ligne, sans changer la règle de soi-même.
- Les vidéos de l'utilisateur comptent comme une source secondaire : les leviers gagnants notés dans `apprentissages.md` (Test & Compare, taux de clics, rétention à 30 s) orientent le choix de la paire principale, à côté des références. Les citer quand ils pèsent dans le choix ; avec moins de 3 lignes, le dire : c'est une tendance, pas encore une règle.

## Préférences de la chaîne
Dans `~/.claude/youtube/preferences.md`, section « Titres » (ton gaming, explicite, fidèle à l'angle, pas de deux-points ni de tiret ni de points de suspension, marques sans version). Si l'utilisateur valide une nouvelle préférence pendant la session, l'ajouter dans ce fichier, pas ici.

## Les mots que les gens tapent
Pour choisir entre deux formulations (« de zéro » ou « from scratch », « IA » ou « intelligence artificielle », le nom exact du jeu), regarder l'autocomplétion de YouTube en français :
```bash
$PY ~/.claude/skills/youtube-titles-ab/suggest.py "claude vs chatgpt" "ia minecraft" --expand
```
Une suggestion qui revient souvent et haut est une tournure que les gens tapent. Ce n'est pas un volume de recherche : s'en servir pour les mots, pas pour promettre du trafic. Si le réseau bloque, le dire et passer.

## Formules de titre
- **Curiosity gap** : résultat surprenant, mécanisme caché (mais le sujet reste explicite).
- **Transformation** : état de départ et état d'arrivée avec un écart visible (la miniature montre l'après). Ex. « Minecraft devient photoréaliste grâce à… ».
- **Duel / affrontement** : deux camps nommés ou comptés, formulés comme une action. Ex. « 2 IA s'affrontent pour… ».
- **« J'ai… » + action** : première personne, action concrète, noms propres.
- **« Minecraft mais… »** : format phare du Minecraft francophone, immédiatement reconnu par ce public. Ex. « Minecraft mais 2 IA s'affrontent pour le rendre réaliste ».
Un jeu de variantes couvre au moins 2 formules différentes, pas 3 reformulations de la même. Éviter que deux variantes commencent par les mêmes mots.

## Instantané de veille (septembre 2026)
Repli seulement quand la collecte de l'étape 1 est impossible : `references/instantane-veille.md` (constats datés, jamais une preuve).

## Règles de vérification (chaque titre)
- 100 caractères max ; idéalement 40 à 60. Le fil mobile coupe vers 40 : les mots qui décident du clic et le sujet doivent être dans les 40 premiers caractères.
- Un chiffre ou un nom propre plutôt qu'un adjectif vague (incroyable, fou, ultime, énorme, beaucoup trop…).
- 2 mots en majuscules maximum ; aucun emoji (règle de la chaîne).
- Curiosité ET nom concret : jamais de mystère vide (« Ça change tout »).
- Promesse honnête : les 30 premières secondes de la vidéo doivent la tenir ; ne pas sous-entendre un échec ou un vainqueur que la vidéo ne montre pas.
- Pas de formules IA ni de « Voici ce que personne ne te dit ».

## Règles de la paire titre + miniature
- Aucun mot du texte de la miniature ne se répète dans le titre, sauf le mot-sujet indispensable (ex. le nom du jeu) ; le signaler quand c'est le cas.
- Le titre nomme ce que la miniature ne montre pas (ex. la miniature montre le logo ChatGPT, le titre nomme aussi Claude).
- Pour chaque paire, dire quel levier elle teste (humour, transformation, mystère, affrontement…).

**Surfaces** (méthode youtube-seo-skills, deeployCO, MIT) : une paire vise le fil d'**accueil** et les suggestions (émotion ou action en tête, curiosité) ou la **recherche** (le mot-clé principal, d'après `suggest.py`, dans les 40 premiers caractères). Au moins une paire de chaque dans le jeu de 3.

Vérification par script (pas à l'œil) : écrire les variantes dans `titres.txt`, une par ligne, au format `titre | TEXTE MINIATURE | accueil` (ou `| recherche`), puis :
```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/youtube-titles-ab/check_titles.py titres.txt --refs refs.json --own ma-chaine.json --mot-cle "<mot-clé principal>"
```
Le script compte les caractères (après normalisation des accents), montre la coupe mobile à 40 caractères, signale la ponctuation interdite, les majuscules, les emojis, les numéros de version, les adjectifs vagues, les mots répétés entre titre et miniature, deux variantes qui commencent pareil, un titre trop proche d'une référence (copie) ou d'un titre déjà publié sur la chaîne. Sans `--mot-cle`, une paire « recherche » est une erreur (le contrôle n'a pas eu lieu). Pour une paire « accueil », un sujet absent de l'aperçu mobile (40 premiers caractères) est un conseil : la miniature doit alors le montrer. **Code de sortie** : 1 = au moins une ERREUR (règle de YouTube ou de la chaîne, ou contrôle obligatoire impossible) : on corrige et on relance, on n'avance pas ; 0 = aucune erreur. Les « conseil » s'affichent sans bloquer : lis-les, suis-les ou dis pourquoi pas. Titres de Shorts : `--shorts` (pas de surfaces, pas de Test & Compare).

## YouTube Test & Compare (Studio, ordinateur uniquement)
- Jusqu'à 3 variantes : titre seul, miniature seule, ou titre + miniature en paires.
- Le gagnant est la variante avec le plus de temps de visionnage (pas le CTR seul) ; test de quelques jours à 2 semaines.
- Non disponible pour les Shorts, les vidéos pour enfants, les premières et les lives programmés.
- Conseil : tester 3 leviers vraiment différents en mode « titre + miniature », pour apprendre ce qui marche sur la chaîne.
- Ce qu'on peut en conclure : en mode « titre + miniature », une variante gagnante dit que **la paire** a mieux marché, pas lequel des deux ni pourquoi. Studio peut aussi conclure « performances similaires » ou « non concluant » : c'est un résultat, il se note tel quel. Pour isoler un élément, il faut un test où lui seul change (titre seul ou miniature seule).

## Livrable
- Le tableau des vidéos de référence (étape 1) et les structures qui reviennent, avec la date de collecte.
- 3 paires (miniature + titre) prêtes à charger dans Test & Compare, chacune avec : levier, nombre de caractères (sortie de check_titles.py), ce que montre la miniature, le titre, et la référence sur laquelle elle s'appuie (ou « pari original »).
- Indiquer la paire à mettre en variante principale.
- Terminer par : « On valide, ou on change quelque chose ? » (dans un run nouvelle-video, cette question est reportée à la validation unique de fin de run : voir les points d'arrêt de `nouvelle-video/references/chaine.md`)