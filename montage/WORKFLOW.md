# Workflow montage TSAR

Le montage (dérushage → motion design → rendu → shorts) vit dans **le même dépôt** que les skills et la production.

**Deux PC** (fixe = atelier, portable = écriture) : rôles et règles dans `CLAUDE.md` § « Deux PC », source unique.

Les rushs, projets CapCut et médias rendus restent sur le fixe, hors git. Le savoir-faire, les textes d'analyse, les réglages, les musiques et bruitages sources sont partagés par git.

```
PC fixe : OBS → rushs .mkv
   │  ranger localement
   ▼
PC fixe : Documents\TSAR\Videos\<Nom de la vidéo>\Rush (ou TSAR_RUSH), lecture seule, hors dépôt
   │  skill derush-capcut   ← suit videos/<id>/script.md
   ▼
Projet CapCut « <id> » (dérushé ; seulement lu ensuite)
   │  skill montage-capcut  (+ kit Hyperframes dans montage/08_HYPERFRAMES)
   ▼
Transcription → video.json + plan.json → scripts → contrôles → rendu.py (MP4 final 1080p60)
   │
   ▼
Description (skill description-video) → publication → shorts 9:16
```

Principe : **on écrit des plans JSON, on ne recode jamais d'animation, on ne copie jamais un script.** Ce qui change d'une vidéo à l'autre est dans `montage/08_HYPERFRAMES/videos/<id>/video.json` + `plan.json`.

L'**id** d'une vidéo est court : 2 ou 3 mots-clés du sujet (ex. `pokemon-ia`), fixé par nouvelle-video (`python ~/.claude/skills/nouvelle-video/scripts/repo.py id pokemon ia`). Le même id nomme `videos/<id>/` (idée, script, titres, résultats, description), `montage/08_HYPERFRAMES/videos/<id>/` et le projet CapCut `<id>` / `<id> - final`.

## 1. Où sont les choses dans le dépôt

| Dossier du dépôt | Contenu |
|---|---|
| `skills/derush-capcut/`, `skills/montage-capcut/` | les deux skills personnels (avec `references/preferences.md`, `outils.md`, `capcut-technique.md`) |
| `skills/nouvelle-video/`, `skills/description-video/`, `skills/bilan-video/` | avant et après le montage |
| `videos/<id>/` | production de la vidéo : `script.md`, `titres-miniatures.md`, `resultats.md`, `description.md`, `suivi.md` |
| `montage/08_HYPERFRAMES/` | l'atelier (scripts, kit, compositions, `videos/<id>/`, `package.json`, `hyperframes.json`) |
| `montage/07_OUTILS/capcut-bridge-windows/` | pilotage de CapCut |
| `montage/04_RESSOURCES/LICENCES.md` | traçabilité des licences des musiques, bruitages et images (musiques et SFX sources versionnés) |
| `config/youtube/` | préférences de la chaîne, apprentissages, mascotte |

Ignorés par git (voir `.gitignore`) : `.whisper/` (567 Mo), `assets/shorts/`, `build/`, `renders/`, `node_modules/`, `06_CAPCUT/`, `02_ANALYSE/` (sauf ses textes `.txt` `.json` `.md` : transcriptions, prises, coupes, partagés entre les deux PC), `05_EXPORTS/`, `01_RUSHS/`, images, et tous les `*.mp4 *.mkv *.mov` (les `*.wav` aussi, sauf ceux des dossiers `sfx`, versionnés). Les musiques et SFX sont, eux, dans git. Un fichier précis à versionner malgré tout : `git add -f`.

Les skills officiels Hyperframes (`hyperframes`, `hyperframes-core`, …) ne sont pas versionnés : `npx hyperframes skills update` les réinstalle.

**Les préférences ne se modifient que dans le dépôt.** `setup.py` relie `~/.claude/skills/<skill>` et `~/.claude/youtube` aux dossiers du dépôt (lien ou jonction Windows) : une préférence ajoutée par un skill est écrite dans le dépôt et part au prochain envoi.

## 2. PC fixe (tournage et montage) : mise en place

L'atelier et les deux skills sont déjà dans le dépôt. Sur le fixe :

```powershell
winget install Git.Git                     # une fois, puis rouvrir le terminal
git config --global user.name  "<ton nom>"
git config --global user.email "<ton e-mail>"

mkdir "$([Environment]::GetFolderPath('MyDocuments'))\TSAR" -Force
cd "$([Environment]::GetFolderPath('MyDocuments'))\TSAR"      # PowerShell
git clone https://github.com/52mazzz/workflow-youtube-claude-code.git "Claude workflow youtube"
cd "Claude workflow youtube"
python setup.py                            # relie skills et config au dépôt (anciennes copies sauvegardées)
cd montage\08_HYPERFRAMES
npm install
npx --yes hyperframes@0.8.123 skills update
```

**Musiques et bruitages** : ils sont dans le dépôt (`montage/04_RESSOURCES/musiques` et `sfx`), donc un `git pull` les amène. Les musiques ne sont pas dans la copie publique (voir `04_RESSOURCES/LICENCES.md`). Seuls les morceaux de `musiques/perso/` servent : les siens et ceux trouvés (StreamBeats, Pixabay) qu'il a gardés après écoute ; `musiques/a_ecouter/` (candidats pas encore écoutés) reste sur le PC qui a cherché (hors git). Choix et recherche : `08_HYPERFRAMES/scripts/musique.py`, fiches dans `musiques/catalogue.json` (règle du 2026-10-08). Les licences et sources connues sont dans `LICENCES.md`.

**Whisper** (modèle d'environ 570 Mo, hors git) : sur le fixe, depuis la racine du dépôt, `.\montage\sync_ressources.ps1 whisper` télécharge la version processeur depuis les sources officielles (whisper.cpp v1.9.2 + modèle Hugging Face). Le script sait aussi récupérer une ancienne installation par clé USB ou Drive : `export E:\` sur le PC source, `import E:\` sur le fixe (il ne supprime rien et n'écrase pas un fichier plus récent). Ce transfert de ressources sert à l'installation ; les rushs restent sur le fixe.

**Si le fixe part de zéro**, installer Python 3, Node 24, FFmpeg avec NVENC, ImageMagick 7 (planches des rushs) et CapCut Windows 9.5. Ajouter `numpy` pour accélérer la mesure du son de fond. Sur la RTX, whisper.cpp 1.9.2 release cublas 12.4 va dans `.whisper\cuda\` ; la version processeur reste dans `.whisper\v1.9.2\Release\`. Le modèle `ggml-large-v3-turbo-q5_0.bin` et le VAD `ggml-silero-v5.1.2.bin` vont dans `.whisper\`. Les scripts prennent CUDA, puis Vulkan si présent, puis le processeur ; `TSAR_WHISPER=cpu` force le processeur, `TSAR_GPU=0` désactive l'accélération du rendu et de l'encodage. Sources et tailles des téléchargements : `INSTALLATION_CLAUDE.md`, étape 3. Puis, dans `montage\08_HYPERFRAMES` : `python scripts\get_fonts.py`, `python scripts\make_sfx.py`, `python scripts\make_compositions.py`.


## 3. PC portable : écriture et accès à distance

Installer le dépôt dans `Documents\TSAR\Claude workflow youtube`, puis lancer `python setup.py` pour les skills, la configuration et les outils d'écriture/bilan. Double-cliquer `maj.bat` avant de reprendre le travail envoyé depuis le fixe. Configurer un accès à distance pour accéder à CapCut et à la fenêtre Claude Code du fixe ; le projet CapCut et `06_CAPCUT/` restent sur le fixe, car ils contiennent des chemins absolus. Le portable n'a pas besoin de Whisper, de CapCut ni de `npm install` pour ce rôle. L'analyse des miniatures (`setup.py --vision`) est facultative.

## 4. Du tournage au dérushage, sur le fixe

1. Après le tournage, ranger **tous les rushs de la session** dans `Documents\TSAR\Videos\<Nom de la vidéo>\Rush` sur le fixe (ex. `Videos\Pokemon IA\Rush`, `.mkv` ou `.mp4`), sans les renommer (le nom date-heure sert à les retrouver et à les ordonner). OBS peut enregistrer directement dans ce dossier. Si les rushs vivent ailleurs ou si Documents est redirigé, définir `TSAR_RUSH` vers le dossier de rushs de cette vidéo, puis rouvrir le terminal. Vérifier que chaque enregistrement ou copie locale est terminé avant le dérushage.
2. Noter dans `videos/<id>/resultats.md` (ou le dire au chat) le vainqueur, les bugs et l'heure de début et de fin du tournage : le dérushage s'en sert pour vérifier qu'il ne manque aucun rush.
3. Importer les rushs dans le projet CapCut du fixe, puis « dérushe <titre> » dans sa session Claude Code (accessible à distance depuis le portable).

## Au quotidien

Une conversation Claude Code par vidéo, ouverte **à la racine du dépôt** ; les commandes du montage s'exécutent sur le fixe. Depuis `montage\08_HYPERFRAMES`, lancer `python scripts\<script>.py <id>` (ou `python <script>.py <id>` depuis `scripts`). Le portable synchronise les livrables d'écriture par git et pilote le montage à distance.

```bash
maj.bat                                      # ou : python setup.py --pull
# … dérushage / montage …
envoi.bat "<id> : montage + nouvelle préférence sous-titres"  # quand l'utilisateur demande l'envoi
```

Rythme : un envoi par étape à la demande de l'utilisateur (`videos/<id>/`, `montage/08_HYPERFRAMES/videos/<id>/`, évolutions du kit, préférences). Le push sauvegarde les fichiers suivis et les partage entre les PC ; les rushs, projets CapCut et rendus restent hors git sur le fixe.

## 5. Le montage, étape par étape

La méthode vit dans les skills (source unique, ne pas la recopier ici) :
- **Dérushage** (étape 5) : skill `derush-capcut`, « dérushe <id> ». Dernière prise complète de chaque phrase du script, coupes posées dans le projet CapCut `<id>`.
- **Montage** (étape 6) : skill `montage-capcut`, « monte <id> ». **Rendu direct** depuis le 2026-10-08 : `video.json` + `plan.json`, scripts de l'atelier, `rendu.py` sort le MP4 final 1080p60 ; CapCut seulement lu. Une seule remise, après `verifie_plan`, `synchro`, `revue`, `controle`, `dosage` et l'agent `relecteur` (SKILL.md § Livrable unique).
- **Fin de vidéo** : skill `description-video` (chapitres calés sur la transcription du montage final), puis `publication-video`.
- **Shorts** : idée avec le skill `short`, montage avec la direction en vertical (`montage-capcut` § Fin de vidéo, shorts ; Short indépendant : § Short indépendant). Idées dans `config/youtube/idees-shorts.md`.
- **Besoin que le kit ne couvre pas** : un type réutilisable dans `kit/tsar.js` + `SPECS` de `make_compositions.py`, avec les skills officiels Hyperframes (`08_HYPERFRAMES/AGENTS.md`). Ne jamais éditer `compositions/*.html` à la main.

## 6. Règles à ne jamais enfreindre

1. Ne jamais toucher aux rushs ni au projet CapCut d'origine : travailler sur la copie « - final ».
2. CapCut ouvert = aucune écriture.
3. Ménage : ne jamais supprimer un fichier cité dans `draft_content.json` **ou** `draft_meta_info.json` ; corbeille seulement.
4. Téléchargements : annoncer quoi / d'où / taille (« prends du Pixabay » vaut accord).
5. Honnêteté : l'IA n'écoute pas l'audio, elle mesure (LUFS, silences) et retranscrit.
6. Économie de crédits : kit d'abord, scripts génériques, lire peu, rendus ciblés, tâches longues en arrière-plan, `/compact` après une grosse phase, `/clear` entre deux vidéos.
7. Avant chaque `git push` demandé par l'utilisateur : `git status` ne montre aucun `.mkv`, `.mp4`, `.mov`, `.wav` hors des dossiers `sfx` versionnés, ni `.whisper/`, ni `06_CAPCUT/`. `envoi.bat` refuse les vidéos et fichiers de plus de 50 Mo ; jamais de push forcé.
