# Code et outils — tactiques par cas

## Trouver du code

| Besoin | Fait | À éviter |
|---|---|---|
| Où est défini `X` ? | `Grep "def X\|class X\|function X"` en `files_with_matches` | lire les fichiers un par un |
| Combien d'usages ? | `Grep` en `count` | `content` sur tout le dépôt |
| Comprendre un module | lire l'index/exports + signatures (`grep -n "^def \|^class "`), puis la fonction utile | lire tout le dossier |
| Structure du projet | `Glob "src/**/*.ts"` ou `git ls-files \| head -100` | `ls -R`, `tree` sans profondeur |
| Question large (« comment marche l'auth ? ») | sous-agent `Explore`, ampleur « medium » | 30 lectures dans le contexte principal |
| Fichier minifié, lockfile, généré, vendored | ne pas le lire ; `grep` ciblé si vraiment nécessaire | `Read` complet |

Exclure du bruit des recherches : `node_modules`, `dist`, `build`, `.git`, `target`, `__pycache__`, `*.min.js`,
`*.lock`, `*.map` (`Grep` avec `glob: "!**/node_modules/**"` ou `rg --glob '!dist'`).

## Lire

- Gros fichier : `Grep -n` pour la ligne, puis `Read offset=ligne-20 limit=60`.
- Fichier inconnu : `wc -l` d'abord ; au-delà de ~300 lignes, lire par zones.
- Plusieurs fichiers indépendants : les lire dans le même message (parallèle).
- Notebooks : lire les cellules utiles ; les sorties d'images y coûtent cher.

## Shell : filtrer à la source

| Commande | Version économe |
|---|---|
| `npm install` / `pip install` | `npm install --silent 2>&1 \| tail -5`, `pip install -q` |
| Build | `... 2>&1 \| grep -iE "error\|warn" \| head -30` |
| Tests | `pytest -q --tb=short`, `pytest -x` (stop au 1er échec), `jest --silent`, `go test ./... 2>&1 \| grep -v "^ok"` |
| Un seul test | le lancer seul plutôt que toute la suite |
| `git status` / `log` / `diff` | `git status -s`, `git log --oneline -15`, `git diff --stat` puis `git diff fichier` |
| Logs | `tail -50`, `grep -n ERROR \| tail -20`, `Select-String ERROR \| Select-Object -Last 20` |
| JSON d'API | `curl -s ... \| jq '.items[] \| {id,name}' \| head -40` |
| Gradle / Maven | `--quiet` / `-q`, grep sur `FAILURE\|error:` |
| Serveur long / watcher | `run_in_background`, puis lire seulement les lignes d'erreur |
| Listing | `ls` du dossier visé, pas `Get-ChildItem -Recurse` |

PowerShell 5.1 : pas de `&&`, pas de `head`/`tail` → `; if ($?) {}`, `Select-Object -First N/-Last N`. Utiliser
l'outil Bash quand la commande est POSIX : une erreur de syntaxe coûte un tour entier.

## Éditer

- `Edit` avec un `old_string` court mais unique ; `replace_all` pour un renommage dans un fichier.
- Même changement dans beaucoup de fichiers : un `sed -i` / script, pas 40 `Edit`.
- `Write` seulement pour un fichier neuf ou une réécriture réelle.
- Ne pas relire après édition. Vérifier par l'exécution (test, build), pas par la relecture.

## Déboguer sans brûler de tokens

1. Reproduire avec la commande la plus petite possible, sortie filtrée.
2. Lire la pile d'appels : elle donne fichier + ligne → lecture ciblée.
3. Une hypothèse à la fois, testée par un `print`/log ciblé plutôt qu'en lisant tout le code autour.
4. Après 2 échecs sur la même piste, changer d'angle plutôt que d'insister.

## Revue de code

- `git diff --stat` d'abord, puis les fichiers à risque ; ignorer lockfiles et fichiers générés.
- Grosse PR : un sous-agent par zone, chacun rend seulement ses constats.

## Tâches répétitives

Écrire un script une fois plutôt que répéter 50 appels d'outils (conversion d'images, renommages, extraction de
données, génération de fichiers). Le script ne rend que le résumé (`OK 48 / échec 2 : a.png, b.png`).
