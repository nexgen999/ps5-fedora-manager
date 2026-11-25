# Recommended setup — reference configuration

This document describes the **developer-recommended setup** applied by
PS5 Fedora Manager (version 0.5). It is offered on the first launch of the
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
Desktop`). The display manager is detected the same way (`gdm.service`,
`sddm.service`, `lightdm.service`).

| Item | GNOME | KDE Plasma | Cinnamon | Budgie |
| --- | --- | --- | --- | --- |
| Screen blanking | `gsettings org.gnome.desktop.session idle-delay` | `kwriteconfig6` + Powerdevil (`DimDisplay`, `DPMSControl`) | `gsettings org.cinnamon.desktop.session idle-delay` | `gsettings org.gnome.desktop.session idle-delay` |
| Full sleep | `sleep-inactive-ac-type` (gnome-settings-daemon) | `SuspendSession` (`idleTime`, `suspendType`) | `org.cinnamon.settings-daemon.plugins.power` | `sleep-inactive-ac-type` (gnome-settings-daemon) |
| System sleep (`systemctl mask …`) | yes | yes | yes | yes |
| App store: Extension Manager | shown | hidden | hidden | hidden |
| Mobile management | GSConnect + Nautilus | KDE Connect + Dolphin | MTP / SSHFS + Nemo | MTP / SSHFS + Nautilus |
| Printers & scanners | CUPS + `system-config-printer` | CUPS + `print-manager` | CUPS + `system-config-printer` | CUPS + `system-config-printer` |
| Gamescope / Steam session | GDM | SDDM | GDM or LightDM | GDM or LightDM |

Notes:

- On KDE Plasma the settings are written to
  `~/.config/powermanagementprofilesrc` and Powerdevil is reloaded
  (`qdbus … org.kde.Solid.PowerManagement.reparseConfiguration`).
- Outside GNOME the recommended setup has **28 items** instead of 29: the
  Extension Manager is removed from the plan (and from the app store).
- Gamescope: autologin is written to `[daemon]` in `/etc/gdm/custom.conf`, to
  `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf` or to `[Seat:*]` in
  `/etc/lightdm/lightdm.conf`. The restored session is the detected desktop
  (`gnome`, `plasma`, `cinnamon`, `budgie-desktop`) instead of a hard-coded
  “gnome”. The 1.5 scaling factor of the login screen is only applied on GDM.
- An unidentified desktop (`unknown`) applies the GNOME commands by default;
  the power switches then appear disabled when `gsettings` is unavailable.

## Application flow

1. **First launch — language**: the bilingual “Choose your language ·
   Choisissez votre langue” dialog (*English* / *Français* buttons) is shown
   first and applies the chosen language immediately.
2. **First launch — welcome**: a dialog offers “Recommended setup (1 click)”
   or “I'll configure it myself”. Choosing the manual option simply closes the
   dialog; choosing the recommended setup starts it.
3. **Progress window** (1320 × 800): the list of the 9 steps and their
   29 items on the left (`○` pending, `●` running, `✔` done, `✖` failed),
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
