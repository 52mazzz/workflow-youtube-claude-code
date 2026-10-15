# Suivi : [TITRE PRINCIPAL]

- Id : `[id]` (id court, 2 ou 3 mots-clés du sujet, ex. `pokemon-ia` ; fixé en fin de phase 5 avec `repo.py id`, ne change plus)
- Statut : en cours (en cours | mis de côté | abandonnée | programmée | publiée | terminée)
- Publication visée : [AAAA-MM-JJ]
- Programmée pour : [AAAA-MM-JJ HH:MM Europe/Paris] (rempli quand la sortie est programmée dans Studio)
- Publiée le : [AAAA-MM-JJ]
- Lien : [https://youtu.be/…]
- Tournage : [AAAA-MM-JJ]
- Dossier montage : `montage/08_HYPERFRAMES/videos/[id]/` ; projet CapCut : `[id]` puis `[id] - final`
- Miniatures finales : `videos/[id]/miniatures/`

Chaque étape lit les fichiers des étapes précédentes de ce dossier, coche sa ligne, note ce qui a changé par rapport au plan, puis envoie (`envoi.bat`, ou commit et push) pour reprendre sur l'autre PC. `repo.py list` lit le statut et les dates ci-dessus ; `repo.py etat` annonce les bilans dus à partir de la sortie effective : « Publiée le », ou « Programmée pour » une fois la date passée (à confirmer).

- [ ] 1. Idée validée (nouvelle-video, phases 1-2) : `idees.md`, `refs.json`
- [ ] 2. Accroches et script (nouvelle-video, phases 3-4) : `script.md`
- [ ] 3. Titres et miniatures (nouvelle-video, phase 5) : `titres-miniatures.md` ; id fixé
- [ ] 3b. Préparation du tournage (nouvelle-video, fin de run, ou « prépare le tournage <id> ») : checklist « Avant » de `resultats.md` remplie (outil, versions, prompt prêt à coller, scènes OBS), `fiche-tournage.md` générée
- [ ] 4. Tournage sur le PC fixe (toi) : `resultats.md` rempli le jour même (vainqueur, versions, heures, nombre de rushs, bugs, captures), rushs rangés sur le fixe dans `Documents\TSAR\Videos\<Nom de la vidéo>\Rush`
- [ ] 5. Dérushage (derush-capcut) : prises choisies d'après `script.md`
- [ ] 6. Montage (montage-capcut) : suit `script.md` beat par beat ; écarts notés ci-dessous ; export 1080p60
- [ ] 7. Miniature finale (youtube-thumbnail-prompts) : avec les vraies captures, 3 paires prêtes pour Test & Compare, fichiers dans `miniatures/`
- [ ] 8. Description (description-video) : `description.md`, chapitres recalés sur le montage final
- [ ] 9. Publication (publication-video ; toi dans Studio) : checklist Studio, puis « Statut : publiée », « Publiée le » et le lien remplis en haut
- [ ] 10. Shorts (montage-capcut) : `shorts.md`
- [ ] 11. Bilan à J+3/J+7 (bilan-video) : ligne dans `apprentissages.md` et action pour la vidéo suivante
- [ ] 11b. Conseil après le bilan J+7 (conseil-workflow) : rapport dans `config/youtube/conseils/`, 1 à 3 changements adoptés dans `apprentissages.md`
- [ ] 12. Bilan à J+28 (bilan-video) : ligne de `apprentissages.md` mise à jour, Test & Compare terminé

## Écarts par rapport au plan
(une ligne par écart : étape, ce qui a changé, pourquoi. Ex. « montage : beat 4 coupé, l'IA n'a pas fini ; chapitre retiré de la description »)
