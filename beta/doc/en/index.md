# Beta documentation (English)

The beta lives entirely inside `beta/`. It changes neither `ps5_manager.py`,
`install.sh` nor `version.txt`: the stable release keeps working while this
edition is being built.

## Run it

```bash
cd ps5-fedora-manager
python3 beta/run.py                 # interface
PS5M_LANG=en python3 beta/run.py    # force the starting language
```

## Where to start

| Document | Content |
|---|---|
| [architecture.md](architecture.md) | layers, install flow, tree |
| [modules/](modules/) | one document per Python module |
| [addons.md](addons.md) | **generated** reference of every addon |
| [languages.md](languages.md) | adding or fixing a language |
| [environments.md](environments.md) | GNOME, KDE, Cinnamon, Budgie, generic |
| [tools.md](tools.md) | checks and generators |
| [contributing.md](contributing.md) | adding an option, a page, a test |
| [../TASKS.md](../TASKS.md) | what is done, what is left |

## Three rules

1. **The stable release does not move.** No file outside `beta/` is modified.
2. **One option = one script.** `beta/addons/*.sh`, versioned, with `--check`.
3. **One language = one file.** `beta/langs/xx.json`, no code to write.
