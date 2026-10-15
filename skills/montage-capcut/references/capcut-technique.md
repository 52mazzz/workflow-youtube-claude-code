# CapCut 9.5 Windows — ce qui a été vérifié (évite de refaire les tests)

Depuis le 2026-10-08, le montage sort en **rendu direct** (`rendu.py`) : CapCut ne sert plus qu'au dérush (le projet est
lu, `duplicate` et `cut-range` seulement). Ce qui suit vaut pour le dérush et pour l'option « poser dans CapCut » s'il
veut retoucher à la main.

- Projets : `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<projet>\` — `draft_content.json` (timeline,
  temps en µs, projet 30 i/s), `draft_meta_info.json` (**panneau Médias** : `draft_materials[].value[].file_Path`),
  `root_meta_info.json` (liste des projets, dossier parent). Cache `Timelines\` : déplacé par le bridge à chaque
  écriture, sinon CapCut ignore le JSON.
- **Transparence** : WebM VP9 alpha = **rectangle noir** ; **MOV QuickTime Animation (qtrle, argb)** ou MOV PNG = OK ;
  PNG fixe = OK. → overlays en MOV qtrle (60 i/s depuis Hyperframes : son MOV ProRes 4444 est converti en qtrle ;
  ProRes 4444 direct dans CapCut non testé), scènes en MP4 H.264.
- **Pas de lueur colorée semi-transparente** (`boxShadow` coloré, glow) sur les overlays : dans CapCut elle devient
  un gros halo rose/rouge baveux. Ombres **noires** uniquement (`rgba(0,0,0,0.4–0.5)`) ; les lueurs colorées
  restent possibles dans les scènes MP4 (fond opaque).
- **Export** : bouton « Exporter » (haut droite). Les menus déroulants se ferment si on refait `focus()` (touche ALT)
  → enchaîner clic + capture sans refocus (script `ui.py` : clics puis gdigrab). Choisir 1080P, débit « Plus
  haut », H.264, mp4, 60fps, flux optique désactivé. Sortie par défaut : `Documents\Infinity Maker\<projet>.mp4`
  (~1 Go pour 7 min 46). Suivre la fin par la taille du fichier, pas par des captures (il peut utiliser le PC).
- **Pas d'arbre d'accessibilité** (UI Automation vide) : pilotage écran = capture + clics aux coordonnées.
  Fermer l'éditeur ramène à l'accueil : `quit` boucle WM_CLOSE jusqu'à la sortie.
- **Pistes** : flag 0 principale, 1 texte, 2 overlay ; clip vidéo = matériau + 6 annexes (speeds, placeholder_infos,
  canvases, sound_channel_mappings, material_colors, vocal_separations). Audio local = modèle
  `audio_template.json` (type `extract_music`, annexes speeds/placeholder_infos/beats/sound_channel_mappings/
  vocal_separations ; `loudnesses` non reprise).
- **Position** : `clip.transform.x/y`, 0 = centre, ±1 = bord ; **+y = haut**. Zoom cadré sur un point (fx, fy en
  0..1 depuis le haut gauche) : `d = (2fx−1, 1−2fy)`, `T = clamp(−d·S, ±(S−1))` → jamais de bord visible.
- **Keyframes** (`common_keyframes`, `time_offset` sur la **source** du clip) : adoucies = `FreeCurveOut` au départ
  (right_control.x > 0), `FreeCurveIn` à l'arrivée (left_control.x < 0), `FreeCurveInOut` au milieu, y = 0,
  poignées ≈ 1/3 de l'intervalle en µs. `Line` = linéaire (refusé par l'utilisateur).
- **Volume** : `segment.volume` (1.0 = 0 dB) ; couper le son d'un clip principal = 0.0 (clip combiné sans chemin :
  le laisser).
- **Média manquant** au chargement → fenêtre « Relier des fichiers multimédia » : vient souvent du **panneau
  Médias** (meta), pas de la timeline. Régénérer le fichier ou retirer l'entrée de `draft_meta_info.json`
  (sauvegarde avant).
- Réécrire un fichier à la **même durée** sous le même nom met à jour le projet sans le toucher (CapCut fermé,
  sinon le fichier est verrouillé).
- Whisper (DTW) : débuts de mots ~0,12 s en retard, fins peu fiables ; parfois **tous les mots d'une phrase au
  même instant** → ne pas sous-titrer ce passage. Noms propres mal transcrits (Claude → « Cloud »).
- Pièges vus : `restore` doit respecter `--no-relaunch` (corrigé) ; échappement PowerShell des backticks dans du
  TS/JS (écrire le code avec l'outil Write/Edit, pas via des remplacements PowerShell) ; `ffmpeg -/filter_complex
  <fichier>` (FFmpeg 7+) pour les gros graphes.
