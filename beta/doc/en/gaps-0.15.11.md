# What is still missing compared to 0.15.11

Comparison produced by `tools/compare_stable.py`: static reading of
`ps5_manager.py` (sections, `build_page_*` functions, `DEV_CATALOG` /
`WEB_CATALOG`, packages passed to `dnf install`), then matched against the 51
addons in `addons/index.json`. Full per-option tables are in
[comparison-0.15.11.md](comparison-0.15.11.md).

Raw result: **149 options** read from the stable, **51 addons**, **79 packages**
with no equivalent — 75 of them in the Development page alone (grouped catalog)
and 4 in Web server.

## 1. Installs still missing

### Development (`dev`)

The stable ships a 20-entry catalog. The beta only has `dev-git-tools` and
`dev-python`. Missing, by value:

| Stable entry | Packages | Proposal |
|---|---|---|
| Build essentials | gcc, gcc-c++, make, cmake, meson, ninja-build, pkgconf, autoconf, automake, libtool, patch, rpmdevtools, rpmlint | a `dev-build` addon (today's `deps-build` is a subset) |
| Python + GTK4 / Libadwaita | python3-devel, python3-pip, python3-virtualenv, python3-pytest, gtk4-devel, libadwaita-devel, blueprint-compiler, devhelp… | `dev-python-gtk` |
| Containers | podman, podman-docker, buildah, skopeo, distrobox, toolbox | `dev-containers` |
| Virtualisation | qemu-kvm, libvirt, virt-install, virt-manager, virt-viewer, gnome-boxes, edk2-ovmf, swtpm | `dev-virt` |
| Rust / Cargo | rust, cargo, rustfmt, clippy | `dev-rust` |
| Search & navigation | ripgrep, fd-find, bat, eza, fzf, zoxide | `dev-cli-search` |
| Git & platforms | git, git-lfs, gh, glab, lazygit, git-delta | extend `dev-git-tools` (1.1.0) |
| Terminal | tmux, zellij | `dev-terminal` |
| Diagnostics | lsof, strace, ltrace, sysstat, perf, ncdu, duf, hyperfine | `dev-diagnostic` |
| Debug & profiling | gdb, lldb, valgrind, heaptrack, sysprof | `dev-debug` |
| Python quality | uv, ruff, mypy, pre-commit | `dev-python-quality` |
| Data & HTTP | jq, yq, httpie, sqlite, sqlitebrowser | `dev-data` |
| Automation | just, direnv, shellcheck | `dev-automation` |
| Terminal editors | neovim, helix | `dev-editors` |
| Node.js / npm | nodejs, npm | done (`deps-node`) but filed under Dependencies |

Entries without a package list cannot become a “dnf install” addon: Docker
Engine (docker-ce repo), VSCodium (repo + panel), GitHub Desktop, Forgejo
(server + service).

### Web server (`websrv`)

- `certbot`, `python3-certbot-apache`, `python3-certbot-nginx` (Let's Encrypt) → `web-certbot`.
- `openssh-server` (remote access) → `web-openssh`.
- PHP + extensions, MySQL community, phpMyAdmin, Adminer, Webmin, web firewall:
  installed by dedicated scripts (repos, FastCGI setup), not a package list —
  they need `install`/`remove` addons with `--check`.

## 2. Actions that are not installs

These stable rows cannot be a `dnf install`: they need a dedicated page (like
`services` or `ui_lang`) or an `action: yes` addon.

| Section | Stable option | State in the beta |
|---|---|---|
| logs | live log, session, older logs, clear | partial: Journal page + log window; “clear” missing |
| library | AppImage install/update/uninstall; Flathub search | missing |
| aidev | Open WebUI, VSCodium, Freebuff, start/stop all, `podman ps/logs`, Ollama models, RAM/GPU diagnostics, Podman cleanup | missing (only `ai-ollama` and `ai-python`) |
| easy | profiles, uninstall components, clean manager files, dnf cache purge | partial: recommended chain only |
| services | “stop useless daemons” (bulk action) | missing (per-unit switches) |
| deps | create a venv, show versions, switch Node major, uninstall Node | missing |
| gaming | uninstall, view log | missing |
| features | mobile sharing, printers (install, enable, disable, sockets, status) | missing (Toolbox and Cockpit only) |
| update | uninstall the manager | missing (system and git update: done) |
| lang | view, install, “install all” | partial: 6 langpacks, no “all” |
| repos | list, refresh, OpenH264, add, enable/disable, remove (dnf and Flatpak) | partial: 5 repos + codecs, no management |
| users | add, delete, become root | **deliberately absent**: destructive, out of beta scope |
| fedora | packages, system, languages, metadata | partial: info page + `dnf check-update` |
| maint | everything, cache, autoremove, journal, /tmp, thumbnails, desktop db, fonts, old kernels, disk, KDE menu | partial: 3 actions (cache, Flatpak, TRIM) |
| power | enable/disable the full profile | partial: `power-profiles` and `power-tlp` |
| fan | status, restart service, install tools | partial: `fan-tools` (no status/restart) |
| hw | check hardware, check updates, uninstall | partial: 3 install addons |
| mesa | update, enable RADV, summary | partial: freeworld, Vulkan, tools |
| kernel | pick, boot into, remove a kernel | **deliberately absent**: unbootable-machine risk |
| fix | Steam repair | missing (`fix-dnf` only) |
| ui_lang | (no options: the page is made of switches) | **done** in the beta |

## 3. Deliberate choices

- **Accounts** (add/delete/root), **kernels** (pick/remove) and **manager
  uninstall**: out of the beta until hardware validation is done.
- **`xhost`** is not ported: the beta never elevates the whole UI (only
  `pkexec` for a `root: yes` addon), so root's X11 authorisation is unnecessary.
- Catalog entries that build or configure (Docker, VSCodium, phpMyAdmin, Webmin,
  Forgejo) need a real `install/remove` script, not a package list, so they are
  listed here instead of being half-generated.

## 4. Suggested order to finish

1. `dev-*`: 13 addons generated from the catalog (biggest block, 75 packages).
2. `web-certbot`, `web-openssh`, then PHP/MySQL/phpMyAdmin as `install/remove`.
3. Dedicated pages: `maint` (10 actions), `repos` (repo management), `fan`
   (status + restart), `hw` (check/uninstall).
4. `aidev`: the Ollama + Open WebUI stack as `action: yes` (start/stop/logs).
5. `library`: AppImage flow, then `fix-steam`.
