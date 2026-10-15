# Configuration de l'accès YouTube Analytics (une seule fois)

Partie du skill bilan-video (section 6), lue seulement quand `bilan.py` dit que l'accès OAuth manque.

**Si les fichiers existent déjà sur une machine** (ils sont ignorés par git, donc absents du dépôt) : dans le dépôt, `python secrets_vault.py status` montre où ils sont trouvés (`~/.claude/`, le dossier du dépôt, ou le nom de téléchargement Google `client_secret_….json`). Puis `python secrets_vault.py encrypt` les chiffre dans `secrets/` (clé API, client OAuth et jeton) et les copie là où les scripts les lisent ; commit et push, et `python setup.py` les déchiffre sur les autres machines. Avec le jeton chiffré, l'autre machine n'a pas besoin de se reconnecter dans le navigateur.

Sinon, les statistiques privées passent par OAuth, sur le compte Google qui possède la chaîne :
1. Google Cloud Console → le projet de la clé API existante → « API et services » → activer **YouTube Analytics API** et **YouTube Data API v3**.
2. « Écran de consentement OAuth » : type Externe, ajouter son adresse en utilisateur test, puis **publier l'application** (« En production »). En mode Test, l'autorisation expire au bout de 7 jours. Pour un usage personnel, l'avertissement « application non validée » à la première connexion est normal.
3. « Identifiants » → Créer → ID client OAuth → **Application de bureau** → télécharger le JSON et l'enregistrer sous `~/.claude/youtube_client_secrets.json`.
4. Chiffrer pour le dépôt : `python secrets_vault.py encrypt`, puis commit et push. Les autres machines le récupèrent avec `python setup.py`.
5. Premier lancement de `bilan.py` : le navigateur s'ouvre pour autoriser la lecture seule ; le jeton est gardé dans `~/.claude/.tmp/`.

Le script ne lit que les statistiques (lecture seule) et ne publie rien.
