# `ps5m/pages/`

A page is a module with `build(win) -> Gtk.Widget`. Two families:

- **generic** (`addons.py`): one row per addon in the section, badge,
  confirmation, install. This is the default.
- **dedicated**: when a real interface is needed (switches, accounts, language
  picker, chained installs).

## Registration

`pages/__init__.py` exposes three things:

| Name | Role |
|---|---|
| `STATIC` | fixed pages: log, about |
| `SECTIONS` | sections with a dedicated page (`easy`, `services`, `ui_lang`, `users`, `fedora`) |
| `ORDER` | sidebar order |

`app.section_ids()` only shows sections listed in `ORDER` that have either a
dedicated page or at least one addon.

## Shipped pages

| Page | Role |
|---|---|
| `addons.py` | generic section from the catalog |
| `easy.py` | four profiles (recommended, gaming, streaming, office) + cleanup |
| `appimage.py` | AppImage install/list/uninstall (+ section addons) |
| `repos.py` | repositories: enable/disable, refresh, add a `.repo` |
| `kernel.py` | installed kernels, default kernel, removal |
| `services.py` | one `systemctl show` call per service (presence + state), toggle through `pkexec`, polkit dismissal (code 126) is not an error |
| `ui_lang.py` | language switch + translation coverage |
| `users.py` | human accounts, creation (`useradd -m`) and removal (`userdel -r`) |
| `fedora.py` | installed release, kernel, `dnf check-update` |
| `logs.py` | journal |
| `about.py` | about, links, credits |

## Adding a page

1. Create `pages/my_page.py` with `build(win)`.
2. Add it to `STATIC` (fixed page) or `SECTIONS` (section).
3. For a section, also add it to `ORDER` and, if needed, to `SECTION_ICONS` in
   `app.py`.
4. Add `section.<id>` and the page strings in all six languages.
