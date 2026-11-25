# Changelog

Version history of **PS5 Fedora Manager** (GTK4 / Libadwaita application for Fedora on PS5).

Format inspired by [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project
does not use Git tags yet, so versions match `APP_VERSION` in `ps5_manager.py`.

French version: [CHANGELOG.md](CHANGELOG.md)

## [0.6] — 2026-11-25

### Added
- **GNOME / KDE Plasma / Cinnamon / Budgie support**: the desktop (session variables, user processes, `loginctl`) and the display manager (GDM / SDDM / LightDM) are detected automatically, and the affected commands adapt to them.
- **Desktop-aware 1-click setup**: the power step applies the detected desktop's commands, the Extension Manager is dropped from the plan outside GNOME (28 items instead of 29) and the Gamescope step follows the display manager; the setup log starts with a “Detected environment” line (desktop · display manager · session).

### Changed
- **Power per desktop**: screen blanking and full sleep through `gsettings` (GNOME, Cinnamon, Budgie) or `kwriteconfig6` + Powerdevil (KDE Plasma), including a Powerdevil reload.
- **GNOME-specific items**: the Extension Manager disappears from the app store and from the recommended setup (28 items outside GNOME); mobile management uses KDE Connect (KDE), Nemo (Cinnamon) or Nautilus (GNOME / Budgie); printers add `print-manager` on KDE.
- **Multi-desktop Gamescope**: autologin is written for GDM, SDDM or LightDM and switches back to the detected desktop session (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) instead of a hard-coded “gnome”.
- `APP_VERSION` bumped to `0.6`, FR/EN release notes of the “About” dialog updated.

### Fixed
- **Release notes (“What's new”)**: no `<b>` tag is left in the text, and the new `_safe_release_notes()` filter keeps only `p` / `ul` / `ol` / `li` / `a` — Libadwaita rejected the markup and displayed “Could not parse release notes: Unexpected element 'b'” instead of the text.
- **Group titles**: `pref_group()` no longer escapes markup, because `Adw.PreferencesGroup` renders title and description as plain text; `IA &amp; Développeur` is `IA & Développeur` again (same for `Imprimantes &amp; scanners`, `Langues &amp; clavier`, `Suivi en direct &amp; historique`, `Système &amp; Utilitaires`).

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
