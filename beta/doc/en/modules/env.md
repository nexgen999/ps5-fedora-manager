# `ps5m/env/`

Everything that differs between desktop environments.

## Contract (`env/base.py`)

`Environment` is a frozen dataclass: `id`, `name`, `terminal`, `file_manager`,
`settings_cli`, `autostart_dir`, `extra_env`.

| Method | Role |
|---|---|
| `open_terminal(command)` | command that opens a terminal |
| `open_path(path)` | open a folder |
| `set_theme_commands(dark)` | theme commands, `[]` when unsupported |
| `set_accent_commands(accent)` | same for the accent colour |
| `session_env()` | variables to forward |
| `supports(feature)` | `theme`, `accent`, `terminal` |
| `describe()` | readable dict (About page) |

## Shipped modules

`gnome.py` (kgx + `gsettings`), `kde.py`, `cinnamon.py`, `budgie.py`,
`generic.py` (fallback), `detect.py` (`registry`, `detect`, `current`,
`select`).

## Detection

`detect()` looks at `XDG_CURRENT_DESKTOP`, `DESKTOP_SESSION` and `GDMSESSION`,
then falls back to the generic environment. `select(id)` forces a desktop (handy
for tests) and raises `KeyError` on an unknown id.

## Adding a desktop

1. `cp ps5m/env/generic.py ps5m/env/mate.py`, adjust `id`, `name`, terminal.
2. Register it in `registry()` (`env/detect.py`).
3. Add detection keywords at the top of `detect()`.
4. `python3 beta/tools/selftest.py` checks that `select()` and `supports()`
   answer for every registered desktop.
