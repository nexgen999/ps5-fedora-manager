# `ps5m/journal.py`

Persistent log, one timestamped line per event.

- Default path: `$XDG_STATE_HOME/ps5m-beta/manager.log`
  (`~/.local/state/ps5m-beta/manager.log`).
- `Journal(path)` accepts another file (used by tests).
- The last 2000 lines are re-read on startup.
- `write(message)`, `lines()`, `text()`, `clear()`.
- Any write error is swallowed and falls back to `/dev/null`: a full disk must
  not prevent installing.

`pages/logs.py` shows `journal.lines()` in a monospace block.
