# Instructions pour une instance Claude Code : installer le workflow YouTube TSAR sur ce PC

Tu installes sur ce PC Windows le workflow YouTube de l'utilisateur (chaîne @letsar555 « tsar rouge555 »). Tout est dans le dépôt GitHub `https://github.com/52mazzz/workflow-youtube-claude-code` (copie publique, sans les données de la chaîne). Parle à l'utilisateur en **français simple**. Pose les questions avec AskUserQuestion (cases à cocher).

## Ce qu'il faut savoir avant de commencer

- **Deux PC, deux rôles.** Le **PC fixe** (RTX 3070 Ti) fait le tournage OBS, la transcription, le dérushage, le montage CapCut et l'export. Le **PC portable** sert aux idées, scripts, titres, descriptions et bilans, et accède au fixe à distance pour CapCut et la fenêtre Claude Code. Les comptes Claude sont différents : pas de Remote Control entre les deux, ni de montage hors connexion. Rushs et projets CapCut restent sur le fixe, **jamais dans git**.
- **Emplacement obligatoire du dépôt** sur chaque PC : `<Documents>\TSAR\Claude workflow youtube`, où `<Documents>` est le vrai dossier Documents (`[Environment]::GetFolderPath('MyDocuments')`). `setup.py` refuse de tourner ailleurs.
- **Le dépôt est la seule copie.** `setup.py` relie `~/.claude/skills/<skill>` et `~/.claude/youtube` aux dossiers du dépôt (jonctions Windows, sans droits admin). Ce qui existait déjà dans `~/.claude` est versé dans le dépôt ou sauvegardé dans `~/.claude/.sauvegarde-<date>/`, jamais supprimé.
- Le mode d'emploi détaillé du montage est dans `montage/WORKFLOW.md`, la vue d'ensemble dans `README.md`. Lis-les après le clonage.

## Règles à ne jamais enfreindre

1. Ne jamais modifier les rushs (`<Documents>\TSAR\Videos\<Nom de la vidéo>\Rush`, ou le dossier indiqué par `TSAR_RUSH`), ni les projets CapCut existants pendant l'installation. L'ancien dossier `<Documents>\TSAR\Rush` reste reconnu.
2. L'ancien dossier « Claude montage » n'est plus utile (la 0927 est publiée) : l'utilisateur a décidé de le supprimer. Ne le supprime pas toi-même : il l'envoie lui-même à la corbeille, après récupération de Whisper (étape 3).
3. Ne rien supprimer d'autre : les anciennes copies de `~/.claude` restent en place.
4. **Secrets** : ne jamais afficher, copier dans le chat ni commiter un fichier d'identifiants en clair (`youtube-credentials.json`, `client_secret*.json`, `youtube_client_secrets.json`, jeton OAuth). Seuls les fichiers `secrets/*.enc` (chiffrés) vont dans git. Ne demande jamais la passphrase du coffre dans le chat : l'utilisateur la tape lui-même dans son terminal.
5. Avant chaque commit demandé par l'utilisateur : `git status` ne doit montrer aucun `.mkv`, `.mp4`, `.mov`, `.wav` hors des dossiers `sfx` versionnés, ni `.whisper/`, ni `06_CAPCUT/`. Jamais de `git push --force`.
6. Les outils utiles au travail peuvent être installés depuis une source officielle : annoncer en une ligne quoi et pourquoi, et noter les prérequis ici. Les gros téléchargements (plus de quelques centaines de Mo) et logiciels lourds restent annoncés avant (voir `CLAUDE.md`).

## Étape 0 : questions à grouper si les réponses manquent

1. Ce PC est-il le **portable** (écriture et accès à distance) ou le **fixe** (tournage et montage) ?
2. Où est l'ancien dossier **« Claude montage »** (Whisper, musiques, `06_CAPCUT`) : sur ce PC, sur l'autre, ou nulle part ? Vérifie toi-même s'il existe dans `<Documents>\TSAR\Claude montage`.

## Étape 1 : prérequis

Vérifie (`where`, `--version`) : **Git**, **Python 3** (attention au faux `python` du Microsoft Store : tester `python -c "import sys"`, sinon `py`), et sur le fixe **Node 24** et **ffmpeg** dans le PATH. Le portable accède au fixe à distance.
- Git manquant : proposer `winget install Git.Git`, puis rouvrir le terminal. Configurer `git config --global user.name` et `user.email` avec ce que l'utilisateur donne.
- Au premier `git push`, Git Credential Manager ouvre le navigateur pour se connecter à GitHub. Prévenir l'utilisateur.

## Étape 2 : cloner au bon endroit et installer

```powershell
$docs = [Environment]::GetFolderPath('MyDocuments')
mkdir "$docs\TSAR" -Force
cd "$docs\TSAR"
git clone https://github.com/52mazzz/workflow-youtube-claude-code.git "Claude workflow youtube"   # si le dossier existe déjà : cd dedans, puis git pull
cd "Claude workflow youtube"
$repo = (Get-Location).Path
python setup.py --skip-secrets
```

Lis la sortie de `setup.py` et rapporte-la : skills et config « linked » ou « ok », liens redirigés depuis une ancienne copie, fichiers versés dans le dépôt (« added », « merged ») et fichiers sauvegardés. Si un dossier est « copied » au lieu de « linked », la jonction a échoué : le signaler.

**Coffre de secrets** : demande à l'utilisateur de taper lui-même, dans son propre terminal ouvert dans ce dossier :

```
python secrets_vault.py decrypt
```

(Il connaît la passphrase. La commande écrit la clé API, et si présents le client OAuth et le jeton, dans `~/.claude/`.) Vérifie d'abord que la commande réussit, puis lance `python secrets_vault.py status`, qui n'affiche aucun secret. Un `setup.py` lancé sans `--skip-secrets` propage l'échec du coffre et signale une installation incomplète ; les liens et dépendances déjà installés sont conservés. Corriger le problème puis relancer le déchiffrement dans le terminal de l'utilisateur.

## Étape 3 : fixe seulement, l'atelier de montage

Dans `montage\08_HYPERFRAMES` :

```powershell
npm install
npx --yes hyperframes@0.8.123 skills update
```

**Si « Claude montage » est encore sur ce PC**, récupérer Whisper (seul élément utile que git ne contient pas) avant de le supprimer :

```powershell
$old = "$docs\TSAR\Claude montage"
robocopy "$old\08_HYPERFRAMES\.whisper" "$repo\montage\08_HYPERFRAMES\.whisper" /E
```

(`robocopy` renvoie un code de 0 à 7 quand tout va bien.) Puis l'utilisateur l'envoie lui-même à la corbeille ; les projets CapCut de la 0927 perdent alors leurs médias : les supprimer dans CapCut.

**Si le fixe part de zéro**, installer CapCut Windows 9.5, FFmpeg, Node 24 et ImageMagick 7 (planches des rushs) ; `python -m pip install numpy` accélère la mesure du son de fond. Whisper et ses modèles sont hors git :
- version processeur whisper.cpp 1.9.2 (Release) dans `montage\08_HYPERFRAMES\.whisper\v1.9.2\Release\` ; `montage\sync_ressources.ps1 whisper`, lancé depuis la racine du dépôt, télécharge cette version et le modèle depuis les sources officielles ;
- modèle `ggml-large-v3-turbo-q5_0.bin` (environ 570 Mo) et VAD `ggml-silero-v5.1.2.bin` (Hugging Face `ggml-org/whisper-vad`) dans `montage\08_HYPERFRAMES\.whisper\` ;
- sur le fixe NVIDIA : `whisper-cublas-12.4.0-bin-x64.zip` (release v1.9.2 de `ggml-org/whisper.cpp`, environ 640 Mo), dossier `Release` extrait dans `.whisper\cuda\` ; les scripts prennent CUDA en premier, puis Vulkan si présent, puis le processeur (`TSAR_WHISPER=cpu` force ce dernier) ;
- FFmpeg avec NVENC et Hyperframes `0.8.123` (`npx --yes hyperframes@0.8.123 --version`). `TSAR_GPU=0` force le rendu et l'encodage sur le processeur.
- Séparation voix / musique (Demucs, installé le 2026-10-05 pour mesurer le montage de WOLF) : `python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128` (environ 3 Go, version carte graphique), puis `python -m pip install demucs soundfile`. Vérifier : `python -c "import torch; print(torch.cuda.is_available())"` doit afficher `True`. Sur la carte graphique, `htdemucs` sépare 18 min de son en ~26 s (plusieurs minutes au processeur). Le modèle (~80 Mo) se télécharge au premier usage.

Les musiques et bruitages sources sont déjà dans git (`montage/04_RESSOURCES/`, licences dans `LICENCES.md`). Puis, dans `montage\08_HYPERFRAMES` : `python scripts\get_fonts.py`, `python scripts\make_sfx.py`, `python scripts\make_compositions.py`.

**Rushs** : OBS les enregistre sur le fixe ; les ranger dans `Documents\TSAR\Videos\<Nom de la vidéo>\Rush` (un dossier par vidéo ; l'ancien `Documents\TSAR\Rush` reste lu). Si Documents est redirigé ou si les rushs vivent ailleurs, définir `TSAR_RUSH` vers le dossier de rushs de la vidéo, puis rouvrir le terminal. Le projet CapCut et `montage\06_CAPCUT\` restent sur ce PC, avec leurs chemins absolus ; ne pas les déplacer pour reprendre depuis le portable.

## Étape 4 : portable, écriture et accès au fixe

Le dépôt et `setup.py` suffisent pour les idées, scripts, titres, descriptions et bilans. L'analyse des miniatures est facultative (`python setup.py --vision`, gros téléchargement à annoncer). Configurer un accès à distance pour ouvrir CapCut et la fenêtre Claude Code du fixe à distance. Le portable n'a pas besoin de Whisper, de CapCut ni de `npm install` pour ce rôle. Mise à jour : `maj.bat`. Il n'y a pas de montage hors connexion.

## Étape 5 : statistiques YouTube (portable, une fois)

Le bilan après publication lit YouTube Analytics via OAuth.
1. `python secrets_vault.py status`. Si le client OAuth est déjà « on this machine », passer au point 3.
2. Sinon, le fichier `client_secret_….apps.googleusercontent.com.json` (type « Application de bureau ») doit être dans le dossier Téléchargements ou dans `~/.claude/`. S'il n'y est pas, demander à l'utilisateur de l'y mettre. Ne jamais l'ouvrir dans le chat.
3. Premier bilan, sur une vidéo publiée de la chaîne (PowerShell) : `python "$env:USERPROFILE\.claude\skills\bilan-video\scripts\bilan.py" <URL>`. Le navigateur s'ouvre : l'utilisateur se connecte avec le compte de la chaîne et accepte (« Application non validée » → « Paramètres avancés » → « Accéder à… » est normal pour un usage personnel). Le jeton est enregistré.
4. Demander à l'utilisateur de taper lui-même `python secrets_vault.py encrypt` (même passphrase), puis :
   `git add secrets && git commit -m "Identifiants YouTube chiffrés" && git push`, quand il demande l'envoi.

Bilans automatiques (fixe seulement, depuis le 2026-10-06) : le jeton OAuth doit aussi être sur le fixe (`python setup.py` le déchiffre). Dans l'app Claude du fixe, créer une tâche planifiée quotidienne (10 h) « Bilan automatique des vidéos TSAR » dont la consigne lance `skills/bilan-video/scripts/bilan_auto.py` (consigne complète : section « Bilans automatiques » du skill bilan-video). Le rappel en début de session vient de `.claude/settings.json` du dépôt : rien à installer.

Annonce des bilans dus (portable seulement, depuis le 2026-10-10) : dans l'app Claude du portable, tâche planifiée quotidienne (11 h) « Bilans dus » : lance `repo.py etat` en lecture seule et notifie les bilans dus de toutes les vidéos (consigne : section « Bilans automatiques » du skill bilan-video). Pas de rappel par vidéo.

## Étape 6 : vérifications

```powershell
Set-Location $repo
python -m unittest discover -s tests                                    # tous OK
python "$env:USERPROFILE\.claude\skills\nouvelle-video\scripts\repo.py" root   # doit afficher le dossier du dépôt
python "$env:USERPROFILE\.claude\skills\nouvelle-video\scripts\repo.py" list
```

Sur le fixe, en plus :
- `montage\08_HYPERFRAMES\.whisper\cuda\whisper-cli.exe` (ou la version processeur), le modèle et `ggml-silero-v5.1.2.bin` existent (sans ce dernier, `takes_map.py` transcrit aussi les blocs de jeu) ;
- `ffmpeg -version` répond ;
- le dossier des projets CapCut existe : `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\` ;
- dans `montage\08_HYPERFRAMES` : `npm run check`, puis examiner toute erreur avant un rendu. Le suivi de pokemon-ia note une erreur existante « Timeline did not advance under seek » sur la racine : elle ne doit pas être confondue avec une installation réussie sans erreur.

Sur le portable : vérifier l'accès à distance au fixe, à CapCut et à la fenêtre Claude Code.

S'il y a eu des fichiers « added » ou « merged » à l'étape 2 (ou de nouveaux fichiers chiffrés), vérifier `git status` (règle 5), puis les signaler à l'utilisateur pour son prochain envoi. Pas de commit ni de push sans sa demande (`CLAUDE.md`).

## Étape 7 : compte rendu à l'utilisateur

En français simple, court :
- quel PC, ce qui est installé et relié, ce qui a été recopié ;
- ce qui manque encore et ce qu'il doit faire lui-même (logiciels, fichiers, passphrase) ;
- rappeler l'usage :
  - « nouvelle vidéo » : idée, script, titres et miniatures ;
  - tournage, rushs, « dérushe <titre> » et « monte <titre> » sur le fixe ; accès à distance depuis le portable ;
  - « description » ;
  - « bilan vidéo » 3 à 7 jours après la sortie ;
  - mise à jour du dépôt : double-clic sur `maj.bat` ;
  - envoi des changements : double-clic sur `envoi.bat` (add, commit, pull, push ; refuse vidéos et fichiers de plus de 50 Mo) ;
  - ce qui attend (non poussé, bilans dus) : `python ~/.claude/skills/nouvelle-video/scripts/repo.py etat`.
- **Redémarrer Claude Code** (nouvelle conversation) pour que les skills reliés soient chargés.
