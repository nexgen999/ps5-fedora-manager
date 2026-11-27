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
| `gamescope_install_budgie.sh` | Budgie (LightDM) |
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

## Troubleshooting

| Symptom | Hint |
|---|---|
| Black screen at boot | `journalctl -b -u gdm` (or `sddm`, `lightdm`) and `session-switch.log` |
| Cannot return to the desktop | desktop session not resolved: check `/usr/share/xsessions/` |
| `switch-session` asks for a password | polkit rule missing: re-run the install script |
| Steam does not start in Big Picture | run `steam -gamepadui` in a terminal to see the error |
| Two “Gaming” sessions | leftover script from another desktop: run the matching `uninstall` |
