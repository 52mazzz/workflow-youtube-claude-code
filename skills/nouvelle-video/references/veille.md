# Phase 1 de nouvelle-video : veille et idées, mode d'emploi détaillé

Lu au début de la phase 1. Les règles de session de `SKILL.md` (ne rien inventer, AskUserQuestion, etc.) s'appliquent. Toute la collecte passe par **`veille.py`** (skill yt-viral) : une commande, et un seul fichier à lire ensuite, `veille/veille-resume.md` (quelques dizaines de lignes au lieu de milliers de lignes de JSON). Ne recopie pas les commandes yt-dlp à la main, sauf pour une vidéo précise.

## Légère ou complète

| | Veille légère (par défaut, chaque semaine) | Veille complète (toutes les 4 semaines) |
|---|---|---|
| Quand | une vidéo par semaine, entre deux veilles complètes | la dernière date de plus de 4 semaines, il n'y en a jamais eu, ou l'utilisateur la demande |
| Chaînes collectées | seulement celles qui ont un des 15 meilleurs outliers des 4 dernières semaines, et celles découvertes depuis moins de 4 semaines | toutes celles de `chaines.json` |
| Recherches | **les 4 à 6 recherches fraîches que tu écris** (`--requete`) : ce qui a bougé depuis la dernière veille | les recherches de base de `veille-requetes.json` + les fraîches |
| Deuxième passage | 10 chaînes au plus | 25 chaînes au plus |
| Coût | quelques minutes, peu de crédits | 15 à 30 minutes de collecte |
| Archive | `<date>-veille.json` | `<date>-veille-complete.json` |

Dans les deux cas, une chaîne collectée il y a moins de 7 jours n'est pas recollectée (cache). La date de la dernière veille complète est celle du fichier le plus récent `~/.claude/youtube/references/*-veille-complete.json`. Dis en une ligne laquelle tu fais et pourquoi.

**Les recherches fraîches** (en français et en anglais, des verbes et des angles variés, pas celles des semaines précédentes) : les nouveaux modèles d'IA, les sorties de jeux de la semaine, les tendances gaming, les formats « IA + création » (jeu, mod, musique, graphismes, animation, speedrun, simulation, agents qui jouent), et **2 ou 3 recherches hors niche** (gaming hors Minecraft, tech, création, divertissement : défis, simulations, « J'ai… », univers et jeux qui attirent) : elles fournissent les matières des idées croisées (§ 3). Le périmètre de la chaîne : `preferences.md` § Chaîne.

## 1. Collecter et classer

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
Y=~/.claude/skills/yt-viral
cd "$REPO/videos/veille-<AAAA-MM-JJ>"          # dossier de la phase 1 ; veille/ y est créé, hors git
$PY $Y/veille.py collecte --mode legere --requete "..." --requete "..." --requete "..." --requete "..."
#                          --mode complete pour une veille complète ; --min-views 10000 par défaut
```

Ce que fait `collecte`, dans l'ordre : `ma-chaine.json` (pour ne pas répéter un sujet, et le nombre d'abonnés, `channel_follower_count`) ; les chaînes suivies et les recherches, 4 à la fois ; le classement par **multiple de la médiane de chaque chaîne** (`swipe.py`), avec un **plancher de 10 000 vues** (une vidéo à ×249 avec 4 000 vues n'est pas une idée qui a voyagé) ; le **deuxième passage** (les chaînes trouvées par les recherches avec trop peu de vidéos pour une médiane, mais une vidéo forte, sont collectées et tout est reclassé : c'est là que sortent les chaînes inconnues) ; la mise à jour de `chaines.json` ; la **dynamique** ; l'archive. Il écrit `refs.json` (classement de niche ; après validation du sujet, `selection.py` produit `refs-sujet.json` pour le script, les titres, les miniatures, la description, la publication et le bilan) et `veille/veille-resume.md`.

Lis **seulement** `veille/veille-resume.md` : meilleurs outliers, ce qui monte (moins de 30 jours), dynamique, signaux faibles, chaînes découvertes, formules de titre, échecs.

- **Dynamique** : pour une vidéo déjà vue dans une veille précédente, les vues par jour depuis cette veille, comparées à sa moyenne d'alors : **monte** (au moins 60 % de sa moyenne), **ralentit**, **plafonne** (moins de 20 %). Une idée dont la preuve plafonne depuis des semaines est moins urgente qu'une qui monte encore.
- **Contre-exemples (flops)** : les vidéos des chaînes suivies à 0,5× leur médiane ou moins (5 à 180 jours). Ce qui ne marche pas renseigne autant que ce qui marche : un sujet ou une formule de titre qui revient parmi les flops (le résumé signale les formules surreprésentées) est à éviter ou à justifier dans `idees.md`.
- **Signaux faibles** : petites chaînes à 10× ou plus, sous le plancher de vues. Une petite chaîne qui décolle est utile pour une chaîne qui démarre, mais ce n'est pas une preuve : à citer comme indice, jamais comme preuve d'une idée.
- **Accroches des références** : `$PY $Y/accroches.py --refs ../refs.json --top 5` mesure les 30 premières secondes des 5 meilleurs outliers (sous-titres) : mots en 15 s, à quelle seconde la mission ou la promesse est dite, premier chiffre (contrainte, enjeu), demande d'abonnement ou salutation avant 30 s, avec la transcription horodatée. Note dans `idees.md` la médiane et ce que font les meilleures ouvertures ; la phase 3 s'en sert. Ce sont des mots, pas des images : regarde aussi leurs miniatures.
- **Commentaires** : sur les 3 à 5 meilleurs outliers, `$PY $Y/comments.py URL1 URL2 …`. Les demandes les plus aimées (« fais-le sur… », « partie 2 », « avec Gemini ») et les jeux ou IA les plus cités sont des idées de sujet ou de suite. Un indice : les commentateurs sont une petite minorité très engagée.
- Les chaînes suivies : `$PY $Y/veille.py chaines` (source, dernière collecte, médiane, meilleur multiple). Les découvertes y entrent seules ; en retirer une = supprimer sa ligne dans `config/youtube/chaines.json`.

Si yt-dlp ne passe pas du tout (réseau bloqué, erreur 403, YouTube qui demande une connexion), le résumé le dit dans « Échecs » : fais alors la veille avec la recherche web en notant les vues visibles, et indique dans `idees.md` que les multiples n'ont pas pu être calculés. N'invente pas de multiple. Pourquoi yt-dlp : WebFetch est redirigé vers la page de consentement YouTube. Données publiques uniquement, jamais de compte connecté.

## 2. Le créneau français

Pour chaque concept fort qui vient de l'anglais (et pour les idées finales), vérifie s'il a déjà été fait en français :

```bash
$PY $Y/veille.py creneau "ia crée un jeu d'horreur" "ia joue à pokémon"      # formulations françaises
```

Verdict par concept : **libre** (aucune vidéo française à 10 000 vues ou plus **parmi les 20 premiers résultats de cette recherche**), **partiel** (1 ou 2), **pris** (au-delà), avec les 3 vidéos françaises les plus vues. Écris-le toujours « aucune référence française forte trouvée dans cette recherche », jamais « créneau libre » : 20 résultats ne prouvent pas l'absence de concurrence. Pour une idée finale, lance 2 ou 3 formulations différentes du même concept. La langue est devinée sur les titres : confirme à l'œil les exemples affichés. Un concept « libre » déclenche la règle « anglais sans français » (point 3).

## 3. Les idées

Lis `~/.claude/youtube/types-de-videos.md` (la base des types de vidéos) avant d'écrire les idées : chaque idée dit de quel type elle relève, et au moins 3 types différents doivent apparaître parmi les 8. Les formats trouvés en veille qui n'y sont pas encore s'ajoutent à ce fichier (fiche : principe, preuves chiffrées, limite, état en français).

**Règle « anglais sans français »** : pour tout concept qui existe en anglais et que `creneau` donne « libre », écris **deux idées jumelles** : la copie fidèle (adaptée à la chaîne) et la même idée avec **une** touche d'originalité (contrainte, enjeu, mélange avec un autre type, point de vue, matière). Les deux partagent la même preuve ; présente-les côte à côte.

**Idées croisées (au moins 2 des 8, décidé le 2026-10-16)** : un **format** qui a marché × une **matière** qui a marché (univers, jeu, objet, tendance, de préférence trouvée par les recherches hors niche) × une **contrainte** inédite. Chaque morceau a sa propre vidéo source chiffrée ; le croisement, lui, n'a pas encore été fait. Dans `idees-grille.json`, remplace `multiple`/`vues` par `"morceaux": [{"role": "format", "source": "…", "multiple": 7.8, "vues": 71777}, {"role": "matière", …}]` : la grille note la preuve du **morceau le plus faible** (un morceau sans multiple compte 0 et rend la preuve inconnue). Pas de bonus d'originalité.

Les 8 idées (croisées comprises) restent dans le ou les domaines choisis au tour 0 (`SKILL.md`), répartis entre eux s'il y en a plusieurs ; les recherches fraîches visent aussi ces domaines. Applique le sous-skill `ideate` du skill youtube : 8 idées, chacune avec stratégie de trafic, urgence, accroche en une phrase, concept de miniature et **preuve chiffrée** (vidéo source, multiple, vues). Garde au moins une idée « format léger » (faisable vite) et une idée « tendance urgente » si une tendance existe.

**Classement par la grille** : écris les 8 idées dans `idees-grille.json` puis classe-les :

```bash
$PY $Y/veille.py grille idees-grille.json        # tableau markdown à coller dans idees.md
```

```json
[{"titre": "Mod de dragons Minecraft", "type": "duel d'IA", "multiple": 36.9, "vues": 2364388,
  "faisabilite": 2, "urgence": 2, "apprentissages": 0,
  "creneau_concept": "ia crée un mod minecraft de dragons", "demande_seeds": ["mod dragon minecraft", "ia minecraft"]}]
```

Ajoute à chaque idée son **intention** (divertissement, comparatif, tutoriel, actualité : ce que cherche le spectateur, affiché sans être noté) et, pour un sujet lié à une date, son **pic** : une date connue (`"pic": "10-31"` pour Halloween, la sortie d'un jeu) ou `"tendance_mot": "mod dragon minecraft"` pour demander à Google Trends (`$PY $Y/veille.py tendance "…"` le montre seul : saisonnier avec la date du prochain pic, tendance, en déclin, permanent ; souvent refusé par Google, alors rien n'est deviné). Un pic dans les 60 jours ajoute 1 à l'urgence.

Barème (sur 13, affiché sous le tableau) : **preuve** 0 à 3 (log du multiple ; divisée par 2 sous 10 000 vues) ; **faisabilité** 1 à 3 (3 = faisable cette semaine avec ce que l'utilisateur a, 1 = gros chantier ; ton jugement, dis-le) ; **créneau français** libre 2, partiel 1, pris 0 (mesuré par `creneau`, ou donné par `creneau`) ; **urgence** 0 à 2 (2 = tendance qui monte ou date fixe proche) ; **demande** 0 à 2 (autocomplétion YouTube, `suggest.py`, sur `demande_seeds`) ; **apprentissages** −1 à +1 (un levier qui a gagné ou perdu sur la chaîne, d'après `apprentissages.md` ; 0 tant qu'il n'y a pas assez de vidéos mesurées). Une valeur non mesurée (créneau, demande, preuve) **compte 0** et s'affiche avec « (?) » : une inconnue ne fait jamais monter une idée. Chaque idée affiche sa **confiance** (élevée : tout mesuré ; moyenne : une inconnue ; faible : deux ou plus) et son **maximum possible**. Si la grille écrit « classement non tranché », mesure ce qu'elle liste (`creneau`, `demande_seeds`) **avant** de recommander un gagnant. La grille ordonne, elle ne décide pas : si tu classes autrement, dis pourquoi.

## 4. `idees.md`

Écris `idees.md`, avec une section **« Vidéos de référence »** : la date de collecte, puis les 10 à 15 meilleurs outliers de `veille-resume.md` (titre exact, chaîne, multiple, vues, âge, vues par jour, lien, formule), la dynamique de ceux qui ont été revus, les chaînes découvertes et celles des références, et le tableau de la grille. `refs.json` est déjà écrit et la collecte déjà archivée par `veille.py`.

Croise avec `apprentissages.md` : si un levier a gagné plusieurs fois sur la chaîne, dis-le dans le classement des idées.

Limite à annoncer : ce sont des vues, pas de la rétention ni des volumes de recherche ; la demande vient de l'autocomplétion (des formulations, pas des volumes).
