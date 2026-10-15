# Outils du dérushage (Windows, déjà installés)

Partie du skill derush-capcut, lue quand une commande ou un chemin d'outil est nécessaire (sortie de `SKILL.md` le 2026-10-07).

Racine : `<dépôt>\montage` (voir « Raccord » plus bas)

| Outil | Rôle |
|---|---|
| `07_OUTILS\capcut-bridge-windows\capcut_bridge.py` | piloter CapCut : `ls`, `state`, `unused`, `check`, `apply-cuts`, `restore`, `add-overlay`, `add-text`… (README à côté) |
| `08_HYPERFRAMES\scripts\takes_map.py <rush.mkv>…` | **carte des prises** : transcrit chaque bloc de voix séparément → `02_ANALYSE\prises\<rush>.txt` ; saute les blocs sans voix (son du jeu seul, VAD Silero), redécoupe aux pauses du VAD les blocs de plus de 20 s (commentaire en jouant, sinon Whisper tourne en boucle), retire les crédits « sous-titrage Société Radio-Canada »… |
| `08_HYPERFRAMES\scripts\verify_cuts.py <coupes.json>` | retranscrit chaque coupe et retire les mots en trop aux bords → `<coupes>.verifie.json` + rapport |
| `08_HYPERFRAMES\scripts\capcut_preview.py <draft_content.json> <début> <fin> <sortie.mp4>` | preview vidéo d'une plage de timeline sans ouvrir CapCut |

Transcription : whisper.cpp 1.9.2 + `ggml-large-v3-turbo-q5_0.bin` dans `08_HYPERFRAMES\.whisper\` (DTW `-nfa`). Détection de voix : `ggml-silero-v5.1.2.bin` (même dossier) via `whisper-vad-speech-segments.exe`, seulement pour trier les blocs ; jamais `--vad` dans `whisper-cli` (débuts de mots faux, reprises fusionnées).
Carte graphique : `.whisper\cuda\` (whisper.cpp 1.9.2 release cublas 12.4, PC fixe RTX, ~30 s de voix en 3 s) est
pris en premier, puis `.whisper\vulkan\`, puis le processeur. Si `08_HYPERFRAMES\.whisper\vulkan\whisper-cli.exe` existe (whisper.cpp 1.9.2 compilé avec Vulkan, puce graphique Intel Arc), tous les scripts le prennent : ~10x plus rapide sur secteur, mêmes débuts de mots (0,02 s près). Sur batterie, la puce est bridée : brancher le PC. `TSAR_WHISPER=cpu` force la version processeur.
Tous les scripts sont dans `08_HYPERFRAMES\scripts` (l'atelier ; Remotion est archivé).
Projets CapCut : `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<projet>\`.

