---
name: description-video
description: Écrire la description YouTube, les chapitres, les tags et la checklist de publication d'une vidéo de la chaîne @letsar555 une fois le montage exporté, à partir de videos/<id>/ (script, titres, résultats, montage final). À utiliser quand l'utilisateur dit "description", "fais la description", "chapitres", "c'est exporté", "prêt à publier", ou quand montage-capcut termine l'export.
model: sonnet
effort: low
---

# Description de la vidéo (étape 8 de la chaîne de production)

Réponds en français. Questions avec AskUserQuestion (cases à cocher), option recommandée en premier.

## 1. Retrouver la vidéo et lire tout ce qui précède

```bash
export PYTHONUTF8=1 PYTHONIOENCODING=utf8
PY=$(sh ~/.claude/skills/nouvelle-video/scripts/find_python.sh)
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py etat          # non poussé, bilans dus : à régler d'abord
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py list          # où en est chaque vidéo
$PY ~/.claude/skills/nouvelle-video/scripts/repo.py video "<titre ou id>"   # dossier de la vidéo existante
```

`repo.py video` retrouve la vidéo par son id ou par un de ses titres (en-tête de `suivi.md`, `titres.txt`) et **ne crée jamais de dossier** sans `--creer` : code 2 = plusieurs vidéos correspondent (demande laquelle avec AskUserQuestion), code 1 = aucune (vérifie avec `repo.py list`).

Dans `videos/<id>/`, lis : `suivi.md` (étapes faites, **écarts par rapport au plan**), `script.md`, `titres-miniatures.md` (titre principal, prompt exact donné aux IA), `resultats.md` (vainqueur, bugs, versions des modèles réellement utilisées), `refs-sujet.json`. Puis `~/.claude/youtube/preferences.md`.

Si le montage n'est pas exporté (étape 6 non cochée), le dire : les chapitres dépendent du montage final.

## 2. Les chapitres viennent du montage final, pas du script

Les coupes du montage décalent tout : un chapitre calé sur le script tombe faux. Prends les temps dans la transcription horodatée du montage final produite par montage-capcut : `montage/02_ANALYSE/vue_<projet - final>.txt` et `02_ANALYSE/transcriptions/capcut_<projet - final>.json`, à refaire sur le fixe après les dernières coupes (`capcut_timeline_audio.py` → `transcribe.ts` → `timeline_overview.py`, voir montage-capcut). Les textes `.txt`, `.json` et `.md` de `02_ANALYSE` sont suivis par git : les récupérer sur le portable avant d'écrire la description. Les pistes audio et médias de montage restent hors git sur le fixe. Si la transcription finale n'existe pas, demande-la avant d'écrire : ne devine pas un horodatage.
- Un chapitre par beat du script réellement présent dans le montage (un beat coupé au montage ne devient pas un chapitre ; voir les écarts de `suivi.md`).
- Titres de chapitres courts, concrets, dans la voix de la chaîne ; pas le résultat final dans un titre de chapitre avant la fin (ne pas spoiler le vainqueur).
- 0:00 en premier, au moins 3, au moins 10 secondes chacun.

## 3. Écrire `description.md`

Format attendu (le vérificateur lit ces deux sections) :

````markdown
# Description : <titre principal>

## Description
```text
<2 premières lignes : la promesse du titre, sans la répéter mot pour mot ; c'est ce qui s'affiche avant « plus »>

<le défi en 2 ou 3 phrases, le prompt exact donné aux IA, les versions réelles des modèles>

Chapitres
0:00 …
…

<une seule demande, la même que la fin du script>

#hashtag1 #hashtag2 #hashtag3
```

## Tags
```text
tag 1, tag 2, …
```

## Entités
```text
Claude Opus 5.5, ChatGPT 6, <le jeu>, <l'outil utilisé>, …
```

## Écran de fin et fiches
## Checklist de publication
````

Règles :
- **Ordre « promesse puis détails »** ; pas d'emoji ; le prompt exact et les versions des modèles ici (le titre n'en a pas, voir `preferences.md`).
- **Ne rien inventer** : versions, vainqueur, chiffres viennent de `resultats.md` et du montage. Ce qui manque reste entre crochets et le vérificateur le signale.
- **Mot-clé principal** : la formulation que les gens tapent (`suggest.py`), en général IA + jeu (« claude chatgpt pokemon »). Il est dans les **150 premiers caractères** (ce que lisent la recherche et l'aperçu avant « plus ») et c'est le **premier tag**. Méthode youtube-seo-skills (deeployCO, MIT).
- **Entités** : la section « Entités » (non collée dans Studio) liste les noms qui situent la vidéo pour YouTube : les IA et leurs versions réelles, le jeu, l'outil, le genre (« jeu d'horreur », « mod »). Chacun doit être cité, naturellement, dans la description ; le vérificateur signale ceux qui manquent. Pas de bourrage : une mention suffit.
- **Chapitres** : des titres qui disent ce qui s'y passe (« Claude plante au premier combat » plutôt que « Partie 2 »), sans révéler le vainqueur avant la fin.
- **Tags** (5 à 8) et vocabulaire : ce qui revient dans les titres de référence (`refs-sujet.json`) et dans les recherches tapées (`$PY ~/.claude/skills/youtube-titles-ab/suggest.py "<sujet>" --json`), en français, sans noms d'autres chaînes ni mots trompeurs.
- **Hashtags** : 3, le plus précis d'abord.
- **Écran de fin** : la vidéo suivante prévue dans `~/.claude/youtube/chaine.md` (skill chaine-youtube ; sinon la plus proche de la chaîne, à y noter) + abonnement, sur les 20 dernières secondes ; vérifier dans le montage que rien d'important n'est caché dessous.
- **Checklist** (5 lignes) : 3 paires chargées dans Test & Compare, miniature finale avec vraies captures, catégorie Jeux vidéo et langue française, sous-titres automatiques relus sur les noms propres (Claude, ChatGPT, nom du jeu), Shorts programmés après la vidéo.

Le sous-skill `metadata` du skill youtube peut servir de pense-bête, mais **ne régénère pas de titres** (le titre est celui de `titres-miniatures.md`) et ses règles anglaises ne remplacent pas celles de la chaîne.

## 4. Vérifier, puis passer la main

```bash
$PY ~/.claude/skills/description-video/check_description.py videos/<id>/description.md --duree <durée du montage final> --mot-cle "<mot-clé principal>"
```

**Code de sortie** : 1 = au moins une ERREUR (règle de YouTube ou de la chaîne, ou contrôle obligatoire impossible) : on corrige et on relance, on n'avance pas ; 0 = aucune erreur. Les « conseil » s'affichent sans bloquer : lis-les, suis-les ou dis pourquoi pas. L'absence de chapitres est une erreur (`--sans-chapitres` seulement si la vidéo n'en a vraiment pas). Coche l'étape 8 de `suivi.md`, puis envoie : `envoi.bat "<id> : description"` à la racine du dépôt (ou `git add -A && git commit -m "<id> : description" && git push`). Rappelle la suite : publication avec le skill publication-video (« publie <id> » ; en haut de `suivi.md` : « Statut : publiée », « Publiée le : AAAA-MM-JJ » et le lien ; c'est cette date qui déclenche les rappels de bilan de `repo.py etat` et de la tâche « Bilans dus » du portable), Shorts (montage-capcut), puis « bilan vidéo » à J+3/J+7. Termine par « On valide, ou on change quelque chose ? ».
