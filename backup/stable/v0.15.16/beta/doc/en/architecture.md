# Architecture

## Layers

```
run.py                  entry point (python3 beta/run.py)
└── ps5m/
    ├── app.py          window, sidebar, live log
    ├── pages/          one page per need (generic or dedicated)
    ├── catalog.py      reads scripts, versions and updates
    ├── i18n.py         loads langs/*.json, English fallback
    ├── env/            what differs between desktops
    ├── runner.py       runs scripts (PTY, pkexec)
    ├── system.py       system state (rpm, paths)
    ├── journal.py      persistent log
    └── ui.py           badges, rows, text blocks
```

No module under `ps5m/` imports GTK except `app.py`, `pages/*` and `ui.py`:
catalog, languages, environments and the runner are testable without a display
(that is what `tools/selftest.py` does).

## Install flow

1. The page lists its section's addons (`catalog.load_local()`), sorted by
   `catalog.order()` so that `needs` come first.
2. The badge comes from `system.rpm_present()` and `system.path_present()`; its
   tooltip names what is missing.
3. A click opens the confirmation dialog (`BetaWindow.show_install_confirm`).
4. `pages/addons._install` calls `runner.run_script(path, emit, root=addon.root)`.
   When the addon declares `root: yes` and the app is not root, the command goes
   through `pkexec`: polkit asks for the password once.
5. Every output line goes to the journal (`journal.write`) and to the log window.
6. At the end, `refresh_addons_state()` re-reads the scripts, so badges update.

## Addon update flow

1. On startup a thread calls `catalog.fetch_index()`: the repository's
   `index.json`.
2. `catalog.pending()` compares versions (`1.10 > 1.9`) and returns only newer
   scripts.
3. The sidebar button calls `catalog.refresh()`: download, verify the published
   SHA-256, atomic write.
4. An up-to-date script is never rewritten: a local edit made without bumping
   the version is preserved.

## Tree

```
beta/
├── run.py · VERSION · README.md · CHANGELOG.md · TASKS.md
├── ps5m/        the code (see modules/)
├── addons/      one .sh per option + generated index.json
├── langs/       one .json per language
├── doc/fr/      French documentation
├── doc/en/      this documentation
└── tools/       build_catalog, check, lang_status, selftest, docs, new_addon
```

## Guarantees

- Nothing outside `beta/` is read or written by the application.
- No implicit `sudo`: only `pkexec`, and only for `root: yes` addons.
- `--check` never changes the system (read-only).
