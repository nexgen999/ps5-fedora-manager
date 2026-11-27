# Tools

All scripts live in `beta/tools/` and run from the repository root.

| Command | Role |
|---|---|
| `python3 beta/tools/check.py` | headers, unique ids, valid `needs`, `bash -n`, index up to date, languages |
| `python3 beta/tools/selftest.py` | pure logic: versions, dependencies, index, languages, environments, paths, journal |
| `python3 beta/tools/build_catalog.py` | regenerate `addons/index.json` |
| `python3 beta/tools/build_catalog.py --check` | fail when the index is stale |
| `python3 beta/tools/lang_status.py` | per-language coverage |
| `python3 beta/tools/lang_status.py --missing xx` | keys missing from a language |
| `python3 beta/tools/docs.py` | regenerate `doc/{fr,en}/addons.md` |
| `python3 beta/tools/new_addon.py` | create an addon from a few options |

## Example: new addon

```bash
python3 beta/tools/new_addon.py --id app-htop --section library \
  --packages "htop" --title-en "htop" --title-fr "htop" \
  --desc-en "Process viewer." --desc-fr "Visionneuse de processus."
python3 beta/tools/build_catalog.py
python3 beta/tools/docs.py
python3 beta/tools/check.py
```

For an addon that installs nothing: `--body-file body.sh` with the script body
and `--check-paths /expected/path`.
