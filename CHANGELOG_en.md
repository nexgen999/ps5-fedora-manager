# Changelog

Version history of **PS5 Fedora Manager** (GTK4 / Libadwaita application for Fedora on PS5).

Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
does not use Git tags yet, so versions match `APP_VERSION` in `ps5_manager.py`.

French version: [CHANGELOG.md](CHANGELOG.md)

## [0.15.1] — 2026-11-27

### Changed
- **Status badges everywhere**: sections that did not show what is installed now use the same badge as the catalogues — **● Installed**, **◐ n/total** (partial), **○ Not installed**, with a tooltip.
  - *Additional dependencies*: FUSE, Steam 32-bit drivers, Python/pip, Tkinter, Node.js/npm.
  - *Add Fedora Feature*: mobile management and printing & scanners (packages matching the detected desktop).
  - *Gaming Mode*: gamescope + `switch-session` session.
  - *Mesa / Vulkan*: `vulkan-tools` and `mesa-demos`.
  - *Fan*: PS5 Linux Tools (`ps5_control`, `ps5fan` service).
  - *Hardware Control*: `ps5-hwcon-gui` UI and the Decky plugin.
  - *Repositories*: RPM Fusion, Flathub, enabled OpenH264, GStreamer codecs.
  - *App store*: AppImage Pool and Gear Lever (Flatpak, system or user).
- Detection runs when the page opens: grouped `rpm -q` (architecture aware), files and systemd units, repositories read from `/etc/yum.repos.d`, Flatpak remotes — nothing blocking.

## [0.15.0] — 2026-11-27

### Added
- **“FX Sound” section** (`audio-volume-high-symbolic` icon, right after *Services*): installs **Easy Effects** (`dnf install easyeffects`) and then the **JackHack96 community presets**, each row with its status badge (● installed / ○ not installed) and the number of presets found in `~/.local/share/easyeffects`.
- Preset installation **answers `1` automatically** to the official script's menu (every preset: Perfect EQ, bass, Dolby Atmos, laptop speaker, impulse responses); the script runs as the **desktop account**, not root.
- **Documentation** `doc/fr/fx-sound.md` and `doc/en/fx-sound.md`: exact commands, option 1 contents, written files, checks, troubleshooting and uninstall; `doc/` index updated.

### Changed
- `SECTIONS` and `PAGE_BUILDERS` now include the `fx` section; `sec_fx` and the new labels are translated in all 6 languages and the “About” release notes are up to date.

## [0.14.0] — 2026-11-26

### Added
- **Status badges** in the *Development* and *Web server* catalogues as well as the *Easy setup* profiles: **● Installed** (green), **◐ 2/3** (partial), **○ Not installed** (grey), with a tooltip; the state comes from real detection (grouped `rpm -q`, dedicated commands).
- **“Services” section**: one switch per systemd unit (`httpd`, `nginx`, `php-fpm`, `mariadb`, `mysqld`, `docker`, `podman.socket`, `forgejo`, `firewalld`, `sshd`, `cockpit.socket`, `bluetooth`, `cups`, `avahi-daemon`, `ModemManager`). The switch starts (`enable --now`) or stops (`disable --now`) the service, rolling back automatically when the action is refused.
- **“Turn off unneeded daemons” shortcut**: disables Bluetooth, CUPS, Avahi and ModemManager behind one confirmation, then reloads the page.
- **`doc/` documentation** in French and English: bilingual index, easy setup, web server, development, services, Gamescope, Freebuff, reset — commands, written files, troubleshooting.

### Changed
- `SECTIONS` and `PAGE_BUILDERS` now include the `services` section; `sec_services` translated in 6 languages.
- `README.md` points to `doc/`.

## [0.13.0] — 2026-11-26

### Added
- **Two new profiles** in “Easy setup”: **WordPress** (Apache, PHP, MariaDB, phpMyAdmin, then WordPress download and a complete `wp-config.php` with a random salt) and **All-in-one** (development tools, containers, Cockpit, firewall).
- **Fifteen configuration options** instead of six: HTTP port (Apache/Nginx virtual host and firewall opening), `memory_limit`, `upload_max_filesize`/`post_max_size`, `date.timezone` (`/etc/php.d/99-ps5-easy.ini`), **Let's Encrypt** domain + e-mail (automatic certificate and HTTPS redirect), Forgejo port and **admin account creation**.
- **MySQL** offered next to MariaDB in the web profiles, with the same database steps.
- **Reset tool** in the section: a page listing the components actually installed (one switch each), a “remove configuration files created by the manager” option (`ps5-easy.conf`, `99-ps5-easy.ini`, `adminer.php`, docker/webmin repos), a “clear the DNF cache” option, and a confirmed uninstall that leaves a clean base.
- Component or selection uninstall, using the **same progress window** as the install (one `dnf remove` step per component).

### Fixed
- `_easy_path` now normalises paths (`..` removed): a typed DocumentRoot can no longer escape the intended tree.
- `wp-config.php` is generated in one go (no more fragile `sed` on a password containing an apostrophe or backslash).

## [0.12.0] — 2026-11-26

### Added
- **“Easy setup” section**: four pre-configured profiles reusing the “Development” and “Web server” catalogues.
  - **LAMP web server**: Apache, PHP + FastCGI handler, MariaDB, phpMyAdmin, firewall (optional: Adminer, Cockpit, Certbot, OpenSSH).
  - **LEMP web server**: the same stack with Nginx.
  - **Code & tools**: build tools, Python + GTK4, search/Git/terminal/diagnostics/quality (optional: debug, Node, Rust, Docker, KVM, GitHub Desktop, editors, SQLite).
  - **Containers & services**: Podman, local Forgejo, firewall (optional: Docker, Cockpit, OpenSSH).
- **Configuration window** (`EasySetupConfigWindow`): one switch per component (already-installed ones flagged), and for the web profiles the ServerName, DocumentRoot, MariaDB/MySQL root password, database and user to create (sensitive fields masked).
- **Progress window identical to the 1-click setup** (`EasySetupWindow`, a `SetupWindow` subclass): same live-checked steps, same log, same progress bar — without the reboot prompt. The **original 1-click setup is left untouched**.
- **Generated server configuration**: Apache or Nginx virtual host (`httpd -t` / `nginx -t` before reload), a test `index.php`, SELinux context, `httpd_can_network_connect_db`, and database/user creation with an optional root password (MariaDB via socket, MySQL with `caching_sha2_password`), all SQL values escaped.

### Changed
- `APP_VERSION` bumped to `0.12.0`, FR/EN release notes of the “About” dialog updated.

## [0.11.0] — 2026-11-26

### Added
- **“Web server” section** (right after “Development”), in three categories:
  - **Servers & languages**: Apache (httpd, mod_ssl), Nginx, PHP 8 + extensions (FPM, mysqlnd, pdo, gd, mbstring, xml, opcache, zip, intl), **PHP ↔ Apache / Nginx** (writes the FastCGI handler to `/run/php-fpm/www.sock`, runs `httpd -t` / `nginx -t` before reloading), MariaDB, MySQL community, Certbot (Let's Encrypt).
  - **Panels & databases**: Cockpit (+ packages, storage, network, Podman, virtual machines), phpMyAdmin, Adminer (a single PHP file), Webmin (official repository).
  - **Network & access**: web firewall (http/https), OpenSSH server.
- Every entry follows the same model: real state, **install**, **update**, **launch** (browser for panels, `http://localhost` for servers) and **uninstall**, with useful notes (Apache/Nginx sharing port 80, MariaDB/MySQL hardening, phpMyAdmin limited to localhost, Cockpit/Webmin ports).
- Services are enabled and started (`systemctl enable --now`), the firewall is opened for http/https/cockpit, and configuration failures are reported without breaking the running server (config test before reload).

### Changed
- Catalogue rendering is shared (`_build_catalog_page`) between “Development” and “Web server”; `_push_dev_entry` now returns to its originating section.
- `APP_VERSION` bumped to `0.11.0`, FR/EN release notes of the “About” dialog updated.

## [0.10.0] — 2026-11-26

### Added
- **“Development” page** (new section, right after “AI & Developer”), organised in three categories:
  - **Components (system base)**: build tools (gcc, g++, cmake, meson, ninja, autotools, rpmdevtools), Python + GTK4/Libadwaita (gtk4-devel, libadwaita-devel, blueprint-compiler, appstream), containers (Podman, Distrobox, Toolbox), Docker Engine + Compose, KVM/QEMU virtualization (virt-manager, GNOME Boxes, OVMF, swtpm), Node.js/npm, Rust.
  - **Command-line tools**: search (ripgrep, fd, bat, eza, fzf, zoxide), Git & platforms (gh, glab, lazygit, git-delta, git-lfs), terminal (tmux, zellij), system diagnostics (btop, ncdu, duf, fastfetch, hyperfine, lsof, strace, sysstat, perf), debug and profiling (gdb, lldb, valgrind, heaptrack, sysprof), Python quality (uv, ruff, mypy, pre-commit), JSON/HTTP (jq, yq, httpie), automation (just, direnv, shellcheck, shfmt).
  - **Graphical applications**: VSCodium (points to its existing panel), GitHub Desktop (Flathub Flatpak), Forgejo as a local Git server (official binary, systemd service, SQLite, `http://localhost:3000`), terminal editors (Neovim, Helix), SQLite Browser.
- Every entry shows its state (`installed/total` or installed/missing) and offers **install**, **update**, **launch** (where it makes sense) and **uninstall** with confirmation.
- State detection is batched in a single `rpm` query (30 s cache) so the UI never freezes, with dedicated scripts for Docker (docker-ce repo + compose/buildx), Forgejo (Codeberg download + `forgejo.service` unit, data in `/var/lib/forgejo`) and GitHub Desktop.

### Changed
- `APP_VERSION` bumped to `0.10.0`, FR/EN release notes of the “About” dialog updated.
- `_launch_in_terminal()` centralises running a command in a terminal (used by Freebuff, Neovim and the other tools).

## [0.9.1] — 2026-11-26

### Added
- **Freebuff (AI coding agent)** on the “AI & Developer” page, below VSCodium: install (`npm install -g freebuff`, installing Node.js + npm when missing), update (`npm install -g freebuff@latest`), uninstall (`npm uninstall -g freebuff`) and launch in a terminal in the user session. The global npm package version is read from disk and shown in the subtitle; labels translated in all six languages.

### Changed
- `APP_VERSION` bumped to `0.9.1`, FR/EN release notes of the “About” dialog updated.
- “AI & Developer” page subtitle: Ollama, Open WebUI, VSCodium, Freebuff and local AI models.

## [0.9.0] — 2026-11-25

### Added
- **Automatic update at launch**: the application reads the repository's `version.txt` (a few bytes) in a background thread right after the window opens. When a newer version exists it downloads `ps5_manager.py`, checks its size, its `APP_VERSION` and that it compiles as Python, installs it to `/usr/local/bin/ps5-manager` (`root:root`, `0755`, permissions and SELinux contexts reapplied), shows a toast and restarts automatically on the new version.
- **Silent when something goes wrong**: offline, unreachable repository or invalid script, the application opens normally with no message; if installation fails, a toast points to the “Manager update” page.
- **Safeguards**: no second attempt for the same version (`PS5_MANAGER_SKIP_UPDATE`), restart postponed while an action is running, and the check can be disabled with `PS5_MANAGER_NO_UPDATE_CHECK=1`.
- `version.txt` published in the repository: it is the only thing fetched during the check.

### Changed
- `APP_VERSION` bumped to `0.9.0`.

## [0.8.3] — 2026-11-25

### Fixed
- **Launching from the menu icon**: with no graphical PolicyKit agent in the session (seen on Budgie), `pkexec` fell back to its textual agent; started from an icon there is no terminal, so authentication failed and the application never opened — only a terminal launch worked. The application now starts a PolicyKit agent (`polkit-gnome`, `polkit-kde`, `mate-polkit`, `lxpolkit`…) before elevating, retries once, then shows a clear, copyable explanation if authentication is still impossible.
- **Launch log**: elevation failures are written to `~/.cache/ps5-manager/launcher.log` (detected desktop, return code, command) instead of vanishing without a terminal.
- **GTK warnings “Entity did not end with a semicolon”**: row titles containing “&” (“AI & Developer”, “Languages & keyboard”, “Live monitoring & history”) were passed to the Adwaita constructor while markup is enabled by default. Text is now set after markup is disabled: no warning at all and the “&” shows as typed.

### Changed
- `polkit-gnome` joins the interface dependencies for desktops that ship no authentication agent.
- `APP_VERSION` bumped to `0.8.3`.

## [0.8.2] — 2026-11-25

### Fixed
- **Main (“burger”) menu not refreshed**: it is a `Gio.Menu` built once at startup, so after a language change it kept the previous language's labels until the app restarted. `rebuild_ui_for_language()` now rebuilds its three entries (`setup_menu`, `system_info`, `about`) and the search button tooltip.
- **Translated “About” dialog**: release notes and debug information (“Version”, “File”) only existed in French and English. They are now available in all six languages (`_RELEASE_NOTES_ITEMS`, with an English fallback when a language is missing).
- Every menu verified: the 20 sidebar entries and the 3 burger menu entries go through `T()` and are translated in all six languages.
- **AI & Developer page**: the two descriptions still hard-coded (Open WebUI state and GNOME icon, installed/active model count) now go through `STRINGS`.
- `APP_VERSION` bumped to `0.8.2`.

### Added
- Translated release notes (`release_notes_html()`): 11 history items × 6 languages.

## [0.8.1] — 2026-11-25

### Fixed
- **Session shortcut icon**: the “Switch Session” shortcut and the menu launcher used `Icon=steam` (Steam logo). Installing Gaming Mode now writes the provided Gamescope (Steam Deck) icon to `/usr/share/pixmaps/ps5-gaming-mode.png` and `/usr/share/icons/hicolor/96x96/apps/`, then references it from `switch-session.desktop` and from the `steam.desktop` session (so the GDM / SDDM / LightDM session picker shows it too).
- Uninstalling Gaming Mode removes both icon files and refreshes the icon theme cache.
- `APP_VERSION` bumped to `0.8.1`.

## [0.8] — 2026-11-25

### Added
- **Fully redesigned “System” window**: header with the Fedora logo, the application name and the detected desktop's logo (GNOME, KDE Plasma, Cinnamon, Budgie), then four readable Adwaita groups — *System* (OS, kernel, architecture, package manager), *Session* (desktop, display manager, graphical session, user, accent colour), *Software* (Gamescope, Steam) and *Application* (version, file, session log with a direct open button).
- **Icons imported into the repository**: the `icons/` folder holds the 96 px PNGs (Fedora, Gamescope, Budgie, Cinnamon, KDE, GNOME); they are also embedded as base64 in `ps5_manager.py` so a `curl` install stays a single file with no network access. Monochrome logos sit on a dark badge so they stay readable on light and dark themes.
- **One-click copy**: a header button copies every piece of information (handy when filing a bug report).
- **Completed translations**: the 64 texts that did not go through `STRINGS` (AI & Developer page, about) are translated into Spanish, Italian, German and Portuguese through `LSTRINGS`; the 18 `... if UI_LANG == "fr" else ...` ternaries are converted to `_L()` and two computed labels (session shortcut, Podman session lingering) now use `STRINGS`. Every `T()` key is covered: **377 keys × 6 languages, none missing**.

### Changed
- `_show_sysinfo()` opens the `SystemInfoWindow` (Adw.Window) instead of a plain-text dialog.
- `_L(fr, en)` relies on an `_L_TABLE` table and the `LSTRINGS` dictionaries (es, it, de, pt).
- `APP_VERSION` bumped to `0.8`, FR/EN release notes of the “About” dialog updated.

## [0.7.1] — 2026-11-25

### Fixed
- **Gaming Mode on Cinnamon and Budgie (and KDE)**: the Gamescope session no longer relaunches Steam in a loop. The application now writes its own `/usr/bin/gamescope-session` (the upstream guide only ran `gamescope … steam` and exited, so the display manager reopened the `steam` session forever). Closing Steam now returns to the detected desktop session.
- **Return to the desktop from Steam Big Picture**: `/usr/bin/steamos-session-select` records the requested session (desktop or Gaming) and shuts Steam down (`steam -shutdown`); `gamescope-session` reads that request once Gamescope exits and switches accordingly (no more being stuck on Steam).
- **Reliable session switch**: `/usr/local/bin/switch-session` now rewrites the display manager's autologin configuration **as well as** AccountsService. With SDDM (`Session=` in `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf`) and LightDM (`autologin-session=` in `[Seat:*]`) the previous session stayed hard-coded, so the display manager kept restarting Steam.
- **DRM error when Gamescope starts**: `gamescope` is installed when missing, the user is added to the `video` and `render` groups (`/dev/dri/card*` access), `WAYLAND_DISPLAY` / `DISPLAY` are removed from the session environment (Gamescope was attempting a nested compositing) and the switch waits for the session to really close before restarting the display manager (the GPU stayed busy).
- **Display manager detection**: `display-manager.service` is read first (`systemctl show -p Id`). Cinnamon and Budgie often start LightDM while `gdm.service` stays “enabled”: the application restarted the wrong service and the switch never happened.
- **Session scripts**: no more failure when the `shahnawazshahin` guide is unreachable (a warning only), and the scripts shipped by the application are written after the guide's ones, so they take precedence.
- `APP_VERSION` bumped to `0.7.1`, FR/EN release notes of the “About” dialog updated.

### Added
- **Gaming Mode log**: new entry on the “Gaming Mode” page showing `/var/log/ps5-manager/gaming-session.log` (command run, Gamescope exit code, possible DRM errors). Three labels translated in all six languages (353 keys).

## [0.7] — 2026-11-25

### Added
- **Interface in 6 languages**: French, English, **Spanish**, **Italian**, **German** and **Brazilian Portuguese**. All 350 `STRINGS` labels are fully translated in every language (no missing key).
- **Language picker**: the “Interface language” page lists the six languages with their native names (Français, English, Español, Italiano, Deutsch, Português (Brasil)); the first-launch welcome dialog offers the six choices.
- `LANG_ORDER` / `LANG_LABELS` centralise the display order and the native names.

### Changed
- **`read_ui_lang()`** accepts variants (`pt_BR`, `pt-BR`, `es_ES`…) and falls back to the base language stored in `/etc/ps5-manager/language`.
- **`T()`** now falls back to English then French: a missing key no longer prints its technical name.
- **`_L(fr, en)`** checks an `LSTRINGS` dictionary (empty for now) before falling back to English, so texts outside `STRINGS` can be translated later without touching the call sites.
- `APP_VERSION` bumped to `0.7`, FR/EN release notes of the “About” dialog updated.

## [0.6.1] — 2026-11-25

### Added
- **Per-desktop repositories**: the Repositories page installs or repairs the detected desktop's official comps group (`@gnome-desktop`, `@kde-desktop-environment`, `@cinnamon-desktop-environment`, `@budgie-desktop-environment`), enables `fedora-cisco-openh264` (H.264) and offers GStreamer codecs through RPM Fusion — no third-party repository is needed for the four desktops.

### Changed
- **Fedora updates**: `fed_apps` updates Flatpak both system-wide **and** for the user; DNF, langpacks, Flatpak and repository refresh commands stay identical on all 4 desktops.
- **Maintenance**: added `update-desktop-database` and `fc-cache -f` (shared) plus a “KDE Plasma maintenance” group with `kbuildsycoca6 --noincremental` (KDE only).
- **Locale & keyboard**: `gsettings org.gnome.system.locale` is only applied on GNOME / Budgie, and the logout uses the detected desktop's command (`gnome-session-quit`, `cinnamon-session-quit`, `qdbus … org.kde.Shutdown.logout`) with a `loginctl terminate-user` fallback.
- **GNOME accent colour**: the group is hidden and the dconf polling is disabled outside GNOME.
- **PS5 kernel**: section audited with no desktop or display-manager dependency; its texts now go through the FR/EN strings.
- `APP_VERSION` bumped to `0.6.1`, FR/EN release notes of the “About” dialog updated.

### Fixed
- **App store**: RPM / Flatpak statuses are computed in a thread and filled in after rendering — no more freeze when the page opens.
- **AI & Developer**: the Podman / Open WebUI state and the Ollama model list are read off the GTK thread (30 s cache, the section is rebuilt once the data arrives).
- **Repositories page**: the comps group check runs when the action starts, never when the page opens.
- **Release notes (“What's new”)**: no `<b>` tag left and a `_safe_release_notes()` filter (Libadwaita rejected the markup).
- **Group titles**: `pref_group()` no longer escapes plain text (`IA &amp;` is `IA &` again).
- **Hard-coded texts**: kernel, users, repositories, Mesa and AI now use `STRINGS` (FR/EN).
- **AI & Developer page**: the 49 labels, subtitles and confirmations still hard-coded in French (Open WebUI, Ollama, VSCodium, models) are bilingual through the new `_L(fr, en)` helper, so the English interface is complete.

## [0.6] — 2026-11-25

### Added
- **GNOME / KDE Plasma / Cinnamon / Budgie support**: the desktop (session variables, user processes, `loginctl`) and the display manager (GDM / SDDM / LightDM) are detected automatically, and the affected commands adapt to them.
- **Desktop-aware 1-click setup**: the power step applies the detected desktop's commands, the Extension Manager is dropped from the plan outside GNOME (28 items instead of 29) and the Gamescope step follows the display manager; the setup log starts with a “Detected environment” line (desktop · display manager · session).

### Changed
- **Power per desktop**: screen blanking and full sleep through `gsettings` (GNOME, Cinnamon, Budgie) or `kwriteconfig6` + Powerdevil (KDE Plasma), including a Powerdevil reload.
- **GNOME-specific items**: the Extension Manager disappears from the app store and from the recommended setup (28 items outside GNOME); mobile management uses KDE Connect (KDE), Nemo (Cinnamon) or Nautilus (GNOME / Budgie); printers add `print-manager` on KDE.
- **Multi-desktop Gamescope**: autologin is written for GDM, SDDM or LightDM and switches back to the detected desktop session (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) instead of a hard-coded “gnome”.
- **Wider setup progress window** (1320 × 800 instead of 1120 × 740) with a wider left column.
- `APP_VERSION` bumped to `0.6`, FR/EN release notes of the “About” dialog updated.

## [0.5] — 2026-11-22

### Added
- **Language choice on first launch**: the bilingual “Choose your language · Choisissez votre langue” dialog (text in both languages, *English* / *Français* buttons) is shown before the setup message, so everyone understands both options; the interface switches to the chosen language immediately.
- **First-launch welcome dialog**: offers the **1-click recommended setup** or manual configuration (which simply closes the dialog). The choice is remembered in `/etc/ps5-manager/setup-welcome-done`, so the dialog never appears again afterwards.
- **Recommended setup** in 9 steps and 29 items: power (system sleep, screen blanking, full sleep), fan (PS5 Linux Tools, `ps5fan`, `ps5boost`), Hardware Control, Mesa / Vulkan, repositories (RPM Fusion, Flatpak/Flathub, cache), extra dependencies (fuse, 32-bit Steam drivers, Python 3 + pip, `my_project` virtual environment, Tkinter, Node.js/npm, Fedora update), app store (Bazaar, GNOME Extension Manager, Steam, Heroic, ProtonUp-Qt, Decky Loader, Universe, AppImage Pool, Opera as the Flatpak `com.opera.Opera`), the Hardware Control plugin and Gaming Mode (Gamescope).
- **Setup progress window**: the list of items on the left with live status (`○` pending, `●` running, `✔` done, `✖` failed), the full command log on the right and a progress bar. A failed item does not stop the following ones.
- **Reboot offered at the end of the setup**: the progress window closes and a dialog offers to reboot now (`systemctl reboot`) or later.
- **Main (burger) menu**: new “Run recommended setup” entry to launch the setup again at any time, with a confirmation.
- [`dev_setup.md`](dev_setup.md) documentation (English: [`dev_setup_en.md`](dev_setup_en.md)): reference configuration, exact commands and the matching application section for each step.
- English versions of the documentation: [`CHANGELOG_en.md`](CHANGELOG_en.md) and [`dev_setup_en.md`](dev_setup_en.md).

### Changed
- **Locale & keyboard**: `gsettings org.gnome.system.locale` is only applied on GNOME / Budgie, and the offered logout uses the detected desktop's command (`gnome-session-quit`, `cinnamon-session-quit`, `qdbus … org.kde.Shutdown.logout`) with a `loginctl terminate-user` fallback — no more hard-coded `gnome-session-quit`.
- **GNOME accent colour**: the group is hidden and the 3-second dconf polling is disabled outside GNOME.
- **PS5 kernel**: section audited with no desktop or display-manager dependency (`dnf`/`rpm`, `depmod`, `dracut`, copy to `/boot/efi`) — identical behaviour on all four environments.
- **Wider setup progress window** (1320 × 800 instead of 1120 × 740) with a wider left column, for a more comfortable reading of the list and the log.
- `APP_VERSION` bumped to `0.5`, FR/EN release notes of the “About” dialog updated.

## [0.4] — 2026-11-22

### Added
- **New “Add Fedora Feature” category** in the sidebar (group 1, right after “Gaming Mode”): groups the activation of Fedora features into one action per feature.
- **Mobile management**: one-command installation of GSConnect (Android phone over Wi-Fi), USB MTP / SSHFS support, Nautilus integrations and ADB / Fastboot — `gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs nautilus-python android-tools`.
- **Printers & scanners**: full printer support (CUPS, `cups-filters`, `system-config-printer`, HP `hplip` drivers, Brother / Epson `gutenprint-cups` and `splix`, generic drivers, network discovery) and scanner support (SANE, `sane-backends-drivers-scanners` drivers, `libsane-hpaio`, GNOME `simple-scan` application) — `cups cups-filters system-config-printer hplip gutenprint-cups splix sane-backends sane-backends-drivers-scanners libsane-hpaio simple-scan`.
- CUPS actions: enable (`systemctl enable --now cups`), stop and disable (`systemctl disable --now cups`) with confirmation, disable the automatic activation sockets (`systemctl disable --now cups.socket cups.path`) with confirmation, and display `systemctl status cups`.

### Changed
- `APP_VERSION` bumped to `0.4`, FR/EN release notes of the “About” dialog updated (19 sections).

## [0.3] — 2026-11-22

### Added
- **PS5 kernel — install a specific kernel**: new “Install a specific kernel (all releases)” entry listing the releases of [`ps5-linux/ps5-linux-patches`](https://github.com/ps5-linux/ps5-linux-patches/releases) (tags `kernel-X.Y.Z-<commit>`, up to 60 releases across all pages) with the version, the commit, the state (“Running”, “Installed”, “Not installed”) and an “Open the GitHub releases page” row.
- Download of the `linux-ps5-<version>-1.x86_64.rpm` RPM of the chosen release, then `rpm -ivh --nosignature --replacefiles --replacepkgs`, `depmod -a`, initramfs generation when missing (`dracut --force --no-hostonly`) and deployment to the ESP (`/boot/efi/bzImage` + `initrd.img`, with a `.old` backup): this makes it possible to **go back to an older kernel**.
- `--replacepkgs` allows reinstalling the same kernel version built from another commit.
- Releases without an RPM (Arch package only, e.g. `kernel-7.0.5-d8d6674`) are detected and reported before any download.
- **App store — Mister Download Manager** (`anefzaoui/misterdownloadmanager`): install / update / uninstall of the RPM published on GitHub (`misterdownloadmanager`), with the installed version and the latest available version.
- The `ghrpm` entry type of the app store now accepts any GitHub repository (`gh_repo`, `gh_asset_pattern`) instead of the Etcher repository only.
- `CHANGELOG.md` file (this file).

### Changed
- `APP_VERSION` bumped to `0.3`, FR/EN release notes of the “About” dialog updated.
- Version detection for `ghrpm` applications generalised (extraction of `X.Y[.Z]` from the published file name).

## [0.2] — 2026-11-21

### Added
- **Gaming Mode**: install and uninstall of Gamescope / Steam Big Picture session, with embedded scripts (backup of `/etc/gdm/custom.conf`, files from the `steam-using-gamescope-guide` guide, targeting the real user instead of the `ps5` account).
- **Extra Dependencies**: `fuse` + `fuse-libs`, 32-bit graphics drivers for Steam (`mesa-vulkan-drivers.i686`, `mesa-dri-drivers.i686`, `libva.i686`).
- **Python 3**: `python3` + `python3-pip`, automatic creation and activation of the `my_project` virtual environment, display of `python3 --version` / `pip3 --version`, installation of `python3-tkinter`.
- **Node.js / npm**: installation, update from the Fedora repositories, switch to the latest major version (NodeSource 26 LTS repository), version check and uninstall.
- **Misc fixes**: forced Steam restart (`pkill -9 steam; steam`).
- **AppImage management** in the app store: AppImage Pool (`io.github.prateekmedia.appimagepool`) and Gear Lever (`it.mijorus.gearlever`), with install / update / uninstall / open the Flathub page.
- **Hardware Control**: installer in `--passwordless` mode and the Decky “Hardware Control Plugin”.
- “Hardware Control Plugin” group in the app store.

### Changed
- Native GTK4 / Libadwaita interface: 18 sections (`APP_VERSION = "0.2"`), FR/EN release notes in “About”.
- Python closure fixes on AppImage actions (Gear Lever inherited AppImage Pool's command).

## [0.1] — 2026-11-17

### Added
- First version of the **GTK4 / Libadwaita** graphical interface (`ps5_manager.py`, a single file installed as `/usr/local/bin/ps5-manager`) progressively replacing the Bash scripts.
- 15 sections: logs, app store, AI & developer, manager update, languages, repositories, users, Fedora, maintenance, power, fan, hardware, Mesa/Vulkan, PS5 kernel, interface language.
- Elevated launch through `pkexec` with real-user detection (`PKEXEC_UID`), commands run as root or as the user depending on the case.
- PS5 kernel management: latest release check, installation of the latest kernel RPM, choice of the kernel to boot from `/boot/efi`, cleanup of old kernels while protecting the running one.

## Older history — Bash scripts (2025 → 2026-11)

Before the graphical interface, the project was a set of Bash scripts launched by `ps5-manager.sh`:

- `02-langues.sh` — language configuration
- `03-depots.sh` — add / remove repositories (RPM Fusion, COPR…)
- `04-utilisateurs.sh` — account management
- `05-maj-systeme.sh` — system updates
- `06-maintenance.sh` — cleanup and maintenance
- `07-alimentation.sh` — power / energy management
- `08-fan-manager.sh` — fan
- `09-hw-control.sh` — Hardware Control
- `10-mesa-vulkan.sh` — Mesa / Vulkan
- `11-kernel.sh` — PS5 kernel
- `12-logiciels.sh` — software installation
- `13-presets.sh` — presets

Those scripts were replaced by the Python application and then removed from the repository.
