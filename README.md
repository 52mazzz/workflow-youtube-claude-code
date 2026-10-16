# Workflow YouTube avec Claude Code

*[English version below](#english)*

Le workflow de production de la chaîne YouTube [@letsar555](https://www.youtube.com/@letsar555) (TSAR : IA et jeux
vidéo), construit avec Claude Code. De l'idée au bilan, chaque étape d'une vidéo a son skill, ses scripts et ses
contrôles. Le créateur parle à Claude (« nouvelle vidéo », « dérushe pokemon-ia », « bilan vidéo ») ; les skills savent
quoi lire, quoi écrire, et à quel moment s'arrêter pour lui demander son avis.

Ce dépôt est la copie publique et nettoyée du dépôt de travail, qui est privé (183 commits). Il garde la méthode et le
code. Les données de la chaîne, les identifiants et les médias sous droits n'y sont pas : voir
[Ce qui n'est pas publié](#ce-qui-nest-pas-publié).

| En chiffres | |
|---|---|
| Skills Claude Code | 14 publiés sur 18 : 11 écrits pour la chaîne, 3 adaptés de skills sous licence MIT |
| Agents | 6, en lecture seule |
| Scripts | 70 fichiers Python, environ 12 600 lignes, surtout en bibliothèque standard |
| Tests | 161, lancés par GitHub Actions sous Linux et Windows |
| Motion design | 36 éléments animés, rendus avec HyperFrames (HTML et GSAP) |

## Le pipeline en 12 étapes

Une vidéo, c'est un dossier `videos/<id>/` et un fichier `suivi.md` qui coche les étapes (modèle :
[`skills/nouvelle-video/templates/suivi.md`](skills/nouvelle-video/templates/suivi.md)). Chaque étape lit ce que les
précédentes ont écrit, et tout écart au plan y est noté.

| # | Étape | Skills, agents, scripts | Ce qui en sort |
|---|---|---|---|
| 1 | Idée : veille de la niche, puis choix avec le créateur | `nouvelle-video`, `yt-viral` (`veille.py` classe chaque vidéo par multiple de la médiane de sa chaîne) | `idees.md`, `refs.json` |
| 2 | Accroches et script | `nouvelle-video`, `yt-script` (`hookscore.py` note les accroches, puis `minutage.py` et `relecture.py`) | `script.md` |
| 3 | Titres et miniatures, en paires pour le Test & Compare de YouTube | `youtube-titles-ab` (`check_titles.py`, `suggest.py`), `youtube-thumbnail-prompts` | `titres-miniatures.md`, id de la vidéo |
| 3b | Préparation du tournage | `nouvelle-video` (`fiche.py`) | checklist de `resultats.md`, `fiche-tournage.md` pour le téléphone |
| 4 | Tournage, par le créateur (OBS, sur le PC fixe) | — | rushs, `resultats.md` rempli le jour même |
| 5 | Dérushage : la dernière prise complète de chaque phrase du script, coupée au mot près | `derush-capcut`, agent `trieur-prises` | projet CapCut dérushé |
| 6 | Montage en rendu direct | `montage-capcut`, kit de motion, agent `relecteur` avant l'export | MP4 final, 1080p à 60 i/s |
| 7 | Miniature finale | `youtube-thumbnail-prompts` (`miniature.py` : OpenCV et CLIP) | 3 paires titre et miniature |
| 8 | Description, chapitres calés sur le montage final, tags | `description-video` (`check_description.py`) | `description.md` |
| 9 | Publication : le créateur publie dans YouTube Studio | `publication-video`, agent `archiviste` | date et lien dans `suivi.md` |
| 10 | Shorts : choix de l'idée, puis montage vertical | `short`, `montage-capcut` | `shorts.md`, MP4 en 9:16 |
| 11 | Bilan à J+3 et J+7 : YouTube Analytics, chutes de rétention reliées au montage | `bilan-video` (`bilan.py`) | une ligne et une action dans `apprentissages.md` |
| 11b | Conseil : trois agents jugent tout le workflow, un juge garde 1 à 3 changements mesurables | `conseil-workflow`, agents `spectateur`, `producteur`, `analyste` | rapport du conseil |
| 12 | Bilan à J+28 et résultat du Test & Compare | `bilan-video` | ligne de `apprentissages.md` mise à jour |

Chaque mois, `chaine-youtube` fait l'audit de la chaîne : rythme, thèmes, grille des miniatures, playlists, sondage.
Le skill `economie-tokens` vaut pour toutes les sessions (voir [Garde-fous](#garde-fous)).

La boucle se ferme d'elle-même : les bilans (11 et 12) et le conseil (11b) écrivent dans `apprentissages.md`, que
l'étape 1 relit avant la vidéo suivante. Entre deux points d'arrêt fixés (choix de l'idée, validation du script, choix
des miniatures…), Claude enchaîne sans poser de question. La liste de ces points est dans
[`skills/nouvelle-video/references/chaine.md`](skills/nouvelle-video/references/chaine.md).

## Les agents

Six agents nommés, dans [`config/agents/`](config/agents/), tournent sur Sonnet avec seulement Read, Grep et Glob : ils
lisent et rendent un avis, ils n'écrivent rien.

| Agent | Appelé par | Rôle |
|---|---|---|
| `trieur-prises` | `derush-capcut`, étape 5 | lit les cartes de prises et le script, rend les prises retenues et les doutes |
| `relecteur` | `montage-capcut`, étape 6 | relit le montage fini contre le script, avec un regard qui ne l'a pas monté |
| `archiviste` | `publication-video`, étape 9 | propose un plan de rangement du dépôt, sans rien déplacer |
| `spectateur` | `conseil-workflow`, étape 11b | juge le sujet, le titre, la miniature, l'accroche et le rythme côté spectateur |
| `producteur` | `conseil-workflow`, étape 11b | cherche ce qui coûte du temps ou des crédits pour rien |
| `analyste` | `conseil-workflow`, étape 11b | part des vrais chiffres pour trouver le goulot et juger la boucle de mesure |

## L'Atelier

`atelier.bat`, ou `python atelier.py`, ouvre une page sur http://127.0.0.1:5555 : le tableau de bord du créateur. Elle
montre où en est chaque vidéo, ce qui est dû (bilans, publications pas notées, fichiers mal rangés), les fichiers d'une
vidéo (lus dans la page ou ouverts dans leur application) et l'état des deux PC, avec deux boutons : récupérer le
travail de l'autre PC, envoyer le sien. Pour l'étape suivante, elle donne la phrase à dire à Claude.

- Rien n'y est recopié : tout vient de `repo.py` (dans `skills/nouvelle-video/scripts/`) et de `rangement.py`.
- Un serveur de la bibliothèque standard (`http.server`) et une seule page HTML, sans dépendance (`atelier.html`).
- Il n'écoute que 127.0.0.1 et refuse tout autre en-tête Host (contre le DNS rebinding). Chaque action demande le jeton
  de la page servie, pour qu'un autre site ne puisse pas cliquer à la place du créateur. Il ne lit que des fichiers du
  dépôt, jamais `.git/` ni `secrets/`.

## Le kit de motion

[`montage/08_HYPERFRAMES/`](montage/08_HYPERFRAMES/) met le style de la chaîne en code, rendu avec
[HyperFrames](https://github.com/heygen-com/hyperframes) : des compositions HTML animées par GSAP, rendues en vidéo à
60 i/s.

- `kit/tsar.js` et `kit/tsar.css` : chaque élément est une fonction du temps, pilotée par une horloge GSAP en pause. Le
  rendu image par image tombe donc toujours juste.
- `compositions/` : 36 éléments générés par `scripts/make_compositions.py`, jamais écrits à la main : duel et VS,
  minuteur, étiquettes, cartes de note, score, captures zoomées, chapitres, frise de progression, réactions de la
  mascotte, sous-titres…
- Une vidéo tient en deux fichiers JSON, `videos/<id>/video.json` et `plan.json` (modèle : `videos/_modele/` ; exemple
  réel : `videos/_exemple-direction/`). On écrit des plans, on ne recode jamais une animation.
- `scripts/` : 44 scripts génériques, lancés avec l'id de la vidéo. Voix nettoyée (`voix.py`), zooms, transitions,
  musique et bruitages (`audio.py`, `musique.py`), sous-titres, puis `rendu.py`, qui lit la timeline dérushée de CapCut
  sans jamais l'ouvrir ni la modifier et sort le MP4 final. Avant la remise : `verifie_plan.py`, `synchro.py`,
  `revue.py`, `controle.py`, `dosage.py` (le montage compté minute par minute contre les cibles) et `variete.py`.
- `short.py` fait les Shorts verticaux (1080×1920) avec le même kit.

Mode d'emploi complet : [`montage/WORKFLOW.md`](montage/WORKFLOW.md) et le skill
[`montage-capcut`](skills/montage-capcut/SKILL.md).

## Garde-fous

- **Hooks Claude Code** ([`.claude/settings.json`](.claude/settings.json)) : au début d'une session, `repo.py etat` dit
  ce qui attend (travail pas envoyé, bilans dus) ; avant chaque écriture, `.claude/hooks/garde.py` vérifie l'emplacement
  et le nom du fichier.
- **Rangement** : `rangement.py` est la source unique des règles du dépôt (où va quoi, ce qui ne va jamais dans git,
  budget de taille des docs que Claude charge). Un test le fait tourner sur le dépôt lui-même.
- **Envoi** : `envoi.py` commite et pousse, mais refuse les vidéos, les fichiers de plus de 50 Mo, les secrets en clair
  et les caches.
- **Secrets** : `secrets_vault.py` chiffre les identifiants YouTube (Fernet, clé tirée d'une phrase de passe par
  PBKDF2-SHA256 en 600 000 tours). Les fichiers chiffrés ne sont pas dans cette copie.
- **Tokens** : le skill `economie-tokens` (20 réflexes et un audit chiffré du contexte, `audit_contexte.py`) et
  [`MODELES.md`](MODELES.md) (quel modèle et quel effort pour quelle tâche ; chaque skill fixe les siens dans son
  en-tête).
- **Tests** : `python -m unittest discover -s tests`, sans réseau.

## Arborescence

```
.claude/            hooks et réglages du projet Claude Code
.github/workflows/  tests sous Linux et Windows
config/agents/      les 6 agents
montage/            dérushage, montage, kit de motion (08_HYPERFRAMES), sons libres (04_RESSOURCES)
skills/             les 14 skills
tests/              les tests des scripts
atelier.*           le tableau de bord
rangement.py        les règles du dépôt ; envoi.py, setup.py, secrets_vault.py : l'outillage
CLAUDE.md           les consignes de Claude pour tout le dépôt
```

## Essayer

Il faut Python 3.9 ou plus récent ; FFmpeg et Node.js pour le montage.

```bash
python -m unittest discover -s tests     # les tests, sans réseau
python atelier.py                        # l'Atelier ; ici, aucune vidéo en cours
```

Le kit de motion (GSAP n'est pas inclus, la commande `curl` le télécharge) :

```bash
cd montage/08_HYPERFRAMES
curl -L --create-dirs -o assets/vendor/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js
npm run dev                              # aperçu HyperFrames des compositions
```

`setup.py` installe le workflow tel que le créateur s'en sert : il relie `~/.claude/skills/`, `~/.claude/youtube` et
`~/.claude/agents` à ce dossier. Pour essayer un seul skill, mieux vaut copier son dossier dans `~/.claude/skills/`.

## Ce qui n'est pas publié

- **Identifiants** : le coffre `secrets/` (clé API YouTube, client et jeton OAuth), même chiffré.
- **Données de la chaîne** : les dossiers des vidéos (`videos/` : idées, scripts, bilans avec les statistiques YouTube
  Analytics), `config/youtube/` (préférences, apprentissages, veilles, conseils), les transcriptions et les dérushs
  (`montage/02_ANALYSE/`) et les réglages de montage de chaque vidéo.
- **Médias sous droits ou de licence incertaine** : les musiques, les sons Pixabay et CapCut, des images d'anime
  (Jujutsu Kaisen), une image Pinterest, et les logos de Claude et de ChatGPT, remplacés par deux pastilles neutres.
- **Le pont CapCut** (`capcut_bridge.py`), adapté de [capcut-kit](https://github.com/matt-j-penny/capcut-kit), un dépôt
  sans licence : il reste à usage personnel. Le dérushage et la pose dans CapCut (dont `short_capcut.py`) passent par
  lui et ne marchent pas sans ; le rendu direct (`rendu.py`) lit le projet CapCut sans lui.
- **GSAP** (`assets/vendor/gsap.min.js`) : sa licence n'autorise pas clairement la redistribution. Voir
  [Essayer](#essayer).
- **Quatre skills** que le workflow appelle sans qu'ils soient publiés ici : `youtube` (claude-youtube, d'AgriciDaniel),
  `grilling`, `baoyu-youtube-transcript` (de JimLiu) et `nano-banana-pro-prompting`.

## Crédits

`yt-viral` et `yt-script` partent de skills de Jake Schincariol, `youtube-titles-ab` est adapté de yt-package (Jake
Schincariol) et de yt-title-optimizer (Sergey Bulaev), et plusieurs skills reprennent des méthodes de
youtube-seo-skills (Deeploy) : tous sous licence MIT. Polices sous SIL OFL 1.1, sons d'interface de Kenney en CC0.
Détail et textes des licences : [`CREDITS.md`](CREDITS.md).

## Licence

Le code est publié sous licence MIT (voir [`LICENSE`](LICENSE)). Les composants tiers gardent la leur (voir
[`CREDITS.md`](CREDITS.md)) et la mascotte Tsar reste la propriété de la chaîne.

---

<a id="english"></a>

# YouTube workflow with Claude Code (English)

The production workflow of the YouTube channel [@letsar555](https://www.youtube.com/@letsar555) (TSAR: AI and video
games), built with Claude Code. From the idea to the review, every step of a video has its skill, its scripts and its
checks. The creator talks to Claude ("nouvelle vidéo", "dérushe pokemon-ia", "bilan vidéo"); the skills know what to
read, what to write, and when to stop and ask for the creator's opinion. Skills, scripts and messages are in French.

This repository is the cleaned public copy of the working repository, which is private (183 commits). It keeps the
method and the code. The channel's data, the credentials and the copyrighted media are left out: see
[What is not published](#what-is-not-published).

| In numbers | |
|---|---|
| Claude Code skills | 14 published out of 18: 11 written for the channel, 3 adapted from MIT-licensed skills |
| Agents | 6, read-only |
| Scripts | 70 Python files, about 12,600 lines, mostly standard library |
| Tests | 161, run by GitHub Actions on Linux and Windows |
| Motion design | 36 animated elements, rendered with HyperFrames (HTML and GSAP) |

## The 12-step pipeline

A video is a `videos/<id>/` folder and a `suivi.md` file that ticks off the steps (template:
[`skills/nouvelle-video/templates/suivi.md`](skills/nouvelle-video/templates/suivi.md)). Each step reads what the
previous ones wrote, and any departure from the plan is recorded there.

| # | Step | Skills, agents, scripts | Output |
|---|---|---|---|
| 1 | Idea: research of the niche, then a choice with the creator | `nouvelle-video`, `yt-viral` (`veille.py` ranks each video by how many times it beat its channel's median) | `idees.md`, `refs.json` |
| 2 | Hooks and script | `nouvelle-video`, `yt-script` (`hookscore.py` scores the hooks, then `minutage.py` and `relecture.py`) | `script.md` |
| 3 | Titles and thumbnails, in pairs for YouTube's Test & Compare | `youtube-titles-ab` (`check_titles.py`, `suggest.py`), `youtube-thumbnail-prompts` | `titres-miniatures.md`, video id |
| 3b | Shoot preparation | `nouvelle-video` (`fiche.py`) | `resultats.md` checklist, `fiche-tournage.md` for the phone |
| 4 | Shoot, by the creator (OBS, on the desktop PC) | — | raw footage, `resultats.md` filled in the same day |
| 5 | Rough cut: the last complete take of each line of the script, cut to the word | `derush-capcut`, agent `trieur-prises` | rough-cut CapCut project |
| 6 | Edit, rendered directly | `montage-capcut`, motion kit, agent `relecteur` before export | final MP4, 1080p at 60 fps |
| 7 | Final thumbnail | `youtube-thumbnail-prompts` (`miniature.py`: OpenCV and CLIP) | 3 title and thumbnail pairs |
| 8 | Description, chapters matched to the final cut, tags | `description-video` (`check_description.py`) | `description.md` |
| 9 | Publication: the creator publishes in YouTube Studio | `publication-video`, agent `archiviste` | date and link in `suivi.md` |
| 10 | Shorts: choice of the idea, then a vertical edit | `short`, `montage-capcut` | `shorts.md`, 9:16 MP4 |
| 11 | Review at day 3 and day 7: YouTube Analytics, retention drops traced back to the edit | `bilan-video` (`bilan.py`) | a row and an action in `apprentissages.md` |
| 11b | Council: three agents judge the whole workflow, a judge keeps 1 to 3 measurable changes | `conseil-workflow`, agents `spectateur`, `producteur`, `analyste` | council report |
| 12 | Review at day 28 and Test & Compare result | `bilan-video` | updated row in `apprentissages.md` |

Every month, `chaine-youtube` audits the channel: pace, topics, thumbnail grid, playlists, poll. The `economie-tokens`
skill applies to every session (see [Safeguards](#safeguards)).

The loop closes by itself: the reviews (11 and 12) and the council (11b) write to `apprentissages.md`, which step 1
reads again before the next video. Between fixed stopping points (choice of the idea, approval of the script, choice of
the thumbnails…), Claude carries on without asking. The list of these points is in
[`skills/nouvelle-video/references/chaine.md`](skills/nouvelle-video/references/chaine.md).

## The agents

Six named agents, in [`config/agents/`](config/agents/), run on Sonnet with only Read, Grep and Glob: they read and
give an opinion, they never write.

| Agent | Called by | Role |
|---|---|---|
| `trieur-prises` | `derush-capcut`, step 5 | reads the take maps and the script, returns the takes to keep and the doubts |
| `relecteur` | `montage-capcut`, step 6 | checks the finished edit against the script, with eyes that did not edit it |
| `archiviste` | `publication-video`, step 9 | proposes a tidy-up plan for the repository, without moving anything |
| `spectateur` | `conseil-workflow`, step 11b | judges topic, title, thumbnail, hook and pace from the viewer's side |
| `producteur` | `conseil-workflow`, step 11b | looks for what costs time or credits for nothing |
| `analyste` | `conseil-workflow`, step 11b | starts from the real numbers to find the bottleneck and judge the measurement loop |

## The Atelier

`atelier.bat`, or `python atelier.py`, opens a page at http://127.0.0.1:5555: the creator's dashboard. It shows where
each video stands, what is due (reviews, publications not recorded, misplaced files), the files of a video (read in the
page or opened in their app) and the state of the two PCs, with two buttons: fetch the other PC's work, send this one's.
For the next step, it gives the sentence to say to Claude.

- Nothing is copied into it: everything comes from `repo.py` (in `skills/nouvelle-video/scripts/`) and `rangement.py`.
- A standard-library server (`http.server`) and a single HTML page with no dependency (`atelier.html`).
- It listens on 127.0.0.1 only and rejects any other Host header (against DNS rebinding). Every action needs the token
  of the page it served, so another website cannot click on the creator's behalf. It only reads files of the
  repository, never `.git/` or `secrets/`.

## The motion kit

[`montage/08_HYPERFRAMES/`](montage/08_HYPERFRAMES/) turns the channel's style into code, rendered with
[HyperFrames](https://github.com/heygen-com/hyperframes): HTML compositions animated with GSAP, rendered to video at
60 fps.

- `kit/tsar.js` and `kit/tsar.css`: each element is a function of time, driven by a paused GSAP clock, so a
  frame-by-frame render always lands right.
- `compositions/`: 36 elements generated by `scripts/make_compositions.py`, never written by hand: duel and VS, timer,
  labels, score cards, score, zoomed captures, chapters, progress timeline, mascot reactions, subtitles…
- A video fits in two JSON files, `videos/<id>/video.json` and `plan.json` (template: `videos/_modele/`; real example:
  `videos/_exemple-direction/`). You write plans, you never re-code an animation.
- `scripts/`: 44 generic scripts, run with the video id. Cleaned-up voice (`voix.py`), zooms, transitions, music and
  sound effects (`audio.py`, `musique.py`), subtitles, then `rendu.py`, which reads the rough-cut CapCut timeline
  without ever opening or changing it and outputs the final MP4. Before delivery: `verifie_plan.py`, `synchro.py`,
  `revue.py`, `controle.py`, `dosage.py` (the edit counted minute by minute against the targets) and `variete.py`.
- `short.py` makes the vertical Shorts (1080×1920) with the same kit.

Full guide, in French: [`montage/WORKFLOW.md`](montage/WORKFLOW.md) and the
[`montage-capcut`](skills/montage-capcut/SKILL.md) skill.

## Safeguards

- **Claude Code hooks** ([`.claude/settings.json`](.claude/settings.json)): at the start of a session,
  `repo.py etat` says what is waiting (work not sent, reviews due); before every write, `.claude/hooks/garde.py` checks
  the file's location and name.
- **Tidiness**: `rangement.py` is the single source of the repository's rules (what goes where, what never goes into
  git, size budget of the docs Claude loads). A test runs it on the repository itself.
- **Sending**: `envoi.py` commits and pushes, but refuses videos, files over 50 MB, plaintext secrets and caches.
- **Secrets**: `secrets_vault.py` encrypts the YouTube credentials (Fernet, key derived from a passphrase with
  PBKDF2-SHA256, 600,000 rounds). The encrypted files are not in this copy.
- **Tokens**: the `economie-tokens` skill (20 habits and a measured audit of the context, `audit_contexte.py`) and
  [`MODELES.md`](MODELES.md) (which model and which effort for which task; each skill sets its own in its header).
- **Tests**: `python -m unittest discover -s tests`, offline.

## Try it

You need Python 3.9 or later; FFmpeg and Node.js for the editing part.

```bash
python -m unittest discover -s tests     # the tests, offline
python atelier.py                        # the Atelier; here, no video in progress
```

The motion kit (GSAP is not included; the `curl` command downloads it):

```bash
cd montage/08_HYPERFRAMES
curl -L --create-dirs -o assets/vendor/gsap.min.js https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js
npm run dev                              # HyperFrames preview of the compositions
```

`setup.py` installs the workflow the way the creator uses it: it links `~/.claude/skills/`, `~/.claude/youtube` and
`~/.claude/agents` to this folder. To try a single skill, copy its folder into `~/.claude/skills/` instead.

## What is not published

- **Credentials**: the `secrets/` vault (YouTube API key, OAuth client and token), even encrypted.
- **The channel's data**: the video folders (`videos/`: ideas, scripts, reviews with YouTube Analytics statistics),
  `config/youtube/` (preferences, learnings, research, councils), the transcripts and rough cuts (`montage/02_ANALYSE/`)
  and the edit settings of each video.
- **Copyrighted media or media with an unclear license**: the music, the Pixabay and CapCut sounds, anime images
  (Jujutsu Kaisen), a Pinterest image, and the Claude and ChatGPT logos, replaced by two neutral discs.
- **The CapCut bridge** (`capcut_bridge.py`), adapted from [capcut-kit](https://github.com/matt-j-penny/capcut-kit), a
  repository without a license: it stays for personal use. The rough cut and the placement in CapCut (including
  `short_capcut.py`) go through it and do not work without it; the direct render (`rendu.py`) reads the CapCut project
  without it.
- **GSAP** (`assets/vendor/gsap.min.js`): its license does not clearly allow redistribution. See [Try it](#try-it).
- **Four skills** the workflow calls but that are not published here: `youtube` (claude-youtube, by AgriciDaniel),
  `grilling`, `baoyu-youtube-transcript` (by JimLiu) and `nano-banana-pro-prompting`.

## Credits

`yt-viral` and `yt-script` start from skills by Jake Schincariol, `youtube-titles-ab` is adapted from yt-package (Jake
Schincariol) and yt-title-optimizer (Sergey Bulaev), and several skills reuse methods from youtube-seo-skills
(Deeploy): all under the MIT license. Fonts under SIL OFL 1.1, interface sounds by Kenney under CC0. Details and
license texts: [`CREDITS.md`](CREDITS.md).

## License

The code is released under the MIT license (see [`LICENSE`](LICENSE)). Third-party components keep their own (see
[`CREDITS.md`](CREDITS.md)) and the Tsar mascot remains the property of the channel.
