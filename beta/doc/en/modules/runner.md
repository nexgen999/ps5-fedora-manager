# `ps5m/runner.py`

Runs scripts and short commands. No GTK dependency.

## `run_script(script, emit, args=(), root=False)`

Runs `bash script.sh [args]` behind a pseudo-terminal so `dnf` and installers
stream line by line. Returns the exit code.

With `root=True` and a non-root app, the command becomes
`pkexec bash script.sh`: polkit shows its own password prompt.

## `check_script(script)`

Runs the script with `--check` and returns `True` on exit code 0. Used before
installing so an already-installed option is not run again.

## `run_command(command, timeout=30)`

Short command, no terminal: returns `(code, output)`. Used for state reads
(`systemctl is-enabled`, `dnf --version`) and page actions (update check).

## Rules

- Never call these from the GTK thread: use `BetaWindow.run_task` or
  `run_background`.
- `emit` is called from the worker thread; `app.py` forwards it to GTK with
  `GLib.idle_add`.
