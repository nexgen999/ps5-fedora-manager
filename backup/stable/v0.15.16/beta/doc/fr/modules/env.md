# `ps5m/env/`

Tout ce qui change d'un environnement de bureau à l'autre.

## Contrat (`env/base.py`)

`Environment` est une dataclass figée : `id`, `name`, `terminal`,
`file_manager`, `settings_cli`, `autostart_dir`, `extra_env`.

| Méthode | Rôle |
|---|---|
| `open_terminal(command)` | commande pour lancer un terminal |
| `open_path(path)` | ouvrir un dossier |
| `set_theme_commands(dark)` | commandes de thème, `[]` si non géré |
| `set_accent_commands(accent)` | idem pour la couleur d'accent |
| `session_env()` | variables à transmettre |
| `supports(feature)` | `theme`, `accent`, `terminal` |
| `describe()` | dictionnaire lisible (page À propos) |

## Modules livrés

`gnome.py` (kgx + `gsettings`), `kde.py`, `cinnamon.py`, `budgie.py`,
`generic.py` (repli), `detect.py` (`registry`, `detect`, `current`, `select`).

## Détection

`detect()` regarde `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION` et `GDMSESSION`,
puis retombe sur l'environnement générique. `select(id)` force un bureau (utile
pour tester) et lève `KeyError` si l'identifiant est inconnu.

## Ajouter un bureau

1. `cp ps5m/env/generic.py ps5m/env/mate.py`, adapter `id`, `name`, terminal.
2. L'enregistrer dans `registry()` (`env/detect.py`).
3. Ajouter les mots-clés de détection en tête de `detect()`.
4. `python3 beta/tools/selftest.py` vérifie que `select()` et `supports()`
   répondent pour chaque bureau enregistré.
