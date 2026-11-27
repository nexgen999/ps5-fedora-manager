# `ps5m/catalog.py`

Lit les scripts de `addons/`, construit `index.json` et gère les mises à jour.

## `Addon`

Champs : `id`, `version`, `file`, `section`, `icon`, `titles`, `descriptions`,
`packages`, `needs`, `check_paths`, `action`, `root`, `sha256`, `path`.

Méthodes utiles : `title(lang)`, `description(lang)` (repli anglais puis
français), `to_dict()` / `from_dict()`.

## Fonctions

| Fonction | Rôle |
|---|---|
| `version_key(v)` | `"1.10.2"` → `(1, 10, 2)` |
| `parse_script(path)` | lit l'en-tête `#@` et calcule le SHA-256 |
| `load_local(dir)` | tous les scripts présents |
| `build_index(dir)` / `write_index(dir)` | catalogue à publier |
| `read_index(path)` | catalogue local ou téléchargé |
| `fetch_index(base_url)` | `index.json` du dépôt, sans rien écrire |
| `pending(local, remote)` | `(à télécharger, disparus)` |
| `refresh(dir, base_url)` | télécharge, vérifie, écrit |
| `order(addons)` | trie pour que `needs` passe avant ses dépendants |

## Contrat d'un script

`bash script.sh --check` renvoie 0 si l'option est déjà installée. Sans
`packages`, `check_paths` ni `action: yes`, `tools/check.py` refuse le greffon.
`root: yes` fait passer l'exécution par `pkexec` (voir `runner.md`).

## Mise à jour

`refresh()` ne remplace que les scripts dont la version a augmenté, vérifie le
SHA-256 annoncé dans l'index et écrit via un fichier `.tmp` renommé : une
coupure ne laisse pas de script à moitié écrit.

`REMOTE_BASE` pointe sur
`https://raw.githubusercontent.com/nexgen999/ps5-fedora-manager/main/beta/addons`.
