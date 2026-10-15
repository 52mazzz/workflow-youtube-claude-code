---
name: yt-script
description: >-
  Write a YouTube video script from a raw idea - hook options off 21
  formulas, scored, then the full spoken script with the retention beats
  marked. Use whenever the user wants a video script, a hook, an opening
  line, "what should I say", "write my next video", or is about to record
  and does not have the first fifteen seconds yet.
model: opus
effort: high
---

# yt-script

Une idée devient un script que le spectateur regarde jusqu'au bout.

Les outils de ce dossier tournent vraiment : on s'en sert, on ne juge pas une accroche à l'œil.

```bash
$PY ~/.claude/skills/yt-script/hookscore.py videos/<id>/script.md   # chaque ouverture « **Version X** » : notes, minutage, titre avant 6 s, tableau à coller
$PY ~/.claude/skills/yt-script/hookscore.py --hook "une phrase" --titre "le titre"   # une accroche seule
$PY ~/.claude/skills/yt-script/hookscore.py --profil solo <fichier>.md   # Short à une seule IA : défi, contrainte, 3 s
$PY ~/.claude/skills/yt-script/relecture.py videos/<id>/script.md   # le script entier : tableau à jour, minutage, beats, voix (code 1 = alerte)
$PY ~/.claude/skills/yt-script/minutage.py <fichier>.md             # le minutage seul (les Shorts : tableau « | 0-3 s | « … » | … | »)
$PY ~/.claude/skills/yt-script/hookscore.py --calibrer              # le scoreur face à nos vraies rétentions à 30 s
```

## Avant d'écrire

1. Lire `~/.claude/youtube/voice.md` : comment l'utilisateur parle face caméra, les mots qu'il n'emploie jamais, à qui il
   parle, ce qu'il n'affirme pas. S'il n'existe pas, demander **trois de ses vidéos**, les lire ou les transcrire, en
   déduire la voix et écrire le fichier. Un script dans la mauvaise voix est pire que pas de script : il doit le dire à
   voix haute.
2. N'inventer aucun chiffre, aucun résultat, aucune source. Si un chiffre manque, le demander ou écrire la phrase sans.

## La boucle

1. **Trois accroches** (cinq en parcours complet de nouvelle-video), sur des formules différentes de
   [hooks.json](hooks.json), écrites directement dans `script.md` en blocs `**Version X**` de lignes minutées
   (`- **0-3 s** [ON SCREEN : …] : « … »`) sur les créneaux de `nouvelle-video/references/accroches-script.md`
   (phase 4, « L'accroche, seconde par seconde », seule référence des créneaux).
2. `hookscore.py script.md`, corriger la propriété la plus faible et chaque ALERTE, relancer. Garder les deux meilleures,
   coller le tableau imprimé. Ne jamais rendre une seule accroche.
3. **Le corps**, beat par beat (ci-dessous).
4. `relecture.py script.md` jusqu'à zéro alerte : elle relance le scoreur (le tableau collé doit avoir les notes du
   jour), `minutage.py` sur chaque créneau, l'ordre des beats, l'image de chaque beat, le verdict et la voix. Ses
   « À VÉRIFIER » se tranchent au jugement et se disent à l'utilisateur.
5. Lire l'ouverture à voix haute, chronomètre en main.

## Une accroche qui tient (ce que le scoreur mesure, et pourquoi)

À 200 mots par minute (3,33 par seconde, le débit mesuré de la chaîne), la mission tient en 13 mots et l'ouverture en 50.

- **0-3 s** : le résultat le plus fort à l'image (`[ON SCREEN]` obligatoire, ni visage ni logo), et la mission dite avec
  les noms du titre (le jeu, le personnage, les deux IA) : un clic non confirmé avant 6 s s'en va (alerte « titre »).
- **3-6 s** : ce qui reste du titre, le duel nommé.
- **6-10 s** : la règle qui rend le duel lisible (« un seul prompt, aucune retouche ») : c'est ENJEU.
- **10-13 s** : une question sur une chose nommée (« lequel me donne un vrai Dismantle ? ») ou la promesse du moment
  fort (« et à la fin, le domaine ») : c'est CURIOSITY. Jamais le gagnant.
- **Ne pas écrire pour la note** : les mots-clés empilés, les chiffres en liste et les questions en rafale sont pénalisés,
  et une note haute n'est pas une prévision (`--calibrer` : garde-fou tant qu'il y a moins de 8 vidéos publiées). Entre
  deux versions proches, trancher sur la voix et les références, pas sur trois points.

## Le corps

L'ouverture confirme le titre, pose l'expérience et ouvre une question utile. Tout le script garde une voix naturelle :
`voice.md` et ses références documentées, du début à la fin.

1. **Le virage** (0:15-0:45). Dire en une phrase ce que la vidéo va faire, et commencer. Seulement les règles
   essentielles : les détails viennent pendant l'expérience, quand ils servent. Le prompt est montré et mis dans la
   description, pas lu en entier. Pas d'intro de chaîne, pas de « avant de commencer », pas d'appel à s'abonner. Une
   référence qui fait autrement ne prouve pas une perte d'audience sans ses données de rétention.
2. **Les beats.** Une idée par beat, chacun avec ce qui est À L'ÉCRAN (`[ON SCREEN : …]`), pas seulement ce qui est
   dit : une tête qui parle sans rien à regarder, c'est un podcast. Dire ce que le créateur veut vérifier, relier chaque
   observation à sa conséquence pour le joueur, motiver chaque transition par une question ou un résultat. Un avis
   personnel avec sa raison. Listes, critères et termes techniques permis quand ils servent ; pas de checklist récitée
   sans commentaire. Écrire les phrases-cadres ; laisser découvertes et réactions au tournage, en `[CROCHETS]`. Aucune
   hésitation, argot ou surprise inventés pour faire naturel. Jamais rallonger pour atteindre une durée.
3. **Le payoff.** Donner explicitement ce que l'accroche a promis, et dire qu'on le donne : « voilà le prompt, il est
   dans la description ». Le verdict dit sa raison (« parce que … »).
4. **La fin.** Une seule demande. Pas trois.

## Ce qu'on rend

- les deux meilleures accroches avec le tableau de `hookscore.py script.md`
- le script beat par beat, un `[ON SCREEN : ...]` sur chaque beat
- la sortie de `relecture.py` (zéro alerte ; les « À VÉRIFIER » dits tels quels), dont la durée écrite à 200 mots/min
- une ligne : la formule de l'accroche gagnante et pourquoi elle va à cette idée

## La porte

Rien ici ne publie : ce skill écrit, l'utilisateur publie. Chaque sortie finit par un bloc à copier, et la dernière
ligne est la question : **on garde, ou on change ?** (dans un run nouvelle-video, cette question attend la vérification
unique de fin de run : voir les points d'arrêt de `nouvelle-video/references/chaine.md`)
