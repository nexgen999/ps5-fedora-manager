# `ps5m/catalog.py`

Reads `addons/` scripts, builds `index.json` and handles updates.

## `Addon`

Fields: `id`, `version`, `file`, `section`, `icon`, `titles`, `descriptions`,
`packages`, `needs`, `check_paths`, `action`, `root`, `sha256`, `path`.

Helpers: `title(lang)`, `description(lang)` (English then French fallback),
`to_dict()` / `from_dict()`.

## Functions

| Function | Role |
|---|---|
| `version_key(v)` | `"1.10.2"` → `(1, 10, 2)` |
| `parse_script(path)` | reads the `#@` header and computes SHA-256 |
| `load_local(dir)` | every script present |
| `build_index(dir)` / `write_index(dir)` | catalog to publish |
| `read_index(path)` | local or downloaded catalog |
| `fetch_index(base_url)` | the repository's `index.json`, no writes |
| `pending(local, remote)` | `(to download, removed)` |
| `refresh(dir, base_url)` | download, verify, write |
| `order(addons)` | sorts so `needs` precede dependants |

## Script contract

`bash script.sh --check` exits 0 when the option is already installed. Without
`packages`, `check_paths` or `action: yes`, `tools/check.py` rejects the addon.
`root: yes` runs the script through `pkexec` (see `runner.md`).

## Updates

`refresh()` only replaces scripts whose version increased, verifies the SHA-256
published in the index and writes through a `.tmp` file that is then renamed:
an interruption never leaves a half-written script.

`REMOTE_BASE` points at
`https://raw.githubusercontent.com/nexgen999/ps5-fedora-manager/main/beta/addons`.
