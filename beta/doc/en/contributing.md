# Contributing to the beta

## Adding an option

1. `tools/new_addon.py` (or copy a sibling script).
2. Fill the header: `id`, `version`, `section`, `title`/`title_fr`,
   `desc`/`desc_fr`, `packages` or `check_paths` (or `action: yes`), `needs`,
   `root`.
3. Implement `--check` (0 = installed) and the install step.
4. `python3 beta/tools/build_catalog.py && python3 beta/tools/docs.py`
5. `python3 beta/tools/check.py && python3 beta/tools/selftest.py`

## Changing an existing option

Edit the script, **bump `#@ version:`**, regenerate the index and docs. Without
a bump, existing installs never receive the fix.

## Adding a page

See [modules/pages.md](modules/pages.md).

## Adding a language

See [languages.md](languages.md).

## Before shipping

```bash
python3 -m py_compile $(find beta -name '*.py')
for f in beta/addons/*.sh; do bash -n "$f"; done
python3 beta/tools/build_catalog.py --check
python3 beta/tools/check.py
python3 beta/tools/selftest.py
```

## Do not

- Modify any file outside `beta/`: the stable release is in production.
- Run a command from the GTK thread: use `run_task`.
- Pass user text through Pango markup.
- Default to `root: yes`: only when required.
