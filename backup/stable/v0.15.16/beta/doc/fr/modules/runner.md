# `ps5m/runner.py`

Exécution des scripts et des commandes courtes. Aucune dépendance GTK.

## `run_script(script, emit, args=(), root=False)`

Lance `bash script.sh [args]` derrière un pseudo-terminal : `dnf` et les
installateurs s'affichent ligne par ligne. Retourne le code de sortie.

Si `root=True` et que l'application n'est pas root, la commande devient
`pkexec bash script.sh` : polkit affiche sa propre demande de mot de passe.

## `check_script(script)`

Lance le script avec `--check` et renvoie `True` si le code est 0. Utilisé avant
d'installer pour éviter de relancer une option déjà en place.

## `run_command(command, timeout=30)`

Commande courte, sans terminal : retourne `(code, sortie)`. Sert aux lectures
d'état (`systemctl is-enabled`, `dnf --version`) et aux actions d'une page
(vérification des mises à jour).

## Règles

- Ne jamais appeler ces fonctions depuis le fil GTK : passer par
  `BetaWindow.run_task` ou `run_background`.
- `emit` est appelé depuis le fil de travail ; `app.py` le renvoie vers GTK avec
  `GLib.idle_add`.
