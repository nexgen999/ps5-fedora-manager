# Desktop environments

Each desktop has its own module in `ps5m/env/`. Pages never say "GNOME" or
"KDE": they call `current().open_terminal(...)`, `supports("accent")`, and so
on.

## What differs

| Item | GNOME example | Why it is isolated |
|---|---|---|
| terminal | `kgx --` | the name changes everywhere |
| file manager | `xdg-open` | sometimes `nautilus`, `dolphin` |
| theme | `gsettings set … color-scheme` | KDE uses its own tools |
| accent | `gsettings set … accent-color` | missing on some desktops |
| autostart | `~/.config/autostart` | varies by desktop |

## Capabilities

`Environment.supports("accent")` returns `False` when the desktop cannot do it:
a page can then hide the option instead of showing a button that would fail.

## Testing

```bash
python3 beta/tools/selftest.py    # every registered desktop answers
```

`env.select("kde")` forces a desktop for one test session without changing real
detection.
