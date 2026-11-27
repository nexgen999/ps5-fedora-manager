# `ps5m/journal.py`

Journal persistant, une ligne horodatée par événement.

- Emplacement par défaut : `$XDG_STATE_HOME/ps5m-beta/manager.log`
  (`~/.local/state/ps5m-beta/manager.log`).
- `Journal(path)` accepte un autre fichier (utilisé par les tests).
- 2000 dernières lignes relues au démarrage.
- `write(message)`, `lines()`, `text()`, `clear()`.
- Toute erreur d'écriture est ignorée et bascule sur `/dev/null` : un disque
  plein ne doit pas empêcher d'installer.

La page `pages/logs.py` affiche `journal.lines()` dans un bloc monospace.
