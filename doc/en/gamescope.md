# Gamescope — external scripts

Two ways to install the Gamescope / Steam Big Picture session:

1. **Gaming section of the manager** (recommended): the script is built into the
   application and adapts to the detected desktop.
2. **External scripts** in `external_addons/`: standalone, editable, with no dependency
   on `ps5_manager.py`.

## The 8 scripts

| File | Desktop |
|---|---|
| `gamescope_install_gnome.sh` | GNOME (GDM) |
| `gamescope_uninstall_gnome.sh` | GNOME |
| `gamescope_install_kde.sh` | KDE Plasma (SDDM) |
| `gamescope_uninstall_kde.sh` | KDE |
| `gamescope_install_cinnamon.sh` | Cinnamon (LightDM) |
| `gamescope_uninstall_cinnamon.sh` | Cinnamon |
| `gamescope_install_budgie.sh` | Budgie (SDDM since Fedora 44, LightDM before) |
| `gamescope_uninstall_budgie.sh` | Budgie |

## Usage

```bash
# From a clone of the repository
# sudo bash external_addons/gamescope_install_budgie.sh

# Choose the account that will be auto-logged in
# sudo bash external_addons/gamescope_install_budgie.sh --user myaccount

# Add the session without switching to it automatically at boot
# sudo bash external_addons/gamescope_install_budgie.sh --no-autologin

# Back to the original desktop
# sudo bash external_addons/gamescope_uninstall_budgie.sh
```

Common options: `--user <account>`, `--no-autologin`. Without options the account is
derived from `SUDO_USER`.

## What the install sets up

| Item | Purpose |
|---|---|
| `/usr/bin/gamescope-session` | launches Gamescope + Steam Big Picture |
| `/usr/local/bin/switch-session` | switches desktop ↔ Gaming (`desktop` / `steam`) |
| `/usr/share/wayland-sessions/*.desktop` | “Gaming” session in the login screen |
| `/etc/sddm.conf.d/zz-ps5-manager-autologin.conf` (KDE) or the LightDM/GDM equivalent | auto-login into the Gaming session |
| polkit rule | `switch-session` usable without a password by the target account |
| systemd unit / drop-in | required graphical dependencies |

The script resolves the **actual** desktop session name at runtime (for instance
`budgie-desktop`, `budgie`, `ubuntu-budgie-desktop`), so the “desktop” switch back keeps
working even if the session id changed.

Steam may be the rpm package (`steam` command) **or** the
`com.valvesoftware.Steam` Flatpak — the Budgie case, where the rpm does not
install. The Gaming session picks whichever launcher is available;
`--mangoapp` is only used with the rpm, since a Flatpak filters `LD_PRELOAD`.

A Flatpak needs a **D-Bus session bus**: on a TTY, logind creates
`/run/user/<uid>/bus` without exporting it, and the sandbox used to quit at
once (`Primary child shut down`). The session now exports it itself (falling
back to `dbus-run-session` when none exists) and logs the bus used as well as
Gamescope's full command line.

## KDE Plasma (Fedora 45) and Steam as an RPM

On KDE Plasma the Gaming session uses the **rpm package** `steam` (RPM Fusion
nonfree). The install script installs it when the command is missing: RPM
Fusion is enabled for the current Fedora release (`rpm -E %fedora`, 45
included), then `steam` and `steam-devices` are installed; the Flatpak is only a
fallback if that fails. SDDM autologin
(`/etc/sddm.conf.d/zz-ps5-manager-autologin.conf`) and the session name
(`plasma`) are resolved at runtime, so switching sessions and getting back to
the desktop need no extra configuration.

## HDR / DTM and driver compatibility

Gamescope only enables HDR — and its dynamic tone mapping (DTM) — when all three
conditions hold:

| Condition | Log trace |
|---|---|
| **amdgpu/RADV** driver (NVIDIA and Intel stay on SDR) | `pilote : amd, Mesa 25.x, sortie DP-1 2560x1440` |
| display advertising HDR in its **EDID** (CTA-861 block, extended tag `0x06`) | same |
| output not 4K/60 (10-bit exceeds the link bandwidth) | same |

The session then adds `--hdr-enabled --hdr-itm-enabled` and writes
`HDR/DTM : actif (…)`; otherwise it writes
`HDR/DTM : inactif (<reason>) : sortie SDR 8 bits` and starts Gamescope in 8-bit.
To force or disable HDR: `PS5_GAMING_HDR=1` or `PS5_GAMING_HDR=0` in the session
environment.

KDE's desktop HDR (System Settings > Display) is not handed over to Gamescope:
the session reads the EDID again. If the picture stays washed out in HDR,
restart with `PS5_GAMING_HDR=0`.

## Daily use

```bash
# Switch to the Gaming session (from the desktop)
$ switch-session steam
# or without privileges
$ sudo -n /usr/local/bin/switch-session steam

# Back to the desktop
$ switch-session desktop

# Auto-login: check the configuration
$ cat /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
# cat /etc/lightdm/lightdm.conf

# Switch log
$ tail -f /var/log/ps5-manager/session-switch.log
```

## Uninstall

The `uninstall` script removes: the Wayland session, `gamescope-session`,
`switch-session`, the polkit rule, auto-login and the systemd drop-in. It **keeps**
the packages (`gamescope`, `steam`) and the Steam data.

```bash
# Check what is left
$ ls /usr/share/wayland-sessions/
$ which gamescope-session switch-session
```

## Diagnosis (before any fix)

`tools/diagnostic_gaming.sh` collects, **read-only**, everything needed to find
out why the Gaming session closes immediately — desktop and session variables,
the real display manager, installed sessions (`wayland-sessions` /
`xsessions`), the AccountsService `Session=`, SDDM / LightDM / GDM autologin,
the Gaming Mode files, `/dev/dri` access and groups, the presence of
`gamescope`, `steam` and a Flatpak Steam, the manager logs and the systemd
journal.

```bash
cd /opt/ps5-manager
sudo bash tools/diagnostic_gaming.sh | tee ~/diagnostic-gaming.txt
```

The file contains no password and no Steam data: it can be shared as is. It
changes nothing.

Read section 12 first: `gaming-session.log` tells which of the three cases
happened — `steam introuvable`, `aucun /dev/dri/card* lisible` or
`gamescope termine (code N)`.

## Troubleshooting

| Symptom | Hint |
|---|---|
| Black screen at boot | `journalctl -b -u gdm` (or `sddm`, `lightdm`) and `session-switch.log` |
| Cannot return to the desktop | desktop session not resolved: check `/usr/share/xsessions/` |
| The Gaming session drops straight back to the desktop | `gaming-session.log`: `steam introuvable` (Flatpak Steam), `aucun /dev/dri/card* lisible` (`video`/`render` groups), `Primary child shut down` (no D-Bus bus) or `gamescope termine (code N)` |
| Black screen then “affichage impossible” | Steam enabled HDR at 4K60: `HDR output enabled` followed by `Failed to prepare 1-layer flip` means the link has no 10-bit bandwidth. In Steam: *Settings > Display* → turn HDR off, then start Gaming Mode again |
| Flatpak Steam quits at once | the sandbox needs a D-Bus session bus: the session exports `unix:path=/run/user/<uid>/bus` (or falls back to `dbus-run-session`); check the `bus de session` line in the log |
| `HDR/DTM : inactif` while the display is HDR | HDR is only enabled on amdgpu, with an HDR EDID and outside 4K/60: check the `pilote :` line and the reason in brackets; `PS5_GAMING_HDR=1` forces a try |
| Washed-out or white picture in HDR | the tone mapping does not match the display: restart with `PS5_GAMING_HDR=0` (SDR) and leave HDR off in Steam |
| Steam rpm missing on KDE Plasma | re-run the Gaming mode install (RPM Fusion + `steam`) or install Steam from the app store, then check `Steam rpm : …` in the log |
| `switch-session` asks for a password | polkit rule missing: re-run the install script |
| Steam does not start in Big Picture | run `steam -gamepadui` in a terminal to see the error |
| Two “Gaming” sessions | leftover script from another desktop: run the matching `uninstall` |
