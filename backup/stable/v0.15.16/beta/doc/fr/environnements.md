# Environnements de bureau

Chaque bureau a son module dans `ps5m/env/`. Les pages n'écrivent jamais
« GNOME » ou « KDE » : elles appellent `current().open_terminal(...)`,
`supports("accent")`, etc.

## Ce qui diffère

| Élément | Exemple GNOME | Pourquoi c'est isolé |
|---|---|---|
| terminal | `kgx --` | le nom change partout |
| gestionnaire de fichiers | `xdg-open` | parfois `nautilus`, `dolphin` |
| thème | `gsettings set … color-scheme` | KDE utilise ses propres outils |
| accent | `gsettings set … accent-color` | absent de certains bureaux |
| autostart | `~/.config/autostart` | variable selon le bureau |

## Capacités

`Environment.supports("accent")` renvoie `False` quand le bureau ne sait pas le
faire : une page peut alors masquer l'option au lieu d'afficher un bouton qui
échouerait.

## Tester

```bash
python3 beta/tools/selftest.py    # chaque bureau enregistré répond
```

`env.select("kde")` force un bureau pour une session de test, sans changer la
détection réelle.
