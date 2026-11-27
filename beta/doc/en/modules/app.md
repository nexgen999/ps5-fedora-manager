# `ps5m/app.py`

Main window and orchestration. It is the only module that knows about pages,
the catalog and the journal at once.

## Classes

### `BetaWindow`

| Member | Role |
|---|---|
| `self.addons` | local catalog, re-read by `refresh_addons_state()` |
| `self.language` | active language code |
| `self.journal` | `Journal` shared by the session |
| `section_ids()` | visible sections (dedicated page or at least one addon) |
| `go_to(ident)` | open a section from an internal link |
| `set_language(code)` | switch language and rebuild the sidebar |
| `show_install_confirm(addon, fn)` | Confirm/Cancel dialog |
| `run_task(title, task)` | long task with a log window |
| `run_background(task, done)` | short action (service switch) |
| `refresh_addons()` | download newer addons |

`task` has the shape `task(emit) -> (ok: bool, message: str)`. `emit` writes to
the journal and the log window; the task runs in a thread so the UI never
freezes.

### `LogWindow`

Modal window with a monospace `Gtk.TextView`. `emit(line)` appends a line and
scrolls to the bottom.

## Rules

- Never pass user text through Pango markup: `&` breaks rendering
  ("FX Sound & Vidéo"). Use `ui.plain_row`.
- Never block the GTK thread: every command goes through `run_task` or
  `run_background`.
- A new section must be listed in `pages.ORDER` and, if it has its own icon, in
  `SECTION_ICONS`.
