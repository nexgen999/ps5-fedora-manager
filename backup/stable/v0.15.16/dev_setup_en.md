# Recommended setup — reference configuration

This document describes the **developer-recommended setup** applied by
PS5 Fedora Manager (version 0.8). It is offered on the first launch of the
application and stays available at any time through the **main (burger)
menu → “Run recommended setup”**.

The setup runs in a single pass, in the order below. Every item is
independent: a failure is reported (✖) and the setup continues with the next
item. A reboot is offered at the end.

> The original list provided by the maintainer contained two “step 4”
> headings; the steps are therefore numbered 1 to 9 here, in their real
> execution order.

French version: [dev_setup.md](dev_setup.md)

---

## 1. Power — “Power” section

| Item | Command |
| --- | --- |
| Disable system sleep | `systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target` |
| Disable screen blanking | depending on the desktop (see [Compatibility](#desktop-environment-compatibility)): `gsettings set org.gnome.desktop.session idle-delay 0` (GNOME / Budgie), `gsettings set org.cinnamon.desktop.session idle-delay 0` (Cinnamon), `kwriteconfig6 --file powermanagementprofilesrc --group AC --group DimDisplay --key idleTime 0` and `--group DPMSControl --key idleTime 0` (KDE) |
| Disable full sleep | depending on the desktop: `sleep-inactive-ac-type nothing` (GNOME / Budgie), `org.cinnamon.settings-daemon.plugins.power sleep-inactive-ac-type nothing` (Cinnamon), `--group SuspendSession --key idleTime 0 --key suspendType 0` (KDE) — user |

## 2. Fan — “Fan” section

| Item | Command |
| --- | --- |
| Install / update PS5 Linux Tools | `git clone --depth=1 https://github.com/ps5-linux/ps5-linux-tools` then `./install.sh` |
| Enable the ps5fan service | `systemctl enable --now ps5fan.service` |
| Enable the ps5boost service (boot) | `systemctl enable --now ps5boost.service` |

## 3. Hardware Control — “Hardware Control” section

| Item | Command |
| --- | --- |
| Install / update Hardware Control | `dnf install -y python3-PyQt6` then `curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh \| bash -s -- --passwordless` (user) |

## 4. Mesa / Vulkan — “Mesa / Vulkan” section

| Item | Command |
| --- | --- |
| Install Vulkan Tools and Mesa Demos | `dnf install -y vulkan-tools mesa-demos` |

## 5. Repositories — “Repositories” section

| Item | Command |
| --- | --- |
| Install RPM Fusion (free + nonfree) | `dnf install -y https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-<VERSION>.noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-<VERSION>.noarch.rpm` |
| Install Flatpak and Flathub | `dnf install -y flatpak` then `flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo` |
| Refresh repositories and clean the cache | `dnf clean all && dnf makecache --refresh` then `flatpak update --appstream -y` |

## 6. Extra dependencies — “Extra Dependencies” section

| Item | Command |
| --- | --- |
| Install FUSE | `dnf install -y fuse fuse-libs` |
| 32-bit graphics drivers for Steam | `dnf install -y mesa-vulkan-drivers.i686 mesa-dri-drivers.i686 libva.i686` |
| Install Python 3 and pip | `dnf install -y python3 python3-pip` |
| Create the virtual environment | `python3 -m venv my_project` (in the user's home directory) |
| Install Tkinter | `dnf install -y python3-tkinter` |
| Install Node.js and npm | `dnf install -y nodejs npm` |
| Update Fedora packages | `dnf upgrade -y --refresh` |

## 7. App store — “App Store” section

| Item | Command |
| --- | --- |
| Bazaar | `flatpak install --system -y flathub io.github.kolunmi.Bazaar` |
| GNOME Extension Manager (GNOME only, removed elsewhere) | `flatpak install --system -y flathub com.mattjakeman.ExtensionManager` |
| Steam | `dnf install -y steam` (RPM Fusion enabled beforehand) |
| Heroic Games Launcher | `flatpak install --system -y flathub com.heroicgameslauncher.hgl` |
| ProtonUp-Qt | `flatpak install --system -y flathub net.davidotek.pupgui2` |
| Decky Loader | `curl -fsSL https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh \| bash` (user) |
| Universe | `dnf copr enable -y ilyasturki/universe`, `dnf install -y universe universe-desktop`, then `universe setup` (user) |
| AppImage Pool | `flatpak install --system -y flathub io.github.prateekmedia.appimagepool` |
| Opera | `flatpak install --system -y flathub com.opera.Opera` |

## 8. Hardware Control — plugin — “Hardware Control” section

| Item | Command |
| --- | --- |
| Install the Hardware Control plugin | `curl -fsSL https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-plugin/main/install.sh \| bash` (user) |

## 9. Gaming Mode — “Gaming Mode” section

| Item | Command |
| --- | --- |
| Install Gamescope | install script embedded in the “Gaming Mode” section (Gamescope + Steam Big Picture session) |

---

## Desktop environment compatibility

The application detects the desktop at startup (`PS5_MANAGER_DESKTOP` when set,
then `XDG_CURRENT_DESKTOP` / `XDG_SESSION_DESKTOP` / `DESKTOP_SESSION`, then the
environment of the real user's processes, then `loginctl show-session -p
Desktop`). The display manager is the one systemd actually starts
(`systemctl show -p Id display-manager.service`, then `gdm.service` /
`sddm.service` / `lightdm.service` as a fallback).

| Item | GNOME | KDE Plasma | Cinnamon | Budgie |
| --- | --- | --- | --- | --- |
| Screen blanking | `gsettings org.gnome.desktop.session idle-delay` | `kwriteconfig6` + Powerdevil (`DimDisplay`, `DPMSControl`) | `gsettings org.cinnamon.desktop.session idle-delay` | `gsettings org.gnome.desktop.session idle-delay` |
| Full sleep | `sleep-inactive-ac-type` (gnome-settings-daemon) | `SuspendSession` (`idleTime`, `suspendType`) | `org.cinnamon.settings-daemon.plugins.power` | `sleep-inactive-ac-type` (gnome-settings-daemon) |
| System sleep (`systemctl mask …`) | yes | yes | yes | yes |
| App store: Extension Manager | shown | hidden | hidden | hidden |
| Mobile management | GSConnect + Nautilus | KDE Connect + Dolphin | MTP / SSHFS + Nemo | MTP / SSHFS + Nautilus |
| Printers & scanners | CUPS + `system-config-printer` | CUPS + `print-manager` | CUPS + `system-config-printer` | CUPS + `system-config-printer` |
| Gamescope / Steam session | GDM | SDDM | GDM or LightDM | GDM or LightDM |
| Locale & keyboard | `localectl` + AccountsService + `gsettings org.gnome.system.locale` | `localectl` + AccountsService (no `gsettings`) | `localectl` + AccountsService | `localectl` + AccountsService + `gsettings` |
| Logout after a language change | `gnome-session-quit --logout --force` | `qdbus6 org.kde.Shutdown /Shutdown org.kde.Shutdown.logout` | `cinnamon-session-quit --logout --force` | `gnome-session-quit --logout --force` |
| Accent colour | group shown | hidden | hidden | hidden |
| PS5 kernel (install, boot choice, removal) | identical everywhere: `dnf` / `rpm`, `depmod`, `dracut`, copy to the ESP `/boot/efi` | same | same | same |

Notes:

- On KDE Plasma the settings are written to
  `~/.config/powermanagementprofilesrc` and Powerdevil is reloaded
  (`qdbus … org.kde.Solid.PowerManagement.reparseConfiguration`).
- The **recommended setup (1 click)** uses exactly these commands: step 1 applies
  the detected desktop's power settings, the plan skips the Extension Manager
  outside GNOME (**28 items** instead of 29) and step 9 generates the Gamescope
  script for the detected display manager. The setup log starts with
  “Detected environment: desktop · display manager · session”.
- Gamescope: autologin is written to `[daemon]` in `/etc/gdm/custom.conf`, to
  `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf` or to `[Seat:*]` in
  `/etc/lightdm/lightdm.conf`. The restored session is the detected desktop
  (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) instead of a hard-coded
  “gnome”. The 1.5 scaling factor of the login screen is only applied on GDM.
- **Gaming Mode**: the `steam` session
  (`/usr/share/wayland-sessions/steam.desktop`) runs `/usr/bin/gamescope-session`,
  which runs Gamescope and, once Steam closes, switches the console back to the
  desktop session instead of relaunching Gaming Mode in a loop.
  `/usr/bin/steamos-session-select` records the requested session (desktop or Gaming)
  and shuts Steam down; `/usr/local/bin/switch-session` updates AccountsService **and**
  the display manager's autologin configuration, waits for the session to close and
  then restarts the display manager. The session log is written to
  `/var/log/ps5-manager/gaming-session.log` and shown from the “Gaming Mode” page.
- **PS5 kernel**: the section only uses system tools (`dnf` / `rpm`, `depmod`, `dracut`,
  `/etc/kernel/postinst.d/zz-update-boot`, copying `vmlinuz-*` / `initrd.img-*` to
  `/boot/efi/bzImage` and `initrd.img`): no desktop or display-manager command, so the
  behaviour is identical on all four environments.
- The logout offered after a language change uses the detected desktop's command and falls
  back to `loginctl terminate-user` when it is missing.
- An unidentified desktop (`unknown`) applies the GNOME commands by default;
  the power switches then appear disabled when `gsettings` is unavailable.

## Repositories, updates and maintenance per desktop

| Item | Command / value | GNOME | KDE Plasma | Cinnamon | Budgie |
| --- | --- | --- | --- | --- | --- |
| Desktop repository itself | no third-party repo: official comps group | `@gnome-desktop` | `@kde-desktop-environment` | `@cinnamon-desktop-environment` | `@budgie-desktop-environment` |
| H.264 codec | `fedora-cisco-openh264` repository (enabled from the Repositories page) | yes | yes | yes | yes |
| Multimedia codecs | RPM Fusion (free + nonfree) then `gstreamer1-plugins-ugly`, `gstreamer1-plugins-bad-free-extras` | yes | yes | yes | yes |
| Flatpak applications | Flathub (`flatpak remote-add --system --if-not-exists flathub …`) | yes | yes | yes | yes |
| Fedora updates | `dnf upgrade -y`, `dnf upgrade --refresh -y`, `dnf upgrade -y langpacks-* glibc-langpack-*` | same | same | same | same |
| Flatpak updates | `flatpak update --system` **and** `--user --noninteractive` | same | same | same | same |
| Common maintenance | `dnf clean all`, `dnf autoremove -y`, `journalctl --vacuum-time=7d`, `/tmp` + `/var/tmp`, thumbnails, `update-desktop-database`, `fc-cache -f` | same | same | same | same |
| Specific maintenance | `kbuildsycoca6 --noincremental` (menu cache) | — | yes | — | — |

Notes:

- **No specific repository is needed for KDE Plasma, Cinnamon or Budgie**: all four
  desktops ship in the official Fedora repositories. The Repositories page can install or
  repair the detected desktop's group; the group is checked when the action runs (never
  when the page opens) and “group not found” is reported when the Fedora release does not
  provide it.
- The only useful additional repositories are the same everywhere: **RPM Fusion**
  (codecs, Steam, drivers), **Flathub** and **fedora-cisco-openh264** (H.264).
- Update commands and common maintenance are identical on all four environments; only KDE
  adds the menu cache rebuild.

## Application flow

1. **First launch — language**: the bilingual “Choose your language ·
   Choisissez votre langue” dialog (*English* / *Français* buttons) is shown
   first and applies the chosen language immediately.
2. **First launch — welcome**: a dialog offers “Recommended setup (1 click)”
   or “I'll configure it myself”. Choosing the manual option simply closes the
   dialog; choosing the recommended setup starts it.
3. **Progress window** (1320 × 800): the list of the 9 steps and their
   28 or 29 items depending on the desktop (`○` pending, `●` running, `✔` done, `✖` failed),
   the full command log on the right, with a progress bar.
4. **End of the setup**: the progress window closes and a reboot is offered
   (`systemctl reboot`).

The first-launch marker is stored in `/etc/ps5-manager/setup-welcome-done`;
deleting that file shows the welcome dialogs again on the next start.

## Notes

- The application already runs with root privileges (pkexec / sudo): system
  commands are launched directly, while user commands (gsettings, venv,
  Decky, Hardware Control, Universe) run with the real user's identity.
- The reboot is performed with `systemctl reboot`: `sudo dnf reboot` does not
  exist in DNF/DNF5.
- A missing repository or package (for example a `ps5fan` service not provided
  by PS5 Linux Tools) appears as ✖ without interrupting the rest of the setup.
