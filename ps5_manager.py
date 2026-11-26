#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PS5 Fedora Manager — GTK4 / Libadwaita (PyGObject)
==================================================
Interface native GTK4 + Libadwaita.
- Couvre les 15 sections (Journal, Logithèque, IA & Développeur, Manager, Langues,
  Dépôts, Utilisateurs, Mises à jour Fedora, Maintenance, Alimentation, Ventilateur,
  Hardware Control, Mesa/Vulkan, Kernel PS5, Langue de l'interface).
- Synchronisation dynamique de la couleur d'accentuation système GNOME
  (Adw.StyleManager + GSettings/dconf de l'utilisateur réel même sous pkexec).
- Exécution des commandes longues dans un pseudo-terminal (PTY) avec journal
  en direct dans /var/log/ps5-manager.
"""

from __future__ import annotations

import base64
import datetime
import glob
import json
import os
import pty
import pwd
import re
import select
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Optional

# ------------------------------------------------------------------------------
# Constantes & URLs
# ------------------------------------------------------------------------------
APP_ID = "io.github.nexgen999.Ps5Manager"
APP_NAME = "PS5 Fedora Manager"
APP_VERSION = "0.12.0"
INSTALL_DIR = "/opt/ps5-manager"
REPO_URL = os.environ.get(
    "PS5_MANAGER_REPO", "https://github.com/nexgen999/ps5-fedora-manager.git"
)
KERNEL_REPO = "ps5-linux/ps5-linux-patches"
KERNEL_BASE = f"https://github.com/{KERNEL_REPO}"
TOOLS_REPO = "https://github.com/ps5-linux/ps5-linux-tools"
HWCON_INSTALL = (
    "https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh"
)
HWCON_PYPROJECT = (
    "https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/pyproject.toml"
)
HWCON_PREFIX = "/opt/ps5-hwcon-gui"
HWCON_PLUGIN_INSTALL = (
    "https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-plugin/main/install.sh"
)

APPIMAGE_APPS = [
    (
        "io.github.prateekmedia.appimagepool",
        "AppImage Pool",
        "appimage_pool_desc",
        "https://flathub.org/fr/apps/io.github.prateekmedia.appimagepool",
    ),
    (
        "it.mijorus.gearlever",
        "Gear Lever",
        "appimage_gear_desc",
        "https://flathub.org/fr/apps/it.mijorus.gearlever",
    ),
]

# Scripts Gamescope / session Steam (lances en root, __USER__/__HOME__ substitues)
GAMING_INSTALL_SCRIPT = r'''#!/bin/bash
# Gamescope / session Steam Big Picture (PS5 Fedora)
set -u
U="__USER__"
H="__HOME__"

step() { printf '\n==> %s\n' "$*"; }
fail() { printf '  x %s\n' "$*" >&2; exit 1; }
warn() { printf '  ! %s\n' "$*" >&2; }

[ "$(id -u)" -eq 0 ] || fail "root requis"
id "$U" >/dev/null 2>&1 || fail "utilisateur inconnu : $U"

step "Dependances : Gamescope et acces DRM"
if ! command -v gamescope >/dev/null 2>&1; then
  dnf install -y gamescope >/dev/null || fail "installation de gamescope impossible"
fi
command -v gamescope >/dev/null 2>&1 || fail "gamescope introuvable apres installation"
# Gamescope doit ouvrir /dev/dri/card* : sans les groupes video/render le
# lancement echoue sur une erreur DRM (permission refusee).
for g in video render; do
  if getent group "$g" >/dev/null 2>&1; then
    usermod -aG "$g" "$U" >/dev/null 2>&1 || warn "ajout au groupe $g impossible"
  fi
done
if ! command -v steam >/dev/null 2>&1; then
  warn "Steam n'est pas installe : le mode Gaming restera sur un ecran noir."
  warn "Installe Steam depuis la Logitheque de PS5 Fedora Manager."
fi
mkdir -p /var/log/ps5-manager
touch /var/log/ps5-manager/gaming-session.log 2>/dev/null || true
chmod 666 /var/log/ps5-manager/gaming-session.log 2>/dev/null || true

step "AccountsService : session __SESSION_LABEL__ pour $U"
AS="/var/lib/AccountsService/users/$U"
mkdir -p "$(dirname "$AS")"
if [ -f "$AS" ]; then
  sed -i 's/^Session=.*/Session=__SESSION__/' "$AS"
  grep -q '^Session=' "$AS" || sed -i '1i Session=__SESSION__' "$AS"
else
  printf '[User]\nSession=__SESSION__\n' > "$AS"
fi
passwd -u "$U" >/dev/null 2>&1 || true

__AUTOLOGIN_BLOCK__

__SCALING_BLOCK__

step "Session Steam + Gamescope (guide shahnawazshahin)"
if command -v git >/dev/null 2>&1; then
  rm -rf /tmp/gamescope-guide
  if git clone --depth 1 https://github.com/shahnawazshahin/steam-using-gamescope-guide.git /tmp/gamescope-guide >/dev/null 2>&1; then
    ( cd /tmp/gamescope-guide && bash ./installer.sh ) >/dev/null 2>&1 \
      || warn "installer.sh du guide a echoue : les outils SteamOS sont ignores"
  else
    warn "guide shahnawazshahin inaccessible : les outils SteamOS sont ignores"
  fi
else
  warn "git absent : les outils SteamOS du guide sont ignores"
fi

step "Session Gaming (Gamescope) : scripts PS5 Fedora Manager"
cat > /usr/bin/gamescope-session <<'SH'
#!/bin/bash
# Session Gaming (Gamescope + Steam Big Picture) - PS5 Fedora Manager
# Fermer Steam ramene au bureau (__SESSION_LABEL__) : la session n'est plus
# relancee en boucle par le gestionnaire de connexion.
LOG="/var/log/ps5-manager/gaming-session.log"
if ! { mkdir -p "$(dirname "$LOG")" 2>/dev/null && : >>"$LOG" 2>/dev/null; }; then
  LOG="$HOME/.cache/ps5-manager/gaming-session.log"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  : >>"$LOG" 2>/dev/null || true
fi
exec >>"$LOG" 2>&1
printf '\n=== %s : session Gaming (%s) ===\n' "$(date '+%F %T')" "__SESSION_LABEL__"

NEXT="$HOME/.cache/ps5-manager/next-session"
mkdir -p "$(dirname "$NEXT")" 2>/dev/null || true
rm -f "$NEXT"

switch_to() {
  if [ "$(id -u)" -eq 0 ]; then
    /usr/local/bin/switch-session "$1" >/dev/null 2>&1 || true
  else
    sudo -n /usr/local/bin/switch-session "$1" >/dev/null 2>&1 || true
  fi
}

if ! command -v gamescope >/dev/null 2>&1; then
  echo "gamescope introuvable : retour au bureau"
  switch_to desktop
  exit 1
fi
if ! command -v steam >/dev/null 2>&1; then
  echo "steam introuvable : retour au bureau"
  switch_to desktop
  exit 1
fi

# Pas de composition imbriquee : Gamescope doit piloter directement le DRM.
unset WAYLAND_DISPLAY WAYLAND_SOCKET DISPLAY
export XDG_SESSION_TYPE=wayland
export GAMESCOPE_MODE_SAVE_FILE="$HOME/.config/gamescope/modes.cfg"
mkdir -p "$HOME/.config/gamescope" 2>/dev/null || true

FLAGS=()
if command -v mangoapp >/dev/null 2>&1; then
  FLAGS=(--mangoapp)
else
  echo "mangoapp absent : lancement sans --mangoapp"
fi

gamescope "${FLAGS[@]}" -e -- steam -steamdeck -steamos3
RC=$?
echo "gamescope termine (code $RC)"

REQUEST=""
if [ -f "$NEXT" ]; then
  REQUEST=$(head -n 1 "$NEXT" 2>/dev/null || true)
  rm -f "$NEXT"
fi
if [ "$REQUEST" = "steam" ]; then
  echo "mode Gaming redemande : relance de Gamescope"
  exec /usr/bin/gamescope-session
fi
echo "retour au bureau (__SESSION_LABEL__)"
switch_to desktop
exit 0
SH
chmod 755 /usr/bin/gamescope-session

step "/usr/bin/steamos-session-select (choix de la session suivante)"
cat > /usr/bin/steamos-session-select <<'SH'
#!/bin/bash
# Appele par Steam (mode Gaming) : choisit la session suivante puis ferme Steam.
NEXT="$HOME/.cache/ps5-manager/next-session"
mkdir -p "$(dirname "$NEXT")" 2>/dev/null || true
case "${1:-desktop}" in
  steam|gamescope|game|gaming) printf 'steam\n' >"$NEXT" ;;
  *) printf 'desktop\n' >"$NEXT" ;;
esac
if command -v steam >/dev/null 2>&1; then
  timeout 10 steam -shutdown >/dev/null 2>&1 || true
fi
exit 0
SH
chmod 755 /usr/bin/steamos-session-select

step "Fichier de session /usr/share/wayland-sessions/steam.desktop"
mkdir -p /usr/share/wayland-sessions
cat > /usr/share/wayland-sessions/steam.desktop <<'DESK'
[Desktop Entry]
Encoding=UTF-8
Name=Steam (Gamescope)
Comment=Run Steam directly in Gamescope
Exec=gamescope-session
Type=Application
Icon=ps5-gaming-mode
DesktopNames=gamescope
DESK
chmod 644 /usr/share/wayland-sessions/steam.desktop

step "Icone Gamescope des raccourcis"
ICON_PNG="/usr/share/pixmaps/ps5-gaming-mode.png"
mkdir -p /usr/share/pixmaps /usr/share/icons/hicolor/96x96/apps
base64 -d > "$ICON_PNG" <<'B64'
__GAMING_ICON_B64__
B64
install -m 0644 "$ICON_PNG" /usr/share/icons/hicolor/96x96/apps/ps5-gaming-mode.png
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

step "sudoers : bascule de session sans mot de passe"
mkdir -p /etc/sudoers.d
printf '%s ALL=(ALL) NOPASSWD: /usr/local/bin/switch-session, /usr/bin/steamos-session-select, /usr/bin/systemd-run *\n' "$U" \
  > /etc/sudoers.d/ps5-session
chmod 440 /etc/sudoers.d/ps5-session
if command -v visudo >/dev/null; then
  visudo -c -f /etc/sudoers.d/ps5-session >/dev/null || fail "regle sudoers invalide"
fi

step "/usr/local/bin/switch-session"
cat > /usr/local/bin/switch-session <<'SH'
#!/bin/bash
# Bascule de session PS5 Fedora Manager.
#   switch-session            bascule bureau <-> Gaming
#   switch-session desktop    revient au bureau (__SESSION_LABEL__)
#   switch-session steam      demarre la session Gaming (Gamescope)
# La bascule est deleguee au gestionnaire systeme : elle survit a la fermeture
# de la session en cours.
set -u
SELF="/usr/local/bin/switch-session"
U="__USER__"
USER_ID=$(id -u "$U" 2>/dev/null || true)

if [ "${1:-}" != "apply" ]; then
  ARGS="${1:-}"
  if [ "$(id -u)" -eq 0 ]; then
    if [ -n "$ARGS" ]; then
      exec systemd-run --quiet --collect "$SELF" apply "$ARGS"
    fi
    exec systemd-run --quiet --collect "$SELF" apply
  fi
  if [ -n "$ARGS" ]; then
    exec sudo -n systemd-run --quiet --collect "$SELF" apply "$ARGS"
  fi
  exec sudo -n systemd-run --quiet --collect "$SELF" apply
fi
shift

[ "$(id -u)" -eq 0 ] || { echo "root requis" >&2; exit 1; }
[ -n "$USER_ID" ] || { echo "utilisateur inconnu : $U" >&2; exit 1; }

DESKTOP_SESSION="__SESSION__"
TARGET="${1:-}"

# Gestionnaire de connexion reellement utilise par systemd
DM=$(systemctl show -p Id --value display-manager.service 2>/dev/null | sed 's/\.service$//')
if [ -z "$DM" ] || [ "$DM" = "display-manager" ]; then
  for d in gdm sddm lightdm; do
    if systemctl is-active --quiet "$d.service" 2>/dev/null; then DM="$d"; break; fi
  done
fi
case "$DM" in
  gdm|sddm|lightdm) ;;
  *) DM="__DISPLAY_MANAGER__" ;;
esac

CURRENT=$(busctl get-property org.freedesktop.Accounts \
  /org/freedesktop/Accounts/User"$USER_ID" \
  org.freedesktop.Accounts.User Session 2>/dev/null | awk -F'"' '{print $2}')

case "$TARGET" in
  desktop|"$DESKTOP_SESSION") TARGET="$DESKTOP_SESSION" ;;
  steam|gamescope|game|gaming) TARGET="steam" ;;
  "")
    if [ "$CURRENT" = "steam" ]; then TARGET="$DESKTOP_SESSION"; else TARGET="steam"; fi
    ;;
  *) echo "session inconnue : $TARGET" >&2; exit 2 ;;
esac

# 1. AccountsService : session que le gestionnaire de connexion doit demarrer
busctl call org.freedesktop.Accounts /org/freedesktop/Accounts/User"$USER_ID" \
  org.freedesktop.Accounts.User SetSession s "$TARGET" >/dev/null 2>&1 || true
AS="/var/lib/AccountsService/users/$U"
mkdir -p "$(dirname "$AS")" 2>/dev/null || true
if [ -f "$AS" ]; then
  sed -i "s/^Session=.*/Session=$TARGET/" "$AS" 2>/dev/null || true
  grep -q '^Session=' "$AS" 2>/dev/null || sed -i "1i Session=$TARGET" "$AS" 2>/dev/null || true
else
  printf '[User]\nSession=%s\n' "$TARGET" >"$AS" 2>/dev/null || true
fi

# 2. Auto-connexion : elle doit viser la nouvelle session, sinon le
#    gestionnaire de connexion relance indefiniment l'ancienne (mode Gaming).
case "$DM" in
  sddm)
    mkdir -p /etc/sddm.conf.d
    printf '[Autologin]\nUser=%s\nSession=%s\nRelogin=false\n' "$U" "$TARGET" \
      > /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
    ;;
  lightdm)
    mkdir -p /etc/lightdm
    LCONF="/etc/lightdm/lightdm.conf"
    [ -f "$LCONF" ] || printf '[Seat:*]\n' > "$LCONF"
    python3 - "$LCONF" "$U" "$TARGET" <<'PY'
import io, re, sys
path, user, session = sys.argv[1], sys.argv[2], sys.argv[3]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*autologin-(user|session)\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[Seat:*]")
except StopIteration:
    lines.insert(0, "[Seat:*]")
    i = 0
lines[i + 1:i + 1] = ["autologin-user=" + user, "autologin-session=" + session]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
    ;;
  gdm)
    mkdir -p /etc/gdm
    GDM="/etc/gdm/custom.conf"
    if [ -f "$GDM" ]; then
      cp -f "$GDM" "$GDM.ps5-manager.bak" 2>/dev/null || true
    else
      printf '[daemon]\n' > "$GDM"
    fi
    grep -q '^\[daemon\]' "$GDM" || printf '\n[daemon]\n' >> "$GDM"
    python3 - "$GDM" "$U" <<'PY'
import io, re, sys
path, user = sys.argv[1], sys.argv[2]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*AutomaticLogin(Enable)?\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[daemon]")
except StopIteration:
    lines.insert(0, "[daemon]")
    i = 0
lines[i + 1:i + 1] = ["AutomaticLoginEnable=True", "AutomaticLogin=" + user]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
    ;;
esac

# 3. Fermeture de la session courante (laisse le DRM libre pour Gamescope)
loginctl terminate-user "$U" >/dev/null 2>&1 || true
i=0
while [ "$i" -lt 20 ]; do
  if ! loginctl list-sessions --no-legend 2>/dev/null | awk '{print $3}' | grep -qx "$U"; then
    break
  fi
  sleep 0.5
  i=$((i + 1))
done
sleep 1

# 4. Redemarrage du gestionnaire de connexion sur la nouvelle session
if ! systemctl restart "$DM" >/dev/null 2>&1; then
  systemctl start "$DM" >/dev/null 2>&1 || true
fi
echo "session $TARGET demandee (bureau $DESKTOP_SESSION, gestionnaire $DM)"
exit 0
SH
chmod 755 /usr/local/bin/switch-session

step "Raccourcis (menu des applications + bureau)"
APP_DIR="$H/.local/share/applications"
mkdir -p "$APP_DIR"
cat > "$APP_DIR/switch-session.desktop" <<'DESK'
[Desktop Entry]
Type=Application
Name=__DESK_NAME__
Comment=__SESSION_LABEL__ / Steam Big Picture
Exec=/usr/local/bin/switch-session steam
Icon=ps5-gaming-mode
Terminal=false
Categories=Game;Utility;
DESK
chmod 755 "$APP_DIR/switch-session.desktop"
for d in Bureau Desktop; do
  if [ -d "$H/$d" ]; then
    cp -f "$APP_DIR/switch-session.desktop" "$H/$d/"
    chown "$U": "$H/$d/switch-session.desktop" 2>/dev/null || true
  fi
done
chown -R "$U": "$APP_DIR" 2>/dev/null || true
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

printf '\nTermine : redemarre la console pour arriver sur la session Steam.\n'
'''
GAMING_UNINSTALL_SCRIPT = r'''#!/bin/bash
# Desinstallation Gamescope / bascule bureau <-> Steam (PS5 Fedora)
set -u
U="__USER__"
H="__HOME__"
USER_ID=$(id -u "$U" 2>/dev/null || true)

step() { printf '\n==> %s\n' "$*"; }

step "Scripts de session Gamescope / Steam"
rm -f /usr/local/bin/switch-session /usr/bin/steamos-session-select \
      /usr/bin/gamescope-session /usr/bin/jupiter-biosupdate \
      /usr/bin/steamos-select-branch /usr/bin/steamos-update
rm -f /usr/bin/steamos-polkit-helpers/jupiter-biosupdate \
      /usr/bin/steamos-polkit-helpers/steamos-update \
      /usr/bin/steamos-polkit-helpers/steamos-set-timezone
rmdir /usr/bin/steamos-polkit-helpers 2>/dev/null || true
rm -f /usr/share/wayland-sessions/steam.desktop
rm -f /usr/share/pixmaps/ps5-gaming-mode.png \
      /usr/share/icons/hicolor/96x96/apps/ps5-gaming-mode.png
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

step "Regle sudoers"
rm -f /etc/sudoers.d/ps5-session

step "Raccourcis"
rm -f "$H/.local/share/applications/switch-session.desktop" \
      "$H/Bureau/switch-session.desktop" "$H/Desktop/switch-session.desktop" \
      "$H/.local/share/applications/mode-gaming.desktop"
rm -f "$H/.cache/ps5-manager/next-session"
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$H/.local/share/applications" >/dev/null 2>&1 || true
fi

step "Session __SESSION_LABEL__ par defaut"
if [ -n "$USER_ID" ]; then
  busctl call org.freedesktop.Accounts /org/freedesktop/Accounts/User$USER_ID \
    org.freedesktop.Accounts.User SetSession s "__SESSION__" >/dev/null 2>&1 || true
fi
AS="/var/lib/AccountsService/users/$U"
if [ -f "$AS" ]; then
  sed -i 's/^Session=.*/Session=__SESSION__/' "$AS"
fi

step "Gestionnaire de connexion : retrait de l'auto-connexion"
if [ -f /etc/gdm/custom.conf ]; then
  sed -i '/^AutomaticLoginEnable=/d;/^AutomaticLogin=/d;/^DefaultSession=/d' /etc/gdm/custom.conf
fi
rm -f /etc/sddm.conf.d/zz-ps5-manager-autologin.conf
if [ -f /etc/lightdm/lightdm.conf ]; then
  sed -i '/^[[:space:]]*autologin-user[[:space:]]*=/d;/^[[:space:]]*autologin-session[[:space:]]*=/d' /etc/lightdm/lightdm.conf
fi
rm -rf /tmp/gamescope-guide

printf '\nDesinstallation terminee : la session __SESSION_LABEL__ redevient celle par defaut.\n'
'''


def _gaming_autologin_block() -> str:
    """Bloc d'auto-connexion adapté au gestionnaire de connexion détecté."""
    if DISPLAY_MANAGER == "sddm":
        return r"""step "SDDM : auto-connexion de $U"
mkdir -p /etc/sddm.conf.d
SDDM_CONF="/etc/sddm.conf.d/zz-ps5-manager-autologin.conf"
printf '[Autologin]\nUser=%s\nSession=steam\nRelogin=false\n' "$U" > "$SDDM_CONF"
chmod 644 "$SDDM_CONF"
"""
    if DISPLAY_MANAGER == "lightdm":
        return r"""step "LightDM : auto-connexion de $U"
mkdir -p /etc/lightdm
LCONF="/etc/lightdm/lightdm.conf"
if [ -f "$LCONF" ]; then
  cp -f "$LCONF" "$LCONF.bak-ps5-manager"
else
  printf '[Seat:*]\n' > "$LCONF"
fi
python3 - "$LCONF" "$U" <<'PY'
import io, re, sys
path, user = sys.argv[1], sys.argv[2]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*autologin-(user|session)\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[Seat:*]")
except StopIteration:
    lines.insert(0, "[Seat:*]")
    i = 0
lines[i + 1:i + 1] = ["autologin-user=" + user, "autologin-session=steam"]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
"""
    return r"""step "GDM : auto-connexion de $U"
mkdir -p /etc/gdm
GDM="/etc/gdm/custom.conf"
if [ -f "$GDM" ]; then
  cp -f "$GDM" "$GDM.bak-ps5-manager"
else
  printf '# GDM configuration storage\n\n[daemon]\n\n[security]\n\n[xdmcp]\n\n[chooser]\n\n[debug]\n#Enable=true\n' > "$GDM"
fi
python3 - "$GDM" "$U" <<'PY'
import io, re, sys
path, user = sys.argv[1], sys.argv[2]
lines = [l for l in io.open(path, encoding="utf-8").read().splitlines()
         if not re.match(r"\s*AutomaticLogin(Enable)?\s*=", l)]
try:
    i = next(n for n, l in enumerate(lines) if l.strip() == "[daemon]")
except StopIteration:
    lines.insert(0, "[daemon]")
    i = 0
lines[i + 1:i + 1] = ["AutomaticLoginEnable=True", "AutomaticLogin=" + user]
io.open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
PY
"""


def _gaming_scaling_block() -> str:
    """Mise à l'échelle de l'écran de connexion (GDM uniquement)."""
    if DISPLAY_MANAGER != "gdm":
        return (
            "step \"Facteur d'echelle de l'ecran de connexion : non modifie "
            f"({DISPLAY_MANAGER_LABEL})\"\n"
        )
    return (
        "step \"GDM : facteur d'echelle 1.5 (dconf)\"\n"
        "mkdir -p /etc/dconf/profile /etc/dconf/db/gdm.d\n"
        "printf 'user-db:user\\nsystem-db:gdm\\n' > /etc/dconf/profile/gdm\n"
        "printf '[org/gnome/desktop/interface]\\ntext-scaling-factor=1.5\\n' "
        "> /etc/dconf/db/gdm.d/00-scaling\n"
        "dconf update >/dev/null 2>&1 || true"
    )


def _gaming_script(kind: str) -> str:
    """Rend le script Gamescope demande pour l'utilisateur courant."""
    text = GAMING_INSTALL_SCRIPT if kind == "install" else GAMING_UNINSTALL_SCRIPT
    desk_name = T("switch_session") % DESKTOP_LABEL
    return (
        text.replace("__USER__", REAL_USER)
        .replace("__HOME__", REAL_HOME or f"/home/{REAL_USER}")
        .replace("__DESK_NAME__", desk_name)
        .replace("__SESSION_LABEL__", DESKTOP_LABEL)
        .replace("__SESSION__", DESKTOP_SESSION)
        .replace("__DM_SERVICE__", DM_SERVICE)
        .replace("__DISPLAY_MANAGER__", DISPLAY_MANAGER)
        .replace("__GAMING_ICON_B64__", ICONS_B64.get("gamescope", ""))
        .replace("__AUTOLOGIN_BLOCK__", _gaming_autologin_block())
        .replace("__SCALING_BLOCK__", _gaming_scaling_block())
    )


def open_uri(url: str) -> None:
    """Ouvre une URL dans le navigateur de l'utilisateur."""
    launcher = getattr(Gtk, "UriLauncher", None)
    if launcher is not None:
        try:
            launcher.new(url).launch(None, None, None)
            return
        except GLib.Error:
            pass
    Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
DECKY_INSTALL = (
    "https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh"
)
DECKY_UNINSTALL = (
    "https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/uninstall.sh"
)
FLATHUB_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"
OPERA_KEY = "https://rpm.opera.com/rpmrepo.key"
OPERA_REPO_FILE = "/etc/yum.repos.d/opera.repo"
BRAVE_REPO = "https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo"
BRAVE_KEY = "https://brave-browser-rpm-release.s3.brave.com/brave-core.asc"

LANG_FILE = "/etc/ps5-manager/language"
LOG_DIR = "/var/log/ps5-manager"
LOG_WINDOW_FILE = "/etc/ps5-manager/log-window"


# ------------------------------------------------------------------------------
# Utilisateur réel + élévation de privilèges (pkexec / sudo)
# ------------------------------------------------------------------------------
def detect_real_user() -> tuple[str, int, str]:
    user = os.environ.get("PS5_MANAGER_USER", "").strip()
    if not user:
        if os.geteuid() == 0:
            sudo_user = os.environ.get("SUDO_USER", "").strip()
            pkexec_uid = os.environ.get("PKEXEC_UID", "").strip()
            if sudo_user and sudo_user != "root":
                user = sudo_user
            elif pkexec_uid.isdigit() and int(pkexec_uid) != 0:
                try:
                    user = pwd.getpwuid(int(pkexec_uid)).pw_name
                except KeyError:
                    user = ""
            if not user:
                try:
                    login = os.getlogin()
                    if login and login != "root":
                        user = login
                except OSError:
                    pass
            if not user:
                user = "root"
        else:
            try:
                user = pwd.getpwuid(os.getuid()).pw_name
            except KeyError:
                user = os.environ.get("USER", "root")
    if not user or user == "UNKNOWN":
        user = "root"
    try:
        pw = pwd.getpwnam(user)
        return user, pw.pw_uid, pw.pw_dir or "/root"
    except KeyError:
        return user, 0, "/root"


REAL_USER, REAL_UID, REAL_HOME = detect_real_user()
try:
    _pw_real = pwd.getpwnam(REAL_USER)
    REAL_GID = _pw_real.pw_gid
    try:
        REAL_GROUPS = os.getgrouplist(REAL_USER, REAL_GID)
    except (AttributeError, OSError):
        REAL_GROUPS = [REAL_GID]
except KeyError:
    REAL_GID = 0
    REAL_GROUPS = [0]

# pkexec restreint PATH à /usr/sbin:/usr/bin:/sbin:/bin : restaurer /usr/local/bin (ex: ollama)
_base_paths = ["/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
if REAL_HOME and REAL_HOME != "/root":
    _base_paths.append(os.path.join(REAL_HOME, ".local", "bin"))
_cur_paths = [p for p in os.environ.get("PATH", "").split(":") if p]
for _p in _cur_paths:
    if _p not in _base_paths:
        _base_paths.append(_p)
os.environ["PATH"] = ":".join(_base_paths)

if not os.environ.get("DISPLAY"):
    os.environ["DISPLAY"] = ":0"
if os.path.isfile(os.path.join(REAL_HOME, ".Xauthority")) and not os.environ.get("XAUTHORITY"):
    os.environ["XAUTHORITY"] = os.path.join(REAL_HOME, ".Xauthority")
runtime_dir = f"/run/user/{REAL_UID}"
if os.path.isdir(runtime_dir):
    cur_xdg = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if not cur_xdg or (REAL_UID != 0 and cur_xdg == "/run/user/0"):
        os.environ["XDG_RUNTIME_DIR"] = runtime_dir
    bus_path = os.path.join(runtime_dir, "bus")
    if os.path.exists(bus_path) and not os.environ.get("DBUS_SESSION_BUS_ADDRESS", "").strip():
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
if os.environ.get("DBUS_SESSION_BUS_ADDRESS", "") == "":
    os.environ.pop("DBUS_SESSION_BUS_ADDRESS", None)


POLKIT_POLICY_PATH = "/usr/share/polkit-1/actions/io.github.nexgen999.ps5-manager.policy"

INTERFACE_DEPS = [
    "python3",
    "python3-gobject",
    "gtk4",
    "libadwaita",
    "gobject-introspection",
    "polkit",
    "glib2",
    "curl",
    "git",
    "desktop-file-utils",
    "polkit-gnome",
    "util-linux",
]


def ensure_polkit_policy() -> None:
    policy_xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="io.github.nexgen999.ps5-manager.pkexec">
    <description>Run PS5 Fedora Manager as root</description>
    <description xml:lang="fr">Exécuter PS5 Fedora Manager en tant que root</description>
    <message>Authentication is required to run PS5 Fedora Manager</message>
    <message xml:lang="fr">Une authentification est requise pour exécuter PS5 Fedora Manager</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/local/bin/ps5-manager</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
"""
    try:
        os.makedirs(os.path.dirname(POLKIT_POLICY_PATH), exist_ok=True)
        with open(POLKIT_POLICY_PATH, "w", encoding="utf-8") as fh:
            fh.write(policy_xml)
        os.chmod(POLKIT_POLICY_PATH, 0o644)
        os.chown(POLKIT_POLICY_PATH, 0, 0)
    except OSError:
        pass


def apply_install_permissions() -> None:
    """Applique les droits, propriétaires root:root et contextes SELinux."""
    for directory in (INSTALL_DIR, "/etc/ps5-manager", LOG_DIR):
        try:
            os.makedirs(directory, mode=0o755, exist_ok=True)
            os.chmod(directory, 0o755)
            os.chown(directory, 0, 0)
        except OSError:
            pass

    if os.path.isdir(INSTALL_DIR):
        for root_dir, dirs, files in os.walk(INSTALL_DIR):
            try:
                os.chown(root_dir, 0, 0)
                os.chmod(root_dir, 0o755)
            except OSError:
                pass
            for d in dirs:
                dp = os.path.join(root_dir, d)
                try:
                    os.chown(dp, 0, 0)
                    os.chmod(dp, 0o755)
                except OSError:
                    pass
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    os.chown(fp, 0, 0)
                    mode = 0o755 if f.endswith((".py", ".sh")) else 0o644
                    os.chmod(fp, mode)
                except OSError:
                    pass

    # Fichiers installés hors de INSTALL_DIR : propriétaire et droits stricts
    for path, mode in (
        ("/usr/local/bin/ps5-manager", 0o755),
        ("/usr/share/applications/ps5-manager.desktop", 0o644),
        ("/usr/share/pixmaps/ps5-manager.png", 0o644),
    ):
        if os.path.exists(path):
            try:
                os.chown(path, 0, 0)
                os.chmod(path, mode)
            except OSError:
                pass

    ensure_polkit_policy()

    if shutil.which("restorecon"):
        targets = [
            p for p in (
                INSTALL_DIR,
                "/usr/local/bin/ps5-manager",
                "/usr/share/applications/ps5-manager.desktop",
                "/usr/share/pixmaps/ps5-manager.png",
                POLKIT_POLICY_PATH,
                "/etc/ps5-manager",
                LOG_DIR,
            )
            if os.path.exists(p)
        ]
        if targets:
            subprocess.run(["restorecon", "-RF", *targets], capture_output=True)


# ------------------------------------------------------------------------------
# Ancienne installation (interface bash/zenity et GUI PyGObject) : ses fichiers
# sont purgés à l'installation, à la mise à jour et à la désinstallation.
# ------------------------------------------------------------------------------
LEGACY_PATHS = (
    "/usr/local/bin/ps5-manager-gui",
    "/usr/local/bin/ps5-manager-gui.py",
    f"{INSTALL_DIR}/ps5-manager.sh",
    f"{INSTALL_DIR}/ps5-manager.sh.next",
    f"{INSTALL_DIR}/ps5-manager-gui.py",
)


def remove_legacy_install(emit: Optional[Callable[[str], None]] = None) -> list[str]:
    """Supprime les restes de l'ancienne installation et renvoie les chemins retirés."""
    removed: list[str] = []
    for path in LEGACY_PATHS:
        if not os.path.lexists(path):
            continue
        try:
            os.remove(path)
        except OSError:
            continue
        removed.append(path)
    if emit is not None:
        for path in removed:
            emit(f"Ancien fichier supprimé : {path}")
    return removed


# ------------------------------------------------------------------------------
# Lancement depuis l'icône du menu (sans terminal)
# Sans agent PolicyKit graphique, pkexec retombe sur son agent texte : appelé
# depuis une icône il n'y a plus de terminal, l'authentification échoue et
# l'application ne s'ouvre jamais (constaté sous Budgie). On démarre donc un
# agent si nécessaire, on journalise les échecs et on les explique à l'écran.
# ------------------------------------------------------------------------------
LAUNCH_LOG_PATH = os.path.join(
    os.environ.get("XDG_CACHE_HOME") or os.path.join(REAL_HOME or "/tmp", ".cache"),
    "ps5-manager",
    "launcher.log",
)

_POLKIT_AGENT_NAMES = (
    "polkit-gnome-authentication-agent-1",
    "polkit-kde-authentication-agent-1",
    "polkit-mate-authentication-agent-1",
    "cinnamon-polkit-authentication-agent-1",
    "lxpolkit",
    "lxqt-policykit-agent",
    "xfce-polkit",
    "hyprpolkitagent",
)
_POLKIT_AGENT_DIRS = (
    "/usr/libexec",
    "/usr/lib/polkit-gnome",
    "/usr/lib/polkit-kde",
    "/usr/lib/mate-polkit",
    "/usr/lib/xfce-polkit",
    "/usr/lib/hyprpolkitagent",
    "/usr/local/libexec",
)


def launcher_log(message: str) -> None:
    """Journalise un échec de lancement hors terminal (icône du menu)."""
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
    try:
        os.makedirs(os.path.dirname(LAUNCH_LOG_PATH), exist_ok=True)
        with open(LAUNCH_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    try:
        if sys.stderr is not None:
            sys.stderr.write(line)
    except (OSError, ValueError):
        pass


def has_terminal() -> bool:
    """Un terminal interactif est-il attaché au processus ?

    L'agent texte de pkexec lit le mot de passe sur le terminal de contrôle :
    seul stdin compte (une sortie redirigée n'empêche pas l'authentification).
    """
    try:
        return bool(sys.stdin is not None and sys.stdin.isatty())
    except (OSError, ValueError):
        return False


def polkit_agent_paths() -> list[str]:
    """Agents PolicyKit graphiques installés sur la machine."""
    paths: list[str] = []
    for name in _POLKIT_AGENT_NAMES:
        found = shutil.which(name)
        if found and found not in paths:
            paths.append(found)
        for directory in _POLKIT_AGENT_DIRS:
            candidate = os.path.join(directory, name)
            if candidate not in paths and os.access(candidate, os.X_OK):
                paths.append(candidate)
    return paths


def polkit_agent_running() -> bool:
    """Un agent PolicyKit (graphique) tourne-t-il déjà dans la session ?

    Seul le nom du programme lancé (premier argument) est comparé : chercher le
    nom n'importe où dans la ligne de commande donnerait un faux positif avec
    n'importe quel processus dont le texte mentionne polkit.
    """
    if not shutil.which("ps"):
        return True  # impossible de vérifier : laisser pkexec essayer
    try:
        out = subprocess.run(
            ["ps", "-eo", "args="], capture_output=True, text=True, timeout=4
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        name = os.path.basename(line.split(" ", 1)[0])
        if name.startswith("polkit-") or name in (
            "lxpolkit",
            "lxqt-policykit-agent",
            "xfce-polkit",
            "hyprpolkitagent",
            "gnome-shell",
        ):
            return True
    return False


def start_polkit_agent() -> bool:
    """Démarre un agent PolicyKit graphique quand la session n'en a pas."""
    if polkit_agent_running():
        return True
    for path in polkit_agent_paths():
        try:
            subprocess.Popen(
                [path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=dict(os.environ),
            )
        except OSError as exc:
            launcher_log(f"Agent PolicyKit non démarré ({path}) : {exc}")
            continue
        for _ in range(20):
            time.sleep(0.1)
            if polkit_agent_running():
                launcher_log(f"Agent PolicyKit démarré : {path}")
                return True
    launcher_log("Aucun agent PolicyKit graphique disponible.")
    return False


def show_launch_error(code: int) -> None:
    """Explique l'échec d'élévation quand aucune fenêtre n'a pu s'ouvrir."""
    detail = f"pkexec : code {code} — journal : {LAUNCH_LOG_PATH}"
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gio, Gtk
    except (ImportError, ValueError):
        return

    class LaunchErrorApp(Adw.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id=f"{APP_ID}.LaunchError",
                flags=Gio.ApplicationFlags.NON_UNIQUE,
            )

        def do_activate(self) -> None:
            dialog = Adw.MessageDialog(
                heading="Authentification impossible / Authentication failed",
                body=(
                    "Aucun agent PolicyKit graphique n'est actif dans cette session : "
                    "le mot de passe ne peut pas être demandé depuis l'icône du menu.\n\n"
                    "• installez l'agent : sudo dnf install polkit-gnome\n"
                    "• ou lancez l'application depuis un terminal :\n"
                    "  pkexec /usr/local/bin/ps5-manager\n\n"
                    "No graphical PolicyKit agent is running, so the password prompt "
                    "cannot be shown from the menu icon. Install polkit-gnome or start "
                    "the application from a terminal."
                ),
            )
            dialog.add_response("close", "Fermer / Close")
            dialog.set_default_response("close")
            dialog.connect("response", lambda *_: self.quit())
            info = Gtk.Label(label=detail, selectable=True, wrap=True)
            info.add_css_class("dim-label")
            dialog.set_extra_child(info)
            dialog.present()

    try:
        LaunchErrorApp().run([sys.argv[0] if sys.argv else "ps5-manager"])
    except Exception as exc:  # noqa: BLE001
        launcher_log(f"Fenêtre d'erreur indisponible : {exc}")


def elevate_if_needed() -> None:
    if os.geteuid() == 0 or os.environ.get("PS5_MANAGER_ELEVATED"):
        return
    # Autorise root à afficher l'interface GTK4 sur Xwayland (Fedora Wayland)
    xhost = shutil.which("xhost")
    if xhost:
        subprocess.run([xhost, "+SI:localuser:root"], capture_output=True)
    self_path = os.path.abspath(sys.argv[0])
    env_args = [
        "PS5_MANAGER_ELEVATED=1",
        f"PS5_MANAGER_USER={REAL_USER}",
        f"PATH={os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')}",
        f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
        # Xwayland prioritaire en root, Wayland en secours
        "GDK_BACKEND=x11,wayland",
    ]
    for _k, _v in (
        ("WAYLAND_DISPLAY", os.environ.get("WAYLAND_DISPLAY", "")),
        ("XAUTHORITY", os.environ.get("XAUTHORITY", os.path.join(REAL_HOME, ".Xauthority"))),
        ("XDG_RUNTIME_DIR", os.environ.get("XDG_RUNTIME_DIR", runtime_dir if os.path.isdir(runtime_dir) else "")),
        ("DBUS_SESSION_BUS_ADDRESS", os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")),
    ):
        if _v:
            env_args.append(f"{_k}={_v}")
    pkexec = shutil.which("pkexec")
    if pkexec:
        cmd = [pkexec, "env", *env_args, sys.executable, self_path, *sys.argv[1:]]
        if has_terminal():
            # Terminal : pkexec utilise son agent texte, comportement habituel.
            try:
                os.execv(pkexec, cmd)
            except OSError as exc:
                launcher_log(f"pkexec n'a pas pu être lancé : {exc}")
        else:
            # Icône du menu : sans agent graphique, pkexec échoue en silence.
            agent_was_running = polkit_agent_running()
            started_agent = False if agent_was_running else start_polkit_agent()
            try:
                code = subprocess.call(cmd)
            except OSError as exc:
                launcher_log(f"pkexec n'a pas pu être lancé : {exc}")
                code = 127
            if code == 0:
                raise SystemExit(0)
            launcher_log(
                f"Échec de l'élévation (code {code}, "
                f"bureau {os.environ.get('XDG_CURRENT_DESKTOP', 'inconnu')}, "
                f"agent PolicyKit au départ : {'oui' if agent_was_running else 'non'})"
            )
            if started_agent:
                try:
                    code = subprocess.call(cmd)
                except OSError:
                    code = 127
                if code == 0:
                    raise SystemExit(0)
                launcher_log(f"Second échec de l'élévation (code {code})")
            show_launch_error(code)
            raise SystemExit(code)
    sudo = shutil.which("sudo")
    if sudo:
        os.execvp(
            sudo,
            [sudo, "-E", "env", *env_args, sys.executable, self_path, *sys.argv[1:]],
        )
    launcher_log("Ni pkexec ni sudo ne sont disponibles.")
    sys.stderr.write("Ce gestionnaire doit être lancé en root (pkexec ou sudo).\n")
    raise SystemExit(1)


if __name__ == "__main__":
    elevate_if_needed()
    os.environ["PS5_MANAGER_ELEVATED"] = "1"
    if os.geteuid() == 0:
        os.environ.setdefault("GDK_BACKEND", "x11,wayland")

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402


# ------------------------------------------------------------------------------
# Couleurs d'accentuation système GNOME (Fedora 41–45 / GNOME 47+)
# ------------------------------------------------------------------------------
# Valeurs Adwaita officielles (light/dark adaptées pour contraste >= 4.5:1)
GNOME_ACCENTS = {
    "blue": ("#3584e4", "#62a0ea", "#ffffff"),
    "teal": ("#2190a4", "#4eb2c5", "#ffffff"),
    "green": ("#3a944a", "#57c26a", "#ffffff"),
    "yellow": ("#c88800", "#e5a50a", "#1e1e1e"),
    "orange": ("#ed5b00", "#ff7800", "#ffffff"),
    "red": ("#e62d42", "#f66151", "#ffffff"),
    "pink": ("#d56199", "#e67fb1", "#ffffff"),
    "purple": ("#9141ac", "#c061cb", "#ffffff"),
    "slate": ("#6f8396", "#8ea1b4", "#ffffff"),
}

ADW_ACCENT_ENUM_MAP = {}
if hasattr(Adw, "AccentColor"):
    for _name in GNOME_ACCENTS:
        _enum_val = getattr(Adw.AccentColor, _name.upper(), None)
        if _enum_val is not None:
            ADW_ACCENT_ENUM_MAP[_enum_val] = _name


# ------------------------------------------------------------------------------
# Notes de version localisées (Adw.AboutDialog n'accepte que p, ul, ol, li, a)
# ------------------------------------------------------------------------------
_RELEASE_NOTES_TITLE = {
    "fr": "Nouveautés de la 0.12.0",
    "en": "What is new in 0.12.0",
    "es": "Novedades de la 0.12.0",
    "it": "Novità della 0.12.0",
    "de": "Neu in 0.12.0",
    "pt": "Novidades da 0.12.0",
}

_RELEASE_NOTES_ITEMS = {
    "fr": [
        "0.12 : section « Installation facile » — profils LAMP, LEMP, Code &amp; outils et Conteneurs, avec choix des composants, configuration (ServerName, dossier web, base de données) et la même fenêtre de progression que le setup 1 clic, qui reste inchangé",
        "0.11 : section « Serveur web » — Apache, Nginx, PHP + handler FastCGI, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, pare-feu et OpenSSH, chacun avec installation, mise à jour et désinstallation",
        "0.10 : page « Développement » (composants, outils en ligne de commande, applications) avec installation, mise à jour et désinstallation par entrée — dont Docker, KVM/QEMU, GitHub Desktop et un Forgejo local",
        "0.9.1 : Freebuff (agent de code IA) dans la page IA &amp; Développeur — installation, mise à jour et désinstallation via npm, lancement dans un terminal",
        "0.8.2 : boîte « À propos » entièrement traduite (notes de version, informations de débogage) et menu principal vérifié dans les six langues",
        "0.8.1 : le raccourci « Basculer Session » et la session Steam utilisent l'icône Gamescope (Steam Deck) fournie, installée dans le thème d'icônes",
        "0.8 : fenêtre « Système » repensée (logos Fedora, bureau et Gamescope, informations regroupées, copie en un clic) et traductions complétées en espagnol, italien, allemand et portugais",
        "0.7.1 : mode Gaming (Gamescope) réparé — retour au bureau à la fermeture de Steam, plus de relance en boucle, accès DRM et journal de session",
        "0.7 : interface en 6 langues (français, anglais, espagnol, italien, allemand, portugais du Brésil)",
        "0.6.1 : interfaces sans gel (Logithèque, Dépôts, IA), textes traduits et notes de version corrigées",
        "Boîte de bienvenue au premier lancement : setup recommandé en 1 clic ou configuration manuelle",
        "Fenêtre de suivi du setup : 9 étapes et 28/29 éléments selon le bureau, validation en direct et journal visible",
        "Redémarrage proposé à la fin du setup et menu principal « Effectuer le setup recommandé »",
        "Compatibilité GNOME, KDE Plasma, Cinnamon et Budgie : setup 1 clic, veille, logithèque, gestion mobile, impression et Gamescope s'adaptent au bureau et au gestionnaire de connexion",
        "0.4 : catégorie « Add Fedora Feature » (mobile, imprimantes &amp; scanners)",
    ],
    "en": [
        "0.12: “Easy setup” section — LAMP, LEMP, Code &amp; tools and Containers profiles, with component selection, configuration (ServerName, web root, database) and the same progress window as the 1-click setup, which stays unchanged",
        "0.11: “Web server” section — Apache, Nginx, PHP + FastCGI handler, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, firewall and OpenSSH, each with install, update and uninstall",
        "0.10: “Development” page (components, command-line tools, applications) with per-entry install, update and uninstall — including Docker, KVM/QEMU, GitHub Desktop and a local Forgejo",
        "0.9.1: Freebuff (AI coding agent) on the AI &amp; Developer page — npm install, update and uninstall, launch in a terminal",
        "0.8.2: fully translated “About” dialog (release notes, debug information) and main menu checked in all six languages",
        "0.8.1: the “Switch Session” shortcut and the Steam session now use the provided Gamescope (Steam Deck) icon, installed in the icon theme",
        "0.8: redesigned “System” window (Fedora, desktop and Gamescope logos, grouped information, one-click copy) and completed translations in Spanish, Italian, German and Portuguese",
        "0.7.1: Gaming Mode (Gamescope) fixed — closing Steam returns to the desktop, no more relaunch loop, DRM access and session log",
        "0.7: interface in 6 languages (French, English, Spanish, Italian, German, Brazilian Portuguese)",
        "0.6.1: no more UI freezes (app store, repositories, AI), translated texts and fixed release notes",
        "First-launch welcome dialog: 1-click recommended setup or manual configuration",
        "Setup progress window: 9 steps and 28/29 items depending on the desktop, live validation and visible log",
        "Reboot offered once the setup is finished, main menu “Run recommended setup”",
        "GNOME, KDE Plasma, Cinnamon and Budgie support: the 1-click setup, power, app store, mobile management, printing and Gamescope adapt to the desktop and display manager",
        "0.4: “Add Fedora Feature” category (mobile, printers &amp; scanners)",
    ],
    "es": [
        "0.12 : sección «Instalación fácil» — perfiles LAMP, LEMP, Código y herramientas y Contenedores, con selección de componentes, configuración (ServerName, carpeta web, base de datos) y la misma ventana de progreso que la configuración en 1 clic, que no cambia",
        "0.11 : sección «Servidor web» — Apache, Nginx, PHP + handler FastCGI, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, cortafuegos y OpenSSH, con instalación, actualización y desinstalación",
        "0.10 : página «Desarrollo» (componentes, herramientas de línea de comandos, aplicaciones) con instalación, actualización y desinstalación por entrada — incluidos Docker, KVM/QEMU, GitHub Desktop y un Forgejo local",
        "0.9.1 : Freebuff (agente de código IA) en la página IA y Desarrollo — instalación, actualización y desinstalación con npm, inicio en una terminal",
        "0.8.2 : diálogo «Acerca de» totalmente traducido (notas de versión, información de depuración) y menú principal revisado en los seis idiomas",
        "0.8.1 : el atajo «Cambiar de sesión» y la sesión Steam usan el icono Gamescope (Steam Deck) proporcionado, instalado en el tema de iconos",
        "0.8 : ventana «Sistema» rediseñada (logos de Fedora, escritorio y Gamescope, información agrupada, copia con un clic) y traducciones completadas en español, italiano, alemán y portugués",
        "0.7.1 : modo Gaming (Gamescope) reparado — vuelve al escritorio al cerrar Steam, sin reinicios en bucle, acceso DRM y registro de sesión",
        "0.7 : interfaz en 6 idiomas (francés, inglés, español, italiano, alemán, portugués de Brasil)",
        "0.6.1 : interfaces sin bloqueos (Tienda, Repositorios, IA), textos traducidos y notas de versión corregidas",
        "Diálogo de bienvenida en el primer inicio: configuración recomendada en 1 clic o configuración manual",
        "Ventana de seguimiento de la configuración: 9 pasos y 28/29 elementos según el escritorio, validación en directo y registro visible",
        "Reinicio propuesto al finalizar la configuración y menú principal «Ejecutar la configuración recomendada»",
        "Compatibilidad con GNOME, KDE Plasma, Cinnamon y Budgie: configuración en 1 clic, suspensión, tienda, gestión móvil, impresión y Gamescope se adaptan al escritorio y al gestor de sesiones",
        "0.4 : categoría «Add Fedora Feature» (móvil, impresoras y escáneres)",
    ],
    "it": [
        "0.12 : sezione «Installazione facile» — profili LAMP, LEMP, Codice e strumenti e Contenitori, con scelta dei componenti, configurazione (ServerName, cartella web, database) e la stessa finestra di avanzamento della configurazione in 1 clic, che resta invariata",
        "0.11 : sezione «Server web» — Apache, Nginx, PHP + handler FastCGI, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, firewall e OpenSSH, con installazione, aggiornamento e disinstallazione",
        "0.10 : pagina «Sviluppo» (componenti, strumenti da riga di comando, applicazioni) con installazione, aggiornamento e disinstallazione per voce — inclusi Docker, KVM/QEMU, GitHub Desktop e un Forgejo locale",
        "0.9.1 : Freebuff (agente di codice IA) nella pagina IA e Sviluppo — installazione, aggiornamento e disinstallazione con npm, avvio in un terminale",
        "0.8.2 : finestra «Informazioni su» completamente tradotta (note di versione, informazioni di debug) e menu principale verificato nelle sei lingue",
        "0.8.1 : il collegamento «Cambia sessione» e la sessione Steam usano l'icona Gamescope (Steam Deck) fornita, installata nel tema delle icone",
        "0.8 : finestra «Sistema» ridisegnata (logo Fedora, desktop e Gamescope, informazioni raggruppate, copia con un clic) e traduzioni completate in spagnolo, italiano, tedesco e portoghese",
        "0.7.1 : modalità Gaming (Gamescope) riparata — ritorno al desktop alla chiusura di Steam, nessun riavvio in loop, accesso DRM e log di sessione",
        "0.7 : interfaccia in 6 lingue (francese, inglese, spagnolo, italiano, tedesco, portoghese brasiliano)",
        "0.6.1 : interfacce senza blocchi (App store, Repository, IA), testi tradotti e note di versione corrette",
        "Finestra di benvenuto al primo avvio: configurazione consigliata in 1 clic o configurazione manuale",
        "Finestra di avanzamento della configurazione: 9 passaggi e 28/29 elementi secondo il desktop, verifica in tempo reale e log visibile",
        "Riavvio proposto al termine della configurazione e menu principale «Esegui la configurazione consigliata»",
        "Compatibilità con GNOME, KDE Plasma, Cinnamon e Budgie: configurazione in 1 clic, sospensione, app store, gestione mobile, stampa e Gamescope si adattano al desktop e al display manager",
        "0.4 : categoria «Add Fedora Feature» (mobile, stampanti e scanner)",
    ],
    "de": [
        "0.12 : Abschnitt „Einfache Installation“ – Profile LAMP, LEMP, Code &amp; Werkzeuge und Container mit Komponentenauswahl, Konfiguration (ServerName, Webverzeichnis, Datenbank) und demselben Fortschrittsfenster wie das 1-Klick-Setup, das unverändert bleibt",
        "0.11 : Abschnitt „Webserver“ – Apache, Nginx, PHP + FastCGI-Handler, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, Firewall und OpenSSH, jeweils mit Installation, Aktualisierung und Deinstallation",
        "0.10 : Seite „Entwicklung“ (Komponenten, Kommandozeilen-Werkzeuge, Anwendungen) mit Installation, Aktualisierung und Deinstallation pro Eintrag – inklusive Docker, KVM/QEMU, GitHub Desktop und einem lokalen Forgejo",
        "0.9.1 : Freebuff (KI-Coding-Agent) auf der Seite „KI &amp; Entwickler“ – npm-Installation, -Aktualisierung und -Deinstallation, Start in einem Terminal",
        "0.8.2 : Dialog „Info über“ vollständig übersetzt (Versionshinweise, Debug-Informationen) und Hauptmenü in allen sechs Sprachen geprüft",
        "0.8.1 : Die Verknüpfung „Sitzung wechseln“ und die Steam-Sitzung verwenden das mitgelieferte Gamescope-Symbol (Steam Deck), installiert im Icon-Theme",
        "0.8 : „System“-Fenster neu gestaltet (Fedora-, Desktop- und Gamescope-Logos, gruppierte Informationen, Kopieren mit einem Klick) und Übersetzungen für Spanisch, Italienisch, Deutsch und Portugiesisch vervollständigt",
        "0.7.1 : Gaming-Modus (Gamescope) repariert — Rückkehr zum Desktop beim Schließen von Steam, keine Neustartschleife mehr, DRM-Zugriff und Sitzungsprotokoll",
        "0.7 : Oberfläche in 6 Sprachen (Französisch, Englisch, Spanisch, Italienisch, Deutsch, brasilianisches Portugiesisch)",
        "0.6.1 : Oberflächen ohne Hänger (App-Store, Paketquellen, KI), übersetzte Texte und korrigierte Versionshinweise",
        "Willkommensdialog beim ersten Start: empfohlenes Setup mit einem Klick oder manuelle Einrichtung",
        "Setup-Fortschrittsfenster: 9 Schritte und 28/29 Elemente je nach Desktop, Live-Prüfung und sichtbares Protokoll",
        "Neustart am Ende des Setups angeboten und Hauptmenü „Empfohlenes Setup ausführen“",
        "Unterstützung für GNOME, KDE Plasma, Cinnamon und Budgie: 1-Klick-Setup, Energieoptionen, App-Store, Mobilgeräteverwaltung, Drucken und Gamescope passen sich an Desktop und Anmeldemanager an",
        "0.4 : Kategorie „Add Fedora Feature“ (Mobilgeräte, Drucker &amp; Scanner)",
    ],
    "pt": [
        "0.12 : secção «Instalação fácil» — perfis LAMP, LEMP, Código e ferramentas e Contêineres, com escolha de componentes, configuração (ServerName, pasta web, base de dados) e a mesma janela de progresso da configuração em 1 clique, que se mantém igual",
        "0.11 : secção «Servidor web» — Apache, Nginx, PHP + handler FastCGI, MariaDB, MySQL, Certbot, Cockpit, phpMyAdmin, Adminer, Webmin, firewall e OpenSSH, com instalação, atualização e desinstalação",
        "0.10 : página «Desenvolvimento» (componentes, ferramentas de linha de comando, aplicativos) com instalação, atualização e desinstalação por entrada — incluindo Docker, KVM/QEMU, GitHub Desktop e um Forgejo local",
        "0.9.1 : Freebuff (agente de código IA) na página IA e Programador — instalação, atualização e desinstalação com npm, arranque num terminal",
        "0.8.2 : caixa «Sobre» totalmente traduzida (notas de versão, informações de depuração) e menu principal verificado nos seis idiomas",
        "0.8.1 : o atalho «Alternar sessão» e a sessão Steam usam o ícone Gamescope (Steam Deck) fornecido, instalado no tema de ícones",
        "0.8 : janela «Sistema» redesenhada (logos do Fedora, da área de trabalho e do Gamescope, informações agrupadas, cópia com um clique) e traduções concluídas em espanhol, italiano, alemão e português",
        "0.7.1 : modo Gaming (Gamescope) corrigido — volta à área de trabalho ao fechar o Steam, sem reinícios em loop, acesso DRM e registro da sessão",
        "0.7 : interface em 6 idiomas (francês, inglês, espanhol, italiano, alemão, português do Brasil)",
        "0.6.1 : interfaces sem travamentos (Loja, Repositórios, IA), textos traduzidos e notas de versão corrigidas",
        "Diálogo de boas-vindas no primeiro início: configuração recomendada em 1 clique ou configuração manual",
        "Janela de acompanhamento da configuração: 9 etapas e 28/29 itens conforme a área de trabalho, validação ao vivo e registro visível",
        "Reinício proposto ao final da configuração e menu principal «Executar a configuração recomendada»",
        "Compatibilidade com GNOME, KDE Plasma, Cinnamon e Budgie: configuração em 1 clique, suspensão, loja, gestão móvel, impressão e Gamescope adaptam-se à área de trabalho e ao gerenciador de sessão",
        "0.4 : categoria «Add Fedora Feature» (celular, impressoras e scanners)",
    ],
}


def release_notes_html() -> str:
    """Notes de version localisées pour la boîte « À propos »."""
    lang = UI_LANG if UI_LANG in _RELEASE_NOTES_ITEMS else "en"
    bullets = "".join(f"<li>{item}</li>" for item in _RELEASE_NOTES_ITEMS[lang])
    return f"<p>{_RELEASE_NOTES_TITLE[lang]}</p><ul>{bullets}</ul>"


# ------------------------------------------------------------------------------
# Environnement de bureau : GNOME, KDE Plasma, Cinnamon, Budgie
# L'application tourne en root (pkexec) : l'environnement de la session
# graphique n'est pas forcément dans os.environ, on le retrouve donc via les
# variables, les processus de l'utilisateur réel puis loginctl.
# ------------------------------------------------------------------------------
DESKTOP_LABELS = {
    "gnome": "GNOME",
    "kde": "KDE Plasma",
    "cinnamon": "Cinnamon",
    "budgie": "Budgie",
    "unknown": "?",
}
# Nom de session XDG utilisé par AccountsService / les gestionnaires de connexion
DESKTOP_SESSIONS = {
    "gnome": "gnome",
    "kde": "plasma",
    "cinnamon": "cinnamon",
    "budgie": "budgie-desktop",
    "unknown": "gnome",
}
DESKTOP_NAMES = {
    "gdm": "GDM",
    "sddm": "SDDM",
    "lightdm": "LightDM",
}


def _desktop_from_string(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return ""
    if "kde" in value or "plasma" in value:
        return "kde"
    if "cinnamon" in value:
        return "cinnamon"
    if "budgie" in value:
        return "budgie"
    if "gnome" in value or value in ("ubuntu", "unity", "pop"):
        return "gnome"
    return ""


def _desktop_from_user_processes() -> str:
    """Lit XDG_CURRENT_DESKTOP dans l'environnement des processus de l'utilisateur."""
    try:
        pids = [name for name in os.listdir("/proc") if name.isdigit()]
    except OSError:
        return ""
    for pid in pids:
        try:
            if os.stat(f"/proc/{pid}").st_uid != REAL_UID:
                continue
            with open(f"/proc/{pid}/environ", "rb") as fh:
                data = fh.read(16384)
        except OSError:
            continue
        for entry in data.split(b"\0"):
            if entry.startswith(b"XDG_CURRENT_DESKTOP="):
                found = _desktop_from_string(
                    entry.split(b"=", 1)[1].decode("utf-8", "replace")
                )
                if found:
                    return found
    return ""


def _desktop_from_loginctl() -> str:
    if not shutil.which("loginctl"):
        return ""
    try:
        out = subprocess.run(
            ["loginctl", "list-sessions", "--no-legend"],
            capture_output=True, text=True, timeout=3,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] != REAL_USER:
            continue
        try:
            desktop = subprocess.run(
                ["loginctl", "show-session", parts[0], "-p", "Desktop", "--value"],
                capture_output=True, text=True, timeout=3,
            ).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        found = _desktop_from_string(desktop)
        if found:
            return found
    return ""


def detect_desktop() -> str:
    """Bureau réel : gnome | kde | cinnamon | budgie | unknown."""
    override = _desktop_from_string(os.environ.get("PS5_MANAGER_DESKTOP", ""))
    if override:
        return override
    for var in ("XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION"):
        found = _desktop_from_string(os.environ.get(var, ""))
        if found:
            return found
    for probe in (_desktop_from_user_processes, _desktop_from_loginctl):
        found = probe()
        if found:
            return found
    return "unknown"


def _display_manager_unit() -> str:
    """Gestionnaire de connexion réellement utilisé (display-manager.service)."""
    try:
        out = subprocess.run(
            ["systemctl", "show", "-p", "Id", "--value", "display-manager.service"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    if out.endswith(".service"):
        out = out[: -len(".service")]
    for dm in ("gdm", "sddm", "lightdm"):
        if out.startswith(dm):
            return dm
    return ""


def detect_display_manager() -> str:
    """Gestionnaire de connexion : gdm | sddm | lightdm."""
    # display-manager.service est le lien réellement démarré par systemd : seule
    # source fiable quand plusieurs gestionnaires sont installés (Cinnamon et
    # Budgie démarrent souvent LightDM alors que gdm.service reste « enabled »).
    found = _display_manager_unit()
    if found:
        return found
    for state in ("is-active", "is-enabled"):
        for dm in ("gdm", "sddm", "lightdm"):
            try:
                rc = subprocess.run(
                    ["systemctl", state, f"{dm}.service"],
                    capture_output=True, timeout=3,
                ).returncode
            except (OSError, subprocess.SubprocessError):
                rc = 1
            if rc == 0:
                return dm
    if os.path.isdir("/etc/sddm.conf.d") or os.path.exists("/etc/sddm.conf"):
        return "sddm"
    if os.path.isdir("/etc/lightdm"):
        return "lightdm"
    return "gdm"


def _accounts_service_session() -> str:
    """Session enregistrée par AccountsService (celle que la console démarre)."""
    try:
        with open(f"/var/lib/AccountsService/users/{REAL_USER}", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("Session="):
                    value = line.split("=", 1)[1].strip()
                    if value and value != "steam":
                        return value
    except OSError:
        pass
    return ""


DESKTOP_ID = detect_desktop()
DESKTOP_LABEL = DESKTOP_LABELS.get(DESKTOP_ID, "?")
DESKTOP_SESSION = _accounts_service_session() or DESKTOP_SESSIONS.get(DESKTOP_ID, "gnome")
DISPLAY_MANAGER = detect_display_manager()
DISPLAY_MANAGER_LABEL = DESKTOP_NAMES.get(DISPLAY_MANAGER, DISPLAY_MANAGER)
DM_SERVICE = f"{DISPLAY_MANAGER}.service"


def _desktop_tool(*names: str) -> Optional[str]:
    for name in names:
        if shutil.which(name):
            return name
    return None


def _kde_power_write(group: str, key: str, value: str) -> Optional[list[str]]:
    tool = _desktop_tool("kwriteconfig6", "kwriteconfig5")
    if not tool:
        return None
    return [
        tool, "--file", "powermanagementprofilesrc",
        "--group", "AC", "--group", group, "--key", key, value,
    ]


def _kde_power_read(group: str, key: str) -> str:
    tool = _desktop_tool("kreadconfig6", "kreadconfig5")
    if not tool:
        return ""
    try:
        return subprocess.run(
            [
                tool, "--file", "powermanagementprofilesrc",
                "--group", "AC", "--group", group, "--key", key,
            ],
            capture_output=True, text=True, timeout=3,
            **user_subprocess_kwargs(),
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _kde_power_reload() -> None:
    """Demande à Powerdevil de relire sa configuration."""
    tool = _desktop_tool("qdbus6", "qdbus")
    if not tool:
        return
    try:
        subprocess.run(
            [
                tool, "org.kde.Solid.PowerManagement",
                "/org/kde/Solid/PowerManagement",
                "org.kde.Solid.PowerManagement.reparseConfiguration",
            ],
            capture_output=True, timeout=5, **user_subprocess_kwargs(),
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _idle_schema() -> str:
    return (
        "org.cinnamon.desktop.session"
        if DESKTOP_ID == "cinnamon"
        else "org.gnome.desktop.session"
    )


def screen_sleep_state() -> bool:
    """La mise en veille de l'écran est-elle active ?"""
    if DESKTOP_ID == "kde":
        return _kde_power_read("DimDisplay", "idleTime") not in ("", "0")
    try:
        value = subprocess.run(
            ["gsettings", "get", _idle_schema(), "idle-delay"],
            capture_output=True, text=True, timeout=3,
            **user_subprocess_kwargs(),
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(value) and not (value.endswith(" 0") or value == "uint32 0")


def screen_sleep_commands(enable: bool) -> list[list[str]]:
    """Commandes utilisateur pour la mise en veille de l'écran du bureau courant."""
    if DESKTOP_ID == "kde":
        ms = "300000" if enable else "0"
        cmds = [
            _kde_power_write("DimDisplay", "idleTime", ms),
            _kde_power_write("DPMSControl", "idleTime", ms),
        ]
        return [cmd for cmd in cmds if cmd]
    return [["gsettings", "set", _idle_schema(), "idle-delay", "300" if enable else "0"]]


def full_sleep_commands(enable: bool) -> list[list[str]]:
    """Mise en veille complète (écran + suspension sur inactivité)."""
    cmds = screen_sleep_commands(enable)
    if DESKTOP_ID == "kde":
        ms = "300000" if enable else "0"
        for key, value in (("idleTime", ms), ("suspendType", "1" if enable else "0")):
            cmd = _kde_power_write("SuspendSession", key, value)
            if cmd:
                cmds.append(cmd)
        return cmds
    if DESKTOP_ID == "cinnamon":
        cmds.append([
            "gsettings", "set",
            "org.cinnamon.settings-daemon.plugins.power",
            "sleep-inactive-ac-type", "suspend" if enable else "nothing",
        ])
        return cmds
    # GNOME, Budgie et bureau non identifié (gnome-settings-daemon)
    cmds.append([
        "gsettings", "set",
        "org.gnome.settings-daemon.plugins.power",
        "sleep-inactive-ac-type", "suspend" if enable else "nothing",
    ])
    return cmds


def run_user_commands(cmds: list[list[str]]) -> int:
    """Exécute des commandes en tant qu'utilisateur réel ; renvoie le 1er code d'échec."""
    rc = 0
    for cmd in cmds:
        try:
            code = subprocess.run(cmd, timeout=30, **user_subprocess_kwargs()).returncode
        except (OSError, subprocess.SubprocessError):
            code = 1
        if code != 0 and rc == 0:
            rc = code
    if DESKTOP_ID == "kde":
        _kde_power_reload()
    return rc


def mobile_feature_packages() -> list[str]:
    """Paquets « gestion mobile » adaptés au bureau (GSConnect = GNOME seulement)."""
    base = ["gvfs-mtp", "fuse-sshfs", "android-tools"]
    if DESKTOP_ID == "kde":
        return ["kdeconnect-kde", "dolphin-plugins", *base]
    if DESKTOP_ID == "cinnamon":
        return [*base, "nemo-python"]
    if DESKTOP_ID == "budgie":
        return [*base, "nautilus-python"]
    return ["gnome-shell-extension-gsconnect", *base, "nautilus-python"]


def printer_feature_packages() -> list[str]:
    """CUPS et pilotes (communs) + l'interface d'imprimantes du bureau courant."""
    packages = [
        "cups",
        "cups-filters",
        "system-config-printer",
        "hplip",
        "gutenprint-cups",
        "splix",
        "sane-backends",
        "sane-backends-drivers-scanners",
        "libsane-hpaio",
        "simple-scan",
    ]
    if DESKTOP_ID == "kde":
        packages.append("print-manager")
    return packages


def _software_supported(item: Any) -> bool:
    """Masque les applications propres à GNOME sur les autres bureaux."""
    fp_id = getattr(item, "fp_id", "") or ""
    if fp_id == "com.mattjakeman.ExtensionManager":
        return DESKTOP_ID == "gnome"
    return True


# Groupes comps officiels Fedora : aucun dépôt tiers n'est nécessaire pour
# installer ou réparer le bureau lui-même.
DESKTOP_GROUPS = {
    "gnome": "gnome-desktop",
    "kde": "kde-desktop-environment",
    "cinnamon": "cinnamon-desktop-environment",
    "budgie": "budgie-desktop-environment",
}


def desktop_group() -> str:
    """Groupe comps du bureau détecté (dépôts Fedora officiels)."""
    return DESKTOP_GROUPS.get(DESKTOP_ID, DESKTOP_GROUPS["gnome"])


def _dnf_group_exists(group: str) -> bool:
    """Le groupe comps existe-t-il dans les dépôts configurés ?"""
    if not shutil.which("dnf"):
        return False
    try:
        res = subprocess.run(
            ["dnf", "group", "info", group], capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


def _install_desktop_group(win: "Ps5ManagerWindow") -> None:
    """Installe / répare les paquets du bureau depuis les dépôts Fedora.

    La vérification du groupe se fait dans la tâche de fond : `dnf group info`
    peut charger les métadonnées pendant plusieurs secondes, ce qui ne doit
    jamais bloquer la construction de la page.
    """
    group = desktop_group()

    def _task(emit: Callable[[str], None]) -> tuple[bool, str]:
        if not _dnf_group_exists(group):
            message = T("repo_de_missing") % group
            emit(message)
            return False, message
        rc = win.run_cmd_pty(["dnf", "group", "install", "-y", group], emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc

    win.run_task(f"@{group}", _task)


def logout_command() -> list[str]:
    """Commande de déconnexion du bureau courant (repli : loginctl)."""
    if DESKTOP_ID == "kde":
        tool = _desktop_tool("qdbus6", "qdbus")
        if tool:
            return [tool, "org.kde.Shutdown", "/Shutdown", "org.kde.Shutdown.logout"]
    if DESKTOP_ID == "cinnamon" and shutil.which("cinnamon-session-quit"):
        return ["cinnamon-session-quit", "--logout", "--force"]
    if shutil.which("gnome-session-quit") and DESKTOP_ID in ("gnome", "budgie", "unknown"):
        return ["gnome-session-quit", "--logout", "--force"]
    return ["loginctl", "terminate-user", REAL_USER]


def user_env() -> dict[str, str]:
    env = dict(os.environ)
    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
    if REAL_USER != "root":
        user_cwd = REAL_HOME if (REAL_HOME and os.path.isdir(REAL_HOME)) else "/tmp"
        env["HOME"] = REAL_HOME
        env["PWD"] = user_cwd
        env["USER"] = REAL_USER
        env["LOGNAME"] = REAL_USER
        env.pop("OLDPWD", None)
        for xdg_k in (
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_CACHE_HOME",
            "XDG_STATE_HOME",
            "CONTAINERS_CONF",
            "CONTAINERS_STORAGE_CONF",
            "TMPDIR",
        ):
            val = env.get(xdg_k, "")
            if val.startswith("/root"):
                env.pop(xdg_k, None)
    if os.path.isdir(runtime_dir):
        env["XDG_RUNTIME_DIR"] = runtime_dir
        bus_path = os.path.join(runtime_dir, "bus")
        if os.path.exists(bus_path):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_path}"
        else:
            env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    else:
        env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    user_paths = ["/usr/local/bin", "/usr/bin", "/bin"]
    if REAL_HOME and REAL_HOME != "/root":
        user_paths.insert(0, os.path.join(REAL_HOME, ".local", "bin"))
    env["PATH"] = ":".join(user_paths)
    return env


def user_subprocess_kwargs() -> dict[str, Any]:
    """Paramètres subprocess pour exécuter directement en tant que REAL_USER sans sudo/PAM."""
    if os.geteuid() == 0 and REAL_USER != "root":
        user_cwd = REAL_HOME if (REAL_HOME and os.path.isdir(REAL_HOME)) else "/tmp"
        return {
            "user": REAL_UID,
            "group": REAL_GID,
            "extra_groups": REAL_GROUPS,
            "cwd": user_cwd,
            "env": user_env(),
        }
    return {"env": user_env()}


def run_as_user_cmd(cmd: list[str]) -> list[str]:
    if os.geteuid() == 0 and REAL_USER != "root":
        user_paths = ["/usr/local/bin", "/usr/bin", "/bin"]
        if REAL_HOME and REAL_HOME != "/root":
            user_paths.insert(0, os.path.join(REAL_HOME, ".local", "bin"))
        env_kv = [
            f"HOME={REAL_HOME}",
            f"USER={REAL_USER}",
            f"LOGNAME={REAL_USER}",
            f"DISPLAY={os.environ.get('DISPLAY', ':0')}",
            f"PATH={':'.join(user_paths)}",
        ]
        if os.path.isdir(runtime_dir):
            env_kv.append(f"XDG_RUNTIME_DIR={runtime_dir}")
            bus_path = os.path.join(runtime_dir, "bus")
            if os.path.exists(bus_path):
                env_kv.append(f"DBUS_SESSION_BUS_ADDRESS=unix:path={bus_path}")
        return [
            "sudo",
            "-n",
            "-u",
            REAL_USER,
            "-H",
            "env",
            *env_kv,
            *cmd,
        ]
    return cmd


# ------------------------------------------------------------------------------
# Texte littéral dans l'interface
# Adw.PreferencesRow:use-markup vaut TRUE par défaut : un « & » non échappé
# casserait le libellé (titre vide). On désactive donc le markup pour les lignes.
# Les groupes (Adw.PreferencesGroup) affichent du texte brut : rien à échapper.
# ------------------------------------------------------------------------------
def plain_row(cls: Any, **kwargs: Any) -> Any:
    """Crée une ligne Adw dont le titre et le sous-titre sont du texte littéral.

    Adw.PreferencesRow:use-markup vaut TRUE par défaut : un titre contenant
    « & » passé au constructeur est analysé comme du Pango avant que le markup
    ne puisse être désactivé, d'où l'avertissement GTK « L'entité ne se termine
    pas par un point-virgule ». On construit donc la ligne sans texte, on coupe
    le markup, puis on renseigne titre et sous-titre : plus aucun avertissement
    et le « & » s'affiche tel quel.
    """
    title = kwargs.pop("title", None)
    subtitle = kwargs.pop("subtitle", None)
    row = cls(**kwargs)
    if hasattr(row, "set_use_markup"):
        row.set_use_markup(False)
    if title is not None and hasattr(row, "set_title"):
        row.set_title(title)
    if subtitle is not None and hasattr(row, "set_subtitle"):
        row.set_subtitle(subtitle)
    return row


def pref_group(**kwargs: Any) -> Adw.PreferencesGroup:
    """Crée un groupe de préférences dont le titre et la description sont littéraux.

    Adw.PreferencesGroup affiche titre et description en texte brut
    (gtk_label_set_label) : il ne faut donc pas échapper le markup, sinon un
    « & » apparaît littéralement sous la forme « &amp; » (« IA &amp; Développeur »).
    """
    return Adw.PreferencesGroup(**kwargs)


# Balises acceptées par Adw.AboutDialog pour release_notes : toute autre balise
# (b, i, span…) fait échouer l'analyse et remplace les notes par « Impossible
# d'analyser les notes de version ».
_NOTES_TAGS = ("p", "ul", "ol", "li", "a")


def _safe_release_notes(html: str) -> str:
    """Ne conserve que les balises comprises par Adw.AboutDialog."""

    def _keep(match: "re.Match[str]") -> str:
        return match.group(0) if match.group(1).lower() in _NOTES_TAGS else ""

    return re.sub(r"</?([A-Za-z][A-Za-z0-9]*)[^>]*>", _keep, html or "")


class SystemThemeSync:
    """
    Synchronise le thème sombre/clair et la couleur d'accentuation GNOME
    (org.gnome.desktop.interface accent-color & color-scheme) même lorsque
    l'application est lancée en root via pkexec.
    """

    def __init__(self) -> None:
        self.style_manager = Adw.StyleManager.get_default()
        self.css_provider = Gtk.CssProvider()
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        self.current_accent: str = "blue"
        self.current_dark: bool = True
        self.follow_system: bool = True
        self._timer_id: Optional[int] = None
        self._last_state: tuple[str, str] = ("", "")

    def start(self) -> None:
        self.refresh()
        self.style_manager.connect("notify::dark", lambda *_: self.refresh())
        if hasattr(self.style_manager, "props") and hasattr(
            self.style_manager.props, "accent_color"
        ):
            self.style_manager.connect("notify::accent-color", lambda *_: self.refresh())
        # Surveillance légère du dconf de REAL_USER (utile sous pkexec).
        # Seul GNOME expose accent-color / color-scheme : inutile ailleurs.
        if DESKTOP_ID == "gnome":
            self._timer_id = GLib.timeout_add_seconds(3, self._poll_user_gsettings)

    def _read_gsetting(self, key: str) -> str:
        try:
            res = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", key],
                capture_output=True,
                text=True,
                timeout=2,
                **user_subprocess_kwargs(),
            )
            if res.returncode == 0:
                return res.stdout.strip().strip("'\"")
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _poll_user_gsettings(self) -> bool:
        if not self.follow_system:
            return True
        accent = self._read_gsetting("accent-color")
        scheme = self._read_gsetting("color-scheme")
        if (accent, scheme) != self._last_state:
            self._last_state = (accent, scheme)
            self.apply(accent or self._native_accent_name(), scheme)
        return True

    def _native_accent_name(self) -> str:
        if hasattr(self.style_manager, "get_accent_color"):
            try:
                enum_val = self.style_manager.get_accent_color()
                if enum_val in ADW_ACCENT_ENUM_MAP:
                    return ADW_ACCENT_ENUM_MAP[enum_val]
            except Exception:
                pass
        return "blue"

    def refresh(self) -> None:
        accent = self._read_gsetting("accent-color") or self._native_accent_name()
        scheme = self._read_gsetting("color-scheme")
        self._last_state = (accent, scheme)
        self.apply(accent, scheme)

    def apply(self, accent_name: str, color_scheme: str = "") -> None:
        if accent_name not in GNOME_ACCENTS:
            accent_name = "blue"
        self.current_accent = accent_name

        if color_scheme == "prefer-dark":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            is_dark = True
        elif color_scheme == "prefer-light":
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            is_dark = False
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
            is_dark = bool(self.style_manager.get_dark())
        self.current_dark = is_dark

        bg_light, bg_dark, fg = GNOME_ACCENTS[accent_name]
        accent_bg = bg_light
        accent_text = bg_dark if is_dark else bg_light

        css = f"""
        @define-color accent_bg_color {accent_bg};
        @define-color accent_color {accent_text};
        @define-color accent_fg_color {fg};

        .ps5-accent-pill {{
            background-color: alpha(@accent_bg_color, 0.16);
            color: @accent_color;
            border-radius: 9999px;
            padding: 2px 10px;
            font-size: 0.82em;
            font-weight: 600;
        }}

        .ps5-status-ok {{
            color: #57e389;
            font-weight: 600;
        }}

        .ps5-status-warn {{
            color: #f8e45c;
            font-weight: 600;
        }}

        .ps5-status-err {{
            color: #ff7b63;
            font-weight: 600;
        }}

        list.navigation-sidebar row.ps5-sidebar-sep,
        list.navigation-sidebar row.ps5-sidebar-sep:hover,
        list.navigation-sidebar row.ps5-sidebar-sep:active,
        list.navigation-sidebar row.ps5-sidebar-sep:selected {{
            min-height: 1px;
            padding: 0;
            margin: 8px 12px;
            background: none;
            box-shadow: none;
            border-radius: 0;
        }}

        list.navigation-sidebar row.ps5-sidebar-sep separator {{
            min-height: 1px;
            background-color: alpha(currentColor, 0.15);
        }}
        """
        self.css_provider.load_from_data(css.encode("utf-8"))


# ------------------------------------------------------------------------------
# Traductions FR / EN (UI Libadwaita)
# ------------------------------------------------------------------------------
STRINGS = {
    "fr": {
        "app_title": "PS5 Fedora Manager",
        "search_placeholder": "Rechercher une option ou un logiciel…",
        "sys_group_session": "Session",
        "sys_group_software": "Logiciels",
        "sys_group_app": "Application",
        "sys_os": "Système d'exploitation",
        "sys_kernel": "Noyau Linux",
        "sys_arch": "Architecture",
        "sys_dnf": "Gestionnaire de paquets",
        "sys_desktop": "Environnement de bureau",
        "sys_dm": "Gestionnaire de connexion",
        "sys_session": "Session graphique",
        "sys_user": "Utilisateur",
        "sys_accent": "Couleur d'accentuation",
        "sys_gamescope": "Gamescope",
        "sys_steam": "Steam",
        "sys_installed": "Installé",
        "sys_version": "Version du manager",
        "sys_file": "Fichier",
        "sys_log": "Journal de session",
        "sys_open": "Ouvrir",
        "sys_copy": "Copier les informations",
        "sys_copy_done": "Informations copiées",
        "switch_session": "Basculer Session (%s / Steam)",
        "podman_linger": "Activer le maintien de session Podman (%s)",
        "podman_linger_sub": "loginctl enable-linger %s · démarre Open WebUI sans terminal",
        "debug_version": "Version",
        "ai_webui_state": "État : %s (%s) · Icône GNOME : %s",
        "ai_icon_installed": "installée",
        "ai_icon_absent": "absente",
        "ai_models_count": "%d modèle(s) · %d actif(s) en RAM",
        "system_info": "Système",
        "accent_label": "Couleur d'accentuation GNOME",
        "follow_gnome": "Synchronisée avec GNOME",
        "about": "À propos de PS5 Fedora Manager",
        "confirm": "Confirmer",
        "cancel": "Annuler",
        "ok": "Valider",
        "close": "Fermer",
        "running": "Traitement en cours…",
        "busy": "Une tâche est déjà en cours d'exécution.",
        "done": "Terminé.",
        "failed": "Échec (code %s)",
        "view_log": "Voir le journal",
        "clear": "Effacer",
        # Sections
        "sec_logs": "Journal / Logs",
        "sec_library": "Logithèque",
        "sec_aidev": "IA & Développeur",
        "sec_dev": "Développement",
        "sec_web": "Serveur web",
        "sec_easy": "Installation facile",
        "sec_deps": "Dépendances Supplémentaires",
        "sec_gaming": "Gaming Mode",
        "sec_fix": "Divers Fix",
        "sec_update": "Mise à jour du manager",
        "sec_lang": "Langues & clavier",
        "sec_repos": "Dépôts",
        "sec_users": "Utilisateurs",
        "sec_fedora": "Mises à jour Fedora",
        "sec_maint": "Maintenance",
        "sec_power": "Alimentation",
        "pwr_env": "Environnement de bureau détecté",
        "pwr_env_sub": "%s · commandes adaptées automatiquement",
        "pwr_note_gnome": "commande GNOME (gsettings, gnome-settings-daemon)",
        "pwr_note_kde": "commandes KDE Plasma (kwriteconfig6, Powerdevil)",
        "pwr_note_cinnamon": "commandes Cinnamon (gsettings)",
        "pwr_note_budgie": "commandes Budgie (gnome-settings-daemon)",
        "pwr_note_unknown": "bureau non identifié : commandes GNOME appliquées",
        "features_de_sub": "paquets adaptés à %s",
        "sec_fan": "Ventilateur",
        "sec_hw": "Hardware Control",
        "sec_mesa": "Mesa / Vulkan",
        "sec_kernel": "Kernel PS5",
        "sec_ui_lang": "Langue de l'interface",

        # Setup recommandé
        "setup_menu": "Effectuer le setup recommandé",
        "setup_title": "Setup recommandé",
        "setup_welcome_title": "Bienvenue dans PS5 Fedora Manager",
        "setup_welcome_body": (
            "Premier lancement. Le setup recommandé par le développeur applique "
            "en une seule fois la configuration de base de la PS5 sous Fedora :\n\n"
            "1. Alimentation (veille désactivée)\n"
            "2. Ventilateur (PS5 Linux Tools, ps5fan, ps5boost)\n"
            "3. Hardware Control\n"
            "4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n"
            "5. Dépôts (RPM Fusion, Flathub, cache)\n"
            "6. Dépendances (fuse, pilotes 32 bits, Python, venv, Tkinter, Node.js, mises à jour)\n"
            "7. Logithèque (Bazaar, Extension Manager (GNOME), Steam, Heroic, ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n"
            "8. Plugin Hardware Control\n"
            "9. Gaming Mode (Gamescope)\n\n"
            "Un redémarrage vous sera proposé à la fin. Vous pouvez aussi configurer "
            "l'environnement vous-même, section par section."
        ),
        "setup_welcome_recommended": "Setup recommandé (1 clic)",
        "setup_welcome_manual": "Configurer moi-même",
        "setup_confirm_body": (
            "Le setup recommandé installe et configure l'ensemble des éléments listés. "
            "Cela peut prendre plusieurs minutes ; la fenêtre de suivi affiche chaque "
            "élément validé et le journal des opérations."
        ),
        "setup_running": "Installation en cours…",
        "setup_finished": "Setup terminé",
        "setup_log": "Journal des opérations",
        "setup_env_line": "Environnement détecté : %s · %s · session %s",
        "setup_close": "Fermer",
        "setup_summary": "%d réussite(s) · %d échec(s)",
        "setup_reboot_title": "Redémarrage nécessaire",
        "setup_reboot_body": (
            "Setup terminé : %d élément(s) installé(s), %d échec(s).\n\n"
            "Un redémarrage est nécessaire pour activer les services et les pilotes. "
            "Redémarrer maintenant ?"
        ),
        "setup_reboot_now": "Redémarrer maintenant",
        "setup_later": "Plus tard",
        "setup_step1": "1. Alimentation",
        "setup_step2": "2. Ventilateur",
        "setup_step3": "3. Hardware Control",
        "setup_step4": "4. Mesa / Vulkan",
        "setup_step5": "5. Dépôts",
        "setup_step6": "6. Dépendances supplémentaires",
        "setup_step7": "7. Logithèque",
        "setup_step8": "8. Hardware Control — plugin",
        "setup_step9": "9. Gaming Mode",
        "setup_pwr_sys": "Désactiver la veille système",
        "setup_pwr_scr": "Désactiver la mise en veille de l'écran",
        "setup_pwr_full": "Désactiver la veille complète",
        "setup_fan_tools": "Installer / mettre à jour PS5 Linux Tools",
        "setup_fan_svc": "Activer le service ps5fan",
        "setup_fan_boot": "Activer le service ps5boost (démarrage)",
        "setup_hw": "Installer / mettre à jour Hardware Control",
        "setup_mesa": "Installer Vulkan Tools et Mesa Demos",
        "setup_repo_rpmfusion": "Installer RPM Fusion (free + nonfree)",
        "setup_repo_flathub": "Installer Flatpak et Flathub",
        "setup_repo_refresh": "Mettre à jour les dépôts et nettoyer le cache",
        "setup_dep_fuse": "Installer FUSE",
        "setup_dep_steam32": "Installer les pilotes graphiques 32 bits pour Steam",
        "setup_dep_python": "Installer Python 3 et pip",
        "setup_dep_venv": "Créer l'environnement virtuel my_project",
        "setup_dep_tk": "Installer Tkinter",
        "setup_dep_node": "Installer Node.js et npm",
        "setup_dep_fedora": "Mettre à jour les paquets Fedora",
        "setup_app_bazaar": "Installer Bazaar",
        "setup_app_extmgr": "Installer GNOME Extension Manager",
        "setup_app_steam": "Installer Steam",
        "setup_app_heroic": "Installer Heroic Games Launcher",
        "setup_app_protonup": "Installer ProtonUp-Qt",
        "setup_app_decky": "Installer Decky Loader",
        "setup_app_universe": "Installer Universe",
        "setup_app_appimagepool": "Installer AppImage Pool",
        "setup_app_opera": "Installer Opera",
        "setup_hw_plugin": "Installer le plugin Hardware Control",
        "setup_gaming": "Installer Gamescope (Gaming Mode)",

        "sec_features": "Add Fedora Feature",
        # Add Fedora Feature
        "features_group_mobile": "Gestion mobile",
        "features_group_mobile_sub": (
            "Téléphone Android en Wi-Fi ou en USB : fichiers, notifications, ADB et Fastboot."
        ),
        "features_mobile_install": "Installer GSConnect, MTP / SSHFS et ADB / Fastboot",
        "features_mobile_install_sub": (
            "gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs nautilus-python android-tools"
        ),
        "features_mobile_done": (
            "GSConnect est installé : activez l'extension depuis l'application "
            "« Extensions » puis appairez le téléphone."
        ),
        "features_group_print": "Imprimantes & scanners",
        "features_group_print_sub": (
            "CUPS, pilotes HP / Brother / Epson / Canon et génériques, découverte réseau, "
            "SANE et Simple Scan."
        ),
        "features_print_install": "Installer l'impression et la numérisation",
        "features_print_install_sub": (
            "cups cups-filters system-config-printer hplip gutenprint-cups splix "
            "sane-backends sane-backends-drivers-scanners libsane-hpaio simple-scan"
        ),
        "features_print_enable": "Activer le service d'impression (CUPS)",
        "features_print_enable_sub": "sudo systemctl enable --now cups",
        "features_print_disable": "Couper et désactiver le service CUPS",
        "features_print_disable_sub": "sudo systemctl disable --now cups",
        "features_print_disable_confirm": (
            "CUPS sera arrêté et désactivé : plus aucune impression possible "
            "tant que le service n'est pas réactivé."
        ),
        "features_print_sockets": "Désactiver les sockets d'activation automatique",
        "features_print_sockets_sub": "sudo systemctl disable --now cups.socket cups.path",
        "features_print_sockets_confirm": (
            "Sans cups.socket ni cups.path, CUPS ne redémarrera plus automatiquement "
            "lors d'une demande d'impression."
        ),
        "features_print_status": "Voir l'état du service CUPS",
        "features_print_status_sub": "systemctl status cups",
        # 14. Logs
        "logs_group_main": "Suivi en direct & historique",
        "logs_group_opts": "Préférences des journaux",
        "logs_live": "Fenêtre de log en direct",
        "logs_live_sub": "Suivre en direct ce que fait le gestionnaire",
        "logs_session": "Journal de cette session",
        "logs_old": "Anciens journaux",
        "logs_old_sub": "14 derniers jours, consultables un par un",
        "logs_auto": "Ouverture automatique",
        "logs_auto_sub": "Ouvrir la fenêtre au premier travail long",
        "logs_clear": "Effacer les journaux",
        "logs_clear_sub": "Supprime les fichiers de /var/log/ps5-manager",
        "logs_clear_confirm": "Supprimer tous les journaux enregistrés dans /var/log/ps5-manager ?",
        "logs_cleared": "Journaux effacés.",
        "logs_none": "Aucun journal enregistré pour le moment.",
        # 12. Library
        "lib_title": "Logithèque PS5",
        "lib_sub": "Installer, mettre à jour, vérifier ou désinstaller les applications essentielles",
        "lib_cat_gaming": "Gaming",
        "lib_cat_gaming_sub": "Lanceurs de jeux, couches de compatibilité Proton et plugins Steam",
        "lib_cat_browser": "Navigateurs",
        "lib_cat_browser_sub": "Navigateurs web (RPM officiel ou Flatpak)",
        "lib_cat_system": "Système & Utilitaires",
        "lib_cat_system_sub": "Outils disque, boutique Flatpak et extensions GNOME",
        "install": "Installer",
        "remove": "Désinstaller",
        "update": "Mettre à jour",
        "check": "Vérifier les mises à jour",
        "installed_rpm": "Installé (RPM)",
        "installed_flatpak": "Installé (Flatpak)",
        "installed": "Installé",
        "not_installed": "Non installé",
        "choose_format": "Quel format d'installation pour %s ?",
        "format_rpm": "RPM (dépôt officiel)",
        "format_flatpak": "Flatpak (Flathub)",
        # 1. Manager
        "mgr_title": "PS5 Fedora Manager",
        "mgr_update": "Mettre à jour le manager + ses dépendances",
        "mgr_update_sub": "git fetch + reset depuis GitHub et installation dans /opt/ps5-manager",
        "mgr_uninstall": "Désinstaller complètement le manager",
        "mgr_uninstall_sub": "Supprime /opt/ps5-manager, le lanceur et le raccourci bureau",
        "mgr_uninstall_confirm": "Supprimer le gestionnaire et tous ses fichiers système ?",
        # 2. Langues
        "lang_view": "Voir les langpacks installés (système + clavier)",
        "lang_view_sub": "Affiche rpm -qa langpacks-* et localectl status",
        "lang_install": "Installer une langue",
        "lang_install_sub": "Ex : fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8",
        "lang_install_prompt": "Code de langue (ex : fr_FR.UTF-8) :",
        "lang_full": "Configuration intégrale (langue + clavier + compte)",
        "lang_full_sub": "Applique la locale système, le clavier X11/console et le compte utilisateur",
        "lang_pick_locale": "Choisir la locale système",
        "lang_pick_kb": "Choisir la disposition clavier",
        "lang_logout_confirm": "Langue (%s) et clavier (%s) appliqués.\nFermer la session %s maintenant pour appliquer les changements ?",
        # 3. Dépôts
        "repo_list": "Voir tous les dépôts (RPM + Flatpak)",
        "repo_list_sub": "dnf repolist --all et dépôts Flatpak système/utilisateur",
        "repo_rpmfusion": "Installer RPM Fusion (free + nonfree)",
        "repo_rpmfusion_sub": "Indispensable pour Steam, codecs multimédias et pilotes",
        "repo_flathub": "Installer Flathub (portée système)",
        "repo_flathub_sub": "Dépôt principal des applications Flatpak",
        "repo_refresh": "Mettre à jour les dépôts & nettoyer le cache",
        "repo_openh264": "Activer le dépôt fedora-cisco-openh264",
        "repo_openh264_sub": "Codec H.264/AVC officiel Fedora (Firefox, GStreamer, navigation) — utile sur les quatre bureaux",
        "repo_codecs": "Installer les codecs multimédias (RPM Fusion)",
        "repo_codecs_sub": "gstreamer1-plugins-ugly et bad-free-extras : lecture H.264 / MPEG dans GNOME, KDE Plasma, Cinnamon et Budgie",
        "repo_de_title": "Dépôts du bureau %s",
        "repo_de_sub": "Aucun dépôt tiers n'est nécessaire : le groupe @%s vient des dépôts Fedora officiels",
        "repo_de_group": "Installer / réparer les paquets du bureau",
        "repo_de_missing": "Groupe @%s introuvable dans les dépôts configurés",
        "mnt_desktop_db": "Reconstruire la base des applications",
        "mnt_desktop_db_sub": "update-desktop-database /usr/share/applications + ~/.local/share/applications",
        "mnt_fonts": "Reconstruire le cache des polices",
        "mnt_fonts_sub": "fc-cache -f (après une mise à jour du bureau)",
        "mnt_kde_title": "Maintenance KDE Plasma",
        "mnt_kde_sub": "Caches propres à KDE Plasma",
        "mnt_kde_menu": "Reconstruire le cache des menus KDE",
        "mnt_kde_menu_sub": "kbuildsycoca6 --noincremental",
        "repo_refresh_sub": "dnf clean all, makecache --refresh et appstream Flatpak",
        "repo_add": "Ajouter un dépôt personnalisé (URL .repo)",
        "repo_add_prompt": "URL du fichier .repo :",
        "repo_disable": "Désactiver un dépôt DNF",
        "repo_disable_sub": "Désactive sans supprimer le fichier .repo",
        "repo_rm_dnf": "Supprimer un dépôt DNF (fichier .repo)",
        "repo_rm_flatpak": "Supprimer un dépôt Flatpak",
        "repo_id_prompt": "ID du dépôt (ex : rpmfusion-nonfree) :",
        "repo_fp_prompt": "Nom du dépôt Flatpak (ex : flathub) :",
        # 4. Utilisateurs
        "usr_list": "Voir la liste des utilisateurs",
        "usr_list_sub": "Comptes humains (UID >= 1000) dans /etc/passwd",
        "usr_edit_me": "Éditer mon compte (%s)",
        "usr_edit_me_sub": "Changer le mot de passe et la langue du compte",
        "usr_add": "Ajouter un utilisateur",
        "usr_del": "Supprimer un compte utilisateur",
        "usr_root": "Compte root : état et mot de passe",
        "usr_name_prompt": "Nom du compte :",
        "usr_pass_prompt": "Mot de passe :",
        "usr_new_pass_prompt": "Nouveau mot de passe (laisser vide pour ne pas changer) :",
        "usr_del_confirm": "Supprimer définitivement le compte %s et son dossier personnel ?",
        # 5. Mises à jour Fedora
        "fed_apps": "Mettre à jour les applications (DNF & Flatpak)",
        "fed_apps_sub": "dnf upgrade -y suivi de flatpak update --system",
        "fed_sys": "Mettre à jour le système complet",
        "fed_sys_sub": "dnf upgrade --refresh -y",
        "fed_lang": "Mettre à jour les langpacks",
        "fed_lang_sub": "dnf upgrade -y langpacks-* glibc-langpack-*",
        "fed_meta": "Rafraîchir les métadonnées des dépôts",
        # 6. Maintenance
        "mnt_all": "Nettoyage complet",
        "mnt_all_sub": "Caches DNF, journaux > 7j, /tmp, vignettes et Flatpak inutilisés",
        "mnt_cache": "Nettoyer uniquement le cache DNF",
        "mnt_autoremove": "Supprimer les paquets orphelins (autoremove)",
        "mnt_journal": "Réduire les journaux systemd (7 jours)",
        "mnt_tmp": "Nettoyer /tmp et /var/tmp",
        "mnt_thumbs": "Nettoyer les vignettes utilisateur",
        "mnt_kernels": "Supprimer les anciens kernels (garder 2)",
        "mnt_disk": "Voir l'espace disque utilisé (df -h)",
        # 7. Alimentation
        "pwr_full": "Veille complète (système + écran)",
        "pwr_full_sub": "Masque/démasque sleep.target et configure l'extinction écran (5 min)",
        "pwr_sys": "Veille système (suspend / hibernate)",
        "pwr_sys_sub": "État de systemd sleep/suspend/hibernate.target",
        "pwr_scr": "Mise en veille de l'écran (5 min)",
        "pwr_scr_sub": "org.gnome.desktop.session idle-delay",
        "pwr_enable_full": "Activer la veille complète",
        "pwr_disable_full": "Désactiver la veille complète",
        # 8. Ventilateur
        "fan_status": "Voir le status complet (services + ps5_control)",
        "fan_svc": "Service ps5fan (ventilation)",
        "fan_svc_sub": "Activer / démarrer au boot (ps5fan.service)",
        "fan_boost": "Service ps5boost (mode boost)",
        "fan_boost_sub": "Activer / démarrer ps5boost.service",
        "fan_restart": "Relancer ps5fan.service",
        "fan_tools": "Installer / mettre à jour ps5-linux-tools",
        "fan_tools_sub": "Clone et compile ps5-linux/ps5-linux-tools",
        # 9. Hardware Control
        "hw_check": "Vérifier la présence du matériel PS5",
        "hw_check_sub": "Inspecte /sys/class/hwmon et les noeuds sysfs PS5",
        "hw_install": "Installer / Mettre à jour PS5 Hardware Control",
        "hw_install_sub": "Installe python3-PyQt6 puis NotHavocc/ps5-hwcon-gui (--passwordless)",
        "hw_check_upd": "Vérifier les mises à jour sur GitHub",
        "hw_uninstall": "Désinstaller PS5 Hardware Control",
        "hw_plugin_group": "Hardware Control Plugin",
        "hw_plugin_group_sub": "Plugin Decky (mode Jeu) : ventilateur, horloges CPU/GPU et LED",
        "hw_plugin_install": "Installer le plugin Hardware Control",
        "hw_plugin_install_sub": "Récupère les sources, compile et installe dans Decky Loader",
        "hw_plugin_uninstall": "Désinstaller le plugin Hardware Control",
        "hw_plugin_uninstall_confirm": "Supprimer le plugin Hardware Control et redémarrer Decky Loader ?",
        "deps_group": "Paquets système",
        "deps_group_sub": "Paquets souvent réclamés par Steam, Proton, Flatpak et les AppImage",
        "deps_fuse": "Fuse (fusermount)",
        "deps_fuse_sub": "Pile FUSE : montage de systèmes de fichiers en espace utilisateur (fusermount, AppImage de type extract-and-run, runtimes Flatpak). fuse-libs fournit libfuse.so, utilisée par de nombreux outils.",
        "deps_steam32": "Steam — pilotes graphiques 32 bits",
        "deps_steam32_sub": "Mesa Vulkan et DRI 32 bits + VA-API 32 bits : sans eux, Steam, Proton/Wine et les jeux 32 bits perdent l'accélération graphique et le décodage vidéo matériel.",
        "gaming_group": "Gamescope / session Steam Big Picture",
        "gaming_group_sub": "Session Steam + bascule GNOME / Steam sur le compte courant (redémarrage nécessaire)",
        "gaming_log": "Journal du mode Gaming",
        "gaming_log_sub": "Afficher le journal de la session Gamescope (erreur de lancement, retour au bureau)",
        "gaming_log_empty": "Aucun journal de session Gaming pour le moment.",
        "gaming_install": "Installer Gamescope",
        "gaming_install_sub": "Session Steam Big Picture, auto-connexion GDM, bascule GNOME/Steam et raccourcis",
        "gaming_uninstall": "Désinstaller Gamescope",
        "gaming_uninstall_confirm": "Supprimer la session Gamescope, la bascule GNOME/Steam, la règle sudoers et les raccourcis ?",
        "fix_group": "Steam",
        "fix_group_sub": "Réparations rapides quand Steam se bloque",
        "fix_steam": "Relancer Steam",
        "fix_steam_sub": "Tue tous les processus Steam (pkill -9 steam) puis relance Steam : corrige une fenêtre noire, un « Steam is already running » ou un client resté en arrière-plan.",
        "fix_steam_confirm": "Fermer brutalement tous les processus Steam puis relancer Steam ?",
        "lib_appimage_group": "Gestion d'AppImage",
        "lib_appimage_group_sub": "AppImage Pool et Gear Lever, installés depuis Flathub",
        "appimage_pool_desc": "Parcourir AppImageHub et installer des AppImage en quelques clics (io.github.prateekmedia.appimagepool).",
        "appimage_gear_desc": "Intègre les AppImage au menu des applications : icône, mises à jour et gestion des versions (it.mijorus.gearlever).",
        "appimage_install": "Installer",
        "appimage_update": "Mettre à jour",
        "appimage_uninstall": "Désinstaller",
        "appimage_uninstall_confirm": "Désinstaller %s (flatpak) ?",
        "appimage_flathub": "Ouvrir la page Flathub",
        "deps_python_group": "Python 3",
        "deps_python_group_sub": "Interpréteur, pip, Tkinter et environnement virtuel",
        "deps_python": "Python 3 + pip",
        "deps_python_sub": "python3, python3-pip : interpréteur et gestionnaire de paquets Python.",
        "deps_python_venv": "Créer l'environnement virtuel my_project",
        "deps_python_venv_sub": "python3 -m venv my_project puis source my_project/bin/activate (dans le dossier personnel).",
        "deps_python_venv_ready": "Environnement créé dans %s. Activation dans un terminal :\nsource %s/bin/activate",
        "deps_python_versions": "Vérifier les versions Python",
        "deps_python_versions_sub": "Affiche la sortie de python3 --version et pip3 --version.",
        "deps_tkinter": "Tkinter (python3-tkinter)",
        "deps_tkinter_sub": "Interface graphique Tk pour Python : IDLE, tkinter, TkAgg de matplotlib.",
        "deps_node_group": "Node.js / npm",
        "deps_node_group_sub": "Runtime JavaScript et gestionnaire de paquets",
        "deps_node_install": "Installer Node.js + npm",
        "deps_node_install_sub": "nodejs et npm depuis les dépôts Fedora.",
        "deps_node_update": "Mettre à jour (dépôts Fedora)",
        "deps_node_update_sub": "dnf upgrade --refresh nodejs npm : corrige les mises à jour mineures.",
        "deps_node_major": "Passer à la version majeure récente (NodeSource 26 LTS)",
        "deps_node_major_sub": "Ajoute le dépôt NodeSource 26 LTS puis réinstalle nodejs : nécessaire pour changer de version majeure.",
        "deps_node_versions": "Vérifier les versions Node.js",
        "deps_node_versions_sub": "Affiche la sortie de node --version et npm --version.",
        "deps_node_uninstall": "Désinstaller Node.js + npm",
        "deps_node_uninstall_confirm": "Supprimer nodejs et npm du système ?",
        # 10. Mesa / Vulkan
        "mesa_tools": "Installer les outils Vulkan & Mesa demos",
        "mesa_tools_sub": "vulkan-tools et mesa-demos",
        "mesa_upd": "Mettre à jour les paquets Mesa & Vulkan",
        "mesa_upd_sub": "dnf upgrade -y mesa* vulkan*",
        "mesa_radv": "Vérifier la prise en charge RADV (GPU AMD PS5)",
        "mesa_summary": "Afficher le résumé Vulkan complet",
        # 11. Kernel PS5
        "krn_latest": "Vérifier la dernière version disponible",
        "krn_latest_sub": "Depuis ps5-linux/ps5-linux-patches sur GitHub",
        "krn_install": "Installer le dernier kernel PS5 (RPM)",
        "krn_install_sub": "rpm -ivh --nosignature --replacefiles puis déploiement EFI",
        "krn_boot": "Choisir le kernel à démarrer (/boot/efi)",
        "krn_none": "Aucun paquet kernel trouvé.",
        "krn_boot_none": "Aucun kernel dans /boot",
        "krn_no_old": "Aucun ancien noyau à supprimer.",
        "krn_files_missing": "vmlinuz-%s ou initrd.img-%s absent.",
        "gh_unreachable": "Impossible de contacter GitHub.",
        "gh_release_missing": "Release introuvable.",
        "repo_none": "Aucun fichier .repo pour [%s]",
        "usr_refuse": "Refusé pour %s",
        "mesa_no_vulkaninfo": "vulkaninfo absent — installez d'abord vulkan-tools.",
        "ai_ollama_absent": "Ollama n'est pas installé.",
        "ai_podman_absent": "Podman n'est pas installé.",
        "krn_boot_sub": "Copie vmlinuz et initrd.img sélectionnés vers l'ESP",
        "krn_remove": "Nettoyer / supprimer d'anciens kernels",
        "krn_remove_sub": "Supprime les anciens paquets linux-ps5 en protégeant le noyau actif",
        "krn_running": "Démarré",
        "krn_esp": "Sur /boot/efi",
        "krn_installed": "Installé",
        "krn_protected": "Protégé (actif / boot)",
        "krn_pick": "Installer un kernel précis (toutes les releases)",
        "krn_pick_sub": "Télécharge le RPM linux-ps5 de la release choisie : permet de revenir sur un ancien kernel",
        "krn_pick_empty": "Aucune release récupérée depuis GitHub.",
        "krn_available": "Non installé",
        "krn_releases_page": "Ouvrir la page GitHub des releases",
        "krn_no_rpm": "Cette release ne publie pas de RPM (paquet Arch uniquement).\nChoisissez une version qui propose un .rpm x86_64.",
        # 13. UI Lang
        "ui_lang_title": "Langue de l'interface",
        "ui_lang_sub": "Changement immédiat et mémorisé dans /etc/ps5-manager/language",
        "fr_label": "Français",
        "en_label": "English",
        # 15. IA & Développeur
        "aidev_open_sub": "Ollama, Open WebUI (Podman), VSCodium, Freebuff et modèles IA locaux",
        "aidev_stack": "Outils & Applications IA / Dev",
        "aidev_stack_sub": "Installation, mise à jour et désinstallation des briques locales",
        "aidev_services": "Contrôle des services IA",
        "aidev_services_sub": "Démarrer, arrêter ou désactiver au démarrage pour libérer la RAM",
        "aidev_models": "Modèles IA locaux (Ollama)",
        "aidev_models_sub": "Télécharger, inspecter, décharger de la RAM ou supprimer les modèles",
        "aidev_extras": "Diagnostic & Maintenance IA (PS5)",
        "aidev_extras_sub": "Vérification RAM/GPU, nettoyage Podman et persistance",
    },
    "en": {
        "app_title": "PS5 Fedora Manager",
        "search_placeholder": "Search an option or software…",
        "sys_group_session": "Session",
        "sys_group_software": "Software",
        "sys_group_app": "Application",
        "sys_os": "Operating system",
        "sys_kernel": "Linux kernel",
        "sys_arch": "Architecture",
        "sys_dnf": "Package manager",
        "sys_desktop": "Desktop environment",
        "sys_dm": "Display manager",
        "sys_session": "Graphical session",
        "sys_user": "User",
        "sys_accent": "Accent colour",
        "sys_gamescope": "Gamescope",
        "sys_steam": "Steam",
        "sys_installed": "Installed",
        "sys_version": "Manager version",
        "sys_file": "File",
        "sys_log": "Session log",
        "sys_open": "Open",
        "sys_copy": "Copy the information",
        "sys_copy_done": "Information copied",
        "switch_session": "Switch Session (%s / Steam)",
        "podman_linger": "Enable Podman session lingering (%s)",
        "podman_linger_sub": "loginctl enable-linger %s · starts Open WebUI without a terminal",
        "debug_version": "Version",
        "ai_webui_state": "State: %s (%s) · GNOME icon: %s",
        "ai_icon_installed": "installed",
        "ai_icon_absent": "missing",
        "ai_models_count": "%d model(s) · %d active in RAM",
        "system_info": "System",
        "accent_label": "GNOME Accent Color",
        "follow_gnome": "Synced with GNOME",
        "about": "About PS5 Fedora Manager",
        "confirm": "Confirm",
        "cancel": "Cancel",
        "ok": "Apply",
        "close": "Close",
        "running": "Working…",
        "busy": "A task is already running.",
        "done": "Done.",
        "failed": "Failed (code %s)",
        "view_log": "View log",
        "clear": "Clear",
        # Sections
        "sec_logs": "Logs",
        "sec_library": "Software library",
        "sec_aidev": "AI & Developer",
        "sec_dev": "Development",
        "sec_web": "Web server",
        "sec_easy": "Easy setup",
        "sec_deps": "Additional Dependencies",
        "sec_gaming": "Gaming Mode",
        "sec_fix": "Misc Fixes",
        "sec_update": "Manager update",
        "sec_lang": "Languages & keyboard",
        "sec_repos": "Repositories",
        "sec_users": "Users",
        "sec_fedora": "Fedora updates",
        "sec_maint": "Maintenance",
        "sec_power": "Power",
        "pwr_env": "Detected desktop environment",
        "pwr_env_sub": "%s · commands adapted automatically",
        "pwr_note_gnome": "GNOME commands (gsettings, gnome-settings-daemon)",
        "pwr_note_kde": "KDE Plasma commands (kwriteconfig6, Powerdevil)",
        "pwr_note_cinnamon": "Cinnamon commands (gsettings)",
        "pwr_note_budgie": "Budgie commands (gnome-settings-daemon)",
        "pwr_note_unknown": "desktop not identified: GNOME commands applied",
        "features_de_sub": "packages adapted to %s",
        "sec_fan": "Fan",
        "sec_hw": "Hardware Control",
        "sec_mesa": "Mesa / Vulkan",
        "sec_kernel": "PS5 Kernel",
        "sec_ui_lang": "Interface language",

        # Recommended setup
        "setup_menu": "Run recommended setup",
        "setup_title": "Recommended setup",
        "setup_welcome_title": "Welcome to PS5 Fedora Manager",
        "setup_welcome_body": (
            "First launch. The developer-recommended setup applies the whole base "
            "configuration of a PS5 running Fedora in one go:\n\n"
            "1. Power (sleep disabled)\n"
            "2. Fan (PS5 Linux Tools, ps5fan, ps5boost)\n"
            "3. Hardware Control\n"
            "4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n"
            "5. Repositories (RPM Fusion, Flathub, cache)\n"
            "6. Dependencies (fuse, 32-bit drivers, Python, venv, Tkinter, Node.js, updates)\n"
            "7. App store (Bazaar, Extension Manager (GNOME), Steam, Heroic, ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n"
            "8. Hardware Control plugin\n"
            "9. Gaming Mode (Gamescope)\n\n"
            "A reboot will be offered at the end. You can also configure the "
            "environment yourself, section by section."
        ),
        "setup_welcome_recommended": "Recommended setup (1 click)",
        "setup_welcome_manual": "I'll configure it myself",
        "setup_confirm_body": (
            "The recommended setup installs and configures every listed item. "
            "It can take several minutes; the progress window shows each validated "
            "item and the operations log."
        ),
        "setup_running": "Installing…",
        "setup_finished": "Setup finished",
        "setup_log": "Operations log",
        "setup_env_line": "Detected environment: %s · %s · session %s",
        "setup_close": "Close",
        "setup_summary": "%d succeeded · %d failed",
        "setup_reboot_title": "Reboot required",
        "setup_reboot_body": (
            "Setup finished: %d item(s) installed, %d failed.\n\n"
            "A reboot is required to enable the services and drivers. "
            "Reboot now?"
        ),
        "setup_reboot_now": "Reboot now",
        "setup_later": "Later",
        "setup_step1": "1. Power",
        "setup_step2": "2. Fan",
        "setup_step3": "3. Hardware Control",
        "setup_step4": "4. Mesa / Vulkan",
        "setup_step5": "5. Repositories",
        "setup_step6": "6. Extra dependencies",
        "setup_step7": "7. App store",
        "setup_step8": "8. Hardware Control — plugin",
        "setup_step9": "9. Gaming Mode",
        "setup_pwr_sys": "Disable system sleep",
        "setup_pwr_scr": "Disable screen blanking",
        "setup_pwr_full": "Disable full sleep",
        "setup_fan_tools": "Install / update PS5 Linux Tools",
        "setup_fan_svc": "Enable the ps5fan service",
        "setup_fan_boot": "Enable the ps5boost service (boot)",
        "setup_hw": "Install / update Hardware Control",
        "setup_mesa": "Install Vulkan Tools and Mesa Demos",
        "setup_repo_rpmfusion": "Install RPM Fusion (free + nonfree)",
        "setup_repo_flathub": "Install Flatpak and Flathub",
        "setup_repo_refresh": "Refresh repositories and clean the cache",
        "setup_dep_fuse": "Install FUSE",
        "setup_dep_steam32": "Install 32-bit graphics drivers for Steam",
        "setup_dep_python": "Install Python 3 and pip",
        "setup_dep_venv": "Create the my_project virtual environment",
        "setup_dep_tk": "Install Tkinter",
        "setup_dep_node": "Install Node.js and npm",
        "setup_dep_fedora": "Update Fedora packages",
        "setup_app_bazaar": "Install Bazaar",
        "setup_app_extmgr": "Install GNOME Extension Manager",
        "setup_app_steam": "Install Steam",
        "setup_app_heroic": "Install Heroic Games Launcher",
        "setup_app_protonup": "Install ProtonUp-Qt",
        "setup_app_decky": "Install Decky Loader",
        "setup_app_universe": "Install Universe",
        "setup_app_appimagepool": "Install AppImage Pool",
        "setup_app_opera": "Install Opera",
        "setup_hw_plugin": "Install the Hardware Control plugin",
        "setup_gaming": "Install Gamescope (Gaming Mode)",

        "sec_features": "Add Fedora Feature",
        # Add Fedora Feature
        "features_group_mobile": "Mobile management",
        "features_group_mobile_sub": (
            "Android phone over Wi-Fi or USB: files, notifications, ADB and Fastboot."
        ),
        "features_mobile_install": "Install GSConnect, MTP / SSHFS and ADB / Fastboot",
        "features_mobile_install_sub": (
            "gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs nautilus-python android-tools"
        ),
        "features_mobile_done": (
            "GSConnect is installed: enable the extension from the Extensions app, "
            "then pair your phone."
        ),
        "features_group_print": "Printers & scanners",
        "features_group_print_sub": (
            "CUPS, HP / Brother / Epson / Canon and generic drivers, network discovery, "
            "SANE and Simple Scan."
        ),
        "features_print_install": "Install printing and scanning",
        "features_print_install_sub": (
            "cups cups-filters system-config-printer hplip gutenprint-cups splix "
            "sane-backends sane-backends-drivers-scanners libsane-hpaio simple-scan"
        ),
        "features_print_enable": "Enable the printing service (CUPS)",
        "features_print_enable_sub": "sudo systemctl enable --now cups",
        "features_print_disable": "Stop and disable the CUPS service",
        "features_print_disable_sub": "sudo systemctl disable --now cups",
        "features_print_disable_confirm": (
            "CUPS will be stopped and disabled: printing will not work again "
            "until the service is re-enabled."
        ),
        "features_print_sockets": "Disable the auto-activation sockets",
        "features_print_sockets_sub": "sudo systemctl disable --now cups.socket cups.path",
        "features_print_sockets_confirm": (
            "Without cups.socket or cups.path, CUPS will no longer start automatically "
            "when a print job is sent."
        ),
        "features_print_status": "Show the CUPS service status",
        "features_print_status_sub": "systemctl status cups",
        # 14. Logs
        "logs_group_main": "Live monitoring & history",
        "logs_group_opts": "Log preferences",
        "logs_live": "Live log window",
        "logs_live_sub": "Watch what the manager is doing in real time",
        "logs_session": "This session's log",
        "logs_old": "Older logs",
        "logs_old_sub": "Last 14 days, inspectable one by one",
        "logs_auto": "Open automatically",
        "logs_auto_sub": "Open log window on the first long task",
        "logs_clear": "Clear logs",
        "logs_clear_sub": "Delete files from /var/log/ps5-manager",
        "logs_clear_confirm": "Delete all recorded logs in /var/log/ps5-manager?",
        "logs_cleared": "Logs cleared.",
        "logs_none": "No log recorded yet.",
        # 12. Library
        "lib_title": "PS5 Software Library",
        "lib_sub": "Install, update, check or uninstall essential applications",
        "lib_cat_gaming": "Gaming",
        "lib_cat_gaming_sub": "Game launchers, Proton compatibility tools and Steam plugins",
        "lib_cat_browser": "Web Browsers",
        "lib_cat_browser_sub": "Web browsers (official RPM or Flatpak)",
        "lib_cat_system": "System & Utilities",
        "lib_cat_system_sub": "Disk imaging, Flatpak store and GNOME extensions",
        "install": "Install",
        "remove": "Uninstall",
        "update": "Update",
        "check": "Check for updates",
        "installed_rpm": "Installed (RPM)",
        "installed_flatpak": "Installed (Flatpak)",
        "installed": "Installed",
        "not_installed": "Not installed",
        "choose_format": "Which installation format for %s?",
        "format_rpm": "RPM (official repository)",
        "format_flatpak": "Flatpak (Flathub)",
        # 1. Manager
        "mgr_title": "PS5 Fedora Manager",
        "mgr_update": "Update manager + dependencies",
        "mgr_update_sub": "git fetch + reset from GitHub and install to /opt/ps5-manager",
        "mgr_uninstall": "Completely uninstall manager",
        "mgr_uninstall_sub": "Removes /opt/ps5-manager, launcher and desktop entry",
        "mgr_uninstall_confirm": "Remove the manager and all its system files?",
        # 2. Langues
        "lang_view": "Show installed language packs (system + keyboard)",
        "lang_view_sub": "Shows rpm -qa langpacks-* and localectl status",
        "lang_install": "Install a language",
        "lang_install_sub": "E.g. fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8",
        "lang_install_prompt": "Language code (e.g. fr_FR.UTF-8):",
        "lang_full": "Full configuration (language + keyboard + account)",
        "lang_full_sub": "Applies system locale, X11/console keymap and user account",
        "lang_pick_locale": "Choose system locale",
        "lang_pick_kb": "Choose keyboard layout",
        "lang_logout_confirm": "Language (%s) and keyboard (%s) applied.\nLog out of the %s session now to apply changes?",
        # 3. Repos
        "repo_list": "List all repositories (RPM + Flatpak)",
        "repo_list_sub": "dnf repolist --all and system/user Flatpak remotes",
        "repo_rpmfusion": "Install RPM Fusion (free + nonfree)",
        "repo_rpmfusion_sub": "Required for Steam, multimedia codecs and drivers",
        "repo_flathub": "Install Flathub (system-wide)",
        "repo_flathub_sub": "Primary Flatpak application repository",
        "repo_refresh": "Refresh repositories & clean the cache",
        "repo_openh264": "Enable the fedora-cisco-openh264 repository",
        "repo_openh264_sub": "Official Fedora H.264/AVC codec (Firefox, GStreamer, browsing) — useful on all four desktops",
        "repo_codecs": "Install multimedia codecs (RPM Fusion)",
        "repo_codecs_sub": "gstreamer1-plugins-ugly and bad-free-extras: H.264 / MPEG playback in GNOME, KDE Plasma, Cinnamon and Budgie",
        "repo_de_title": "%s desktop repositories",
        "repo_de_sub": "No third-party repository is needed: the @%s group comes from the official Fedora repositories",
        "repo_de_group": "Install / repair the desktop packages",
        "repo_de_missing": "@%s group not found in the configured repositories",
        "mnt_desktop_db": "Rebuild the application database",
        "mnt_desktop_db_sub": "update-desktop-database /usr/share/applications + ~/.local/share/applications",
        "mnt_fonts": "Rebuild the font cache",
        "mnt_fonts_sub": "fc-cache -f (after a desktop update)",
        "mnt_kde_title": "KDE Plasma maintenance",
        "mnt_kde_sub": "KDE Plasma-specific caches",
        "mnt_kde_menu": "Rebuild the KDE menu cache",
        "mnt_kde_menu_sub": "kbuildsycoca6 --noincremental",
        "repo_refresh_sub": "dnf clean all, makecache --refresh and Flatpak appstream",
        "repo_add": "Add custom repository (.repo URL)",
        "repo_add_prompt": "URL of the .repo file:",
        "repo_disable": "Disable a DNF repository",
        "repo_disable_sub": "Disables without deleting the .repo file",
        "repo_rm_dnf": "Remove a DNF repository (.repo file)",
        "repo_rm_flatpak": "Remove a Flatpak repository",
        "repo_id_prompt": "Repository ID (e.g. rpmfusion-nonfree):",
        "repo_fp_prompt": "Flatpak remote name (e.g. flathub):",
        # 4. Users
        "usr_list": "List system users",
        "usr_list_sub": "Regular accounts (UID >= 1000) in /etc/passwd",
        "usr_edit_me": "Edit my account (%s)",
        "usr_edit_me_sub": "Change account password and language",
        "usr_add": "Add a user",
        "usr_del": "Delete a user account",
        "usr_root": "Root account: status & password",
        "usr_name_prompt": "Account name:",
        "usr_pass_prompt": "Password:",
        "usr_new_pass_prompt": "New password (leave empty to keep unchanged):",
        "usr_del_confirm": "Permanently delete account %s and its home directory?",
        # 5. Fedora updates
        "fed_apps": "Update applications (DNF & Flatpak)",
        "fed_apps_sub": "dnf upgrade -y followed by flatpak update --system",
        "fed_sys": "Update entire system",
        "fed_sys_sub": "dnf upgrade --refresh -y",
        "fed_lang": "Update language packs",
        "fed_lang_sub": "dnf upgrade -y langpacks-* glibc-langpack-*",
        "fed_meta": "Refresh repository metadata",
        # 6. Maintenance
        "mnt_all": "Full cleanup",
        "mnt_all_sub": "DNF caches, logs > 7d, /tmp, thumbnails & unused Flatpak runtimes",
        "mnt_cache": "Clean DNF cache only",
        "mnt_autoremove": "Remove orphaned packages (autoremove)",
        "mnt_journal": "Shrink systemd journal (7 days)",
        "mnt_tmp": "Clean /tmp and /var/tmp",
        "mnt_thumbs": "Clean user thumbnails",
        "mnt_kernels": "Remove old kernels (keep 2)",
        "mnt_disk": "Show disk usage (df -h)",
        # 7. Power
        "pwr_full": "Full sleep (system + screen)",
        "pwr_full_sub": "Masks/unmasks sleep.target and sets screen idle delay (5 min)",
        "pwr_sys": "System sleep (suspend / hibernate)",
        "pwr_sys_sub": "systemd sleep/suspend/hibernate.target status",
        "pwr_scr": "Screen blanking (5 min)",
        "pwr_scr_sub": "org.gnome.desktop.session idle-delay",
        "pwr_enable_full": "Enable full sleep",
        "pwr_disable_full": "Disable full sleep",
        # 8. Fan
        "fan_status": "Show full status (services + ps5_control)",
        "fan_svc": "ps5fan service (fan control)",
        "fan_svc_sub": "Enable / start at boot (ps5fan.service)",
        "fan_boost": "ps5boost service (boost mode)",
        "fan_boost_sub": "Enable / start ps5boost.service",
        "fan_restart": "Restart ps5fan.service",
        "fan_tools": "Install / update ps5-linux-tools",
        "fan_tools_sub": "Clones and builds ps5-linux/ps5-linux-tools",
        # 9. Hardware Control
        "hw_check": "Check PS5 hardware presence",
        "hw_check_sub": "Inspects /sys/class/hwmon and PS5 sysfs nodes",
        "hw_install": "Install / Update PS5 Hardware Control",
        "hw_install_sub": "Installs python3-PyQt6 then NotHavocc/ps5-hwcon-gui (--passwordless)",
        "hw_check_upd": "Check GitHub for updates",
        "hw_uninstall": "Uninstall PS5 Hardware Control",
        "hw_plugin_group": "Hardware Control Plugin",
        "hw_plugin_group_sub": "Decky (Game Mode) plugin: fan, CPU/GPU clocks and LEDs",
        "hw_plugin_install": "Install the Hardware Control plugin",
        "hw_plugin_install_sub": "Fetches sources, builds and installs into Decky Loader",
        "hw_plugin_uninstall": "Uninstall the Hardware Control plugin",
        "hw_plugin_uninstall_confirm": "Remove the Hardware Control plugin and restart Decky Loader?",
        "deps_group": "System packages",
        "deps_group_sub": "Packages Steam, Proton, Flatpak and AppImages commonly ask for",
        "deps_fuse": "Fuse (fusermount)",
        "deps_fuse_sub": "FUSE stack: user-space filesystem mounting (fusermount, extract-and-run AppImages, Flatpak runtimes). fuse-libs ships libfuse.so, used by many tools.",
        "deps_steam32": "Steam — 32-bit graphics drivers",
        "deps_steam32_sub": "32-bit Mesa Vulkan and DRI plus 32-bit VA-API: without them Steam, Proton/Wine and 32-bit games lose GPU acceleration and hardware video decoding.",
        "gaming_group": "Gamescope / Steam Big Picture session",
        "gaming_group_sub": "Steam session plus GNOME / Steam switching for the current account (reboot required)",
        "gaming_log": "Gaming Mode log",
        "gaming_log_sub": "Show the Gamescope session log (launch error, return to the desktop)",
        "gaming_log_empty": "No Gaming Mode session log yet.",
        "gaming_install": "Install Gamescope",
        "gaming_install_sub": "Steam Big Picture session, GDM auto-login, GNOME/Steam switch and shortcuts",
        "gaming_uninstall": "Uninstall Gamescope",
        "gaming_uninstall_confirm": "Remove the Gamescope session, the GNOME/Steam switch, the sudoers rule and the shortcuts?",
        "fix_group": "Steam",
        "fix_group_sub": "Quick fixes when Steam gets stuck",
        "fix_steam": "Restart Steam",
        "fix_steam_sub": "Kills every Steam process (pkill -9 steam) then starts Steam again: fixes a black window, a 'Steam is already running' error or a client left in the background.",
        "fix_steam_confirm": "Force-close every Steam process and restart Steam?",
        "lib_appimage_group": "AppImage management",
        "lib_appimage_group_sub": "AppImage Pool and Gear Lever, installed from Flathub",
        "appimage_pool_desc": "Browse AppImageHub and install AppImages in a few clicks (io.github.prateekmedia.appimagepool).",
        "appimage_gear_desc": "Adds AppImages to the application menu: icon, updates and version management (it.mijorus.gearlever).",
        "appimage_install": "Install",
        "appimage_update": "Update",
        "appimage_uninstall": "Uninstall",
        "appimage_uninstall_confirm": "Uninstall %s (flatpak)?",
        "appimage_flathub": "Open the Flathub page",
        "deps_python_group": "Python 3",
        "deps_python_group_sub": "Interpreter, pip, Tkinter and virtual environment",
        "deps_python": "Python 3 + pip",
        "deps_python_sub": "python3, python3-pip: the Python interpreter and package manager.",
        "deps_python_venv": "Create the my_project virtual environment",
        "deps_python_venv_sub": "python3 -m venv my_project then source my_project/bin/activate (in your home directory).",
        "deps_python_venv_ready": "Environment created in %s. To activate it in a terminal:\nsource %s/bin/activate",
        "deps_python_versions": "Check the Python versions",
        "deps_python_versions_sub": "Shows the output of python3 --version and pip3 --version.",
        "deps_tkinter": "Tkinter (python3-tkinter)",
        "deps_tkinter_sub": "Tk GUI toolkit for Python: IDLE, tkinter, matplotlib's TkAgg backend.",
        "deps_node_group": "Node.js / npm",
        "deps_node_group_sub": "JavaScript runtime and package manager",
        "deps_node_install": "Install Node.js + npm",
        "deps_node_install_sub": "nodejs and npm from the Fedora repositories.",
        "deps_node_update": "Update (Fedora repositories)",
        "deps_node_update_sub": "dnf upgrade --refresh nodejs npm: applies the minor updates.",
        "deps_node_major": "Move to the recent major version (NodeSource 26 LTS)",
        "deps_node_major_sub": "Adds the NodeSource 26 LTS repository then reinstalls nodejs: required to switch major version.",
        "deps_node_versions": "Check the Node.js versions",
        "deps_node_versions_sub": "Shows the output of node --version and npm --version.",
        "deps_node_uninstall": "Uninstall Node.js + npm",
        "deps_node_uninstall_confirm": "Remove nodejs and npm from the system?",
        # 10. Mesa / Vulkan
        "mesa_tools": "Install Vulkan tools & Mesa demos",
        "mesa_tools_sub": "vulkan-tools and mesa-demos",
        "mesa_upd": "Update Mesa & Vulkan packages",
        "mesa_upd_sub": "dnf upgrade -y mesa* vulkan*",
        "mesa_radv": "Check RADV support (PS5 AMD GPU)",
        "mesa_summary": "Show full Vulkan summary",
        # 11. Kernel PS5
        "krn_latest": "Check latest available release",
        "krn_latest_sub": "From ps5-linux/ps5-linux-patches on GitHub",
        "krn_install": "Install latest PS5 kernel (RPM)",
        "krn_install_sub": "rpm -ivh --nosignature --replacefiles then EFI deploy",
        "krn_boot": "Choose boot kernel (/boot/efi)",
        "krn_none": "No kernel package found.",
        "krn_boot_none": "No kernel in /boot",
        "krn_no_old": "No old kernel to remove.",
        "krn_files_missing": "vmlinuz-%s or initrd.img-%s missing.",
        "gh_unreachable": "Cannot reach GitHub.",
        "gh_release_missing": "Release not found.",
        "repo_none": "No .repo file for [%s]",
        "usr_refuse": "Refused for %s",
        "mesa_no_vulkaninfo": "vulkaninfo missing — install vulkan-tools first.",
        "ai_ollama_absent": "Ollama is not installed.",
        "ai_podman_absent": "Podman is not installed.",
        "krn_boot_sub": "Copies selected vmlinuz & initrd.img to ESP",
        "krn_remove": "Clean / remove old kernels",
        "krn_remove_sub": "Removes old linux-ps5 packages while protecting the active kernel",
        "krn_running": "Running",
        "krn_esp": "On /boot/efi",
        "krn_installed": "Installed",
        "krn_protected": "Protected (active / boot)",
        "krn_pick": "Install a specific kernel (all releases)",
        "krn_pick_sub": "Downloads the linux-ps5 RPM of the chosen release: lets you roll back to an older kernel",
        "krn_pick_empty": "No release fetched from GitHub.",
        "krn_available": "Not installed",
        "krn_releases_page": "Open the GitHub releases page",
        "krn_no_rpm": "This release does not publish an RPM (Arch package only).\nPick a version that ships an x86_64 .rpm.",
        # 13. UI Lang
        "ui_lang_title": "Interface language",
        "ui_lang_sub": "Applies immediately and saved to /etc/ps5-manager/language",
        "fr_label": "Français",
        "en_label": "English",
        # 15. AI & Developer
        "aidev_open_sub": "Ollama, Open WebUI (Podman), VSCodium, Freebuff and local AI models",
        "aidev_stack": "AI & Developer Stack",
        "aidev_stack_sub": "Install, update and uninstall local AI and coding tools",
        "aidev_services": "AI Services Control",
        "aidev_services_sub": "Start, stop or disable at boot to save RAM on PS5",
        "aidev_models": "Local AI Models (Ollama)",
        "aidev_models_sub": "Pull, inspect, unload from RAM or remove models",
        "aidev_extras": "AI Diagnostics & Maintenance (PS5)",
        "aidev_extras_sub": "RAM/GPU check, Podman cleanup and rootless linger",
    },
}


# Langues disponibles : ordre d'affichage dans la barre latérale et noms natifs.
LANG_ORDER = ["fr", "en", "es", "it", "de", "pt"]
LANG_LABELS = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "it": "Italiano",
    "de": "Deutsch",
    "pt": "Português (Brasil)",
}


STRINGS['es'] = {'app_title': 'PS5 Fedora Manager',
 'search_placeholder': 'Buscar una opción o un programa…',
 'sys_group_session': 'Sesión',
 'sys_group_software': 'Software',
 'sys_group_app': 'Aplicación',
 'sys_os': 'Sistema operativo',
 'sys_kernel': 'Núcleo Linux',
 'sys_arch': 'Arquitectura',
 'sys_dnf': 'Gestor de paquetes',
 'sys_desktop': 'Entorno de escritorio',
 'sys_dm': 'Gestor de sesiones',
 'sys_session': 'Sesión gráfica',
 'sys_user': 'Usuario',
 'sys_accent': 'Color de acento',
 'sys_gamescope': 'Gamescope',
 'sys_steam': 'Steam',
 'sys_installed': 'Instalado',
 'sys_version': 'Versión del manager',
 'sys_file': 'Archivo',
 'sys_log': 'Registro de sesión',
 'sys_open': 'Abrir',
 'sys_copy': 'Copiar la información',
 'sys_copy_done': 'Información copiada',
 'switch_session': 'Cambiar de sesión (%s / Steam)',
 'podman_linger': 'Activar la persistencia de sesión de Podman (%s)',
 'podman_linger_sub': 'loginctl enable-linger %s · inicia Open WebUI sin terminal',
 'debug_version': 'Versión',
 'ai_webui_state': 'Estado: %s (%s) · Icono de GNOME: %s',
 'ai_icon_installed': 'instalado',
 'ai_icon_absent': 'ausente',
 'ai_models_count': '%d modelo(s) · %d activo(s) en RAM',
 'system_info': 'Sistema',
 'accent_label': 'Color de acento de GNOME',
 'follow_gnome': 'Sincronizado con GNOME',
 'about': 'Acerca de PS5 Fedora Manager',
 'confirm': 'Confirmar',
 'cancel': 'Cancelar',
 'ok': 'Aceptar',
 'close': 'Cerrar',
 'running': 'Procesando…',
 'busy': 'Ya hay una tarea en curso.',
 'done': 'Hecho.',
 'failed': 'Error (código %s)',
 'view_log': 'Ver el registro',
 'clear': 'Borrar',
 'sec_logs': 'Registro / Logs',
 'sec_library': 'Tienda de aplicaciones',
 'sec_aidev': 'IA y Desarrollo',
 'sec_dev': 'Desarrollo',
 'sec_web': 'Servidor web',
 'sec_easy': 'Instalación fácil',
 'sec_deps': 'Dependencias adicionales',
 'sec_gaming': 'Gaming Mode',
 'sec_fix': 'Arreglos varios',
 'sec_update': 'Actualización del gestor',
 'sec_lang': 'Idiomas y teclado',
 'sec_repos': 'Repositorios',
 'sec_users': 'Usuarios',
 'sec_fedora': 'Actualizaciones de Fedora',
 'sec_maint': 'Mantenimiento',
 'sec_power': 'Alimentación',
 'pwr_env': 'Entorno de escritorio detectado',
 'pwr_env_sub': '%s · comandos adaptados automáticamente',
 'pwr_note_gnome': 'comandos de GNOME (gsettings, gnome-settings-daemon)',
 'pwr_note_kde': 'comandos de KDE Plasma (kwriteconfig6, Powerdevil)',
 'pwr_note_cinnamon': 'comandos de Cinnamon (gsettings)',
 'pwr_note_budgie': 'comandos de Budgie (gnome-settings-daemon)',
 'pwr_note_unknown': 'escritorio no identificado: se aplican los comandos de GNOME',
 'features_de_sub': 'paquetes adaptados a %s',
 'sec_fan': 'Ventilador',
 'sec_hw': 'Hardware Control',
 'sec_mesa': 'Mesa / Vulkan',
 'sec_kernel': 'Kernel PS5',
 'sec_ui_lang': 'Idioma de la interfaz',
 'setup_menu': 'Ejecutar la configuración recomendada',
 'setup_title': 'Configuración recomendada',
 'setup_welcome_title': 'Bienvenido a PS5 Fedora Manager',
 'setup_welcome_body': 'Primer arranque. La configuración recomendada por el desarrollador '
                       'aplica de una vez los ajustes básicos de la PS5 con Fedora:\n'
                       '\n'
                       '1. Alimentación (suspensión desactivada)\n'
                       '2. Ventilador (PS5 Linux Tools, ps5fan, ps5boost)\n'
                       '3. Hardware Control\n'
                       '4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n'
                       '5. Repositorios (RPM Fusion, Flathub, caché)\n'
                       '6. Dependencias (fuse, controladores de 32 bits, Python, venv, '
                       'Tkinter, Node.js, actualizaciones)\n'
                       '7. Tienda de aplicaciones (Bazaar, Extension Manager (GNOME), Steam, '
                       'Heroic, ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n'
                       '8. Plugin Hardware Control\n'
                       '9. Gaming Mode (Gamescope)\n'
                       '\n'
                       'Al final se te propondrá reiniciar. También puedes configurar el '
                       'entorno tú mismo, sección por sección.',
 'setup_welcome_recommended': 'Configuración recomendada (1 clic)',
 'setup_welcome_manual': 'Configurar yo mismo',
 'setup_confirm_body': 'La configuración recomendada instala y ajusta todos los elementos de '
                       'la lista. Puede tardar varios minutos; la ventana de seguimiento '
                       'muestra cada elemento validado y el registro de operaciones.',
 'setup_running': 'Instalación en curso…',
 'setup_finished': 'Configuración terminada',
 'setup_log': 'Registro de operaciones',
 'setup_env_line': 'Entorno detectado: %s · %s · sesión %s',
 'setup_close': 'Cerrar',
 'setup_summary': '%d correcto(s) · %d fallo(s)',
 'setup_reboot_title': 'Reinicio necesario',
 'setup_reboot_body': 'Configuración terminada: %d elemento(s) instalado(s), %d fallo(s).\n'
                      '\n'
                      'Es necesario reiniciar para activar los servicios y los controladores. '
                      '¿Reiniciar ahora?',
 'setup_reboot_now': 'Reiniciar ahora',
 'setup_later': 'Más tarde',
 'setup_step1': '1. Alimentación',
 'setup_step2': '2. Ventilador',
 'setup_step3': '3. Hardware Control',
 'setup_step4': '4. Mesa / Vulkan',
 'setup_step5': '5. Repositorios',
 'setup_step6': '6. Dependencias adicionales',
 'setup_step7': '7. Tienda de aplicaciones',
 'setup_step8': '8. Hardware Control — plugin',
 'setup_step9': '9. Gaming Mode',
 'setup_pwr_sys': 'Desactivar la suspensión del sistema',
 'setup_pwr_scr': 'Desactivar el apagado de la pantalla',
 'setup_pwr_full': 'Desactivar la suspensión completa',
 'setup_fan_tools': 'Instalar / actualizar PS5 Linux Tools',
 'setup_fan_svc': 'Activar el servicio ps5fan',
 'setup_fan_boot': 'Activar el servicio ps5boost (arranque)',
 'setup_hw': 'Instalar / actualizar Hardware Control',
 'setup_mesa': 'Instalar Vulkan Tools y Mesa Demos',
 'setup_repo_rpmfusion': 'Instalar RPM Fusion (free + nonfree)',
 'setup_repo_flathub': 'Instalar Flatpak y Flathub',
 'setup_repo_refresh': 'Actualizar los repositorios y limpiar la caché',
 'setup_dep_fuse': 'Instalar FUSE',
 'setup_dep_steam32': 'Instalar los controladores gráficos de 32 bits para Steam',
 'setup_dep_python': 'Instalar Python 3 y pip',
 'setup_dep_venv': 'Crear el entorno virtual my_project',
 'setup_dep_tk': 'Instalar Tkinter',
 'setup_dep_node': 'Instalar Node.js y npm',
 'setup_dep_fedora': 'Actualizar los paquetes de Fedora',
 'setup_app_bazaar': 'Instalar Bazaar',
 'setup_app_extmgr': 'Instalar GNOME Extension Manager',
 'setup_app_steam': 'Instalar Steam',
 'setup_app_heroic': 'Instalar Heroic Games Launcher',
 'setup_app_protonup': 'Instalar ProtonUp-Qt',
 'setup_app_decky': 'Instalar Decky Loader',
 'setup_app_universe': 'Instalar Universe',
 'setup_app_appimagepool': 'Instalar AppImage Pool',
 'setup_app_opera': 'Instalar Opera',
 'setup_hw_plugin': 'Instalar el plugin Hardware Control',
 'setup_gaming': 'Instalar Gamescope (Gaming Mode)',
 'sec_features': 'Add Fedora Feature',
 'features_group_mobile': 'Gestión del móvil',
 'features_group_mobile_sub': 'Teléfono Android por Wi-Fi o USB: archivos, notificaciones, ADB '
                              'y Fastboot.',
 'features_mobile_install': 'Instalar GSConnect, MTP / SSHFS y ADB / Fastboot',
 'features_mobile_install_sub': 'gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs '
                                'nautilus-python android-tools',
 'features_mobile_done': 'GSConnect está instalado: activa la extensión desde la aplicación '
                         '«Extensiones» y empareja el teléfono.',
 'features_group_print': 'Impresoras y escáneres',
 'features_group_print_sub': 'CUPS, controladores HP / Brother / Epson / Canon y genéricos, '
                             'descubrimiento en red, SANE y Simple Scan.',
 'features_print_install': 'Instalar la impresión y el escaneo',
 'features_print_install_sub': 'cups cups-filters system-config-printer hplip gutenprint-cups '
                               'splix sane-backends sane-backends-drivers-scanners '
                               'libsane-hpaio simple-scan',
 'features_print_enable': 'Activar el servicio de impresión (CUPS)',
 'features_print_enable_sub': 'sudo systemctl enable --now cups',
 'features_print_disable': 'Parar y desactivar el servicio CUPS',
 'features_print_disable_sub': 'sudo systemctl disable --now cups',
 'features_print_disable_confirm': 'CUPS se detendrá y se desactivará: no se podrá imprimir '
                                   'nada hasta que se vuelva a activar.',
 'features_print_sockets': 'Desactivar los sockets de activación automática',
 'features_print_sockets_sub': 'sudo systemctl disable --now cups.socket cups.path',
 'features_print_sockets_confirm': 'Sin cups.socket ni cups.path, CUPS ya no arrancará '
                                   'automáticamente cuando se solicite una impresión.',
 'features_print_status': 'Ver el estado del servicio CUPS',
 'features_print_status_sub': 'systemctl status cups',
 'logs_group_main': 'Seguimiento en directo e historial',
 'logs_group_opts': 'Preferencias de los registros',
 'logs_live': 'Ventana de registro en directo',
 'logs_live_sub': 'Seguir en directo lo que hace el gestor',
 'logs_session': 'Registro de esta sesión',
 'logs_old': 'Registros anteriores',
 'logs_old_sub': 'Últimos 14 días, consultables uno por uno',
 'logs_auto': 'Apertura automática',
 'logs_auto_sub': 'Abrir la ventana en la primera tarea larga',
 'logs_clear': 'Borrar los registros',
 'logs_clear_sub': 'Elimina los archivos de /var/log/ps5-manager',
 'logs_clear_confirm': '¿Eliminar todos los registros guardados en /var/log/ps5-manager?',
 'logs_cleared': 'Registros borrados.',
 'logs_none': 'Todavía no hay ningún registro guardado.',
 'lib_title': 'Tienda de aplicaciones PS5',
 'lib_sub': 'Instalar, actualizar, comprobar o desinstalar las aplicaciones esenciales',
 'lib_cat_gaming': 'Gaming',
 'lib_cat_gaming_sub': 'Lanzadores de juegos, capas de compatibilidad Proton y plugins de '
                       'Steam',
 'lib_cat_browser': 'Navegadores',
 'lib_cat_browser_sub': 'Navegadores web (RPM oficial o Flatpak)',
 'lib_cat_system': 'Sistema y utilidades',
 'lib_cat_system_sub': 'Herramientas de disco, tienda Flatpak y extensiones de GNOME',
 'install': 'Instalar',
 'remove': 'Desinstalar',
 'update': 'Actualizar',
 'check': 'Buscar actualizaciones',
 'installed_rpm': 'Instalado (RPM)',
 'installed_flatpak': 'Instalado (Flatpak)',
 'installed': 'Instalado',
 'not_installed': 'No instalado',
 'choose_format': '¿Qué formato de instalación para %s?',
 'format_rpm': 'RPM (repositorio oficial)',
 'format_flatpak': 'Flatpak (Flathub)',
 'mgr_title': 'PS5 Fedora Manager',
 'mgr_update': 'Actualizar el gestor y sus dependencias',
 'mgr_update_sub': 'git fetch + reset desde GitHub e instalación en /opt/ps5-manager',
 'mgr_uninstall': 'Desinstalar completamente el gestor',
 'mgr_uninstall_sub': 'Elimina /opt/ps5-manager, el lanzador y el acceso directo del '
                      'escritorio',
 'mgr_uninstall_confirm': '¿Eliminar el gestor y todos sus archivos del sistema?',
 'lang_view': 'Ver los paquetes de idioma instalados (sistema + teclado)',
 'lang_view_sub': 'Muestra rpm -qa langpacks-* y localectl status',
 'lang_install': 'Instalar un idioma',
 'lang_install_sub': 'Ej.: fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8',
 'lang_install_prompt': 'Código de idioma (ej.: fr_FR.UTF-8):',
 'lang_full': 'Configuración completa (idioma + teclado + cuenta)',
 'lang_full_sub': 'Aplica la configuración regional del sistema, el teclado X11/consola y la '
                  'cuenta de usuario',
 'lang_pick_locale': 'Elegir la configuración regional del sistema',
 'lang_pick_kb': 'Elegir la distribución del teclado',
 'lang_logout_confirm': 'Idioma (%s) y teclado (%s) aplicados.\n'
                        '¿Cerrar ahora la sesión %s para aplicar los cambios?',
 'repo_list': 'Ver todos los repositorios (RPM + Flatpak)',
 'repo_list_sub': 'dnf repolist --all y repositorios Flatpak de sistema/usuario',
 'repo_rpmfusion': 'Instalar RPM Fusion (free + nonfree)',
 'repo_rpmfusion_sub': 'Imprescindible para Steam, códecs multimedia y controladores',
 'repo_flathub': 'Instalar Flathub (ámbito de sistema)',
 'repo_flathub_sub': 'Repositorio principal de las aplicaciones Flatpak',
 'repo_refresh': 'Actualizar los repositorios y limpiar la caché',
 'repo_openh264': 'Activar el repositorio fedora-cisco-openh264',
 'repo_openh264_sub': 'Códec H.264/AVC oficial de Fedora (Firefox, GStreamer, navegación): '
                      'útil en los cuatro escritorios',
 'repo_codecs': 'Instalar los códecs multimedia (RPM Fusion)',
 'repo_codecs_sub': 'gstreamer1-plugins-ugly y bad-free-extras: reproducción H.264 / MPEG en '
                    'GNOME, KDE Plasma, Cinnamon y Budgie',
 'repo_de_title': 'Repositorios del escritorio %s',
 'repo_de_sub': 'No hace falta ningún repositorio de terceros: el grupo @%s viene de los '
                'repositorios oficiales de Fedora',
 'repo_de_group': 'Instalar / reparar los paquetes del escritorio',
 'repo_de_missing': 'Grupo @%s no encontrado en los repositorios configurados',
 'mnt_desktop_db': 'Reconstruir la base de datos de aplicaciones',
 'mnt_desktop_db_sub': 'update-desktop-database /usr/share/applications + '
                       '~/.local/share/applications',
 'mnt_fonts': 'Reconstruir la caché de fuentes',
 'mnt_fonts_sub': 'fc-cache -f (después de actualizar el escritorio)',
 'mnt_kde_title': 'Mantenimiento de KDE Plasma',
 'mnt_kde_sub': 'Cachés propias de KDE Plasma',
 'mnt_kde_menu': 'Reconstruir la caché de menús de KDE',
 'mnt_kde_menu_sub': 'kbuildsycoca6 --noincremental',
 'repo_refresh_sub': 'dnf clean all, makecache --refresh y appstream de Flatpak',
 'repo_add': 'Añadir un repositorio personalizado (URL .repo)',
 'repo_add_prompt': 'URL del archivo .repo:',
 'repo_disable': 'Desactivar un repositorio DNF',
 'repo_disable_sub': 'Desactiva sin eliminar el archivo .repo',
 'repo_rm_dnf': 'Eliminar un repositorio DNF (archivo .repo)',
 'repo_rm_flatpak': 'Eliminar un repositorio Flatpak',
 'repo_id_prompt': 'ID del repositorio (ej.: rpmfusion-nonfree):',
 'repo_fp_prompt': 'Nombre del repositorio Flatpak (ej.: flathub):',
 'usr_list': 'Ver la lista de usuarios',
 'usr_list_sub': 'Cuentas humanas (UID >= 1000) en /etc/passwd',
 'usr_edit_me': 'Editar mi cuenta (%s)',
 'usr_edit_me_sub': 'Cambiar la contraseña y el idioma de la cuenta',
 'usr_add': 'Añadir un usuario',
 'usr_del': 'Eliminar una cuenta de usuario',
 'usr_root': 'Cuenta root: estado y contraseña',
 'usr_name_prompt': 'Nombre de la cuenta:',
 'usr_pass_prompt': 'Contraseña:',
 'usr_new_pass_prompt': 'Nueva contraseña (dejar vacío para no cambiarla):',
 'usr_del_confirm': '¿Eliminar definitivamente la cuenta %s y su carpeta personal?',
 'fed_apps': 'Actualizar las aplicaciones (DNF y Flatpak)',
 'fed_apps_sub': 'dnf upgrade -y seguido de flatpak update --system',
 'fed_sys': 'Actualizar todo el sistema',
 'fed_sys_sub': 'dnf upgrade --refresh -y',
 'fed_lang': 'Actualizar los paquetes de idioma',
 'fed_lang_sub': 'dnf upgrade -y langpacks-* glibc-langpack-*',
 'fed_meta': 'Actualizar los metadatos de los repositorios',
 'mnt_all': 'Limpieza completa',
 'mnt_all_sub': 'Cachés de DNF, registros > 7 días, /tmp, miniaturas y Flatpak sin usar',
 'mnt_cache': 'Limpiar solo la caché de DNF',
 'mnt_autoremove': 'Eliminar los paquetes huérfanos (autoremove)',
 'mnt_journal': 'Reducir los registros de systemd (7 días)',
 'mnt_tmp': 'Limpiar /tmp y /var/tmp',
 'mnt_thumbs': 'Limpiar las miniaturas del usuario',
 'mnt_kernels': 'Eliminar los kernels antiguos (conservar 2)',
 'mnt_disk': 'Ver el espacio de disco usado (df -h)',
 'pwr_full': 'Suspensión completa (sistema + pantalla)',
 'pwr_full_sub': 'Enmascara/desenmascara sleep.target y configura el apagado de pantalla (5 '
                 'min)',
 'pwr_sys': 'Suspensión del sistema (suspend / hibernate)',
 'pwr_sys_sub': 'Estado de systemd sleep/suspend/hibernate.target',
 'pwr_scr': 'Apagado de la pantalla (5 min)',
 'pwr_scr_sub': 'org.gnome.desktop.session idle-delay',
 'pwr_enable_full': 'Activar la suspensión completa',
 'pwr_disable_full': 'Desactivar la suspensión completa',
 'fan_status': 'Ver el estado completo (servicios + ps5_control)',
 'fan_svc': 'Servicio ps5fan (ventilación)',
 'fan_svc_sub': 'Activar / arrancar al inicio (ps5fan.service)',
 'fan_boost': 'Servicio ps5boost (modo boost)',
 'fan_boost_sub': 'Activar / arrancar ps5boost.service',
 'fan_restart': 'Reiniciar ps5fan.service',
 'fan_tools': 'Instalar / actualizar ps5-linux-tools',
 'fan_tools_sub': 'Clona y compila ps5-linux/ps5-linux-tools',
 'hw_check': 'Comprobar la presencia del hardware PS5',
 'hw_check_sub': 'Inspecciona /sys/class/hwmon y los nodos sysfs de la PS5',
 'hw_install': 'Instalar / actualizar PS5 Hardware Control',
 'hw_install_sub': 'Instala python3-PyQt6 y luego NotHavocc/ps5-hwcon-gui (--passwordless)',
 'hw_check_upd': 'Buscar actualizaciones en GitHub',
 'hw_uninstall': 'Desinstalar PS5 Hardware Control',
 'hw_plugin_group': 'Plugin Hardware Control',
 'hw_plugin_group_sub': 'Plugin Decky (modo Juego): ventilador, relojes de CPU/GPU y LED',
 'hw_plugin_install': 'Instalar el plugin Hardware Control',
 'hw_plugin_install_sub': 'Obtiene las fuentes, compila e instala en Decky Loader',
 'hw_plugin_uninstall': 'Desinstalar el plugin Hardware Control',
 'hw_plugin_uninstall_confirm': '¿Eliminar el plugin Hardware Control y reiniciar Decky '
                                'Loader?',
 'deps_group': 'Paquetes del sistema',
 'deps_group_sub': 'Paquetes que suelen pedir Steam, Proton, Flatpak y las AppImage',
 'deps_fuse': 'Fuse (fusermount)',
 'deps_fuse_sub': 'Pila FUSE: montaje de sistemas de archivos en espacio de usuario '
                  '(fusermount, AppImage de tipo extract-and-run, runtimes de Flatpak). '
                  'fuse-libs proporciona libfuse.so, usada por muchas herramientas.',
 'deps_steam32': 'Steam — controladores gráficos de 32 bits',
 'deps_steam32_sub': 'Mesa Vulkan y DRI de 32 bits + VA-API de 32 bits: sin ellos, Steam, '
                     'Proton/Wine y los juegos de 32 bits pierden la aceleración gráfica y la '
                     'decodificación de vídeo por hardware.',
 'gaming_group': 'Gamescope / sesión Steam Big Picture',
 'gaming_group_sub': 'Sesión Steam + alternancia GNOME / Steam en la cuenta actual (requiere '
                     'reinicio)',
 'gaming_log': 'Registro del modo Gaming',
 'gaming_log_sub': 'Mostrar el registro de la sesión Gamescope (error de inicio, vuelta al escritorio)',
 'gaming_log_empty': 'Todavía no hay registro de la sesión Gaming.',
 'gaming_install': 'Instalar Gamescope',
 'gaming_install_sub': 'Sesión Steam Big Picture, autologueo en GDM, alternancia GNOME/Steam y '
                       'atajos',
 'gaming_uninstall': 'Desinstalar Gamescope',
 'gaming_uninstall_confirm': '¿Eliminar la sesión Gamescope, la alternancia GNOME/Steam, la '
                             'regla sudoers y los atajos?',
 'fix_group': 'Steam',
 'fix_group_sub': 'Reparaciones rápidas cuando Steam se bloquea',
 'fix_steam': 'Reiniciar Steam',
 'fix_steam_sub': 'Mata todos los procesos de Steam (pkill -9 steam) y vuelve a lanzar Steam: '
                  'corrige una ventana negra, un «Steam is already running» o un cliente que '
                  'se quedó en segundo plano.',
 'fix_steam_confirm': '¿Cerrar a la fuerza todos los procesos de Steam y reiniciar Steam?',
 'lib_appimage_group': 'Gestión de AppImage',
 'lib_appimage_group_sub': 'AppImage Pool y Gear Lever, instalados desde Flathub',
 'appimage_pool_desc': 'Explora AppImageHub e instala AppImage en unos clics '
                       '(io.github.prateekmedia.appimagepool).',
 'appimage_gear_desc': 'Integra las AppImage en el menú de aplicaciones: icono, '
                       'actualizaciones y gestión de versiones (it.mijorus.gearlever).',
 'appimage_install': 'Instalar',
 'appimage_update': 'Actualizar',
 'appimage_uninstall': 'Desinstalar',
 'appimage_uninstall_confirm': '¿Desinstalar %s (flatpak)?',
 'appimage_flathub': 'Abrir la página de Flathub',
 'deps_python_group': 'Python 3',
 'deps_python_group_sub': 'Intérprete, pip, Tkinter y entorno virtual',
 'deps_python': 'Python 3 + pip',
 'deps_python_sub': 'python3, python3-pip: intérprete y gestor de paquetes de Python.',
 'deps_python_venv': 'Crear el entorno virtual my_project',
 'deps_python_venv_sub': 'python3 -m venv my_project y luego source my_project/bin/activate '
                         '(en la carpeta personal).',
 'deps_python_venv_ready': 'Entorno creado en %s. Activación en una terminal:\n'
                           'source %s/bin/activate',
 'deps_python_versions': 'Comprobar las versiones de Python',
 'deps_python_versions_sub': 'Muestra la salida de python3 --version y pip3 --version.',
 'deps_tkinter': 'Tkinter (python3-tkinter)',
 'deps_tkinter_sub': 'Interfaz gráfica Tk para Python: IDLE, tkinter, TkAgg de matplotlib.',
 'deps_node_group': 'Node.js / npm',
 'deps_node_group_sub': 'Runtime de JavaScript y gestor de paquetes',
 'deps_node_install': 'Instalar Node.js + npm',
 'deps_node_install_sub': 'nodejs y npm desde los repositorios de Fedora.',
 'deps_node_update': 'Actualizar (repositorios de Fedora)',
 'deps_node_update_sub': 'dnf upgrade --refresh nodejs npm: corrige las actualizaciones '
                         'menores.',
 'deps_node_major': 'Pasar a la versión mayor reciente (NodeSource 26 LTS)',
 'deps_node_major_sub': 'Añade el repositorio NodeSource 26 LTS y reinstala nodejs: necesario '
                        'para cambiar de versión mayor.',
 'deps_node_versions': 'Comprobar las versiones de Node.js',
 'deps_node_versions_sub': 'Muestra la salida de node --version y npm --version.',
 'deps_node_uninstall': 'Desinstalar Node.js + npm',
 'deps_node_uninstall_confirm': '¿Eliminar nodejs y npm del sistema?',
 'mesa_tools': 'Instalar las herramientas Vulkan y las Mesa demos',
 'mesa_tools_sub': 'vulkan-tools y mesa-demos',
 'mesa_upd': 'Actualizar los paquetes Mesa y Vulkan',
 'mesa_upd_sub': 'dnf upgrade -y mesa* vulkan*',
 'mesa_radv': 'Comprobar la compatibilidad con RADV (GPU AMD de la PS5)',
 'mesa_summary': 'Mostrar el resumen completo de Vulkan',
 'krn_latest': 'Comprobar la última versión disponible',
 'krn_latest_sub': 'Desde ps5-linux/ps5-linux-patches en GitHub',
 'krn_install': 'Instalar el último kernel PS5 (RPM)',
 'krn_install_sub': 'rpm -ivh --nosignature --replacefiles y despliegue en la EFI',
 'krn_boot': 'Elegir el kernel con el que arrancar (/boot/efi)',
 'krn_none': 'No se encontró ningún paquete de kernel.',
 'krn_boot_none': 'Ningún kernel en /boot',
 'krn_no_old': 'No hay ningún kernel antiguo que eliminar.',
 'krn_files_missing': 'falta vmlinuz-%s o initrd.img-%s.',
 'gh_unreachable': 'No se puede contactar con GitHub.',
 'gh_release_missing': 'Versión no encontrada.',
 'repo_none': 'Ningún archivo .repo para [%s]',
 'usr_refuse': 'Rechazado para %s',
 'mesa_no_vulkaninfo': 'falta vulkaninfo: instala primero vulkan-tools.',
 'ai_ollama_absent': 'Ollama no está instalado.',
 'ai_podman_absent': 'Podman no está instalado.',
 'krn_boot_sub': 'Copia vmlinuz e initrd.img seleccionados a la ESP',
 'krn_remove': 'Limpiar / eliminar kernels antiguos',
 'krn_remove_sub': 'Elimina los paquetes linux-ps5 antiguos protegiendo el kernel activo',
 'krn_running': 'Arrancado',
 'krn_esp': 'En /boot/efi',
 'krn_installed': 'Instalado',
 'krn_protected': 'Protegido (activo / arranque)',
 'krn_pick': 'Instalar un kernel concreto (todas las versiones)',
 'krn_pick_sub': 'Descarga el RPM linux-ps5 de la versión elegida: permite volver a un kernel '
                 'anterior',
 'krn_pick_empty': 'No se obtuvo ninguna versión desde GitHub.',
 'krn_available': 'No instalado',
 'krn_releases_page': 'Abrir la página de versiones de GitHub',
 'krn_no_rpm': 'Esta versión no publica ningún RPM (solo paquete de Arch).\n'
               'Elige una versión que ofrezca un .rpm x86_64.',
 'ui_lang_title': 'Idioma de la interfaz',
 'ui_lang_sub': 'Cambio inmediato y guardado en /etc/ps5-manager/language',
 'fr_label': 'Français',
 'en_label': 'English',
 'aidev_open_sub': 'Ollama, Open WebUI (Podman), VSCodium, Freebuff y modelos de IA locales',
 'aidev_stack': 'Herramientas y aplicaciones IA / Dev',
 'aidev_stack_sub': 'Instalación, actualización y desinstalación de los componentes locales',
 'aidev_services': 'Control de los servicios de IA',
 'aidev_services_sub': 'Iniciar, parar o desactivar al arrancar para liberar RAM',
 'aidev_models': 'Modelos de IA locales (Ollama)',
 'aidev_models_sub': 'Descargar, inspeccionar, descargar de la RAM o eliminar los modelos',
 'aidev_extras': 'Diagnóstico y mantenimiento de IA (PS5)',
 'aidev_extras_sub': 'Comprobación de RAM/GPU, limpieza de Podman y persistencia'}


STRINGS['it'] = {'app_title': 'PS5 Fedora Manager',
 'search_placeholder': "Cerca un'opzione o un programma…",
 'sys_group_session': 'Sessione',
 'sys_group_software': 'Software',
 'sys_group_app': 'Applicazione',
 'sys_os': 'Sistema operativo',
 'sys_kernel': 'Kernel Linux',
 'sys_arch': 'Architettura',
 'sys_dnf': 'Gestore dei pacchetti',
 'sys_desktop': 'Ambiente desktop',
 'sys_dm': 'Display manager',
 'sys_session': 'Sessione grafica',
 'sys_user': 'Utente',
 'sys_accent': 'Colore d\'accento',
 'sys_gamescope': 'Gamescope',
 'sys_steam': 'Steam',
 'sys_installed': 'Installato',
 'sys_version': 'Versione del manager',
 'sys_file': 'File',
 'sys_log': 'Log di sessione',
 'sys_open': 'Apri',
 'sys_copy': 'Copia le informazioni',
 'sys_copy_done': 'Informazioni copiate',
 'switch_session': 'Cambia sessione (%s / Steam)',
 'podman_linger': 'Attiva la persistenza di sessione Podman (%s)',
 'podman_linger_sub': 'loginctl enable-linger %s · avvia Open WebUI senza terminale',
 'debug_version': 'Versione',
 'ai_webui_state': 'Stato: %s (%s) · Icona GNOME: %s',
 'ai_icon_installed': 'installata',
 'ai_icon_absent': 'assente',
 'ai_models_count': '%d modello(i) · %d attivo(i) in RAM',
 'system_info': 'Sistema',
 'accent_label': "Colore d'accento di GNOME",
 'follow_gnome': 'Sincronizzato con GNOME',
 'about': 'Informazioni su PS5 Fedora Manager',
 'confirm': 'Conferma',
 'cancel': 'Annulla',
 'ok': 'OK',
 'close': 'Chiudi',
 'running': 'Elaborazione in corso…',
 'busy': "Un'operazione è già in corso.",
 'done': 'Fatto.',
 'failed': 'Errore (codice %s)',
 'view_log': 'Vedi il registro',
 'clear': 'Cancella',
 'sec_logs': 'Registro / Log',
 'sec_library': 'App store',
 'sec_aidev': 'IA e Sviluppo',
 'sec_dev': 'Sviluppo',
 'sec_web': 'Server web',
 'sec_easy': 'Installazione facile',
 'sec_deps': 'Dipendenze aggiuntive',
 'sec_gaming': 'Gaming Mode',
 'sec_fix': 'Correzioni varie',
 'sec_update': 'Aggiornamento del gestore',
 'sec_lang': 'Lingue e tastiera',
 'sec_repos': 'Repository',
 'sec_users': 'Utenti',
 'sec_fedora': 'Aggiornamenti Fedora',
 'sec_maint': 'Manutenzione',
 'sec_power': 'Alimentazione',
 'pwr_env': 'Ambiente desktop rilevato',
 'pwr_env_sub': '%s · comandi adattati automaticamente',
 'pwr_note_gnome': 'comandi GNOME (gsettings, gnome-settings-daemon)',
 'pwr_note_kde': 'comandi KDE Plasma (kwriteconfig6, Powerdevil)',
 'pwr_note_cinnamon': 'comandi Cinnamon (gsettings)',
 'pwr_note_budgie': 'comandi Budgie (gnome-settings-daemon)',
 'pwr_note_unknown': 'desktop non identificato: applicati i comandi GNOME',
 'features_de_sub': 'pacchetti adattati a %s',
 'sec_fan': 'Ventola',
 'sec_hw': 'Hardware Control',
 'sec_mesa': 'Mesa / Vulkan',
 'sec_kernel': 'Kernel PS5',
 'sec_ui_lang': "Lingua dell'interfaccia",
 'setup_menu': 'Esegui la configurazione consigliata',
 'setup_title': 'Configurazione consigliata',
 'setup_welcome_title': 'Benvenuto in PS5 Fedora Manager',
 'setup_welcome_body': 'Primo avvio. La configurazione consigliata dallo sviluppatore applica '
                       "in un'unica volta le impostazioni di base della PS5 con Fedora:\n"
                       '\n'
                       '1. Alimentazione (sospensione disattivata)\n'
                       '2. Ventola (PS5 Linux Tools, ps5fan, ps5boost)\n'
                       '3. Hardware Control\n'
                       '4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n'
                       '5. Repository (RPM Fusion, Flathub, cache)\n'
                       '6. Dipendenze (fuse, driver a 32 bit, Python, venv, Tkinter, Node.js, '
                       'aggiornamenti)\n'
                       '7. App store (Bazaar, Extension Manager (GNOME), Steam, Heroic, '
                       'ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n'
                       '8. Plugin Hardware Control\n'
                       '9. Gaming Mode (Gamescope)\n'
                       '\n'
                       'Al termine ti verrà proposto un riavvio. Puoi anche configurare '
                       "l'ambiente da solo, sezione per sezione.",
 'setup_welcome_recommended': 'Configurazione consigliata (1 clic)',
 'setup_welcome_manual': 'Configuro da solo',
 'setup_confirm_body': 'La configurazione consigliata installa e imposta tutti gli elementi '
                       'elencati. Può richiedere diversi minuti; la finestra di monitoraggio '
                       'mostra ogni elemento convalidato e il registro delle operazioni.',
 'setup_running': 'Installazione in corso…',
 'setup_finished': 'Configurazione completata',
 'setup_log': 'Registro delle operazioni',
 'setup_env_line': 'Ambiente rilevato: %s · %s · sessione %s',
 'setup_close': 'Chiudi',
 'setup_summary': '%d riuscito/i · %d fallito/i',
 'setup_reboot_title': 'Riavvio necessario',
 'setup_reboot_body': 'Configurazione completata: %d elemento/i installato/i, %d errore/i.\n'
                      '\n'
                      'È necessario riavviare per attivare i servizi e i driver. Riavviare '
                      'ora?',
 'setup_reboot_now': 'Riavvia ora',
 'setup_later': 'Più tardi',
 'setup_step1': '1. Alimentazione',
 'setup_step2': '2. Ventola',
 'setup_step3': '3. Hardware Control',
 'setup_step4': '4. Mesa / Vulkan',
 'setup_step5': '5. Repository',
 'setup_step6': '6. Dipendenze aggiuntive',
 'setup_step7': '7. App store',
 'setup_step8': '8. Hardware Control — plugin',
 'setup_step9': '9. Gaming Mode',
 'setup_pwr_sys': 'Disattiva la sospensione di sistema',
 'setup_pwr_scr': 'Disattiva lo spegnimento dello schermo',
 'setup_pwr_full': 'Disattiva la sospensione completa',
 'setup_fan_tools': 'Installa / aggiorna PS5 Linux Tools',
 'setup_fan_svc': 'Attiva il servizio ps5fan',
 'setup_fan_boot': 'Attiva il servizio ps5boost (avvio)',
 'setup_hw': 'Installa / aggiorna Hardware Control',
 'setup_mesa': 'Installa Vulkan Tools e Mesa Demos',
 'setup_repo_rpmfusion': 'Installa RPM Fusion (free + nonfree)',
 'setup_repo_flathub': 'Installa Flatpak e Flathub',
 'setup_repo_refresh': 'Aggiorna i repository e pulisci la cache',
 'setup_dep_fuse': 'Installa FUSE',
 'setup_dep_steam32': 'Installa i driver grafici a 32 bit per Steam',
 'setup_dep_python': 'Installa Python 3 e pip',
 'setup_dep_venv': "Crea l'ambiente virtuale my_project",
 'setup_dep_tk': 'Installa Tkinter',
 'setup_dep_node': 'Installa Node.js e npm',
 'setup_dep_fedora': 'Aggiorna i pacchetti Fedora',
 'setup_app_bazaar': 'Installa Bazaar',
 'setup_app_extmgr': 'Installa GNOME Extension Manager',
 'setup_app_steam': 'Installa Steam',
 'setup_app_heroic': 'Installa Heroic Games Launcher',
 'setup_app_protonup': 'Installa ProtonUp-Qt',
 'setup_app_decky': 'Installa Decky Loader',
 'setup_app_universe': 'Installa Universe',
 'setup_app_appimagepool': 'Installa AppImage Pool',
 'setup_app_opera': 'Installa Opera',
 'setup_hw_plugin': 'Installa il plugin Hardware Control',
 'setup_gaming': 'Installa Gamescope (Gaming Mode)',
 'sec_features': 'Add Fedora Feature',
 'features_group_mobile': 'Gestione del telefono',
 'features_group_mobile_sub': 'Telefono Android via Wi-Fi o USB: file, notifiche, ADB e '
                              'Fastboot.',
 'features_mobile_install': 'Installa GSConnect, MTP / SSHFS e ADB / Fastboot',
 'features_mobile_install_sub': 'gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs '
                                'nautilus-python android-tools',
 'features_mobile_done': "GSConnect è installato: attiva l'estensione dall'applicazione "
                         '«Estensioni» e abbina il telefono.',
 'features_group_print': 'Stampanti e scanner',
 'features_group_print_sub': 'CUPS, driver HP / Brother / Epson / Canon e generici, scoperta '
                             'in rete, SANE e Simple Scan.',
 'features_print_install': 'Installa la stampa e la scansione',
 'features_print_install_sub': 'cups cups-filters system-config-printer hplip gutenprint-cups '
                               'splix sane-backends sane-backends-drivers-scanners '
                               'libsane-hpaio simple-scan',
 'features_print_enable': 'Attiva il servizio di stampa (CUPS)',
 'features_print_enable_sub': 'sudo systemctl enable --now cups',
 'features_print_disable': 'Ferma e disattiva il servizio CUPS',
 'features_print_disable_sub': 'sudo systemctl disable --now cups',
 'features_print_disable_confirm': 'CUPS verrà arrestato e disattivato: non sarà più possibile '
                                   'stampare finché il servizio non viene riattivato.',
 'features_print_sockets': 'Disattiva i socket di attivazione automatica',
 'features_print_sockets_sub': 'sudo systemctl disable --now cups.socket cups.path',
 'features_print_sockets_confirm': 'Senza cups.socket e cups.path, CUPS non si riavvierà più '
                                   'automaticamente quando viene richiesta una stampa.',
 'features_print_status': 'Vedi lo stato del servizio CUPS',
 'features_print_status_sub': 'systemctl status cups',
 'logs_group_main': 'Monitoraggio dal vivo e cronologia',
 'logs_group_opts': 'Preferenze dei registri',
 'logs_live': 'Finestra di log dal vivo',
 'logs_live_sub': 'Segui in tempo reale ciò che fa il gestore',
 'logs_session': 'Registro di questa sessione',
 'logs_old': 'Registri precedenti',
 'logs_old_sub': 'Ultimi 14 giorni, consultabili uno alla volta',
 'logs_auto': 'Apertura automatica',
 'logs_auto_sub': 'Apri la finestra al primo lavoro lungo',
 'logs_clear': 'Cancella i registri',
 'logs_clear_sub': 'Elimina i file da /var/log/ps5-manager',
 'logs_clear_confirm': 'Eliminare tutti i registri salvati in /var/log/ps5-manager?',
 'logs_cleared': 'Registri cancellati.',
 'logs_none': 'Nessun registro salvato per ora.',
 'lib_title': 'App store PS5',
 'lib_sub': 'Installa, aggiorna, verifica o disinstalla le applicazioni essenziali',
 'lib_cat_gaming': 'Gaming',
 'lib_cat_gaming_sub': 'Launcher di giochi, livelli di compatibilità Proton e plugin Steam',
 'lib_cat_browser': 'Browser',
 'lib_cat_browser_sub': 'Browser web (RPM ufficiale o Flatpak)',
 'lib_cat_system': 'Sistema e utilità',
 'lib_cat_system_sub': 'Strumenti disco, store Flatpak ed estensioni GNOME',
 'install': 'Installa',
 'remove': 'Disinstalla',
 'update': 'Aggiorna',
 'check': 'Verifica gli aggiornamenti',
 'installed_rpm': 'Installato (RPM)',
 'installed_flatpak': 'Installato (Flatpak)',
 'installed': 'Installato',
 'not_installed': 'Non installato',
 'choose_format': 'Quale formato di installazione per %s?',
 'format_rpm': 'RPM (repository ufficiale)',
 'format_flatpak': 'Flatpak (Flathub)',
 'mgr_title': 'PS5 Fedora Manager',
 'mgr_update': 'Aggiorna il gestore e le sue dipendenze',
 'mgr_update_sub': 'git fetch + reset da GitHub e installazione in /opt/ps5-manager',
 'mgr_uninstall': 'Disinstalla completamente il gestore',
 'mgr_uninstall_sub': 'Rimuove /opt/ps5-manager, il launcher e la scorciatoia del desktop',
 'mgr_uninstall_confirm': 'Rimuovere il gestore e tutti i suoi file di sistema?',
 'lang_view': 'Vedi i language pack installati (sistema + tastiera)',
 'lang_view_sub': 'Mostra rpm -qa langpacks-* e localectl status',
 'lang_install': 'Installa una lingua',
 'lang_install_sub': 'Es.: fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8',
 'lang_install_prompt': 'Codice lingua (es.: fr_FR.UTF-8):',
 'lang_full': 'Configurazione completa (lingua + tastiera + account)',
 'lang_full_sub': "Applica la locale di sistema, la tastiera X11/console e l'account utente",
 'lang_pick_locale': 'Scegli la locale di sistema',
 'lang_pick_kb': 'Scegli la disposizione della tastiera',
 'lang_logout_confirm': 'Lingua (%s) e tastiera (%s) applicate.\n'
                        'Chiudere ora la sessione %s per applicare le modifiche?',
 'repo_list': 'Vedi tutti i repository (RPM + Flatpak)',
 'repo_list_sub': 'dnf repolist --all e repository Flatpak di sistema/utente',
 'repo_rpmfusion': 'Installa RPM Fusion (free + nonfree)',
 'repo_rpmfusion_sub': 'Indispensabile per Steam, codec multimediali e driver',
 'repo_flathub': 'Installa Flathub (ambito di sistema)',
 'repo_flathub_sub': 'Repository principale delle applicazioni Flatpak',
 'repo_refresh': 'Aggiorna i repository e pulisci la cache',
 'repo_openh264': 'Attiva il repository fedora-cisco-openh264',
 'repo_openh264_sub': 'Codec H.264/AVC ufficiale Fedora (Firefox, GStreamer, navigazione): '
                      'utile sui quattro desktop',
 'repo_codecs': 'Installa i codec multimediali (RPM Fusion)',
 'repo_codecs_sub': 'gstreamer1-plugins-ugly e bad-free-extras: riproduzione H.264 / MPEG in '
                    'GNOME, KDE Plasma, Cinnamon e Budgie',
 'repo_de_title': 'Repository del desktop %s',
 'repo_de_sub': 'Nessun repository di terze parti è necessario: il gruppo @%s proviene dai '
                'repository ufficiali Fedora',
 'repo_de_group': 'Installa / ripara i pacchetti del desktop',
 'repo_de_missing': 'Gruppo @%s non trovato nei repository configurati',
 'mnt_desktop_db': 'Ricostruisci il database delle applicazioni',
 'mnt_desktop_db_sub': 'update-desktop-database /usr/share/applications + '
                       '~/.local/share/applications',
 'mnt_fonts': 'Ricostruisci la cache dei font',
 'mnt_fonts_sub': 'fc-cache -f (dopo un aggiornamento del desktop)',
 'mnt_kde_title': 'Manutenzione KDE Plasma',
 'mnt_kde_sub': 'Cache specifiche di KDE Plasma',
 'mnt_kde_menu': 'Ricostruisci la cache dei menu KDE',
 'mnt_kde_menu_sub': 'kbuildsycoca6 --noincremental',
 'repo_refresh_sub': 'dnf clean all, makecache --refresh e appstream Flatpak',
 'repo_add': 'Aggiungi un repository personalizzato (URL .repo)',
 'repo_add_prompt': 'URL del file .repo:',
 'repo_disable': 'Disattiva un repository DNF',
 'repo_disable_sub': 'Disattiva senza rimuovere il file .repo',
 'repo_rm_dnf': 'Rimuovi un repository DNF (file .repo)',
 'repo_rm_flatpak': 'Rimuovi un repository Flatpak',
 'repo_id_prompt': 'ID del repository (es.: rpmfusion-nonfree):',
 'repo_fp_prompt': 'Nome del repository Flatpak (es.: flathub):',
 'usr_list': "Vedi l'elenco degli utenti",
 'usr_list_sub': 'Account umani (UID >= 1000) in /etc/passwd',
 'usr_edit_me': 'Modifica il mio account (%s)',
 'usr_edit_me_sub': "Cambia la password e la lingua dell'account",
 'usr_add': 'Aggiungi un utente',
 'usr_del': 'Elimina un account utente',
 'usr_root': 'Account root: stato e password',
 'usr_name_prompt': "Nome dell'account:",
 'usr_pass_prompt': 'Password:',
 'usr_new_pass_prompt': 'Nuova password (lasciare vuoto per non cambiarla):',
 'usr_del_confirm': "Eliminare definitivamente l'account %s e la sua cartella personale?",
 'fed_apps': 'Aggiorna le applicazioni (DNF e Flatpak)',
 'fed_apps_sub': 'dnf upgrade -y seguito da flatpak update --system',
 'fed_sys': "Aggiorna l'intero sistema",
 'fed_sys_sub': 'dnf upgrade --refresh -y',
 'fed_lang': 'Aggiorna i language pack',
 'fed_lang_sub': 'dnf upgrade -y langpacks-* glibc-langpack-*',
 'fed_meta': 'Aggiorna i metadati dei repository',
 'mnt_all': 'Pulizia completa',
 'mnt_all_sub': 'Cache DNF, registri > 7 giorni, /tmp, miniature e Flatpak inutilizzati',
 'mnt_cache': 'Pulisci solo la cache DNF',
 'mnt_autoremove': 'Rimuovi i pacchetti orfani (autoremove)',
 'mnt_journal': 'Riduci i registri systemd (7 giorni)',
 'mnt_tmp': 'Pulisci /tmp e /var/tmp',
 'mnt_thumbs': "Pulisci le miniature dell'utente",
 'mnt_kernels': 'Rimuovi i kernel vecchi (mantieni 2)',
 'mnt_disk': 'Vedi lo spazio su disco usato (df -h)',
 'pwr_full': 'Sospensione completa (sistema + schermo)',
 'pwr_full_sub': 'Maschera/smascherà sleep.target e configura lo spegnimento dello schermo (5 '
                 'min)',
 'pwr_sys': 'Sospensione di sistema (suspend / hibernate)',
 'pwr_sys_sub': 'Stato di systemd sleep/suspend/hibernate.target',
 'pwr_scr': 'Spegnimento dello schermo (5 min)',
 'pwr_scr_sub': 'org.gnome.desktop.session idle-delay',
 'pwr_enable_full': 'Attiva la sospensione completa',
 'pwr_disable_full': 'Disattiva la sospensione completa',
 'fan_status': 'Vedi lo stato completo (servizi + ps5_control)',
 'fan_svc': 'Servizio ps5fan (ventilazione)',
 'fan_svc_sub': "Attiva / avvia all'avvio (ps5fan.service)",
 'fan_boost': 'Servizio ps5boost (modalità boost)',
 'fan_boost_sub': 'Attiva / avvia ps5boost.service',
 'fan_restart': 'Riavvia ps5fan.service',
 'fan_tools': 'Installa / aggiorna ps5-linux-tools',
 'fan_tools_sub': 'Clona e compila ps5-linux/ps5-linux-tools',
 'hw_check': "Verifica la presenza dell'hardware PS5",
 'hw_check_sub': 'Ispeziona /sys/class/hwmon e i nodi sysfs della PS5',
 'hw_install': 'Installa / aggiorna PS5 Hardware Control',
 'hw_install_sub': 'Installa python3-PyQt6 poi NotHavocc/ps5-hwcon-gui (--passwordless)',
 'hw_check_upd': 'Cerca aggiornamenti su GitHub',
 'hw_uninstall': 'Disinstalla PS5 Hardware Control',
 'hw_plugin_group': 'Plugin Hardware Control',
 'hw_plugin_group_sub': 'Plugin Decky (modalità Gioco): ventola, clock CPU/GPU e LED',
 'hw_plugin_install': 'Installa il plugin Hardware Control',
 'hw_plugin_install_sub': 'Scarica i sorgenti, compila e installa in Decky Loader',
 'hw_plugin_uninstall': 'Disinstalla il plugin Hardware Control',
 'hw_plugin_uninstall_confirm': 'Rimuovere il plugin Hardware Control e riavviare Decky '
                                'Loader?',
 'deps_group': 'Pacchetti di sistema',
 'deps_group_sub': 'Pacchetti spesso richiesti da Steam, Proton, Flatpak e dalle AppImage',
 'deps_fuse': 'Fuse (fusermount)',
 'deps_fuse_sub': 'Stack FUSE: montaggio di file system nello spazio utente (fusermount, '
                  'AppImage di tipo extract-and-run, runtime Flatpak). fuse-libs fornisce '
                  'libfuse.so, usata da molti strumenti.',
 'deps_steam32': 'Steam — driver grafici a 32 bit',
 'deps_steam32_sub': 'Mesa Vulkan e DRI a 32 bit + VA-API a 32 bit: senza di essi Steam, '
                     "Proton/Wine e i giochi a 32 bit perdono l'accelerazione grafica e la "
                     'decodifica video hardware.',
 'gaming_group': 'Gamescope / sessione Steam Big Picture',
 'gaming_group_sub': "Sessione Steam + commutazione GNOME / Steam sull'account corrente "
                     '(riavvio necessario)',
 'gaming_log': 'Log della modalità Gaming',
 'gaming_log_sub': 'Mostra il log della sessione Gamescope (errore di avvio, ritorno al desktop)',
 'gaming_log_empty': 'Nessun log della sessione Gaming per ora.',
 'gaming_install': 'Installa Gamescope',
 'gaming_install_sub': 'Sessione Steam Big Picture, login automatico GDM, commutazione '
                       'GNOME/Steam e scorciatoie',
 'gaming_uninstall': 'Disinstalla Gamescope',
 'gaming_uninstall_confirm': 'Rimuovere la sessione Gamescope, la commutazione GNOME/Steam, la '
                             'regola sudoers e le scorciatoie?',
 'fix_group': 'Steam',
 'fix_group_sub': 'Riparazioni rapide quando Steam si blocca',
 'fix_steam': 'Riavvia Steam',
 'fix_steam_sub': 'Termina tutti i processi Steam (pkill -9 steam) e riavvia Steam: risolve '
                  'una finestra nera, un «Steam is already running» o un client rimasto in '
                  'background.',
 'fix_steam_confirm': 'Chiudere forzatamente tutti i processi Steam e riavviare Steam?',
 'lib_appimage_group': 'Gestione AppImage',
 'lib_appimage_group_sub': 'AppImage Pool e Gear Lever, installati da Flathub',
 'appimage_pool_desc': 'Esplora AppImageHub e installa AppImage in pochi clic '
                       '(io.github.prateekmedia.appimagepool).',
 'appimage_gear_desc': 'Integra le AppImage nel menu delle applicazioni: icona, aggiornamenti '
                       'e gestione delle versioni (it.mijorus.gearlever).',
 'appimage_install': 'Installa',
 'appimage_update': 'Aggiorna',
 'appimage_uninstall': 'Disinstalla',
 'appimage_uninstall_confirm': 'Disinstallare %s (flatpak)?',
 'appimage_flathub': 'Apri la pagina Flathub',
 'deps_python_group': 'Python 3',
 'deps_python_group_sub': 'Interprete, pip, Tkinter e ambiente virtuale',
 'deps_python': 'Python 3 + pip',
 'deps_python_sub': 'python3, python3-pip: interprete e gestore di pacchetti Python.',
 'deps_python_venv': "Crea l'ambiente virtuale my_project",
 'deps_python_venv_sub': 'python3 -m venv my_project poi source my_project/bin/activate (nella '
                         'cartella personale).',
 'deps_python_venv_ready': 'Ambiente creato in %s. Attivazione nel terminale:\n'
                           'source %s/bin/activate',
 'deps_python_versions': 'Verifica le versioni Python',
 'deps_python_versions_sub': "Mostra l'output di python3 --version e pip3 --version.",
 'deps_tkinter': 'Tkinter (python3-tkinter)',
 'deps_tkinter_sub': 'Interfaccia grafica Tk per Python: IDLE, tkinter, TkAgg di matplotlib.',
 'deps_node_group': 'Node.js / npm',
 'deps_node_group_sub': 'Runtime JavaScript e gestore di pacchetti',
 'deps_node_install': 'Installa Node.js + npm',
 'deps_node_install_sub': 'nodejs e npm dai repository Fedora.',
 'deps_node_update': 'Aggiorna (repository Fedora)',
 'deps_node_update_sub': 'dnf upgrade --refresh nodejs npm: corregge gli aggiornamenti minori.',
 'deps_node_major': 'Passa alla versione maggiore recente (NodeSource 26 LTS)',
 'deps_node_major_sub': 'Aggiunge il repository NodeSource 26 LTS e reinstalla nodejs: '
                        'necessario per cambiare versione maggiore.',
 'deps_node_versions': 'Verifica le versioni Node.js',
 'deps_node_versions_sub': "Mostra l'output di node --version e npm --version.",
 'deps_node_uninstall': 'Disinstalla Node.js + npm',
 'deps_node_uninstall_confirm': 'Rimuovere nodejs e npm dal sistema?',
 'mesa_tools': 'Installa gli strumenti Vulkan e le Mesa demos',
 'mesa_tools_sub': 'vulkan-tools e mesa-demos',
 'mesa_upd': 'Aggiorna i pacchetti Mesa e Vulkan',
 'mesa_upd_sub': 'dnf upgrade -y mesa* vulkan*',
 'mesa_radv': 'Verifica il supporto RADV (GPU AMD della PS5)',
 'mesa_summary': 'Mostra il riepilogo completo di Vulkan',
 'krn_latest': "Verifica l'ultima versione disponibile",
 'krn_latest_sub': 'Da ps5-linux/ps5-linux-patches su GitHub',
 'krn_install': "Installa l'ultimo kernel PS5 (RPM)",
 'krn_install_sub': "rpm -ivh --nosignature --replacefiles poi distribuzione sull'EFI",
 'krn_boot': 'Scegli il kernel da avviare (/boot/efi)',
 'krn_none': 'Nessun pacchetto kernel trovato.',
 'krn_boot_none': 'Nessun kernel in /boot',
 'krn_no_old': 'Nessun kernel vecchio da rimuovere.',
 'krn_files_missing': 'vmlinuz-%s o initrd.img-%s mancante.',
 'gh_unreachable': 'Impossibile contattare GitHub.',
 'gh_release_missing': 'Release non trovata.',
 'repo_none': 'Nessun file .repo per [%s]',
 'usr_refuse': 'Rifiutato per %s',
 'mesa_no_vulkaninfo': 'vulkaninfo mancante: installa prima vulkan-tools.',
 'ai_ollama_absent': 'Ollama non è installato.',
 'ai_podman_absent': 'Podman non è installato.',
 'krn_boot_sub': 'Copia vmlinuz e initrd.img selezionati sulla ESP',
 'krn_remove': 'Pulisci / rimuovi i kernel vecchi',
 'krn_remove_sub': 'Rimuove i vecchi pacchetti linux-ps5 proteggendo il kernel attivo',
 'krn_running': 'Avviato',
 'krn_esp': 'Su /boot/efi',
 'krn_installed': 'Installato',
 'krn_protected': 'Protetto (attivo / avvio)',
 'krn_pick': 'Installa un kernel specifico (tutte le release)',
 'krn_pick_sub': "Scarica l'RPM linux-ps5 della release scelta: permette di tornare a un "
                 'kernel precedente',
 'krn_pick_empty': 'Nessuna release recuperata da GitHub.',
 'krn_available': 'Non installato',
 'krn_releases_page': 'Apri la pagina delle release su GitHub',
 'krn_no_rpm': 'Questa release non pubblica RPM (solo pacchetto Arch).\n'
               'Scegli una versione che offra un .rpm x86_64.',
 'ui_lang_title': "Lingua dell'interfaccia",
 'ui_lang_sub': 'Cambio immediato e salvato in /etc/ps5-manager/language',
 'fr_label': 'Français',
 'en_label': 'English',
 'aidev_open_sub': 'Ollama, Open WebUI (Podman), VSCodium, Freebuff e modelli IA locali',
 'aidev_stack': 'Strumenti e applicazioni IA / Dev',
 'aidev_stack_sub': 'Installazione, aggiornamento e disinstallazione dei componenti locali',
 'aidev_services': 'Controllo dei servizi IA',
 'aidev_services_sub': "Avvia, ferma o disattiva all'avvio per liberare RAM",
 'aidev_models': 'Modelli IA locali (Ollama)',
 'aidev_models_sub': 'Scarica, ispeziona, scarica dalla RAM o rimuovi i modelli',
 'aidev_extras': 'Diagnostica e manutenzione IA (PS5)',
 'aidev_extras_sub': 'Controllo RAM/GPU, pulizia Podman e persistenza'}


STRINGS['de'] = {'app_title': 'PS5 Fedora Manager',
 'search_placeholder': 'Option oder Programm suchen…',
 'sys_group_session': 'Sitzung',
 'sys_group_software': 'Software',
 'sys_group_app': 'Anwendung',
 'sys_os': 'Betriebssystem',
 'sys_kernel': 'Linux-Kernel',
 'sys_arch': 'Architektur',
 'sys_dnf': 'Paketmanager',
 'sys_desktop': 'Desktop-Umgebung',
 'sys_dm': 'Anmeldemanager',
 'sys_session': 'Grafische Sitzung',
 'sys_user': 'Benutzer',
 'sys_accent': 'Akzentfarbe',
 'sys_gamescope': 'Gamescope',
 'sys_steam': 'Steam',
 'sys_installed': 'Installiert',
 'sys_version': 'Manager-Version',
 'sys_file': 'Datei',
 'sys_log': 'Sitzungsprotokoll',
 'sys_open': 'Öffnen',
 'sys_copy': 'Informationen kopieren',
 'sys_copy_done': 'Informationen kopiert',
 'switch_session': 'Sitzung wechseln (%s / Steam)',
 'podman_linger': 'Podman-Sitzung dauerhaft aktivieren (%s)',
 'podman_linger_sub': 'loginctl enable-linger %s · startet Open WebUI ohne Terminal',
 'debug_version': 'Version',
 'ai_webui_state': 'Status: %s (%s) · GNOME-Symbol: %s',
 'ai_icon_installed': 'installiert',
 'ai_icon_absent': 'fehlt',
 'ai_models_count': '%d Modell(e) · %d aktiv im RAM',
 'system_info': 'System',
 'accent_label': 'GNOME-Akzentfarbe',
 'follow_gnome': 'Mit GNOME synchronisiert',
 'about': 'Über PS5 Fedora Manager',
 'confirm': 'Bestätigen',
 'cancel': 'Abbrechen',
 'ok': 'OK',
 'close': 'Schließen',
 'running': 'Wird verarbeitet…',
 'busy': 'Es läuft bereits eine Aufgabe.',
 'done': 'Fertig.',
 'failed': 'Fehlgeschlagen (Code %s)',
 'view_log': 'Protokoll anzeigen',
 'clear': 'Löschen',
 'sec_logs': 'Protokoll / Logs',
 'sec_library': 'App-Store',
 'sec_aidev': 'KI & Entwicklung',
 'sec_dev': 'Entwicklung',
 'sec_web': 'Webserver',
 'sec_easy': 'Einfache Installation',
 'sec_deps': 'Zusätzliche Abhängigkeiten',
 'sec_gaming': 'Gaming Mode',
 'sec_fix': 'Diverse Korrekturen',
 'sec_update': 'Aktualisierung des Managers',
 'sec_lang': 'Sprachen & Tastatur',
 'sec_repos': 'Paketquellen',
 'sec_users': 'Benutzer',
 'sec_fedora': 'Fedora-Aktualisierungen',
 'sec_maint': 'Wartung',
 'sec_power': 'Energie',
 'pwr_env': 'Erkannte Desktop-Umgebung',
 'pwr_env_sub': '%s · Befehle automatisch angepasst',
 'pwr_note_gnome': 'GNOME-Befehle (gsettings, gnome-settings-daemon)',
 'pwr_note_kde': 'KDE-Plasma-Befehle (kwriteconfig6, Powerdevil)',
 'pwr_note_cinnamon': 'Cinnamon-Befehle (gsettings)',
 'pwr_note_budgie': 'Budgie-Befehle (gnome-settings-daemon)',
 'pwr_note_unknown': 'Desktop nicht erkannt: GNOME-Befehle werden verwendet',
 'features_de_sub': 'an %s angepasste Pakete',
 'sec_fan': 'Lüfter',
 'sec_hw': 'Hardware Control',
 'sec_mesa': 'Mesa / Vulkan',
 'sec_kernel': 'Kernel PS5',
 'sec_ui_lang': 'Sprache der Oberfläche',
 'setup_menu': 'Empfohlenes Setup ausführen',
 'setup_title': 'Empfohlenes Setup',
 'setup_welcome_title': 'Willkommen bei PS5 Fedora Manager',
 'setup_welcome_body': 'Erster Start. Das vom Entwickler empfohlene Setup richtet die PS5 '
                       'unter Fedora in einem Durchgang ein:\n'
                       '\n'
                       '1. Energie (Standby deaktiviert)\n'
                       '2. Lüfter (PS5 Linux Tools, ps5fan, ps5boost)\n'
                       '3. Hardware Control\n'
                       '4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n'
                       '5. Paketquellen (RPM Fusion, Flathub, Cache)\n'
                       '6. Abhängigkeiten (fuse, 32-Bit-Treiber, Python, venv, Tkinter, '
                       'Node.js, Aktualisierungen)\n'
                       '7. App-Store (Bazaar, Extension Manager (GNOME), Steam, Heroic, '
                       'ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n'
                       '8. Hardware-Control-Plugin\n'
                       '9. Gaming Mode (Gamescope)\n'
                       '\n'
                       'Am Ende wird ein Neustart angeboten. Du kannst die Umgebung auch '
                       'selbst Abschnitt für Abschnitt einrichten.',
 'setup_welcome_recommended': 'Empfohlenes Setup (1 Klick)',
 'setup_welcome_manual': 'Selbst einrichten',
 'setup_confirm_body': 'Das empfohlene Setup installiert und konfiguriert alle aufgeführten '
                       'Elemente. Das kann mehrere Minuten dauern; das Fortschrittsfenster '
                       'zeigt jedes bestätigte Element und das Protokoll der Vorgänge.',
 'setup_running': 'Installation läuft…',
 'setup_finished': 'Setup abgeschlossen',
 'setup_log': 'Protokoll der Vorgänge',
 'setup_env_line': 'Erkannte Umgebung: %s · %s · Sitzung %s',
 'setup_close': 'Schließen',
 'setup_summary': '%d erfolgreich · %d fehlgeschlagen',
 'setup_reboot_title': 'Neustart erforderlich',
 'setup_reboot_body': 'Setup abgeschlossen: %d Element(e) installiert, %d Fehler.\n'
                      '\n'
                      'Ein Neustart ist nötig, um Dienste und Treiber zu aktivieren. Jetzt neu '
                      'starten?',
 'setup_reboot_now': 'Jetzt neu starten',
 'setup_later': 'Später',
 'setup_step1': '1. Energie',
 'setup_step2': '2. Lüfter',
 'setup_step3': '3. Hardware Control',
 'setup_step4': '4. Mesa / Vulkan',
 'setup_step5': '5. Paketquellen',
 'setup_step6': '6. Zusätzliche Abhängigkeiten',
 'setup_step7': '7. App-Store',
 'setup_step8': '8. Hardware Control — Plugin',
 'setup_step9': '9. Gaming Mode',
 'setup_pwr_sys': 'System-Standby deaktivieren',
 'setup_pwr_scr': 'Bildschirm-Abschaltung deaktivieren',
 'setup_pwr_full': 'Vollständigen Standby deaktivieren',
 'setup_fan_tools': 'PS5 Linux Tools installieren / aktualisieren',
 'setup_fan_svc': 'Dienst ps5fan aktivieren',
 'setup_fan_boot': 'Dienst ps5boost aktivieren (Systemstart)',
 'setup_hw': 'Hardware Control installieren / aktualisieren',
 'setup_mesa': 'Vulkan Tools und Mesa Demos installieren',
 'setup_repo_rpmfusion': 'RPM Fusion installieren (free + nonfree)',
 'setup_repo_flathub': 'Flatpak und Flathub installieren',
 'setup_repo_refresh': 'Paketquellen aktualisieren und Cache leeren',
 'setup_dep_fuse': 'FUSE installieren',
 'setup_dep_steam32': '32-Bit-Grafiktreiber für Steam installieren',
 'setup_dep_python': 'Python 3 und pip installieren',
 'setup_dep_venv': 'Virtuelle Umgebung my_project erstellen',
 'setup_dep_tk': 'Tkinter installieren',
 'setup_dep_node': 'Node.js und npm installieren',
 'setup_dep_fedora': 'Fedora-Pakete aktualisieren',
 'setup_app_bazaar': 'Bazaar installieren',
 'setup_app_extmgr': 'GNOME Extension Manager installieren',
 'setup_app_steam': 'Steam installieren',
 'setup_app_heroic': 'Heroic Games Launcher installieren',
 'setup_app_protonup': 'ProtonUp-Qt installieren',
 'setup_app_decky': 'Decky Loader installieren',
 'setup_app_universe': 'Universe installieren',
 'setup_app_appimagepool': 'AppImage Pool installieren',
 'setup_app_opera': 'Opera installieren',
 'setup_hw_plugin': 'Hardware-Control-Plugin installieren',
 'setup_gaming': 'Gamescope installieren (Gaming Mode)',
 'sec_features': 'Add Fedora Feature',
 'features_group_mobile': 'Handyverwaltung',
 'features_group_mobile_sub': 'Android-Telefon per WLAN oder USB: Dateien, Benachrichtigungen, '
                              'ADB und Fastboot.',
 'features_mobile_install': 'GSConnect, MTP / SSHFS und ADB / Fastboot installieren',
 'features_mobile_install_sub': 'gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs '
                                'nautilus-python android-tools',
 'features_mobile_done': 'GSConnect ist installiert: aktiviere die Erweiterung in der App '
                         '„Erweiterungen“ und koppele das Telefon.',
 'features_group_print': 'Drucker & Scanner',
 'features_group_print_sub': 'CUPS, Treiber für HP / Brother / Epson / Canon und generische, '
                             'Netzwerkerkennung, SANE und Simple Scan.',
 'features_print_install': 'Drucken und Scannen installieren',
 'features_print_install_sub': 'cups cups-filters system-config-printer hplip gutenprint-cups '
                               'splix sane-backends sane-backends-drivers-scanners '
                               'libsane-hpaio simple-scan',
 'features_print_enable': 'Druckdienst (CUPS) aktivieren',
 'features_print_enable_sub': 'sudo systemctl enable --now cups',
 'features_print_disable': 'CUPS-Dienst stoppen und deaktivieren',
 'features_print_disable_sub': 'sudo systemctl disable --now cups',
 'features_print_disable_confirm': 'CUPS wird gestoppt und deaktiviert: Drucken ist nicht mehr '
                                   'möglich, bis der Dienst wieder aktiviert wird.',
 'features_print_sockets': 'Sockets für die automatische Aktivierung deaktivieren',
 'features_print_sockets_sub': 'sudo systemctl disable --now cups.socket cups.path',
 'features_print_sockets_confirm': 'Ohne cups.socket und cups.path startet CUPS bei einem '
                                   'Druckauftrag nicht mehr automatisch.',
 'features_print_status': 'Status des CUPS-Dienstes anzeigen',
 'features_print_status_sub': 'systemctl status cups',
 'logs_group_main': 'Live-Verfolgung & Verlauf',
 'logs_group_opts': 'Protokoll-Einstellungen',
 'logs_live': 'Live-Protokollfenster',
 'logs_live_sub': 'In Echtzeit verfolgen, was der Manager tut',
 'logs_session': 'Protokoll dieser Sitzung',
 'logs_old': 'Ältere Protokolle',
 'logs_old_sub': 'Letzte 14 Tage, einzeln einsehbar',
 'logs_auto': 'Automatisch öffnen',
 'logs_auto_sub': 'Fenster beim ersten längeren Vorgang öffnen',
 'logs_clear': 'Protokolle löschen',
 'logs_clear_sub': 'Löscht die Dateien in /var/log/ps5-manager',
 'logs_clear_confirm': 'Alle in /var/log/ps5-manager gespeicherten Protokolle löschen?',
 'logs_cleared': 'Protokolle gelöscht.',
 'logs_none': 'Noch kein Protokoll gespeichert.',
 'lib_title': 'PS5-App-Store',
 'lib_sub': 'Wichtige Anwendungen installieren, aktualisieren, prüfen oder entfernen',
 'lib_cat_gaming': 'Gaming',
 'lib_cat_gaming_sub': 'Spiele-Launcher, Proton-Kompatibilitätsschichten und Steam-Plugins',
 'lib_cat_browser': 'Browser',
 'lib_cat_browser_sub': 'Webbrowser (offizielles RPM oder Flatpak)',
 'lib_cat_system': 'System & Werkzeuge',
 'lib_cat_system_sub': 'Datenträgerwerkzeuge, Flatpak-Store und GNOME-Erweiterungen',
 'install': 'Installieren',
 'remove': 'Deinstallieren',
 'update': 'Aktualisieren',
 'check': 'Auf Aktualisierungen prüfen',
 'installed_rpm': 'Installiert (RPM)',
 'installed_flatpak': 'Installiert (Flatpak)',
 'installed': 'Installiert',
 'not_installed': 'Nicht installiert',
 'choose_format': 'Welches Installationsformat für %s?',
 'format_rpm': 'RPM (offizielles Repository)',
 'format_flatpak': 'Flatpak (Flathub)',
 'mgr_title': 'PS5 Fedora Manager',
 'mgr_update': 'Manager und seine Abhängigkeiten aktualisieren',
 'mgr_update_sub': 'git fetch + reset von GitHub und Installation in /opt/ps5-manager',
 'mgr_uninstall': 'Manager vollständig deinstallieren',
 'mgr_uninstall_sub': 'Entfernt /opt/ps5-manager, den Starter und die Desktop-Verknüpfung',
 'mgr_uninstall_confirm': 'Manager und alle seine Systemdateien entfernen?',
 'lang_view': 'Installierte Sprachpakete anzeigen (System + Tastatur)',
 'lang_view_sub': 'Zeigt rpm -qa langpacks-* und localectl status',
 'lang_install': 'Sprache installieren',
 'lang_install_sub': 'Z. B.: fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8',
 'lang_install_prompt': 'Sprachcode (z. B. fr_FR.UTF-8):',
 'lang_full': 'Vollständige Konfiguration (Sprache + Tastatur + Konto)',
 'lang_full_sub': 'Setzt System-Locale, X11-/Konsolen-Tastatur und Benutzerkonto',
 'lang_pick_locale': 'System-Locale wählen',
 'lang_pick_kb': 'Tastaturbelegung wählen',
 'lang_logout_confirm': 'Sprache (%s) und Tastatur (%s) gesetzt.\n'
                        'Sitzung %s jetzt abmelden, um die Änderungen anzuwenden?',
 'repo_list': 'Alle Paketquellen anzeigen (RPM + Flatpak)',
 'repo_list_sub': 'dnf repolist --all und Flatpak-Quellen für System/Benutzer',
 'repo_rpmfusion': 'RPM Fusion installieren (free + nonfree)',
 'repo_rpmfusion_sub': 'Unverzichtbar für Steam, Multimedia-Codecs und Treiber',
 'repo_flathub': 'Flathub installieren (systemweit)',
 'repo_flathub_sub': 'Hauptquelle für Flatpak-Anwendungen',
 'repo_refresh': 'Paketquellen aktualisieren & Cache leeren',
 'repo_openh264': 'Repository fedora-cisco-openh264 aktivieren',
 'repo_openh264_sub': 'Offizieller Fedora-Codec H.264/AVC (Firefox, GStreamer, Surfen) — '
                      'nützlich auf allen vier Desktops',
 'repo_codecs': 'Multimedia-Codecs installieren (RPM Fusion)',
 'repo_codecs_sub': 'gstreamer1-plugins-ugly und bad-free-extras: H.264-/MPEG-Wiedergabe in '
                    'GNOME, KDE Plasma, Cinnamon und Budgie',
 'repo_de_title': 'Paketquellen des Desktops %s',
 'repo_de_sub': 'Keine Drittquelle nötig: die Gruppe @%s stammt aus den offiziellen '
                'Fedora-Repositories',
 'repo_de_group': 'Desktop-Pakete installieren / reparieren',
 'repo_de_missing': 'Gruppe @%s in den eingerichteten Quellen nicht gefunden',
 'mnt_desktop_db': 'Anwendungsdatenbank neu aufbauen',
 'mnt_desktop_db_sub': 'update-desktop-database /usr/share/applications + '
                       '~/.local/share/applications',
 'mnt_fonts': 'Schrift-Cache neu aufbauen',
 'mnt_fonts_sub': 'fc-cache -f (nach einer Desktop-Aktualisierung)',
 'mnt_kde_title': 'KDE-Plasma-Wartung',
 'mnt_kde_sub': 'KDE-Plasma-spezifische Caches',
 'mnt_kde_menu': 'KDE-Menü-Cache neu aufbauen',
 'mnt_kde_menu_sub': 'kbuildsycoca6 --noincremental',
 'repo_refresh_sub': 'dnf clean all, makecache --refresh und Flatpak-Appstream',
 'repo_add': 'Eigene Paketquelle hinzufügen (.repo-URL)',
 'repo_add_prompt': 'URL der .repo-Datei:',
 'repo_disable': 'DNF-Paketquelle deaktivieren',
 'repo_disable_sub': 'Deaktiviert, ohne die .repo-Datei zu löschen',
 'repo_rm_dnf': 'DNF-Paketquelle entfernen (.repo-Datei)',
 'repo_rm_flatpak': 'Flatpak-Quelle entfernen',
 'repo_id_prompt': 'ID der Quelle (z. B. rpmfusion-nonfree):',
 'repo_fp_prompt': 'Name der Flatpak-Quelle (z. B. flathub):',
 'usr_list': 'Benutzerliste anzeigen',
 'usr_list_sub': 'Menschliche Konten (UID >= 1000) in /etc/passwd',
 'usr_edit_me': 'Mein Konto bearbeiten (%s)',
 'usr_edit_me_sub': 'Passwort und Kontosprache ändern',
 'usr_add': 'Benutzer hinzufügen',
 'usr_del': 'Benutzerkonto löschen',
 'usr_root': 'Root-Konto: Status und Passwort',
 'usr_name_prompt': 'Kontoname:',
 'usr_pass_prompt': 'Passwort:',
 'usr_new_pass_prompt': 'Neues Passwort (leer lassen, um es nicht zu ändern):',
 'usr_del_confirm': 'Konto %s und sein Heimatverzeichnis endgültig löschen?',
 'fed_apps': 'Anwendungen aktualisieren (DNF & Flatpak)',
 'fed_apps_sub': 'dnf upgrade -y gefolgt von flatpak update --system',
 'fed_sys': 'Gesamtes System aktualisieren',
 'fed_sys_sub': 'dnf upgrade --refresh -y',
 'fed_lang': 'Sprachpakete aktualisieren',
 'fed_lang_sub': 'dnf upgrade -y langpacks-* glibc-langpack-*',
 'fed_meta': 'Metadaten der Paketquellen erneuern',
 'mnt_all': 'Komplette Bereinigung',
 'mnt_all_sub': 'DNF-Caches, Protokolle > 7 Tage, /tmp, Vorschaubilder und ungenutzte Flatpaks',
 'mnt_cache': 'Nur den DNF-Cache leeren',
 'mnt_autoremove': 'Verwaiste Pakete entfernen (autoremove)',
 'mnt_journal': 'systemd-Protokolle reduzieren (7 Tage)',
 'mnt_tmp': '/tmp und /var/tmp leeren',
 'mnt_thumbs': 'Benutzer-Vorschaubilder leeren',
 'mnt_kernels': 'Alte Kernel entfernen (2 behalten)',
 'mnt_disk': 'Belegten Speicherplatz anzeigen (df -h)',
 'pwr_full': 'Vollständiger Standby (System + Bildschirm)',
 'pwr_full_sub': 'Maskiert/demaskiert sleep.target und stellt die Bildschirmabschaltung ein (5 '
                 'Min.)',
 'pwr_sys': 'System-Standby (suspend / hibernate)',
 'pwr_sys_sub': 'Status von systemd sleep/suspend/hibernate.target',
 'pwr_scr': 'Bildschirm-Abschaltung (5 Min.)',
 'pwr_scr_sub': 'org.gnome.desktop.session idle-delay',
 'pwr_enable_full': 'Vollständigen Standby aktivieren',
 'pwr_disable_full': 'Vollständigen Standby deaktivieren',
 'fan_status': 'Vollständigen Status anzeigen (Dienste + ps5_control)',
 'fan_svc': 'Dienst ps5fan (Lüftung)',
 'fan_svc_sub': 'Aktivieren / beim Start starten (ps5fan.service)',
 'fan_boost': 'Dienst ps5boost (Boost-Modus)',
 'fan_boost_sub': 'Aktivieren / ps5boost.service starten',
 'fan_restart': 'ps5fan.service neu starten',
 'fan_tools': 'ps5-linux-tools installieren / aktualisieren',
 'fan_tools_sub': 'Klont und kompiliert ps5-linux/ps5-linux-tools',
 'hw_check': 'Vorhandensein der PS5-Hardware prüfen',
 'hw_check_sub': 'Untersucht /sys/class/hwmon und die sysfs-Knoten der PS5',
 'hw_install': 'PS5 Hardware Control installieren / aktualisieren',
 'hw_install_sub': 'Installiert python3-PyQt6, dann NotHavocc/ps5-hwcon-gui (--passwordless)',
 'hw_check_upd': 'Auf GitHub nach Aktualisierungen suchen',
 'hw_uninstall': 'PS5 Hardware Control deinstallieren',
 'hw_plugin_group': 'Hardware-Control-Plugin',
 'hw_plugin_group_sub': 'Decky-Plugin (Spielmodus): Lüfter, CPU-/GPU-Takt und LEDs',
 'hw_plugin_install': 'Hardware-Control-Plugin installieren',
 'hw_plugin_install_sub': 'Holt die Quellen, kompiliert und installiert in Decky Loader',
 'hw_plugin_uninstall': 'Hardware-Control-Plugin deinstallieren',
 'hw_plugin_uninstall_confirm': 'Hardware-Control-Plugin entfernen und Decky Loader neu '
                                'starten?',
 'deps_group': 'Systempakete',
 'deps_group_sub': 'Pakete, die Steam, Proton, Flatpak und AppImages oft benötigen',
 'deps_fuse': 'Fuse (fusermount)',
 'deps_fuse_sub': 'FUSE-Stack: Einbinden von Dateisystemen im Benutzerraum (fusermount, '
                  'AppImages vom Typ extract-and-run, Flatpak-Runtimes). fuse-libs liefert '
                  'libfuse.so, die viele Werkzeuge nutzen.',
 'deps_steam32': 'Steam — 32-Bit-Grafiktreiber',
 'deps_steam32_sub': 'Mesa Vulkan und DRI in 32 Bit + VA-API in 32 Bit: ohne sie verlieren '
                     'Steam, Proton/Wine und 32-Bit-Spiele die Grafikbeschleunigung und die '
                     'Hardware-Videodekodierung.',
 'gaming_group': 'Gamescope / Steam-Big-Picture-Sitzung',
 'gaming_group_sub': 'Steam-Sitzung + Umschalten GNOME / Steam im aktuellen Konto (Neustart '
                     'nötig)',
 'gaming_log': 'Gaming-Modus-Protokoll',
 'gaming_log_sub': 'Protokoll der Gamescope-Sitzung anzeigen (Startfehler, Rückkehr zum Desktop)',
 'gaming_log_empty': 'Noch kein Protokoll der Gaming-Sitzung.',
 'gaming_install': 'Gamescope installieren',
 'gaming_install_sub': 'Steam-Big-Picture-Sitzung, GDM-Autologin, GNOME/Steam-Umschaltung und '
                       'Verknüpfungen',
 'gaming_uninstall': 'Gamescope deinstallieren',
 'gaming_uninstall_confirm': 'Gamescope-Sitzung, GNOME/Steam-Umschaltung, sudoers-Regel und '
                             'Verknüpfungen entfernen?',
 'fix_group': 'Steam',
 'fix_group_sub': 'Schnelle Reparaturen, wenn Steam hängt',
 'fix_steam': 'Steam neu starten',
 'fix_steam_sub': 'Beendet alle Steam-Prozesse (pkill -9 steam) und startet Steam neu: behebt '
                  'ein schwarzes Fenster, „Steam is already running“ oder einen im Hintergrund '
                  'hängenden Client.',
 'fix_steam_confirm': 'Alle Steam-Prozesse hart beenden und Steam neu starten?',
 'lib_appimage_group': 'AppImage-Verwaltung',
 'lib_appimage_group_sub': 'AppImage Pool und Gear Lever, aus Flathub installiert',
 'appimage_pool_desc': 'AppImageHub durchsuchen und AppImages mit wenigen Klicks installieren '
                       '(io.github.prateekmedia.appimagepool).',
 'appimage_gear_desc': 'Bindet AppImages ins Anwendungsmenü ein: Symbol, Aktualisierungen und '
                       'Versionsverwaltung (it.mijorus.gearlever).',
 'appimage_install': 'Installieren',
 'appimage_update': 'Aktualisieren',
 'appimage_uninstall': 'Deinstallieren',
 'appimage_uninstall_confirm': '%s (flatpak) deinstallieren?',
 'appimage_flathub': 'Flathub-Seite öffnen',
 'deps_python_group': 'Python 3',
 'deps_python_group_sub': 'Interpreter, pip, Tkinter und virtuelle Umgebung',
 'deps_python': 'Python 3 + pip',
 'deps_python_sub': 'python3, python3-pip: Interpreter und Python-Paketverwaltung.',
 'deps_python_venv': 'Virtuelle Umgebung my_project erstellen',
 'deps_python_venv_sub': 'python3 -m venv my_project und dann source my_project/bin/activate '
                         '(im Heimatverzeichnis).',
 'deps_python_venv_ready': 'Umgebung in %s erstellt. Aktivierung im Terminal:\n'
                           'source %s/bin/activate',
 'deps_python_versions': 'Python-Versionen prüfen',
 'deps_python_versions_sub': 'Zeigt die Ausgabe von python3 --version und pip3 --version.',
 'deps_tkinter': 'Tkinter (python3-tkinter)',
 'deps_tkinter_sub': 'Tk-Oberfläche für Python: IDLE, tkinter, TkAgg von matplotlib.',
 'deps_node_group': 'Node.js / npm',
 'deps_node_group_sub': 'JavaScript-Laufzeit und Paketverwaltung',
 'deps_node_install': 'Node.js + npm installieren',
 'deps_node_install_sub': 'nodejs und npm aus den Fedora-Repositories.',
 'deps_node_update': 'Aktualisieren (Fedora-Repositories)',
 'deps_node_update_sub': 'dnf upgrade --refresh nodejs npm: behebt kleinere Aktualisierungen.',
 'deps_node_major': 'Auf die aktuelle Hauptversion wechseln (NodeSource 26 LTS)',
 'deps_node_major_sub': 'Fügt das NodeSource-26-LTS-Repository hinzu und installiert nodejs '
                        'neu: nötig für einen Hauptversionswechsel.',
 'deps_node_versions': 'Node.js-Versionen prüfen',
 'deps_node_versions_sub': 'Zeigt die Ausgabe von node --version und npm --version.',
 'deps_node_uninstall': 'Node.js + npm deinstallieren',
 'deps_node_uninstall_confirm': 'nodejs und npm vom System entfernen?',
 'mesa_tools': 'Vulkan-Werkzeuge und Mesa Demos installieren',
 'mesa_tools_sub': 'vulkan-tools und mesa-demos',
 'mesa_upd': 'Mesa- und Vulkan-Pakete aktualisieren',
 'mesa_upd_sub': 'dnf upgrade -y mesa* vulkan*',
 'mesa_radv': 'RADV-Unterstützung prüfen (AMD-GPU der PS5)',
 'mesa_summary': 'Vollständige Vulkan-Übersicht anzeigen',
 'krn_latest': 'Neueste verfügbare Version prüfen',
 'krn_latest_sub': 'Aus ps5-linux/ps5-linux-patches auf GitHub',
 'krn_install': 'Neuesten PS5-Kernel installieren (RPM)',
 'krn_install_sub': 'rpm -ivh --nosignature --replacefiles und anschließend EFI-Deployment',
 'krn_boot': 'Startkernel wählen (/boot/efi)',
 'krn_none': 'Kein Kernel-Paket gefunden.',
 'krn_boot_none': 'Kein Kernel in /boot',
 'krn_no_old': 'Kein alter Kernel zu entfernen.',
 'krn_files_missing': 'vmlinuz-%s oder initrd.img-%s fehlt.',
 'gh_unreachable': 'GitHub ist nicht erreichbar.',
 'gh_release_missing': 'Release nicht gefunden.',
 'repo_none': 'Keine .repo-Datei für [%s]',
 'usr_refuse': 'Abgelehnt für %s',
 'mesa_no_vulkaninfo': 'vulkaninfo fehlt — bitte zuerst vulkan-tools installieren.',
 'ai_ollama_absent': 'Ollama ist nicht installiert.',
 'ai_podman_absent': 'Podman ist nicht installiert.',
 'krn_boot_sub': 'Kopiert die gewählten vmlinuz und initrd.img auf die ESP',
 'krn_remove': 'Alte Kernel bereinigen / entfernen',
 'krn_remove_sub': 'Entfernt alte linux-ps5-Pakete und schützt den aktiven Kernel',
 'krn_running': 'Gestartet',
 'krn_esp': 'Auf /boot/efi',
 'krn_installed': 'Installiert',
 'krn_protected': 'Geschützt (aktiv / Boot)',
 'krn_pick': 'Bestimmten Kernel installieren (alle Releases)',
 'krn_pick_sub': 'Lädt das linux-ps5-RPM des gewählten Releases: erlaubt die Rückkehr zu einem '
                 'älteren Kernel',
 'krn_pick_empty': 'Kein Release von GitHub abgerufen.',
 'krn_available': 'Nicht installiert',
 'krn_releases_page': 'GitHub-Release-Seite öffnen',
 'krn_no_rpm': 'Dieses Release veröffentlicht kein RPM (nur Arch-Paket).\n'
               'Wähle eine Version mit einer .rpm-Datei für x86_64.',
 'ui_lang_title': 'Sprache der Oberfläche',
 'ui_lang_sub': 'Sofortige Änderung, gespeichert in /etc/ps5-manager/language',
 'fr_label': 'Français',
 'en_label': 'English',
 'aidev_open_sub': 'Ollama, Open WebUI (Podman), VSCodium, Freebuff und lokale KI-Modelle',
 'aidev_stack': 'KI- und Entwicklerwerkzeuge',
 'aidev_stack_sub': 'Installation, Aktualisierung und Deinstallation der lokalen Bausteine',
 'aidev_services': 'KI-Dienste steuern',
 'aidev_services_sub': 'Starten, stoppen oder beim Booten deaktivieren, um RAM zu sparen',
 'aidev_models': 'Lokale KI-Modelle (Ollama)',
 'aidev_models_sub': 'Modelle herunterladen, prüfen, aus dem RAM entladen oder löschen',
 'aidev_extras': 'KI-Diagnose & Wartung (PS5)',
 'aidev_extras_sub': 'RAM-/GPU-Prüfung, Podman-Bereinigung und Persistenz'}


STRINGS['pt'] = {'app_title': 'PS5 Fedora Manager',
 'search_placeholder': 'Pesquisar uma opção ou um programa…',
 'sys_group_session': 'Sessão',
 'sys_group_software': 'Software',
 'sys_group_app': 'Aplicação',
 'sys_os': 'Sistema operativo',
 'sys_kernel': 'Kernel Linux',
 'sys_arch': 'Arquitetura',
 'sys_dnf': 'Gerenciador de pacotes',
 'sys_desktop': 'Ambiente de desktop',
 'sys_dm': 'Gerenciador de sessão',
 'sys_session': 'Sessão gráfica',
 'sys_user': 'Usuário',
 'sys_accent': 'Cor de destaque',
 'sys_gamescope': 'Gamescope',
 'sys_steam': 'Steam',
 'sys_installed': 'Instalado',
 'sys_version': 'Versão do manager',
 'sys_file': 'Arquivo',
 'sys_log': 'Registro da sessão',
 'sys_open': 'Abrir',
 'sys_copy': 'Copiar as informações',
 'sys_copy_done': 'Informações copiadas',
 'switch_session': 'Alternar sessão (%s / Steam)',
 'podman_linger': 'Ativar a persistência de sessão do Podman (%s)',
 'podman_linger_sub': 'loginctl enable-linger %s · inicia o Open WebUI sem terminal',
 'debug_version': 'Versão',
 'ai_webui_state': 'Estado: %s (%s) · Ícone do GNOME: %s',
 'ai_icon_installed': 'instalado',
 'ai_icon_absent': 'ausente',
 'ai_models_count': '%d modelo(s) · %d ativo(s) na RAM',
 'system_info': 'Sistema',
 'accent_label': 'Cor de destaque do GNOME',
 'follow_gnome': 'Sincronizada com o GNOME',
 'about': 'Sobre o PS5 Fedora Manager',
 'confirm': 'Confirmar',
 'cancel': 'Cancelar',
 'ok': 'OK',
 'close': 'Fechar',
 'running': 'Processando…',
 'busy': 'Já existe uma tarefa em andamento.',
 'done': 'Concluído.',
 'failed': 'Falha (código %s)',
 'view_log': 'Ver o registro',
 'clear': 'Limpar',
 'sec_logs': 'Registro / Logs',
 'sec_library': 'Loja de aplicativos',
 'sec_aidev': 'IA e Desenvolvimento',
 'sec_dev': 'Desenvolvimento',
 'sec_web': 'Servidor web',
 'sec_easy': 'Instalação fácil',
 'sec_deps': 'Dependências adicionais',
 'sec_gaming': 'Gaming Mode',
 'sec_fix': 'Correções diversas',
 'sec_update': 'Atualização do gerenciador',
 'sec_lang': 'Idiomas e teclado',
 'sec_repos': 'Repositórios',
 'sec_users': 'Usuários',
 'sec_fedora': 'Atualizações do Fedora',
 'sec_maint': 'Manutenção',
 'sec_power': 'Energia',
 'pwr_env': 'Ambiente de desktop detectado',
 'pwr_env_sub': '%s · comandos ajustados automaticamente',
 'pwr_note_gnome': 'comandos do GNOME (gsettings, gnome-settings-daemon)',
 'pwr_note_kde': 'comandos do KDE Plasma (kwriteconfig6, Powerdevil)',
 'pwr_note_cinnamon': 'comandos do Cinnamon (gsettings)',
 'pwr_note_budgie': 'comandos do Budgie (gnome-settings-daemon)',
 'pwr_note_unknown': 'desktop não identificado: comandos do GNOME aplicados',
 'features_de_sub': 'pacotes adaptados ao %s',
 'sec_fan': 'Ventoinha',
 'sec_hw': 'Hardware Control',
 'sec_mesa': 'Mesa / Vulkan',
 'sec_kernel': 'Kernel PS5',
 'sec_ui_lang': 'Idioma da interface',
 'setup_menu': 'Executar a configuração recomendada',
 'setup_title': 'Configuração recomendada',
 'setup_welcome_title': 'Bem-vindo ao PS5 Fedora Manager',
 'setup_welcome_body': 'Primeira inicialização. A configuração recomendada pelo desenvolvedor '
                       'aplica de uma só vez os ajustes básicos do PS5 com Fedora:\n'
                       '\n'
                       '1. Energia (suspensão desativada)\n'
                       '2. Ventoinha (PS5 Linux Tools, ps5fan, ps5boost)\n'
                       '3. Hardware Control\n'
                       '4. Mesa / Vulkan (vulkan-tools, mesa-demos)\n'
                       '5. Repositórios (RPM Fusion, Flathub, cache)\n'
                       '6. Dependências (fuse, drivers de 32 bits, Python, venv, Tkinter, '
                       'Node.js, atualizações)\n'
                       '7. Loja de aplicativos (Bazaar, Extension Manager (GNOME), Steam, '
                       'Heroic, ProtonUp-Qt, Decky, Universe, AppImage Pool, Opera)\n'
                       '8. Plugin Hardware Control\n'
                       '9. Gaming Mode (Gamescope)\n'
                       '\n'
                       'No final será proposto reiniciar. Você também pode configurar o '
                       'ambiente por conta própria, seção por seção.',
 'setup_welcome_recommended': 'Configuração recomendada (1 clique)',
 'setup_welcome_manual': 'Configurar eu mesmo',
 'setup_confirm_body': 'A configuração recomendada instala e ajusta todos os itens listados. '
                       'Isso pode levar vários minutos; a janela de acompanhamento mostra cada '
                       'item validado e o registro das operações.',
 'setup_running': 'Instalação em andamento…',
 'setup_finished': 'Configuração concluída',
 'setup_log': 'Registro das operações',
 'setup_env_line': 'Ambiente detectado: %s · %s · sessão %s',
 'setup_close': 'Fechar',
 'setup_summary': '%d sucesso(s) · %d falha(s)',
 'setup_reboot_title': 'Reinicialização necessária',
 'setup_reboot_body': 'Configuração concluída: %d item(ns) instalado(s), %d falha(s).\n'
                      '\n'
                      'É necessário reiniciar para ativar os serviços e os drivers. Reiniciar '
                      'agora?',
 'setup_reboot_now': 'Reiniciar agora',
 'setup_later': 'Mais tarde',
 'setup_step1': '1. Energia',
 'setup_step2': '2. Ventoinha',
 'setup_step3': '3. Hardware Control',
 'setup_step4': '4. Mesa / Vulkan',
 'setup_step5': '5. Repositórios',
 'setup_step6': '6. Dependências adicionais',
 'setup_step7': '7. Loja de aplicativos',
 'setup_step8': '8. Hardware Control — plugin',
 'setup_step9': '9. Gaming Mode',
 'setup_pwr_sys': 'Desativar a suspensão do sistema',
 'setup_pwr_scr': 'Desativar o desligamento da tela',
 'setup_pwr_full': 'Desativar a suspensão completa',
 'setup_fan_tools': 'Instalar / atualizar PS5 Linux Tools',
 'setup_fan_svc': 'Ativar o serviço ps5fan',
 'setup_fan_boot': 'Ativar o serviço ps5boost (inicialização)',
 'setup_hw': 'Instalar / atualizar Hardware Control',
 'setup_mesa': 'Instalar Vulkan Tools e Mesa Demos',
 'setup_repo_rpmfusion': 'Instalar RPM Fusion (free + nonfree)',
 'setup_repo_flathub': 'Instalar Flatpak e Flathub',
 'setup_repo_refresh': 'Atualizar os repositórios e limpar o cache',
 'setup_dep_fuse': 'Instalar FUSE',
 'setup_dep_steam32': 'Instalar os drivers gráficos de 32 bits para o Steam',
 'setup_dep_python': 'Instalar Python 3 e pip',
 'setup_dep_venv': 'Criar o ambiente virtual my_project',
 'setup_dep_tk': 'Instalar Tkinter',
 'setup_dep_node': 'Instalar Node.js e npm',
 'setup_dep_fedora': 'Atualizar os pacotes do Fedora',
 'setup_app_bazaar': 'Instalar Bazaar',
 'setup_app_extmgr': 'Instalar GNOME Extension Manager',
 'setup_app_steam': 'Instalar Steam',
 'setup_app_heroic': 'Instalar Heroic Games Launcher',
 'setup_app_protonup': 'Instalar ProtonUp-Qt',
 'setup_app_decky': 'Instalar Decky Loader',
 'setup_app_universe': 'Instalar Universe',
 'setup_app_appimagepool': 'Instalar AppImage Pool',
 'setup_app_opera': 'Instalar Opera',
 'setup_hw_plugin': 'Instalar o plugin Hardware Control',
 'setup_gaming': 'Instalar Gamescope (Gaming Mode)',
 'sec_features': 'Add Fedora Feature',
 'features_group_mobile': 'Gerenciamento do celular',
 'features_group_mobile_sub': 'Celular Android por Wi-Fi ou USB: arquivos, notificações, ADB e '
                              'Fastboot.',
 'features_mobile_install': 'Instalar GSConnect, MTP / SSHFS e ADB / Fastboot',
 'features_mobile_install_sub': 'gnome-shell-extension-gsconnect gvfs-mtp fuse-sshfs '
                                'nautilus-python android-tools',
 'features_mobile_done': 'O GSConnect está instalado: ative a extensão no aplicativo '
                         '«Extensões» e emparelhe o celular.',
 'features_group_print': 'Impressoras e scanners',
 'features_group_print_sub': 'CUPS, drivers HP / Brother / Epson / Canon e genéricos, '
                             'descoberta em rede, SANE e Simple Scan.',
 'features_print_install': 'Instalar a impressão e a digitalização',
 'features_print_install_sub': 'cups cups-filters system-config-printer hplip gutenprint-cups '
                               'splix sane-backends sane-backends-drivers-scanners '
                               'libsane-hpaio simple-scan',
 'features_print_enable': 'Ativar o serviço de impressão (CUPS)',
 'features_print_enable_sub': 'sudo systemctl enable --now cups',
 'features_print_disable': 'Parar e desativar o serviço CUPS',
 'features_print_disable_sub': 'sudo systemctl disable --now cups',
 'features_print_disable_confirm': 'O CUPS será parado e desativado: não será possível '
                                   'imprimir até que o serviço seja reativado.',
 'features_print_sockets': 'Desativar os sockets de ativação automática',
 'features_print_sockets_sub': 'sudo systemctl disable --now cups.socket cups.path',
 'features_print_sockets_confirm': 'Sem cups.socket nem cups.path, o CUPS não reiniciará mais '
                                   'automaticamente quando uma impressão for solicitada.',
 'features_print_status': 'Ver o estado do serviço CUPS',
 'features_print_status_sub': 'systemctl status cups',
 'logs_group_main': 'Acompanhamento ao vivo e histórico',
 'logs_group_opts': 'Preferências dos registros',
 'logs_live': 'Janela de log ao vivo',
 'logs_live_sub': 'Acompanhar em tempo real o que o gerenciador faz',
 'logs_session': 'Registro desta sessão',
 'logs_old': 'Registros anteriores',
 'logs_old_sub': 'Últimos 14 dias, consultáveis um por um',
 'logs_auto': 'Abertura automática',
 'logs_auto_sub': 'Abrir a janela no primeiro trabalho longo',
 'logs_clear': 'Limpar os registros',
 'logs_clear_sub': 'Apaga os arquivos de /var/log/ps5-manager',
 'logs_clear_confirm': 'Apagar todos os registros salvos em /var/log/ps5-manager?',
 'logs_cleared': 'Registros apagados.',
 'logs_none': 'Nenhum registro salvo por enquanto.',
 'lib_title': 'Loja de aplicativos PS5',
 'lib_sub': 'Instalar, atualizar, verificar ou desinstalar as aplicações essenciais',
 'lib_cat_gaming': 'Gaming',
 'lib_cat_gaming_sub': 'Lançadores de jogos, camadas de compatibilidade Proton e plugins do '
                       'Steam',
 'lib_cat_browser': 'Navegadores',
 'lib_cat_browser_sub': 'Navegadores web (RPM oficial ou Flatpak)',
 'lib_cat_system': 'Sistema e utilitários',
 'lib_cat_system_sub': 'Ferramentas de disco, loja Flatpak e extensões do GNOME',
 'install': 'Instalar',
 'remove': 'Desinstalar',
 'update': 'Atualizar',
 'check': 'Verificar atualizações',
 'installed_rpm': 'Instalado (RPM)',
 'installed_flatpak': 'Instalado (Flatpak)',
 'installed': 'Instalado',
 'not_installed': 'Não instalado',
 'choose_format': 'Qual formato de instalação para %s?',
 'format_rpm': 'RPM (repositório oficial)',
 'format_flatpak': 'Flatpak (Flathub)',
 'mgr_title': 'PS5 Fedora Manager',
 'mgr_update': 'Atualizar o gerenciador e suas dependências',
 'mgr_update_sub': 'git fetch + reset do GitHub e instalação em /opt/ps5-manager',
 'mgr_uninstall': 'Desinstalar completamente o gerenciador',
 'mgr_uninstall_sub': 'Remove /opt/ps5-manager, o lançador e o atalho da área de trabalho',
 'mgr_uninstall_confirm': 'Remover o gerenciador e todos os seus arquivos de sistema?',
 'lang_view': 'Ver os pacotes de idioma instalados (sistema + teclado)',
 'lang_view_sub': 'Mostra rpm -qa langpacks-* e localectl status',
 'lang_install': 'Instalar um idioma',
 'lang_install_sub': 'Ex.: fr_FR.UTF-8, es_ES.UTF-8, de_DE.UTF-8',
 'lang_install_prompt': 'Código do idioma (ex.: fr_FR.UTF-8):',
 'lang_full': 'Configuração completa (idioma + teclado + conta)',
 'lang_full_sub': 'Aplica a localidade do sistema, o teclado X11/console e a conta de usuário',
 'lang_pick_locale': 'Escolher a localidade do sistema',
 'lang_pick_kb': 'Escolher o layout do teclado',
 'lang_logout_confirm': 'Idioma (%s) e teclado (%s) aplicados.\n'
                        'Encerrar a sessão %s agora para aplicar as mudanças?',
 'repo_list': 'Ver todos os repositórios (RPM + Flatpak)',
 'repo_list_sub': 'dnf repolist --all e repositórios Flatpak de sistema/usuário',
 'repo_rpmfusion': 'Instalar RPM Fusion (free + nonfree)',
 'repo_rpmfusion_sub': 'Indispensável para Steam, codecs de mídia e drivers',
 'repo_flathub': 'Instalar Flathub (escopo de sistema)',
 'repo_flathub_sub': 'Repositório principal das aplicações Flatpak',
 'repo_refresh': 'Atualizar os repositórios e limpar o cache',
 'repo_openh264': 'Ativar o repositório fedora-cisco-openh264',
 'repo_openh264_sub': 'Codec H.264/AVC oficial do Fedora (Firefox, GStreamer, navegação) — '
                      'útil nos quatro desktops',
 'repo_codecs': 'Instalar os codecs de mídia (RPM Fusion)',
 'repo_codecs_sub': 'gstreamer1-plugins-ugly e bad-free-extras: reprodução H.264 / MPEG no '
                    'GNOME, KDE Plasma, Cinnamon e Budgie',
 'repo_de_title': 'Repositórios do desktop %s',
 'repo_de_sub': 'Nenhum repositório de terceiros é necessário: o grupo @%s vem dos '
                'repositórios oficiais do Fedora',
 'repo_de_group': 'Instalar / reparar os pacotes do desktop',
 'repo_de_missing': 'Grupo @%s não encontrado nos repositórios configurados',
 'mnt_desktop_db': 'Reconstruir o banco de dados de aplicações',
 'mnt_desktop_db_sub': 'update-desktop-database /usr/share/applications + '
                       '~/.local/share/applications',
 'mnt_fonts': 'Reconstruir o cache de fontes',
 'mnt_fonts_sub': 'fc-cache -f (após uma atualização do desktop)',
 'mnt_kde_title': 'Manutenção do KDE Plasma',
 'mnt_kde_sub': 'Caches específicos do KDE Plasma',
 'mnt_kde_menu': 'Reconstruir o cache de menus do KDE',
 'mnt_kde_menu_sub': 'kbuildsycoca6 --noincremental',
 'repo_refresh_sub': 'dnf clean all, makecache --refresh e appstream do Flatpak',
 'repo_add': 'Adicionar um repositório personalizado (URL .repo)',
 'repo_add_prompt': 'URL do arquivo .repo:',
 'repo_disable': 'Desativar um repositório DNF',
 'repo_disable_sub': 'Desativa sem remover o arquivo .repo',
 'repo_rm_dnf': 'Remover um repositório DNF (arquivo .repo)',
 'repo_rm_flatpak': 'Remover um repositório Flatpak',
 'repo_id_prompt': 'ID do repositório (ex.: rpmfusion-nonfree):',
 'repo_fp_prompt': 'Nome do repositório Flatpak (ex.: flathub):',
 'usr_list': 'Ver a lista de usuários',
 'usr_list_sub': 'Contas humanas (UID >= 1000) em /etc/passwd',
 'usr_edit_me': 'Editar minha conta (%s)',
 'usr_edit_me_sub': 'Alterar a senha e o idioma da conta',
 'usr_add': 'Adicionar um usuário',
 'usr_del': 'Remover uma conta de usuário',
 'usr_root': 'Conta root: estado e senha',
 'usr_name_prompt': 'Nome da conta:',
 'usr_pass_prompt': 'Senha:',
 'usr_new_pass_prompt': 'Nova senha (deixe vazio para não alterar):',
 'usr_del_confirm': 'Remover definitivamente a conta %s e sua pasta pessoal?',
 'fed_apps': 'Atualizar as aplicações (DNF e Flatpak)',
 'fed_apps_sub': 'dnf upgrade -y seguido de flatpak update --system',
 'fed_sys': 'Atualizar o sistema completo',
 'fed_sys_sub': 'dnf upgrade --refresh -y',
 'fed_lang': 'Atualizar os pacotes de idioma',
 'fed_lang_sub': 'dnf upgrade -y langpacks-* glibc-langpack-*',
 'fed_meta': 'Atualizar os metadados dos repositórios',
 'mnt_all': 'Limpeza completa',
 'mnt_all_sub': 'Caches do DNF, registros > 7 dias, /tmp, miniaturas e Flatpaks não usados',
 'mnt_cache': 'Limpar apenas o cache do DNF',
 'mnt_autoremove': 'Remover os pacotes órfãos (autoremove)',
 'mnt_journal': 'Reduzir os registros do systemd (7 dias)',
 'mnt_tmp': 'Limpar /tmp e /var/tmp',
 'mnt_thumbs': 'Limpar as miniaturas do usuário',
 'mnt_kernels': 'Remover os kernels antigos (manter 2)',
 'mnt_disk': 'Ver o espaço em disco usado (df -h)',
 'pwr_full': 'Suspensão completa (sistema + tela)',
 'pwr_full_sub': 'Mascara/desmascara sleep.target e configura o desligamento da tela (5 min)',
 'pwr_sys': 'Suspensão do sistema (suspend / hibernate)',
 'pwr_sys_sub': 'Estado do systemd sleep/suspend/hibernate.target',
 'pwr_scr': 'Desligamento da tela (5 min)',
 'pwr_scr_sub': 'org.gnome.desktop.session idle-delay',
 'pwr_enable_full': 'Ativar a suspensão completa',
 'pwr_disable_full': 'Desativar a suspensão completa',
 'fan_status': 'Ver o status completo (serviços + ps5_control)',
 'fan_svc': 'Serviço ps5fan (ventilação)',
 'fan_svc_sub': 'Ativar / iniciar no boot (ps5fan.service)',
 'fan_boost': 'Serviço ps5boost (modo boost)',
 'fan_boost_sub': 'Ativar / iniciar ps5boost.service',
 'fan_restart': 'Reiniciar ps5fan.service',
 'fan_tools': 'Instalar / atualizar ps5-linux-tools',
 'fan_tools_sub': 'Clona e compila ps5-linux/ps5-linux-tools',
 'hw_check': 'Verificar a presença do hardware PS5',
 'hw_check_sub': 'Inspeciona /sys/class/hwmon e os nós sysfs do PS5',
 'hw_install': 'Instalar / atualizar PS5 Hardware Control',
 'hw_install_sub': 'Instala python3-PyQt6 e depois NotHavocc/ps5-hwcon-gui (--passwordless)',
 'hw_check_upd': 'Procurar atualizações no GitHub',
 'hw_uninstall': 'Desinstalar PS5 Hardware Control',
 'hw_plugin_group': 'Plugin Hardware Control',
 'hw_plugin_group_sub': 'Plugin Decky (modo Jogo): ventoinha, clocks de CPU/GPU e LEDs',
 'hw_plugin_install': 'Instalar o plugin Hardware Control',
 'hw_plugin_install_sub': 'Baixa as fontes, compila e instala no Decky Loader',
 'hw_plugin_uninstall': 'Desinstalar o plugin Hardware Control',
 'hw_plugin_uninstall_confirm': 'Remover o plugin Hardware Control e reiniciar o Decky Loader?',
 'deps_group': 'Pacotes do sistema',
 'deps_group_sub': 'Pacotes frequentemente exigidos por Steam, Proton, Flatpak e AppImages',
 'deps_fuse': 'Fuse (fusermount)',
 'deps_fuse_sub': 'Pilha FUSE: montagem de sistemas de arquivos no espaço do usuário '
                  '(fusermount, AppImage do tipo extract-and-run, runtimes Flatpak). fuse-libs '
                  'fornece libfuse.so, usada por muitas ferramentas.',
 'deps_steam32': 'Steam — drivers gráficos de 32 bits',
 'deps_steam32_sub': 'Mesa Vulkan e DRI de 32 bits + VA-API de 32 bits: sem eles, o Steam, o '
                     'Proton/Wine e os jogos de 32 bits perdem a aceleração gráfica e a '
                     'decodificação de vídeo por hardware.',
 'gaming_group': 'Gamescope / sessão Steam Big Picture',
 'gaming_group_sub': 'Sessão Steam + alternância GNOME / Steam na conta atual (reinicialização '
                     'necessária)',
 'gaming_log': 'Registro do modo Gaming',
 'gaming_log_sub': 'Mostrar o registro da sessão Gamescope (erro de inicialização, volta à área de trabalho)',
 'gaming_log_empty': 'Ainda não há registro da sessão Gaming.',
 'gaming_install': 'Instalar Gamescope',
 'gaming_install_sub': 'Sessão Steam Big Picture, login automático no GDM, alternância '
                       'GNOME/Steam e atalhos',
 'gaming_uninstall': 'Desinstalar Gamescope',
 'gaming_uninstall_confirm': 'Remover a sessão Gamescope, a alternância GNOME/Steam, a regra '
                             'sudoers e os atalhos?',
 'fix_group': 'Steam',
 'fix_group_sub': 'Reparos rápidos quando o Steam trava',
 'fix_steam': 'Reiniciar o Steam',
 'fix_steam_sub': 'Mata todos os processos do Steam (pkill -9 steam) e reinicia o Steam: '
                  'corrige uma janela preta, um «Steam is already running» ou um cliente que '
                  'ficou em segundo plano.',
 'fix_steam_confirm': 'Fechar à força todos os processos do Steam e reiniciar o Steam?',
 'lib_appimage_group': 'Gerenciamento de AppImage',
 'lib_appimage_group_sub': 'AppImage Pool e Gear Lever, instalados pelo Flathub',
 'appimage_pool_desc': 'Navegue pelo AppImageHub e instale AppImages em poucos cliques '
                       '(io.github.prateekmedia.appimagepool).',
 'appimage_gear_desc': 'Integra as AppImages ao menu de aplicativos: ícone, atualizações e '
                       'gerenciamento de versões (it.mijorus.gearlever).',
 'appimage_install': 'Instalar',
 'appimage_update': 'Atualizar',
 'appimage_uninstall': 'Desinstalar',
 'appimage_uninstall_confirm': 'Desinstalar %s (flatpak)?',
 'appimage_flathub': 'Abrir a página do Flathub',
 'deps_python_group': 'Python 3',
 'deps_python_group_sub': 'Interpretador, pip, Tkinter e ambiente virtual',
 'deps_python': 'Python 3 + pip',
 'deps_python_sub': 'python3, python3-pip: interpretador e gerenciador de pacotes Python.',
 'deps_python_venv': 'Criar o ambiente virtual my_project',
 'deps_python_venv_sub': 'python3 -m venv my_project e depois source my_project/bin/activate '
                         '(na pasta pessoal).',
 'deps_python_venv_ready': 'Ambiente criado em %s. Ativação no terminal:\n'
                           'source %s/bin/activate',
 'deps_python_versions': 'Verificar as versões do Python',
 'deps_python_versions_sub': 'Mostra a saída de python3 --version e pip3 --version.',
 'deps_tkinter': 'Tkinter (python3-tkinter)',
 'deps_tkinter_sub': 'Interface gráfica Tk para Python: IDLE, tkinter, TkAgg do matplotlib.',
 'deps_node_group': 'Node.js / npm',
 'deps_node_group_sub': 'Runtime JavaScript e gerenciador de pacotes',
 'deps_node_install': 'Instalar Node.js + npm',
 'deps_node_install_sub': 'nodejs e npm dos repositórios do Fedora.',
 'deps_node_update': 'Atualizar (repositórios do Fedora)',
 'deps_node_update_sub': 'dnf upgrade --refresh nodejs npm: corrige as atualizações menores.',
 'deps_node_major': 'Passar para a versão principal recente (NodeSource 26 LTS)',
 'deps_node_major_sub': 'Adiciona o repositório NodeSource 26 LTS e reinstala o nodejs: '
                        'necessário para mudar a versão principal.',
 'deps_node_versions': 'Verificar as versões do Node.js',
 'deps_node_versions_sub': 'Mostra a saída de node --version e npm --version.',
 'deps_node_uninstall': 'Desinstalar Node.js + npm',
 'deps_node_uninstall_confirm': 'Remover nodejs e npm do sistema?',
 'mesa_tools': 'Instalar as ferramentas Vulkan e as Mesa demos',
 'mesa_tools_sub': 'vulkan-tools e mesa-demos',
 'mesa_upd': 'Atualizar os pacotes Mesa e Vulkan',
 'mesa_upd_sub': 'dnf upgrade -y mesa* vulkan*',
 'mesa_radv': 'Verificar o suporte a RADV (GPU AMD do PS5)',
 'mesa_summary': 'Mostrar o resumo completo do Vulkan',
 'krn_latest': 'Verificar a última versão disponível',
 'krn_latest_sub': 'De ps5-linux/ps5-linux-patches no GitHub',
 'krn_install': 'Instalar o último kernel PS5 (RPM)',
 'krn_install_sub': 'rpm -ivh --nosignature --replacefiles e implantação na EFI',
 'krn_boot': 'Escolher o kernel para iniciar (/boot/efi)',
 'krn_none': 'Nenhum pacote kernel encontrado.',
 'krn_boot_none': 'Nenhum kernel em /boot',
 'krn_no_old': 'Nenhum kernel antigo para remover.',
 'krn_files_missing': 'vmlinuz-%s ou initrd.img-%s ausente.',
 'gh_unreachable': 'Não foi possível contatar o GitHub.',
 'gh_release_missing': 'Release não encontrada.',
 'repo_none': 'Nenhum arquivo .repo para [%s]',
 'usr_refuse': 'Recusado para %s',
 'mesa_no_vulkaninfo': 'vulkaninfo ausente — instale primeiro vulkan-tools.',
 'ai_ollama_absent': 'O Ollama não está instalado.',
 'ai_podman_absent': 'O Podman não está instalado.',
 'krn_boot_sub': 'Copia vmlinuz e initrd.img selecionados para a ESP',
 'krn_remove': 'Limpar / remover kernels antigos',
 'krn_remove_sub': 'Remove os pacotes linux-ps5 antigos protegendo o kernel ativo',
 'krn_running': 'Iniciado',
 'krn_esp': 'Em /boot/efi',
 'krn_installed': 'Instalado',
 'krn_protected': 'Protegido (ativo / boot)',
 'krn_pick': 'Instalar um kernel específico (todas as releases)',
 'krn_pick_sub': 'Baixa o RPM linux-ps5 da release escolhida: permite voltar a um kernel '
                 'anterior',
 'krn_pick_empty': 'Nenhuma release obtida do GitHub.',
 'krn_available': 'Não instalado',
 'krn_releases_page': 'Abrir a página de releases do GitHub',
 'krn_no_rpm': 'Esta release não publica RPM (apenas pacote Arch).\n'
               'Escolha uma versão que ofereça um .rpm x86_64.',
 'ui_lang_title': 'Idioma da interface',
 'ui_lang_sub': 'Mudança imediata e salva em /etc/ps5-manager/language',
 'fr_label': 'Français',
 'en_label': 'English',
 'aidev_open_sub': 'Ollama, Open WebUI (Podman), VSCodium, Freebuff e modelos de IA locais',
 'aidev_stack': 'Ferramentas e aplicativos de IA / Dev',
 'aidev_stack_sub': 'Instalação, atualização e desinstalação dos componentes locais',
 'aidev_services': 'Controle dos serviços de IA',
 'aidev_services_sub': 'Iniciar, parar ou desativar na inicialização para liberar RAM',
 'aidev_models': 'Modelos de IA locais (Ollama)',
 'aidev_models_sub': 'Baixar, inspecionar, descarregar da RAM ou remover os modelos',
 'aidev_extras': 'Diagnóstico e manutenção de IA (PS5)',
 'aidev_extras_sub': 'Verificação de RAM/GPU, limpeza do Podman e persistência'}


def read_ui_lang() -> str:
    try:
        with open(LANG_FILE, encoding="utf-8") as fh:
            val = fh.readline().strip().replace("_", "-").lower()
            code = val.split("-")[0]
            if code in LANG_ORDER:
                return code
    except OSError:
        pass
    return "fr"


def write_ui_lang(code: str) -> None:
    try:
        os.makedirs(os.path.dirname(LANG_FILE), exist_ok=True)
        with open(LANG_FILE, "w", encoding="utf-8") as fh:
            fh.write(code + "\n")
    except OSError:
        pass


UI_LANG = read_ui_lang()


def T(key: str) -> str:
    """Traduit `key` ; repli sur l'anglais puis sur la clé brute."""
    table = STRINGS.get(UI_LANG) or {}
    if key in table:
        return table[key]
    return STRINGS["en"].get(key) or STRINGS["fr"].get(key, key)


# ------------------------------------------------------------------------------
# Utilitaires système & journalisation
# ------------------------------------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\r")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def dnf_is_v5() -> bool:
    try:
        res = subprocess.run(
            ["dnf", "--version"], capture_output=True, text=True, timeout=3
        )
        return "dnf5" in (res.stdout.splitlines()[0] if res.stdout else "").lower()
    except (OSError, subprocess.SubprocessError):
        return False


IS_DNF5 = dnf_is_v5()


class SessionLogger:
    def __init__(self) -> None:
        self.path: str = self._init_log_file()

    def _init_log_file(self) -> str:
        try:
            os.makedirs(LOG_DIR, mode=0o755, exist_ok=True)
            cutoff = datetime.datetime.now().timestamp() - (14 * 86400)
            for fname in glob.glob(os.path.join(LOG_DIR, "session-*.log")):
                try:
                    if os.path.getmtime(fname) < cutoff:
                        os.remove(fname)
                except OSError:
                    pass
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            path = os.path.join(LOG_DIR, f"session-{ts}-{os.getpid()}.log")
            with open(path, "w", encoding="utf-8") as fh:
                os.chmod(path, 0o644)
                fh.write(
                    f"════ PS5 Fedora Manager — {datetime.datetime.now():%F %T} — utilisateur : {REAL_USER} — PID {os.getpid()}\n"
                )
                fh.write(f"système : {' '.join(os.uname()[:3])}\n")
            latest = os.path.join(LOG_DIR, "latest.log")
            try:
                if os.path.islink(latest) or os.path.exists(latest):
                    os.remove(latest)
                os.symlink(path, latest)
            except OSError:
                pass
            return path
        except OSError:
            fd, tmp = tempfile.mkstemp(prefix="ps5-manager-", suffix=".log")
            os.close(fd)
            return tmp

    def write_line(self, msg: str) -> None:
        line = f"{datetime.datetime.now():%H:%M:%S}  {msg}\n"
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass

    def list_logs(self) -> list[str]:
        files = glob.glob(os.path.join(LOG_DIR, "session-*.log"))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[:20]

    def clear_all(self) -> None:
        for fname in glob.glob(os.path.join(LOG_DIR, "session-*.log")):
            if fname != self.path:
                try:
                    os.remove(fname)
                except OSError:
                    pass
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(f"{datetime.datetime.now():%H:%M:%S}  journaux effacés\n")
        except OSError:
            pass


def log_window_enabled() -> bool:
    try:
        with open(LOG_WINDOW_FILE, encoding="utf-8") as fh:
            return fh.readline().strip() != "off"
    except OSError:
        return True


def set_log_window_enabled(enabled: bool) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_WINDOW_FILE), exist_ok=True)
        with open(LOG_WINDOW_FILE, "w", encoding="utf-8") as fh:
            fh.write("on\n" if enabled else "off\n")
    except OSError:
        pass


def get_os_summary() -> tuple[str, str]:
    pretty = "Fedora Linux"
    try:
        with open("/etc/os-release", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("PRETTY_NAME="):
                    val = line.split("=", 1)[1].strip().strip('"')
                    pretty = val.split(" (")[0]
                    break
    except OSError:
        pass
    return pretty, os.uname().release


def gh_latest_tag(repo: str) -> Optional[str]:
    url = f"https://github.com/{repo}/releases/latest"
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            final_url = resp.geturl()
            tag = final_url.rstrip("/").split("/")[-1]
            return tag if tag and tag != "latest" else None
    except (urllib.error.URLError, OSError):
        return None


def gh_latest_asset(repo: str, pattern: str) -> Optional[str]:
    tag = gh_latest_tag(repo)
    if not tag:
        return None
    expanded = f"https://github.com/{repo}/releases/expanded_assets/{tag}"
    try:
        with urllib.request.urlopen(expanded, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        matches = re.findall(rf"/{re.escape(repo)}/releases/download/[^\"]+", html)
        rx = re.compile(pattern)
        for m in matches:
            if rx.search(m):
                return f"https://github.com{m}"
    except (urllib.error.URLError, OSError):
        pass
    return None


def gh_release_tags(
    repo: str, prefix: str = "", limit: int = 60, max_pages: int = 8
) -> list[str]:
    """Tags des releases du dépôt (les plus récentes d'abord).

    Les pages HTML de GitHub sont parcourues (10 releases par page) afin de
    proposer aussi les anciens kernels, pas seulement les 10 derniers.
    """
    tags: list[str] = []

    def _add(found: list[str]) -> int:
        added = 0
        for tag in found:
            if prefix and not tag.startswith(prefix):
                continue
            if tag in tags:
                continue
            tags.append(tag)
            added += 1
            if len(tags) >= limit:
                break
        return added

    for page in range(1, max_pages + 1):
        url = f"https://github.com/{repo}/releases" + (f"?page={page}" if page > 1 else "")
        req = urllib.request.Request(url, headers={"User-Agent": "ps5-fedora-manager"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, OSError):
            break
        found = list(dict.fromkeys(re.findall(r"/releases/tag/([^\"<]+)", html)))
        if not found:
            break
        if _add(found) == 0 and tags:
            break
        if len(tags) >= limit:
            break
    return tags


def gh_tag_rpm(repo: str, tag: str) -> tuple[str, str]:
    """Cherche l'asset RPM d'une release donnée.

    Retourne (état, url) : "ok" (url de l'asset), "norpm" (release sans RPM,
    par exemple paquet Arch uniquement) ou "error" (GitHub injoignable).
    """
    url = f"https://github.com/{repo}/releases/expanded_assets/{tag}"
    req = urllib.request.Request(url, headers={"User-Agent": "ps5-fedora-manager"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return "error", ""
    found = re.findall(rf"/{re.escape(repo)}/releases/download/[^\"]+", html)
    for match in dict.fromkeys(found):
        if match.endswith(".rpm"):
            return "ok", f"https://github.com{match}"
    return "norpm", ""


# ------------------------------------------------------------------------------
# Modèle Logithèque
# ------------------------------------------------------------------------------
@dataclass
class SoftwareItem:
    name: str
    kind: str  # rpm | flatpak | decky | ghrpm | dual
    category: str = "system"  # gaming | browser | system
    rpm_name: str = ""
    gh_repo: str = ""
    gh_asset_pattern: str = r"x86_64\.rpm$"
    extra_rpms: tuple[str, ...] = ()
    copr_repo: str = ""
    post_install_user_cmd: tuple[str, ...] = ()
    fp_id: str = ""
    description_fr: str = ""
    description_en: str = ""
    icon: str = "application-x-executable-symbolic"


SOFTWARE_CATEGORIES: list[tuple[str, str, str]] = [
    ("gaming", "lib_cat_gaming", "lib_cat_gaming_sub"),
    ("browser", "lib_cat_browser", "lib_cat_browser_sub"),
    ("system", "lib_cat_system", "lib_cat_system_sub"),
]


SOFTWARE_CATALOG: list[SoftwareItem] = [
    # --- Gaming ---
    SoftwareItem(
        name="Steam",
        kind="rpm",
        category="gaming",
        rpm_name="steam",
        description_fr="Client de jeu Valve (active RPM Fusion automatiquement)",
        description_en="Valve gaming client (auto-enables RPM Fusion)",
        icon="applications-games-symbolic",
    ),
    SoftwareItem(
        name="Heroic Games Launcher",
        kind="flatpak",
        category="gaming",
        fp_id="com.heroicgameslauncher.hgl",
        description_fr="Lanceur Epic Games, GOG et Amazon Games",
        description_en="Epic Games, GOG and Amazon Games launcher",
        icon="applications-games-symbolic",
    ),
    SoftwareItem(
        name="ProtonUp-Qt",
        kind="flatpak",
        category="gaming",
        fp_id="net.davidotek.pupgui2",
        description_fr="Gérer Proton-GE et Wine-GE pour Steam & Heroic",
        description_en="Manage Proton-GE and Wine-GE for Steam & Heroic",
        icon="system-software-install-symbolic",
    ),
    SoftwareItem(
        name="Decky Loader",
        kind="decky",
        category="gaming",
        description_fr="Gestionnaire de plugins pour Steam Big Picture / Game Mode",
        description_en="Plugin loader for Steam Big Picture / Game Mode",
        icon="application-x-addon-symbolic",
    ),
    SoftwareItem(
        name="Universe",
        kind="rpm",
        category="gaming",
        rpm_name="universe",
        extra_rpms=("universe-desktop",),
        copr_repo="ilyasturki/universe",
        post_install_user_cmd=("universe", "setup"),
        description_fr="Lanceur manette (GOG, Steam, Epic, émulateurs) · COPR + GTK",
        description_en="Controller game launcher (GOG, Steam, Epic, emulators) · COPR + GTK",
        icon="applications-games-symbolic",
    ),
    # --- Navigateurs ---
    SoftwareItem(
        name="Opera",
        kind="dual",
        category="browser",
        rpm_name="opera-stable",
        fp_id="com.opera.Opera",
        description_fr="Navigateur web (RPM officiel ou Flatpak)",
        description_en="Web browser (official RPM or Flatpak)",
        icon="web-browser-symbolic",
    ),
    SoftwareItem(
        name="Brave",
        kind="dual",
        category="browser",
        rpm_name="brave-browser",
        fp_id="com.brave.Browser",
        description_fr="Navigateur orienté confidentialité (RPM ou Flatpak)",
        description_en="Privacy-focused browser (RPM or Flatpak)",
        icon="web-browser-symbolic",
    ),
    # --- Système & Utilitaires ---
    SoftwareItem(
        name="Etcher",
        kind="ghrpm",
        category="system",
        rpm_name="balena-etcher",
        gh_repo="balena-io/etcher",
        gh_asset_pattern=r"x86_64\.rpm$",
        description_fr="Écrire des images ISO/IMG sur clé USB (RPM GitHub)",
        description_en="Flash OS images to USB drives (GitHub RPM)",
        icon="drive-removable-media-symbolic",
    ),
    SoftwareItem(
        name="Mister Download Manager",
        kind="ghrpm",
        category="system",
        rpm_name="misterdownloadmanager",
        gh_repo="anefzaoui/misterdownloadmanager",
        gh_asset_pattern=r"linux-x86_64\.rpm$",
        description_fr="Gestionnaire de téléchargements (RPM GitHub)",
        description_en="Download manager (GitHub RPM)",
        icon="folder-download-symbolic",
    ),
    SoftwareItem(
        name="Bazaar",
        kind="flatpak",
        category="system",
        fp_id="io.github.kolunmi.Bazaar",
        description_fr="Boutique Flatpak moderne pour GNOME",
        description_en="Modern Flatpak store for GNOME",
        icon="system-software-install-symbolic",
    ),
    SoftwareItem(
        name="GNOME Extension Manager",
        kind="flatpak",
        category="system",
        fp_id="com.mattjakeman.ExtensionManager",
        description_fr="Parcourir et gérer les extensions GNOME Shell",
        description_en="Browse and manage GNOME Shell extensions",
        icon="application-x-addon-symbolic",
    ),
]


def detect_software_status(item: SoftwareItem) -> tuple[str, str]:
    """Retourne (status_code, label) : rpm | flatpak | installed | none."""
    if item.kind == "decky":
        if os.path.isdir(os.path.join(REAL_HOME, "homebrew")):
            return "installed", T("installed")
        return "none", T("not_installed")
    if item.rpm_name:
        res = subprocess.run(
            ["rpm", "-q", item.rpm_name], capture_output=True, text=True
        )
        if res.returncode == 0:
            return "rpm", T("installed_rpm")
    if item.fp_id and shutil.which("flatpak"):
        for scope in ("--system", "--user"):
            res = subprocess.run(
                ["flatpak", "info", scope, item.fp_id],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                return "flatpak", T("installed_flatpak")
    return "none", T("not_installed")


# ------------------------------------------------------------------------------
# Fenêtre de journal / texte (GTK4 + Libadwaita)
# ------------------------------------------------------------------------------
class TextLogWindow(Adw.Window):
    def __init__(self, parent: Gtk.Window, title: str) -> None:
        super().__init__(
            transient_for=parent,
            title=title,
            default_width=920,
            default_height=580,
        )
        self._path: Optional[str] = None
        self._offset: int = 0
        self._timer_id: Optional[int] = None

        self.view = Gtk.TextView(
            editable=False, monospace=True, cursor_visible=False
        )
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_left_margin(16)
        self.view.set_right_margin(16)
        self.view.set_top_margin(12)
        self.view.set_bottom_margin(12)
        self.buf = self.view.get_buffer()

        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title=title)
        header.set_title_widget(self.title_widget)

        clear_btn = Gtk.Button(icon_name="edit-clear-all-symbolic")
        clear_btn.set_tooltip_text(T("clear"))
        clear_btn.connect("clicked", lambda *_: self.buf.set_text(""))
        header.pack_end(clear_btn)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        scroll = Gtk.ScrolledWindow(child=self.view, hexpand=True, vexpand=True)
        toolbar.set_content(scroll)
        self.set_content(toolbar)
        self.connect("close-request", self._on_close)

    def _on_close(self, *_args) -> bool:
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self.hide()
        return True

    def append(self, text: str) -> None:
        clean = strip_ansi(text)
        if not clean:
            return
        end_iter = self.buf.get_end_iter()
        existing = self.buf.get_text(
            self.buf.get_start_iter(), end_iter, False
        )
        if existing and not existing.endswith("\n"):
            self.buf.insert(end_iter, "\n")
            end_iter = self.buf.get_end_iter()
        self.buf.insert(end_iter, clean if clean.endswith("\n") else clean + "\n")
        end_iter = self.buf.get_end_iter()
        self.buf.place_cursor(end_iter)
        self.view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)

    def load_text(self, text: str) -> None:
        self.buf.set_text(strip_ansi(text))
        end_iter = self.buf.get_end_iter()
        self.view.scroll_to_iter(end_iter, 0.0, False, 0.0, 0.0)

    def follow(self, path: str) -> None:
        self._path = path
        self._offset = 0
        self.buf.set_text("")
        self._tick()
        if self._timer_id is None:
            self._timer_id = GLib.timeout_add(350, self._tick)

    def _tick(self) -> bool:
        if not self._path:
            return False
        try:
            with open(self._path, encoding="utf-8", errors="replace") as fh:
                fh.seek(self._offset)
                chunk = fh.read()
                self._offset = fh.tell()
        except OSError:
            return True
        if chunk:
            self.append(chunk)
        return True


# ------------------------------------------------------------------------------
# Setup recommandé (bienvenue au premier lancement + menu principal)
# ------------------------------------------------------------------------------
SETUP_WELCOME_FILE = "/etc/ps5-manager/setup-welcome-done"


def welcome_seen() -> bool:
    """Vrai si la boîte de bienvenue du premier lancement a déjà été affichée."""
    return os.path.exists(SETUP_WELCOME_FILE)


def mark_welcome_seen() -> None:
    try:
        os.makedirs(os.path.dirname(SETUP_WELCOME_FILE), exist_ok=True)
        with open(SETUP_WELCOME_FILE, "w", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.now():%F %T} {REAL_USER}\n")
    except OSError:
        pass


def _setup_cmd(
    win: "Ps5ManagerWindow",
    cmd: list[str] | str,
    as_user: bool = False,
) -> Callable[[Callable[[str], None]], bool]:
    """Étape de setup exécutant une commande unique."""

    def _run(emit: Callable[[str], None]) -> bool:
        return win.run_cmd_pty(cmd, emit, as_user=as_user) == 0

    return _run


def _setup_user_cmds(
    win: "Ps5ManagerWindow", cmds: list[list[str]]
) -> Callable[[Callable[[str], None]], bool]:
    """Étape de setup exécutant plusieurs commandes utilisateur (bureau courant)."""

    def _run(emit: Callable[[str], None]) -> bool:
        ok = True
        for cmd in cmds:
            if win.run_cmd_pty(cmd, emit, as_user=True) != 0:
                ok = False
        if DESKTOP_ID == "kde":
            _kde_power_reload()
        return ok

    return _run


def _flatpak_app_installed(app_id: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    for scope in ("--system", "--user"):
        if subprocess.run(
            ["flatpak", "info", scope, app_id], capture_output=True
        ).returncode == 0:
            return True
    return False


def _setup_flatpak_app(
    win: "Ps5ManagerWindow", app_id: str
) -> Callable[[Callable[[str], None]], bool]:
    """Étape de setup installant une application Flatpak depuis Flathub."""

    def _run(emit: Callable[[str], None]) -> bool:
        if _flatpak_app_installed(app_id):
            emit(f"{app_id} : {T('installed')}")
            return True
        if not shutil.which("flatpak") and win.run_cmd_pty(
            ["dnf", "install", "-y", "flatpak"], emit
        ) != 0:
            return False
        _ensure_flathub()
        return (
            win.run_cmd_pty(
                [
                    "flatpak",
                    "install",
                    "--system",
                    "--noninteractive",
                    "-y",
                    "flathub",
                    app_id,
                ],
                emit,
            )
            == 0
        )

    return _run


def _setup_fan_tools(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        cmd = (
            "tmp=$(mktemp -d) && git clone --depth=1 "
            f"'{TOOLS_REPO}' \"$tmp/tools\" && cd \"$tmp/tools\" "
            "&& ./install.sh && rm -rf \"$tmp\""
        )
        return win.run_cmd_pty(["bash", "-c", cmd], emit) == 0

    return _run


def _setup_hwcon(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        if win.run_cmd_pty(["dnf", "install", "-y", "python3-PyQt6"], emit) != 0:
            return False
        return (
            win.run_cmd_pty(
                f"curl -fsSL '{HWCON_INSTALL}' | bash -s -- --passwordless",
                emit,
                as_user=True,
            )
            == 0
        )

    return _run


def _setup_hwcon_plugin(
    win: "Ps5ManagerWindow",
) -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        return win.run_cmd_pty(f"curl -fsSL '{HWCON_PLUGIN_INSTALL}' | bash", emit, as_user=True) == 0

    return _run


def _setup_rpmfusion(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        return _ensure_rpmfusion(win, emit)

    return _run


def _setup_flathub(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        if not shutil.which("flatpak") and win.run_cmd_pty(
            ["dnf", "install", "-y", "flatpak"], emit
        ) != 0:
            return False
        return _ensure_flathub()

    return _run


def _setup_repos_refresh(
    win: "Ps5ManagerWindow",
) -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        if win.run_cmd_pty(
            ["bash", "-c", "dnf clean all && dnf makecache --refresh"], emit
        ) != 0:
            return False
        if shutil.which("flatpak"):
            win.run_cmd_pty(["flatpak", "update", "--appstream", "-y"], emit)
        return True

    return _run


def _setup_venv(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        return (
            win.run_cmd_pty(
                "python3 -m venv my_project && . my_project/bin/activate "
                "&& python3 --version && pip3 --version",
                emit,
                as_user=True,
            )
            == 0
        )

    return _run


def _setup_steam(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        _ensure_rpmfusion(win, emit)
        return win.run_cmd_pty(["dnf", "install", "-y", "steam"], emit) == 0

    return _run


def _setup_decky(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        return win.run_cmd_pty(f"curl -fsSL '{DECKY_INSTALL}' | bash", emit, as_user=True) == 0

    return _run


def _setup_universe(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        if not _ensure_copr_repo(win, "ilyasturki/universe", emit):
            return False
        if win.run_cmd_pty(
            ["dnf", "install", "-y", "universe", "universe-desktop"], emit
        ) != 0:
            return False
        win.run_cmd_pty(["universe", "setup"], emit, as_user=True)
        return True

    return _run


def _setup_gamescope(win: "Ps5ManagerWindow") -> Callable[[Callable[[str], None]], bool]:
    def _run(emit: Callable[[str], None]) -> bool:
        fd, path = tempfile.mkstemp(
            prefix="ps5-manager-setup-gamescope-", suffix=".sh", dir="/tmp"
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_gaming_script("install"))
        os.chmod(path, 0o700)
        try:
            return win.run_cmd_pty(["bash", path], emit) == 0
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    return _run


@dataclass
class SetupStep:
    """Une étape du setup recommandé et ses éléments à installer."""

    title_key: str
    items: list[tuple[str, Callable[[Callable[[str], None]], bool]]]


def _build_setup_plan(win: "Ps5ManagerWindow") -> list[SetupStep]:
    """Plan du setup recommandé par le développeur (9 étapes, 29 éléments)."""
    return [
        SetupStep(
            "setup_step1",
            [
                (
                    "setup_pwr_sys",
                    _setup_cmd(
                        win,
                        [
                            "systemctl",
                            "mask",
                            "sleep.target",
                            "suspend.target",
                            "hibernate.target",
                            "hybrid-sleep.target",
                            "suspend-then-hibernate.target",
                        ],
                    ),
                ),
                ("setup_pwr_scr", _setup_user_cmds(win, screen_sleep_commands(False))),
                ("setup_pwr_full", _setup_user_cmds(win, full_sleep_commands(False))),
            ],
        ),
        SetupStep(
            "setup_step2",
            [
                ("setup_fan_tools", _setup_fan_tools(win)),
                (
                    "setup_fan_svc",
                    _setup_cmd(win, ["systemctl", "enable", "--now", "ps5fan.service"]),
                ),
                (
                    "setup_fan_boot",
                    _setup_cmd(
                        win, ["systemctl", "enable", "--now", "ps5boost.service"]
                    ),
                ),
            ],
        ),
        SetupStep("setup_step3", [("setup_hw", _setup_hwcon(win))]),
        SetupStep(
            "setup_step4",
            [
                (
                    "setup_mesa",
                    _setup_cmd(win, ["dnf", "install", "-y", "vulkan-tools", "mesa-demos"]),
                )
            ],
        ),
        SetupStep(
            "setup_step5",
            [
                ("setup_repo_rpmfusion", _setup_rpmfusion(win)),
                ("setup_repo_flathub", _setup_flathub(win)),
                ("setup_repo_refresh", _setup_repos_refresh(win)),
            ],
        ),
        SetupStep(
            "setup_step6",
            [
                (
                    "setup_dep_fuse",
                    _setup_cmd(win, ["dnf", "install", "-y", "fuse", "fuse-libs"]),
                ),
                (
                    "setup_dep_steam32",
                    _setup_cmd(
                        win,
                        [
                            "dnf",
                            "install",
                            "-y",
                            "mesa-vulkan-drivers.i686",
                            "mesa-dri-drivers.i686",
                            "libva.i686",
                        ],
                    ),
                ),
                (
                    "setup_dep_python",
                    _setup_cmd(win, ["dnf", "install", "-y", "python3", "python3-pip"]),
                ),
                ("setup_dep_venv", _setup_venv(win)),
                (
                    "setup_dep_tk",
                    _setup_cmd(win, ["dnf", "install", "-y", "python3-tkinter"]),
                ),
                (
                    "setup_dep_node",
                    _setup_cmd(win, ["dnf", "install", "-y", "nodejs", "npm"]),
                ),
                (
                    "setup_dep_fedora",
                    _setup_cmd(win, ["dnf", "upgrade", "-y", "--refresh"]),
                ),
            ],
        ),
        SetupStep(
            "setup_step7",
            [
                (
                    "setup_app_bazaar",
                    _setup_flatpak_app(win, "io.github.kolunmi.Bazaar"),
                ),
                *(
                    [
                        (
                            "setup_app_extmgr",
                            _setup_flatpak_app(win, "com.mattjakeman.ExtensionManager"),
                        )
                    ]
                    if DESKTOP_ID == "gnome"
                    else []
                ),
                ("setup_app_steam", _setup_steam(win)),
                (
                    "setup_app_heroic",
                    _setup_flatpak_app(win, "com.heroicgameslauncher.hgl"),
                ),
                (
                    "setup_app_protonup",
                    _setup_flatpak_app(win, "net.davidotek.pupgui2"),
                ),
                ("setup_app_decky", _setup_decky(win)),
                ("setup_app_universe", _setup_universe(win)),
                (
                    "setup_app_appimagepool",
                    _setup_flatpak_app(win, "io.github.prateekmedia.appimagepool"),
                ),
                (
                    "setup_app_opera",
                    _setup_flatpak_app(win, "com.opera.Opera"),
                ),
            ],
        ),
        SetupStep("setup_step8", [("setup_hw_plugin", _setup_hwcon_plugin(win))]),
        SetupStep("setup_step9", [("setup_gaming", _setup_gamescope(win))]),
    ]


class SetupWindow(Adw.Window):
    """Suivi du setup recommandé : liste validée en direct + journal visible."""

    def __init__(self, win: "Ps5ManagerWindow", plan: list[SetupStep]) -> None:
        super().__init__(
            transient_for=win,
            title=T("setup_title"),
            default_width=1320,
            default_height=800,
        )
        self.win = win
        self.plan = plan
        self._labels: dict[tuple[int, int], Gtk.Label] = {}
        self._buffer: list[str] = []
        self._buffer_lock = threading.Lock()
        self._flush_id: Optional[int] = None
        self._running = True
        self._done_count = 0
        self._fail_count = 0
        self._total = sum(len(step.items) for step in plan)

        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(
            title=T("setup_title"), subtitle=T("setup_running")
        )
        header.set_title_widget(self.title_widget)

        page = Adw.PreferencesPage()
        for s_idx, step in enumerate(plan):
            grp = pref_group(title=T(step.title_key))
            for i_idx, (item_key, _runner) in enumerate(step.items):
                row = plain_row(Adw.ActionRow, title=T(item_key))
                lbl = Gtk.Label(label="○")
                lbl.add_css_class("dim-label")
                lbl.set_valign(Gtk.Align.CENTER)
                row.add_suffix(lbl)
                self._labels[(s_idx, i_idx)] = lbl
                grp.add(row)
            page.add(grp)

        self.log_view = Gtk.TextView(
            editable=False, monospace=True, cursor_visible=False
        )
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_left_margin(12)
        self.log_view.set_right_margin(12)
        self.log_view.set_top_margin(8)
        self.log_view.set_bottom_margin(8)
        self.log_buf = self.log_view.get_buffer()

        log_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        log_box.set_margin_top(8)
        log_box.set_margin_bottom(8)
        log_box.set_margin_start(8)
        log_box.set_margin_end(8)
        log_title = Gtk.Label(label=T("setup_log"), xalign=0)
        log_title.add_css_class("heading")
        log_box.append(log_title)
        log_box.append(
            Gtk.ScrolledWindow(child=self.log_view, hexpand=True, vexpand=True)
        )

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_start_child(page)
        split.set_end_child(log_box)
        split.set_resize_start_child(False)
        split.set_shrink_start_child(False)
        split.set_position(540)

        self.progress = Gtk.ProgressBar(show_text=True)
        self.progress.set_hexpand(True)
        self.progress.set_valign(Gtk.Align.CENTER)
        self.progress.set_text(f"0 / {self._total}")
        self.close_btn = Gtk.Button(label=T("setup_close"))
        self.close_btn.set_sensitive(False)
        self.close_btn.connect("clicked", lambda *_: self.close())

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom.set_margin_top(10)
        bottom.set_margin_bottom(10)
        bottom.set_margin_start(12)
        bottom.set_margin_end(12)
        bottom.append(self.progress)
        bottom.append(self.close_btn)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(split)
        toolbar.add_bottom_bar(bottom)
        self.set_content(toolbar)
        self.connect("close-request", self._on_close_request)

    # ---- Suivi de l'interface (thread principal) ----
    def _set_status(self, key: tuple[int, int], text: str, css: str) -> bool:
        lbl = self._labels.get(key)
        if lbl is not None:
            lbl.set_text(text)
            for name in ("dim-label", "accent", "success", "error"):
                lbl.remove_css_class(name)
            if css:
                lbl.add_css_class(css)
        return False

    def _log_line(self, text: str) -> bool:
        with self._buffer_lock:
            self._buffer.append(text)
        return False

    def _append(self, line: str) -> None:
        """Reçoit les lignes du PTY (thread d'installation)."""
        with self._buffer_lock:
            self._buffer.append(line + "\n")

    def _flush(self) -> bool:
        with self._buffer_lock:
            chunk = "".join(self._buffer)
            self._buffer.clear()
        if chunk:
            end = self.log_buf.get_end_iter()
            self.log_buf.insert(end, chunk)
            end = self.log_buf.get_end_iter()
            self.log_buf.place_cursor(end)
            self.log_view.scroll_to_iter(end, 0.0, False, 0.0, 0.0)
        return self._running

    def _tick_progress(self, ok: bool) -> bool:
        if ok:
            self._done_count += 1
        else:
            self._fail_count += 1
        done = self._done_count + self._fail_count
        self.progress.set_fraction(done / max(self._total, 1))
        self.progress.set_text(f"{done} / {self._total}")
        return False

    def _finish(self) -> bool:
        self._running = False
        if self._flush_id is not None:
            GLib.source_remove(self._flush_id)
            self._flush_id = None
        self._flush()
        self.title_widget.set_subtitle(T("setup_finished"))
        self.progress.set_fraction(1.0)
        self.progress.set_text(T("setup_summary") % (self._done_count, self._fail_count))
        self.close_btn.set_sensitive(True)
        self.win.busy = False
        self.win.busy_spinner.stop()
        self.close()
        self.win.prompt_reboot(self._done_count, self._fail_count)
        return False

    # ---- Exécution ----
    def start(self) -> None:
        self._flush_id = GLib.timeout_add(150, self._flush)
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        GLib.idle_add(
            self._log_line,
            T("setup_env_line")
            % (DESKTOP_LABEL, DISPLAY_MANAGER_LABEL, DESKTOP_SESSION)
            + "\n",
        )
        for s_idx, step in enumerate(self.plan):
            GLib.idle_add(self._log_line, f"\n=== {T(step.title_key)} ===\n")
            for i_idx, (item_key, runner) in enumerate(step.items):
                GLib.idle_add(self._set_status, (s_idx, i_idx), "●", "accent")
                GLib.idle_add(self._log_line, f"→ {T(item_key)}\n")
                ok = False
                try:
                    ok = bool(runner(self._append))
                except Exception as exc:  # noqa: BLE001 - le setup ne doit pas s'arrêter
                    self._append(f"  ! {exc}")
                    ok = False
                GLib.idle_add(
                    self._set_status,
                    (s_idx, i_idx),
                    "✔" if ok else "✖",
                    "success" if ok else "error",
                )
                GLib.idle_add(self._tick_progress, ok)
        GLib.idle_add(self._finish)

    def _on_close_request(self, *_args) -> bool:
        if self._running:
            return True
        self.win.setup_window = None
        return False

# ------------------------------------------------------------------------------
# Définition des 15 sections de la barre latérale
# ------------------------------------------------------------------------------
SECTIONS = [
    # Groupe 1
    ("logs", "utilities-terminal-symbolic", "sec_logs", 1),
    ("library", "system-software-install-symbolic", "sec_library", 1),
    ("aidev", "applications-development-symbolic", "sec_aidev", 1),
    ("dev", "applications-engineering-symbolic", "sec_dev", 1),
    ("websrv", "network-server-symbolic", "sec_web", 1),
    ("easy", "preferences-other-symbolic", "sec_easy", 1),
    ("deps", "application-x-addon-symbolic", "sec_deps", 1),
    ("gaming", "input-gaming-symbolic", "sec_gaming", 1),
    ("features", "application-x-executable-symbolic", "sec_features", 1),
    # Groupe 2
    ("update", "software-update-available-symbolic", "sec_update", 2),
    ("lang", "preferences-desktop-locale-symbolic", "sec_lang", 2),
    ("repos", "network-server-symbolic", "sec_repos", 2),
    ("users", "system-users-symbolic", "sec_users", 2),
    ("fedora", "system-software-update-symbolic", "sec_fedora", 2),
    ("maint", "applications-engineering-symbolic", "sec_maint", 2),
    # Groupe 3
    ("power", "preferences-system-power-symbolic", "sec_power", 3),
    ("fan", "weather-windy-symbolic", "sec_fan", 3),
    ("hw", "applications-system-symbolic", "sec_hw", 3),
    ("mesa", "video-display-symbolic", "sec_mesa", 3),
    ("kernel", "drive-harddisk-symbolic", "sec_kernel", 3),
    ("fix", "view-refresh-symbolic", "sec_fix", 3),
    ("ui_lang", "preferences-desktop-keyboard-symbolic", "sec_ui_lang", 3),
]


# ------------------------------------------------------------------------------
# Fenêtre principale (GNOME Settings / Libadwaita NavigationSplitView)
# ------------------------------------------------------------------------------
_L_TABLE = {
    "Mise à jour %s installée — redémarrage…": (
        "Actualización %s instalada: reiniciando…",
        "Aggiornamento %s installato: riavvio…",
        "Aktualisierung %s installiert – Neustart…",
        "Atualização %s instalada: reiniciando…",
    ),
    "Mise à jour %s disponible : installe-la depuis « Mise à jour du manager ».": (
        "Actualización %s disponible: instálala desde «Actualización del gestor».",
        "Aggiornamento %s disponibile: installalo da «Aggiornamento del gestore».",
        "Aktualisierung %s verfügbar: installiere sie über „Manager-Aktualisierung“.",
        "Atualização %s disponível: instale-a em «Atualização do gerenciador».",
    ),
    "Mise à jour installée — active au prochain démarrage.": (
        "Actualización instalada: activa en el próximo inicio.",
        "Aggiornamento installato: attivo al prossimo avvio.",
        "Aktualisierung installiert – beim nächsten Start aktiv.",
        "Atualização instalada: ativa no próximo início.",
    ),
    "Droits (root:root, 0755/0644, Polkit GUI, SELinux) appliqués.": (
        "Permisos (root:root, 0755/0644, Polkit GUI, SELinux) aplicados.",
        "Permessi (root:root, 0755/0644, Polkit GUI, SELinux) applicati.",
        "Rechte (root:root, 0755/0644, Polkit GUI, SELinux) angewendet.",
        "Permissões (root:root, 0755/0644, Polkit GUI, SELinux) aplicadas.",
    ),
    "Redémarrage automatique de PS5 Fedora Manager…": (
        "Reinicio automático de PS5 Fedora Manager…",
        "Riavvio automatico di PS5 Fedora Manager…",
        "Automatischer Neustart von PS5 Fedora Manager…",
        "Reinício automático do PS5 Fedora Manager…",
    ),
    "Ollama non détecté — installation avec pciutils…": (
        "Ollama no detectado — instalando con pciutils…",
        "Ollama non rilevato — installazione con pciutils…",
        "Ollama nicht gefunden — Installation mit pciutils…",
        "Ollama não detectado — instalando com pciutils…",
    ),
    "VSCodium (éditeur de code libre)": (
        "VSCodium (editor de código libre)",
        "VSCodium (editor di codice libero)",
        "VSCodium (freier Code-Editor)",
        "VSCodium (editor de código livre)",
    ),
    "Ollama non détecté sur ce système.": (
        "Ollama no detectado en este sistema.",
        "Ollama non rilevato su questo sistema.",
        "Ollama wurde auf diesem System nicht gefunden.",
        "Ollama não detectado neste sistema.",
    ),
    "Conteneur Podman open-webui non détecté.": (
        "Contenedor Podman open-webui no detectado.",
        "Contenitore Podman open-webui non rilevato.",
        "Podman-Container open-webui nicht gefunden.",
        "Contêiner Podman open-webui não detectado.",
    ),
    "Podman non installé.": (
        "Podman no instalado.",
        "Podman non installato.",
        "Podman ist nicht installiert.",
        "Podman não instalado.",
    ),
    "Démarrez d'abord le conteneur Open WebUI.": (
        "Inicia primero el contenedor Open WebUI.",
        "Avvia prima il contenitore Open WebUI.",
        "Starte zuerst den Open-WebUI-Container.",
        "Inicie primeiro o contêiner Open WebUI.",
    ),
    "Vérifie l'état exact de open-webui": (
        "Comprueba el estado exacto de open-webui",
        "Controlla lo stato esatto di open-webui",
        "Prüft den genauen Status von open-webui",
        "Verifica o estado exato do open-webui",
    ),
    "Affiche les 30 dernières lignes du conteneur open-webui": (
        "Muestra las 30 últimas líneas del contenedor open-webui",
        "Mostra le ultime 30 righe del contenitore open-webui",
        "Zeigt die letzten 30 Zeilen des open-webui-Containers",
        "Mostra as 30 últimas linhas do contêiner open-webui",
    ),
    "Affiche les modèles actuellement chargés en mémoire": (
        "Muestra los modelos cargados actualmente en memoria",
        "Mostra i modelli attualmente caricati in memoria",
        "Zeigt die derzeit im Speicher geladenen Modelle",
        "Mostra os modelos atualmente carregados na memória",
    ),
    "Diagnostic matériel IA (PS5)": (
        "Diagnóstico de hardware de IA (PS5)",
        "Diagnostica hardware IA (PS5)",
        "KI-Hardware-Diagnose (PS5)",
        "Diagnóstico de hardware de IA (PS5)",
    ),
    "Vérifie la mémoire libre avant d'exécuter un modèle 7B / 9B / 12B": (
        "Comprueba la memoria libre antes de ejecutar un modelo 7B / 9B / 12B",
        "Controlla la memoria libera prima di eseguire un modello 7B / 9B / 12B",
        "Prüft den freien Speicher vor dem Start eines 7B-/9B-/12B-Modells",
        "Verifica a memória livre antes de executar um modelo 7B / 9B / 12B",
    ),
    "podman image prune -f (libère l'espace après mise à jour Open WebUI)": (
        "podman image prune -f (libera espacio tras actualizar Open WebUI)",
        "podman image prune -f (libera spazio dopo l'aggiornamento di Open WebUI)",
        "podman image prune -f (gibt Speicher nach dem Open-WebUI-Update frei)",
        "podman image prune -f (libera espaço após atualizar o Open WebUI)",
    ),
    "Avertissement : impossible de télécharger open-webui.png (icône générique utilisée).": (
        "Aviso: no se pudo descargar open-webui.png (se usa el icono genérico).",
        "Avviso: impossibile scaricare open-webui.png (usata l'icona generica).",
        "Warnung: open-webui.png konnte nicht geladen werden (allgemeines Symbol wird verwendet).",
        "Aviso: não foi possível baixar open-webui.png (ícone genérico usado).",
    ),
    "Désinstaller Ollama": (
        "Desinstalar Ollama",
        "Disinstalla Ollama",
        "Ollama deinstallieren",
        "Desinstalar o Ollama",
    ),
    "Met à jour Ollama vers la dernière version officielle": (
        "Actualiza Ollama a la última versión oficial",
        "Aggiorna Ollama all'ultima versione ufficiale",
        "Aktualisiert Ollama auf die neueste offizielle Version",
        "Atualiza o Ollama para a última versão oficial",
    ),
    "Supprime le service et les binaires, conserve /usr/share/ollama": (
        "Elimina el servicio y los binarios, conserva /usr/share/ollama",
        "Rimuove il servizio e i binari, conserva /usr/share/ollama",
        "Entfernt Dienst und Programme, /usr/share/ollama bleibt erhalten",
        "Remove o serviço e os binários, mantém /usr/share/ollama",
    ),
    "Supprimer Ollama tout en conservant les modèles dans /usr/share/ollama ?": (
        "¿Eliminar Ollama conservando los modelos en /usr/share/ollama?",
        "Rimuovere Ollama conservando i modelli in /usr/share/ollama?",
        "Ollama entfernen und die Modelle in /usr/share/ollama behalten?",
        "Remover o Ollama mantendo os modelos em /usr/share/ollama?",
    ),
    "Désinstaller complètement (+ supprimer tous les modèles)": (
        "Desinstalar por completo (+ eliminar todos los modelos)",
        "Disinstalla completamente (+ elimina tutti i modelli)",
        "Vollständig deinstallieren (+ alle Modelle löschen)",
        "Desinstalar completamente (+ remover todos os modelos)",
    ),
    "Supprimer définitivement Ollama ET tous les modèles téléchargés (/usr/share/ollama) ?": (
        "¿Eliminar definitivamente Ollama Y todos los modelos descargados (/usr/share/ollama)?",
        "Rimuovere definitivamente Ollama E tutti i modelli scaricati (/usr/share/ollama)?",
        "Ollama UND alle heruntergeladenen Modelle (/usr/share/ollama) endgültig löschen?",
        "Remover definitivamente o Ollama E todos os modelos baixados (/usr/share/ollama)?",
    ),
    "Désinstaller Open WebUI": (
        "Desinstalar Open WebUI",
        "Disinstalla Open WebUI",
        "Open WebUI deinstallieren",
        "Desinstalar o Open WebUI",
    ),
    "Podman + conteneur open-webui + icône locale dans le menu GNOME": (
        "Podman + contenedor open-webui + icono local en el menú GNOME",
        "Podman + contenitore open-webui + icona locale nel menu GNOME",
        "Podman + open-webui-Container + lokales Symbol im GNOME-Menü",
        "Podman + contêiner open-webui + ícone local no menu GNOME",
    ),
    "podman pull + recréation (données conservées) + icône GNOME": (
        "podman pull + recreación (datos conservados) + icono GNOME",
        "podman pull + ricreazione (dati conservati) + icona GNOME",
        "podman pull + Neuanlage (Daten bleiben erhalten) + GNOME-Symbol",
        "podman pull + recriação (dados mantidos) + ícone GNOME",
    ),
    "Ouvrir dans le navigateur (http://127.0.0.1:8080)": (
        "Abrir en el navegador (http://127.0.0.1:8080)",
        "Apri nel browser (http://127.0.0.1:8080)",
        "Im Browser öffnen (http://127.0.0.1:8080)",
        "Abrir no navegador (http://127.0.0.1:8080)",
    ),
    "Démarre open-webui si arrêté puis ouvre la page web": (
        "Inicia open-webui si está detenido y abre la página web",
        "Avvia open-webui se fermo, poi apre la pagina web",
        "Startet open-webui bei Bedarf und öffnet die Webseite",
        "Inicia o open-webui se estiver parado e abre a página web",
    ),
    "Installer / mettre à jour l'icône GNOME (menu Applications)": (
        "Instalar / actualizar el icono GNOME (menú Aplicaciones)",
        "Installa / aggiorna l'icona GNOME (menu Applicazioni)",
        "GNOME-Symbol installieren / aktualisieren (Anwendungsmenü)",
        "Instalar / atualizar o ícone GNOME (menu Aplicativos)",
    ),
    "Télécharge open-webui.png dans /usr/share/pixmaps/ et crée open-webui.desktop": (
        "Descarga open-webui.png en /usr/share/pixmaps/ y crea open-webui.desktop",
        "Scarica open-webui.png in /usr/share/pixmaps/ e crea open-webui.desktop",
        "Lädt open-webui.png nach /usr/share/pixmaps/ und erstellt open-webui.desktop",
        "Baixa open-webui.png em /usr/share/pixmaps/ e cria open-webui.desktop",
    ),
    "Supprime conteneur + lanceur/icône GNOME (conserve les conversations)": (
        "Elimina el contenedor + lanzador/icono GNOME (conserva las conversaciones)",
        "Rimuove contenitore + lanciatore/icona GNOME (conserva le conversazioni)",
        "Entfernt Container + GNOME-Starter/Symbol (Unterhaltungen bleiben erhalten)",
        "Remove o contêiner + atalho/ícone GNOME (mantém as conversas)",
    ),
    "Supprimer le conteneur open-webui et son icône du menu GNOME en conservant vos données ?": (
        "¿Eliminar el contenedor open-webui y su icono del menú GNOME conservando tus datos?",
        "Rimuovere il contenitore open-webui e la sua icona dal menu GNOME conservando i dati?",
        "open-webui-Container und sein Menüsymbol entfernen und die Daten behalten?",
        "Remover o contêiner open-webui e seu ícone do menu GNOME mantendo os seus dados?",
    ),
    "Désinstaller complètement (conteneur + volume + image + icône)": (
        "Desinstalar por completo (contenedor + volumen + imagen + icono)",
        "Disinstalla completamente (contenitore + volume + immagine + icona)",
        "Vollständig deinstallieren (Container + Volume + Image + Symbol)",
        "Desinstalar completamente (contêiner + volume + imagem + ícone)",
    ),
    "Supprime aussi le volume open-webui et l'image": (
        "Elimina también el volumen open-webui y la imagen",
        "Rimuove anche il volume open-webui e l'immagine",
        "Entfernt auch das open-webui-Volume und das Image",
        "Remove também o volume open-webui e a imagem",
    ),
    "Supprimer le conteneur, l'icône, l'image ET toutes les conversations (volume open-webui) ?": (
        "¿Eliminar el contenedor, el icono, la imagen Y todas las conversaciones (volumen open-webui)?",
        "Rimuovere contenitore, icona, immagine E tutte le conversazioni (volume open-webui)?",
        "Container, Symbol, Image UND alle Unterhaltungen (open-webui-Volume) löschen?",
        "Remover o contêiner, o ícone, a imagem E todas as conversas (volume open-webui)?",
    ),
    "Désinstaller VSCodium": (
        "Desinstalar VSCodium",
        "Disinstalla VSCodium",
        "VSCodium deinstallieren",
        "Desinstalar o VSCodium",
    ),
    "Clé GPG + vscodium.repo + dnf install codium": (
        "Clave GPG + vscodium.repo + dnf install codium",
        "Chiave GPG + vscodium.repo + dnf install codium",
        "GPG-Schlüssel + vscodium.repo + dnf install codium",
        "Chave GPG + vscodium.repo + dnf install codium",
    ),
    "Ouvre codium sous votre session utilisateur": (
        "Abre codium en tu sesión de usuario",
        "Apre codium nella tua sessione utente",
        "Öffnet codium in deiner Benutzersitzung",
        "Abre o codium na sua sessão de usuário",
    ),
    "dnf remove -y codium + retrait dépôt": (
        "dnf remove -y codium + eliminación del repositorio",
        "dnf remove -y codium + rimozione del repository",
        "dnf remove -y codium + Entfernen des Repositorys",
        "dnf remove -y codium + remoção do repositório",
    ),
    "Supprimer VSCodium (codium) et son dépôt ?": (
        "¿Eliminar VSCodium (codium) y su repositorio?",
        "Rimuovere VSCodium (codium) e il suo repository?",
        "VSCodium (codium) und sein Repository entfernen?",
        "Remover o VSCodium (codium) e o seu repositório?",
    ),
    "Ollama n'est pas installé (sera installé au premier pull).": (
        "Ollama no está instalado (se instalará en el primer pull).",
        "Ollama non è installato (verrà installato al primo pull).",
        "Ollama ist nicht installiert (wird beim ersten Pull installiert).",
        "O Ollama não está instalado (será instalado no primeiro pull).",
    ),
    "Aucun modèle installé pour le moment.": (
        "Todavía no hay ningún modelo instalado.",
        "Nessun modello installato per ora.",
        "Noch kein Modell installiert.",
        "Nenhum modelo instalado por enquanto.",
    ),
    "ollama stop sur tous les modèles actifs": (
        "ollama stop en todos los modelos activos",
        "ollama stop su tutti i modelli attivi",
        "ollama stop für alle aktiven Modelle",
        "ollama stop em todos os modelos ativos",
    ),
    "Cliquez sur un modèle pour le télécharger, mettre à jour, stopper ou supprimer": (
        "Haz clic en un modelo para descargarlo, actualizarlo, detenerlo o eliminarlo",
        "Fai clic su un modello per scaricarlo, aggiornarlo, fermarlo o rimuoverlo",
        "Klicke auf ein Modell, um es zu laden, zu aktualisieren, zu stoppen oder zu löschen",
        "Clique num modelo para baixar, atualizar, parar ou remover",
    ),
    "Décharger de la RAM (ollama stop)": (
        "Descargar de la RAM (ollama stop)",
        "Scarica dalla RAM (ollama stop)",
        "Aus dem Arbeitsspeicher entladen (ollama stop)",
        "Descarregar da memória RAM (ollama stop)",
    ),
    "Afficher les détails du modèle (ollama show)": (
        "Mostrar los detalles del modelo (ollama show)",
        "Mostra i dettagli del modello (ollama show)",
        "Modelldetails anzeigen (ollama show)",
        "Mostrar os detalhes do modelo (ollama show)",
    ),
    "Architecture, quantification, paramètres et licence": (
        "Arquitectura, cuantización, parámetros y licencia",
        "Architettura, quantizzazione, parametri e licenza",
        "Architektur, Quantisierung, Parameter und Lizenz",
        "Arquitetura, quantização, parâmetros e licença",
    ),
    "Supprimer le modèle (stop auto + ollama rm)": (
        "Eliminar el modelo (stop automático + ollama rm)",
        "Rimuovi il modello (stop automatico + ollama rm)",
        "Modell löschen (automatischer Stop + ollama rm)",
        "Remover o modelo (paragem automática + ollama rm)",
    ),
    "Gestionnaire système, matériel et logiciels pour Fedora sur PS5.": (
        "Gestor de sistema, hardware y software para Fedora en PS5.",
        "Gestore di sistema, hardware e software per Fedora su PS5.",
        "System-, Hardware- und Softwareverwaltung für Fedora auf der PS5.",
        "Gerenciador de sistema, hardware e software para Fedora no PS5.",
    ),
    "Mise à jour terminée — redémarrage automatique…": (
        "Actualización terminada — reiniciando automáticamente…",
        "Aggiornamento completato — riavvio automatico…",
        "Aktualisierung abgeschlossen — automatischer Neustart…",
        "Atualização concluída — reiniciando automaticamente…",
    ),
    "Démarrer / arrêter le serveur IA (port 11434)": (
        "Iniciar / detener el servidor de IA (puerto 11434)",
        "Avvia / arresta il server IA (porta 11434)",
        "KI-Server starten / stoppen (Port 11434)",
        "Iniciar / parar o servidor de IA (porta 11434)",
    ),
    "Démarrage automatique Ollama au boot": (
        "Inicio automático de Ollama al arrancar",
        "Avvio automatico di Ollama all'avvio",
        "Ollama automatisch beim Start laden",
        "Início automático do Ollama na inicialização",
    ),
    "Tout démarrer (Ollama + Open WebUI)": (
        "Iniciar todo (Ollama + Open WebUI)",
        "Avvia tutto (Ollama + Open WebUI)",
        "Alles starten (Ollama + Open WebUI)",
        "Iniciar tudo (Ollama + Open WebUI)",
    ),
    "Tout arrêter (libérer la RAM)": (
        "Detener todo (liberar la RAM)",
        "Arresta tutto (libera la RAM)",
        "Alles stoppen (Arbeitsspeicher freigeben)",
        "Parar tudo (liberar a RAM)",
    ),
    "Ouvrir Open WebUI dans le navigateur": (
        "Abrir Open WebUI en el navegador",
        "Apri Open WebUI nel browser",
        "Open WebUI im Browser öffnen",
        "Abrir o Open WebUI no navegador",
    ),
    "État des conteneurs Podman (podman ps -a)": (
        "Estado de los contenedores Podman (podman ps -a)",
        "Stato dei contenitori Podman (podman ps -a)",
        "Status der Podman-Container (podman ps -a)",
        "Estado dos contêineres Podman (podman ps -a)",
    ),
    "Logs Open WebUI (podman logs --tail 30)": (
        "Registros de Open WebUI (podman logs --tail 30)",
        "Log di Open WebUI (podman logs --tail 30)",
        "Open-WebUI-Protokolle (podman logs --tail 30)",
        "Registros do Open WebUI (podman logs --tail 30)",
    ),
    "Gérer les modèles IA (catalogue & installés)": (
        "Gestionar los modelos de IA (catálogo e instalados)",
        "Gestisci i modelli IA (catalogo e installati)",
        "KI-Modelle verwalten (Katalog & installiert)",
        "Gerenciar os modelos de IA (catálogo e instalados)",
    ),
    "Voir les modèles installés (ollama list)": (
        "Ver los modelos instalados (ollama list)",
        "Vedi i modelli installati (ollama list)",
        "Installierte Modelle anzeigen (ollama list)",
        "Ver os modelos instalados (ollama list)",
    ),
    "Modèles actifs en RAM (ollama ps)": (
        "Modelos activos en RAM (ollama ps)",
        "Modelli attivi in RAM (ollama ps)",
        "Aktive Modelle im Speicher (ollama ps)",
        "Modelos ativos na RAM (ollama ps)",
    ),
    "Diagnostic RAM / GPU / Disque pour l'IA": (
        "Diagnóstico de RAM / GPU / disco para la IA",
        "Diagnostica RAM / GPU / disco per l'IA",
        "RAM-/GPU-/Festplatten-Diagnose für KI",
        "Diagnóstico de RAM / GPU / disco para a IA",
    ),
    "Nettoyer les anciennes images Podman": (
        "Limpiar las imágenes Podman antiguas",
        "Pulisci le vecchie immagini Podman",
        "Alte Podman-Images bereinigen",
        "Limpar as imagens Podman antigas",
    ),
    "Modèles installés sur le système": (
        "Modelos instalados en el sistema",
        "Modelli installati sul sistema",
        "Auf dem System installierte Modelle",
        "Modelos instalados no sistema",
    ),
    "Décharger tous les modèles de la RAM": (
        "Descargar todos los modelos de la RAM",
        "Scarica tutti i modelli dalla RAM",
        "Alle Modelle aus dem Arbeitsspeicher entladen",
        "Descarregar todos os modelos da RAM",
    ),
    "Catalogue des modèles recommandés": (
        "Catálogo de modelos recomendados",
        "Catalogo dei modelli consigliati",
        "Katalog empfohlener Modelle",
        "Catálogo de modelos recomendados",
    ),
    "Télécharger un autre modèle (nom personnalisé)": (
        "Descargar otro modelo (nombre personalizado)",
        "Scarica un altro modello (nome personalizzato)",
        "Ein weiteres Modell laden (eigener Name)",
        "Baixar outro modelo (nome personalizado)",
    ),
    "Freebuff (agent de code IA)": (
        "Freebuff (agente de código IA)",
        "Freebuff (agente di codice IA)",
        "Freebuff (KI-Coding-Agent)",
        "Freebuff (agente de código IA)",
    ),
    "Non installé · npm install -g freebuff": (
        "No instalado · npm install -g freebuff",
        "Non installato · npm install -g freebuff",
        "Nicht installiert · npm install -g freebuff",
        "Não instalado · npm install -g freebuff",
    ),
    "Installé (binaire détecté)": (
        "Instalado (binario detectado)",
        "Installato (binario rilevato)",
        "Installiert (Binärdatei gefunden)",
        "Instalado (binário detetado)",
    ),
    "npm install -g freebuff (Node.js + npm installés si absents)": (
        "npm install -g freebuff (Node.js y npm instalados si faltan)",
        "npm install -g freebuff (Node.js e npm installati se assenti)",
        "npm install -g freebuff (Node.js und npm bei Bedarf installiert)",
        "npm install -g freebuff (Node.js e npm instalados se ausentes)",
    ),
    "Lancer Freebuff dans un terminal": (
        "Iniciar Freebuff en una terminal",
        "Avvia Freebuff in un terminale",
        "Freebuff in einem Terminal starten",
        "Iniciar o Freebuff num terminal",
    ),
    "Ouvre freebuff dans un terminal sous votre session utilisateur": (
        "Abre freebuff en una terminal en tu sesión de usuario",
        "Apre freebuff in un terminale nella tua sessione utente",
        "Öffnet freebuff in einem Terminal Ihrer Benutzersitzung",
        "Abre o freebuff num terminal na sua sessão de utilizador",
    ),
    "Désinstaller Freebuff": (
        "Desinstalar Freebuff",
        "Disinstalla Freebuff",
        "Freebuff deinstallieren",
        "Desinstalar o Freebuff",
    ),
    "Supprimer Freebuff (npm uninstall -g freebuff) ?": (
        "¿Eliminar Freebuff (npm uninstall -g freebuff)?",
        "Rimuovere Freebuff (npm uninstall -g freebuff)?",
        "Freebuff entfernen (npm uninstall -g freebuff)?",
        "Remover o Freebuff (npm uninstall -g freebuff)?",
    ),
    "Installer Freebuff": (
        "Instalar Freebuff",
        "Installa Freebuff",
        "Freebuff installieren",
        "Instalar o Freebuff",
    ),
    "Mettre à jour Freebuff": (
        "Actualizar Freebuff",
        "Aggiorna Freebuff",
        "Freebuff aktualisieren",
        "Atualizar o Freebuff",
    ),
    "Node.js et npm sont requis pour Freebuff : installation…": (
        "Node.js y npm son necesarios para Freebuff: instalando…",
        "Node.js e npm sono necessari per Freebuff: installazione…",
        "Node.js und npm werden für Freebuff benötigt – Installation…",
        "Node.js e npm são necessários para o Freebuff: a instalar…",
    ),
    "Node.js et npm sont requis pour Freebuff.": (
        "Node.js y npm son necesarios para Freebuff.",
        "Node.js e npm sono necessari per Freebuff.",
        "Node.js und npm werden für Freebuff benötigt.",
        "Node.js e npm são necessários para o Freebuff.",
    ),
    "npm est introuvable : Freebuff n'a pas été installé par npm.": (
        "npm no encontrado: Freebuff no se instaló con npm.",
        "npm non trovato: Freebuff non è stato installato con npm.",
        "npm nicht gefunden: Freebuff wurde nicht mit npm installiert.",
        "npm não encontrado: o Freebuff não foi instalado com npm.",
    ),
    "Terminal introuvable : lance « freebuff » depuis un terminal.": (
        "Terminal no encontrada: ejecuta «freebuff» desde una terminal.",
        "Terminale non trovato: avvia «freebuff» da un terminale.",
        "Kein Terminal gefunden: starte „freebuff“ in einem Terminal.",
        "Terminal não encontrado: execute «freebuff» num terminal.",
    ),
    "Composants (socle système)": (
        "Componentes (base del sistema)",
        "Componenti (base di sistema)",
        "Komponenten (Systembasis)",
        "Componentes (base do sistema)",
    ),
    "Outils en ligne de commande": (
        "Herramientas de línea de comandos",
        "Strumenti da riga di comando",
        "Kommandozeilen-Werkzeuge",
        "Ferramentas de linha de comando",
    ),
    "Applications graphiques": (
        "Aplicaciones gráficas",
        "Applicazioni grafiche",
        "Grafische Anwendungen",
        "Aplicativos gráficos",
    ),
    "Installation, mise à jour et désinstallation par catégorie — tout est optionnel.": (
        "Instalación, actualización y desinstalación por categoría: todo es opcional.",
        "Installazione, aggiornamento e disinstallazione per categoria: tutto è opzionale.",
        "Installation, Aktualisierung und Deinstallation nach Kategorie – alles ist optional.",
        "Instalação, atualização e desinstalação por categoria: tudo é opcional.",
    ),
    "Socle de compilation": (
        "Base de compilación",
        "Base di compilazione",
        "Build-Grundlage",
        "Base de compilação",
    ),
    "Conteneurs (Podman, Distrobox, Toolbox)": (
        "Contenedores (Podman, Distrobox, Toolbox)",
        "Contenitori (Podman, Distrobox, Toolbox)",
        "Container (Podman, Distrobox, Toolbox)",
        "Contêineres (Podman, Distrobox, Toolbox)",
    ),
    "Virtualisation KVM / QEMU": (
        "Virtualización KVM / QEMU",
        "Virtualizzazione KVM / QEMU",
        "Virtualisierung KVM / QEMU",
        "Virtualização KVM / QEMU",
    ),
    "Recherche & navigation": (
        "Búsqueda y navegación",
        "Ricerca e navigazione",
        "Suche & Navigation",
        "Pesquisa e navegação",
    ),
    "Git & plateformes (GitHub, GitLab)": (
        "Git y plataformas (GitHub, GitLab)",
        "Git e piattaforme (GitHub, GitLab)",
        "Git & Plattformen (GitHub, GitLab)",
        "Git e plataformas (GitHub, GitLab)",
    ),
    "Diagnostic système": (
        "Diagnóstico del sistema",
        "Diagnostica di sistema",
        "Systemdiagnose",
        "Diagnóstico do sistema",
    ),
    "Debug & profilage": (
        "Depuración y perfilado",
        "Debug e profilazione",
        "Debug & Profiling",
        "Depuração e perfilagem",
    ),
    "Qualité Python (uv, ruff, mypy)": (
        "Calidad Python (uv, ruff, mypy)",
        "Qualità Python (uv, ruff, mypy)",
        "Python-Qualität (uv, ruff, mypy)",
        "Qualidade Python (uv, ruff, mypy)",
    ),
    "Automatisation (just, direnv, shellcheck)": (
        "Automatización (just, direnv, shellcheck)",
        "Automazione (just, direnv, shellcheck)",
        "Automatisierung (just, direnv, shellcheck)",
        "Automação (just, direnv, shellcheck)",
    ),
    "Forgejo (serveur Git local)": (
        "Forgejo (servidor Git local)",
        "Forgejo (server Git locale)",
        "Forgejo (lokaler Git-Server)",
        "Forgejo (servidor Git local)",
    ),
    "Éditeurs terminal (Neovim, Helix)": (
        "Editores de terminal (Neovim, Helix)",
        "Editor da terminale (Neovim, Helix)",
        "Terminal-Editoren (Neovim, Helix)",
        "Editores de terminal (Neovim, Helix)",
    ),
    "Bases de données (SQLite)": (
        "Bases de datos (SQLite)",
        "Database (SQLite)",
        "Datenbanken (SQLite)",
        "Bases de dados (SQLite)",
    ),
    "script d'installation intégré": (
        "script de instalación integrado",
        "script di installazione integrato",
        "integriertes Installationsskript",
        "script de instalação integrado",
    ),
    "script de mise à jour intégré": (
        "script de actualización integrado",
        "script di aggiornamento integrato",
        "integriertes Aktualisierungsskript",
        "script de atualização integrado",
    ),
    "script de désinstallation intégré": (
        "script de desinstalación integrado",
        "script di disinstallazione integrato",
        "integriertes Deinstallationsskript",
        "script de desinstalação integrado",
    ),
    "Déconnecte-toi puis reconnecte-toi pour activer les groupes docker, libvirt et kvm.": (
        "Cierra la sesión y vuelve a entrar para activar los grupos docker, libvirt y kvm.",
        "Esci e rientra per attivare i gruppi docker, libvirt e kvm.",
        "Melde dich ab und wieder an, um die Gruppen docker, libvirt und kvm zu aktivieren.",
        "Termina e volta a iniciar sessão para ativar os grupos docker, libvirt e kvm.",
    ),
    "Désinstallation : les données restent dans /var/lib/forgejo.": (
        "Desinstalación: los datos permanecen en /var/lib/forgejo.",
        "Disinstallazione: i dati restano in /var/lib/forgejo.",
        "Deinstallation: die Daten bleiben in /var/lib/forgejo.",
        "Desinstalação: os dados permanecem em /var/lib/forgejo.",
    ),
    "Rien à faire pour cette entrée.": (
        "Nada que hacer para esta entrada.",
        "Niente da fare per questa voce.",
        "Für diesen Eintrag gibt es nichts zu tun.",
        "Nada a fazer para esta entrada.",
    ),
    "Installer": (
        "Instalar",
        "Installa",
        "Installieren",
        "Instalar",
    ),
    "Mettre à jour": (
        "Actualizar",
        "Aggiorna",
        "Aktualisieren",
        "Atualizar",
    ),
    "Désinstaller": (
        "Desinstalar",
        "Disinstalla",
        "Deinstallieren",
        "Desinstalar",
    ),
    "Lancer": (
        "Iniciar",
        "Avvia",
        "Starten",
        "Iniciar",
    ),
    "Supprimer": (
        "Eliminar",
        "Rimuovi",
        "Entfernen",
        "Remover",
    ),
    "Lancement impossible : commande ou terminal introuvable.": (
        "No se puede iniciar: comando o terminal no encontrado.",
        "Avvio impossibile: comando o terminale non trovato.",
        "Start nicht möglich: Befehl oder Terminal nicht gefunden.",
        "Não é possível iniciar: comando ou terminal não encontrado.",
    ),
    "À propos de cette page": (
        "Acerca de esta página",
        "Informazioni su questa pagina",
        "Über diese Seite",
        "Sobre esta página",
    ),
    "Les groupes docker, libvirt et kvm ne s'appliquent qu'après une reconnexion.": (
        "Los grupos docker, libvirt y kvm solo se aplican tras volver a iniciar sesión.",
        "I gruppi docker, libvirt e kvm si applicano solo dopo un nuovo accesso.",
        "Die Gruppen docker, libvirt und kvm gelten erst nach einer neuen Anmeldung.",
        "Os grupos docker, libvirt e kvm só se aplicam após nova sessão.",
    ),
    "Serveurs & langages": (
        "Servidores y lenguajes",
        "Server e linguaggi",
        "Server & Sprachen",
        "Servidores e linguagens",
    ),
    "Panneaux & bases de données": (
        "Paneles y bases de datos",
        "Pannelli e database",
        "Panels & Datenbanken",
        "Painéis e bases de dados",
    ),
    "Réseau & accès": (
        "Red y acceso",
        "Rete e accesso",
        "Netzwerk & Zugriff",
        "Rede e acesso",
    ),
    "PHP 8 + extensions": (
        "PHP 8 + extensiones",
        "PHP 8 + estensioni",
        "PHP 8 + Erweiterungen",
        "PHP 8 + extensões",
    ),
    "Panneau web Cockpit": (
        "Panel web Cockpit",
        "Pannello web Cockpit",
        "Cockpit-Weboberfläche",
        "Painel web Cockpit",
    ),
    "Pare-feu web (80 / 443 / 9090)": (
        "Cortafuegos web (80 / 443 / 9090)",
        "Firewall web (80 / 443 / 9090)",
        "Web-Firewall (80 / 443 / 9090)",
        "Firewall web (80 / 443 / 9090)",
    ),
    "Serveur OpenSSH (accès distant)": (
        "Servidor OpenSSH (acceso remoto)",
        "Server OpenSSH (accesso remoto)",
        "OpenSSH-Server (Fernzugriff)",
        "Servidor OpenSSH (acesso remoto)",
    ),
    "Apache et Nginx ne peuvent pas écouter le port 80 en même temps : garde un seul serveur actif.": (
        "Apache y Nginx no pueden escuchar el puerto 80 a la vez: mantén un solo servidor activo.",
        "Apache e Nginx non possono ascoltare la porta 80 contemporaneamente: tieni un solo server attivo.",
        "Apache und Nginx können nicht gleichzeitig auf Port 80 lauschen: lass nur einen Server aktiv.",
        "O Apache e o Nginx não podem escutar a porta 80 ao mesmo tempo: mantém apenas um servidor ativo.",
    ),
    "Apache : page par défaut sur http://localhost après activation du service.": (
        "Apache: página por defecto en http://localhost tras activar el servicio.",
        "Apache: pagina predefinita su http://localhost dopo l'attivazione del servizio.",
        "Apache: Standardseite unter http://localhost nach dem Start des Dienstes.",
        "Apache: página predefinida em http://localhost após ativar o serviço.",
    ),
    "Nginx : page par défaut sur http://localhost après activation du service.": (
        "Nginx: página por defecto en http://localhost tras activar el servicio.",
        "Nginx: pagina predefinita su http://localhost dopo l'attivazione del servizio.",
        "Nginx: Standardseite unter http://localhost nach dem Start des Dienstes.",
        "Nginx: página predefinida em http://localhost após ativar o serviço.",
    ),
    "MariaDB : lance « mariadb-secure-installation » pour durcir le serveur ; root se connecte en local via socket.": (
        "MariaDB: ejecuta «mariadb-secure-installation» para asegurar el servidor; root se conecta en local por socket.",
        "MariaDB: esegui «mariadb-secure-installation» per proteggere il server; root si connette in locale via socket.",
        "MariaDB: „mariadb-secure-installation“ ausführen, um den Server abzusichern; root verbindet sich lokal über den Socket.",
        "MariaDB: executa «mariadb-secure-installation» para proteger o servidor; o root liga-se localmente pelo socket.",
    ),
    "MySQL community : lance « mysql_secure_installation » après l'installation.": (
        "MySQL community: ejecuta «mysql_secure_installation» tras la instalación.",
        "MySQL community: esegui «mysql_secure_installation» dopo l'installazione.",
        "MySQL community: nach der Installation „mysql_secure_installation“ ausführen.",
        "MySQL community: executa «mysql_secure_installation» após a instalação.",
    ),
    "PHP-FPM : socket /run/php-fpm/www.sock ; l'entrée « PHP ↔ Apache / Nginx » ajoute le handler FastCGI.": (
        "PHP-FPM: socket /run/php-fpm/www.sock; la entrada «PHP ↔ Apache / Nginx» añade el handler FastCGI.",
        "PHP-FPM: socket /run/php-fpm/www.sock; la voce «PHP ↔ Apache / Nginx» aggiunge l'handler FastCGI.",
        "PHP-FPM: Socket /run/php-fpm/www.sock; der Eintrag „PHP ↔ Apache / Nginx“ fügt den FastCGI-Handler hinzu.",
        "PHP-FPM: socket /run/php-fpm/www.sock; a entrada «PHP ↔ Apache / Nginx» adiciona o handler FastCGI.",
    ),
    "Cockpit : https://localhost:9090 (comptes système, port 9090 ouvert dans le pare-feu).": (
        "Cockpit: https://localhost:9090 (cuentas del sistema, puerto 9090 abierto en el cortafuegos).",
        "Cockpit: https://localhost:9090 (account di sistema, porta 9090 aperta nel firewall).",
        "Cockpit: https://localhost:9090 (Systemkonten, Port 9090 in der Firewall geöffnet).",
        "Cockpit: https://localhost:9090 (contas do sistema, porta 9090 aberta na firewall).",
    ),
    "phpMyAdmin est limité à localhost par défaut (/etc/httpd/conf.d/phpMyAdmin.conf).": (
        "phpMyAdmin está limitado a localhost por defecto (/etc/httpd/conf.d/phpMyAdmin.conf).",
        "phpMyAdmin è limitato a localhost per impostazione predefinita (/etc/httpd/conf.d/phpMyAdmin.conf).",
        "phpMyAdmin ist standardmäßig auf localhost beschränkt (/etc/httpd/conf.d/phpMyAdmin.conf).",
        "O phpMyAdmin está limitado a localhost por predefinição (/etc/httpd/conf.d/phpMyAdmin.conf).",
    ),
    "Adminer : un seul fichier PHP dans /var/www/html/adminer.php.": (
        "Adminer: un solo archivo PHP en /var/www/html/adminer.php.",
        "Adminer: un solo file PHP in /var/www/html/adminer.php.",
        "Adminer: eine einzelne PHP-Datei unter /var/www/html/adminer.php.",
        "Adminer: um único ficheiro PHP em /var/www/html/adminer.php.",
    ),
    "Webmin écoute sur https://localhost:10000 ; crée un compte depuis l'interface.": (
        "Webmin escucha en https://localhost:10000; crea una cuenta desde la interfaz.",
        "Webmin ascolta su https://localhost:10000; crea un account dall'interfaccia.",
        "Webmin lauscht auf https://localhost:10000; Konto in der Oberfläche anlegen.",
        "O Webmin escuta em https://localhost:10000; cria uma conta na interface.",
    ),
    "OpenSSH : sshd écoute sur le port 22 ; ouvre-le dans le pare-feu si nécessaire.": (
        "OpenSSH: sshd escucha en el puerto 22; ábrelo en el cortafuegos si hace falta.",
        "OpenSSH: sshd ascolta sulla porta 22; aprila nel firewall se necessario.",
        "OpenSSH: sshd lauscht auf Port 22; bei Bedarf in der Firewall öffnen.",
        "OpenSSH: o sshd escuta na porta 22; abre-a na firewall se necessário.",
    ),
    "Certbot : « certbot --apache » ou « certbot --nginx » une fois le domaine pointé.": (
        "Certbot: «certbot --apache» o «certbot --nginx» una vez apuntado el dominio.",
        "Certbot: «certbot --apache» o «certbot --nginx» una volta puntato il dominio.",
        "Certbot: „certbot --apache“ oder „certbot --nginx“, sobald die Domain zeigt.",
        "Certbot: «certbot --apache» ou «certbot --nginx» depois de apontar o domínio.",
    ),
    "Ouvre GitHub Desktop (Flatpak) sous votre session": (
        "Abre GitHub Desktop (Flatpak) en tu sesión",
        "Apre GitHub Desktop (Flatpak) nella tua sessione",
        "Öffnet GitHub Desktop (Flatpak) in Ihrer Sitzung",
        "Abre o GitHub Desktop (Flatpak) na sua sessão",
    ),
    "Ouvre Neovim dans un terminal": (
        "Abre Neovim en una terminal",
        "Apre Neovim in un terminale",
        "Öffnet Neovim in einem Terminal",
        "Abre o Neovim num terminal",
    ),
    "Ouvre SQLite Browser": (
        "Abre SQLite Browser",
        "Apre SQLite Browser",
        "Öffnet SQLite Browser",
        "Abre o SQLite Browser",
    ),
    "Ouvre Forgejo dans le navigateur (http://localhost:3000)": (
        "Abre Forgejo en el navegador (http://localhost:3000)",
        "Apre Forgejo nel browser (http://localhost:3000)",
        "Öffnet Forgejo im Browser (http://localhost:3000)",
        "Abre o Forgejo no navegador (http://localhost:3000)",
    ),
    "Ouvre http://localhost dans le navigateur": (
        "Abre http://localhost en el navegador",
        "Apre http://localhost nel browser",
        "Öffnet http://localhost im Browser",
        "Abre http://localhost no navegador",
    ),
    "Ouvre Cockpit (https://localhost:9090)": (
        "Abre Cockpit (https://localhost:9090)",
        "Apre Cockpit (https://localhost:9090)",
        "Öffnet Cockpit (https://localhost:9090)",
        "Abre o Cockpit (https://localhost:9090)",
    ),
    "Ouvre http://localhost/phpMyAdmin": (
        "Abre http://localhost/phpMyAdmin",
        "Apre http://localhost/phpMyAdmin",
        "Öffnet http://localhost/phpMyAdmin",
        "Abre http://localhost/phpMyAdmin",
    ),
    "Ouvre http://localhost/adminer.php": (
        "Abre http://localhost/adminer.php",
        "Apre http://localhost/adminer.php",
        "Öffnet http://localhost/adminer.php",
        "Abre http://localhost/adminer.php",
    ),
    "Ouvre Webmin (https://localhost:10000)": (
        "Abre Webmin (https://localhost:10000)",
        "Apre Webmin (https://localhost:10000)",
        "Öffnet Webmin (https://localhost:10000)",
        "Abre o Webmin (https://localhost:10000)",
    ),
    "Nécessaire pour accéder au serveur depuis une autre machine du réseau.": (
        "Necesario para acceder al servidor desde otra máquina de la red.",
        "Necessario per accedere al server da un'altra macchina della rete.",
        "Nötig, um den Server von einem anderen Rechner im Netzwerk zu erreichen.",
        "Necessário para aceder ao servidor a partir de outra máquina da rede.",
    ),
    "Serveur web LAMP": (
        "Servidor web LAMP",
        "Server web LAMP",
        "LAMP-Webserver",
        "Servidor web LAMP",
    ),
    "Serveur web LEMP": (
        "Servidor web LEMP",
        "Server web LEMP",
        "LEMP-Webserver",
        "Servidor web LEMP",
    ),
    "Code & outils": (
        "Código y herramientas",
        "Codice e strumenti",
        "Code & Werkzeuge",
        "Código e ferramentas",
    ),
    "Conteneurs & services": (
        "Contenedores y servicios",
        "Contenitori e servizi",
        "Container & Dienste",
        "Contêineres e serviços",
    ),
    "Apache + PHP + MariaDB + phpMyAdmin, prêt à héberger un site": (
        "Apache + PHP + MariaDB + phpMyAdmin, listo para alojar un sitio",
        "Apache + PHP + MariaDB + phpMyAdmin, pronto per ospitare un sito",
        "Apache + PHP + MariaDB + phpMyAdmin, bereit für eine Website",
        "Apache + PHP + MariaDB + phpMyAdmin, pronto para alojar um site",
    ),
    "Nginx + PHP-FPM + MariaDB, la variante légère": (
        "Nginx + PHP-FPM + MariaDB, la variante ligera",
        "Nginx + PHP-FPM + MariaDB, la variante leggera",
        "Nginx + PHP-FPM + MariaDB, die schlanke Variante",
        "Nginx + PHP-FPM + MariaDB, a variante leve",
    ),
    "Compilation, Python + GTK4, outils CLI, qualité et debug": (
        "Compilación, Python + GTK4, herramientas CLI, calidad y depuración",
        "Compilazione, Python + GTK4, strumenti CLI, qualità e debug",
        "Kompilierung, Python + GTK4, CLI-Werkzeuge, Qualität und Debug",
        "Compilação, Python + GTK4, ferramentas CLI, qualidade e depuração",
    ),
    "Podman, Docker, Forgejo local, Cockpit, pare-feu et SSH": (
        "Podman, Docker, Forgejo local, Cockpit, cortafuegos y SSH",
        "Podman, Docker, Forgejo locale, Cockpit, firewall e SSH",
        "Podman, Docker, lokales Forgejo, Cockpit, Firewall und SSH",
        "Podman, Docker, Forgejo local, Cockpit, firewall e SSH",
    ),
    "Composants à installer": (
        "Componentes a instalar",
        "Componenti da installare",
        "Zu installierende Komponenten",
        "Componentes a instalar",
    ),
    "Décoche ce dont tu n'as pas besoin — rien n'est obligatoire.": (
        "Desmarca lo que no necesites: nada es obligatorio.",
        "Deseleziona ciò che non ti serve: nulla è obbligatorio.",
        "Abwählen, was nicht gebraucht wird – nichts ist Pflicht.",
        "Desmarca o que não precisas: nada é obrigatório.",
    ),
    "Configuration": (
        "Configuración",
        "Configurazione",
        "Konfiguration",
        "Configuração",
    ),
    "Bon à savoir": (
        "Bueno saberlo",
        "Buono a sapersi",
        "Gut zu wissen",
        "Bom saber",
    ),
    "Utilisé pour l'hôte virtuel et la base de données.": (
        "Se usa para el host virtual y la base de datos.",
        "Usato per l'host virtuale e il database.",
        "Wird für virtuellen Host und Datenbank verwendet.",
        "Usado para o host virtual e a base de dados.",
    ),
    "Installer la sélection": (
        "Instalar la selección",
        "Installa la selezione",
        "Auswahl installieren",
        "Instalar a seleção",
    ),
    "Aucun composant sélectionné.": (
        "Ningún componente seleccionado.",
        "Nessun componente selezionato.",
        "Keine Komponente ausgewählt.",
        "Nenhum componente selecionado.",
    ),
    "Configuration du serveur": (
        "Configuración del servidor",
        "Configurazione del server",
        "Serverkonfiguration",
        "Configuração do servidor",
    ),
    "Nom du serveur (ServerName)": (
        "Nombre del servidor (ServerName)",
        "Nome del server (ServerName)",
        "Servername (ServerName)",
        "Nome do servidor (ServerName)",
    ),
    "Dossier web (DocumentRoot)": (
        "Carpeta web (DocumentRoot)",
        "Cartella web (DocumentRoot)",
        "Webverzeichnis (DocumentRoot)",
        "Pasta web (DocumentRoot)",
    ),
    "Mot de passe root MariaDB/MySQL (facultatif)": (
        "Contraseña root de MariaDB/MySQL (opcional)",
        "Password root MariaDB/MySQL (facoltativa)",
        "MariaDB/MySQL-root-Passwort (optional)",
        "Palavra-passe root do MariaDB/MySQL (opcional)",
    ),
    "Base de données à créer (facultatif)": (
        "Base de datos a crear (opcional)",
        "Database da creare (facoltativo)",
        "Anzulegende Datenbank (optional)",
        "Base de dados a criar (opcional)",
    ),
    "Utilisateur de la base (facultatif)": (
        "Usuario de la base (opcional)",
        "Utente del database (facoltativo)",
        "Datenbankbenutzer (optional)",
        "Utilizador da base de dados (opcional)",
    ),
    "Mot de passe de la base (facultatif)": (
        "Contraseña de la base (opcional)",
        "Password del database (facoltativa)",
        "Datenbank-Passwort (optional)",
        "Palavra-passe da base de dados (opcional)",
    ),
    "Le setup 1 clic d'origine (menu ⋮) reste inchangé.": (
        "La configuración en 1 clic original (menú ⋮) no cambia.",
        "La configurazione in 1 clic originale (menu ⋮) resta invariata.",
        "Das ursprüngliche 1-Klick-Setup (Menü ⋮) bleibt unverändert.",
        "A configuração em 1 clique original (menu ⋮) mantém-se igual.",
    ),
    "Les profils peuvent être relancés : ce qui est déjà installé est simplement mis à jour.": (
        "Los perfiles se pueden relanzar: lo ya instalado solo se actualiza.",
        "I profili possono essere rilanciati: ciò che è già installato viene solo aggiornato.",
        "Profile lassen sich erneut starten: bereits Installiertes wird nur aktualisiert.",
        "Os perfis podem ser relançados: o que já está instalado é apenas atualizado.",
    ),
    "Choisis un profil, ajuste les composants et la configuration, puis lance l'installation.": (
        "Elige un perfil, ajusta los componentes y la configuración, y lanza la instalación.",
        "Scegli un profilo, regola componenti e configurazione, poi avvia l'installazione.",
        "Profil wählen, Komponenten und Konfiguration anpassen, dann Installation starten.",
        "Escolhe um perfil, ajusta os componentes e a configuração e inicia a instalação.",
    ),
}


# LSTRINGS[langue][texte français] : traductions des textes hors STRINGS
# (page IA & Développeur, à propos). L'anglais sert de repli via _L().
LSTRINGS: dict[str, dict[str, str]] = {
    "es": {key: values[0] for key, values in _L_TABLE.items()},
    "it": {key: values[1] for key, values in _L_TABLE.items()},
    "de": {key: values[2] for key, values in _L_TABLE.items()},
    "pt": {key: values[3] for key, values in _L_TABLE.items()},
}


def _L(fr: str, en: str) -> str:
    """Libellé bilingue ponctuel pour les textes hors dictionnaire `STRINGS`."""
    if UI_LANG == "fr":
        return fr
    return LSTRINGS.get(UI_LANG, {}).get(fr) or en


# ------------------------------------------------------------------------------
# Fenêtre « Système » : logos Fedora / bureau / Gamescope + informations
# ------------------------------------------------------------------------------
# Icônes PNG 96 px embarquées en base64 (sources : dossier icons/ du dépôt) :
# l'application reste un fichier unique installé par curl, sans accès réseau.
ICONS_B64: dict[str, str] = {
    "fedora":
        "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",
    "gamescope":
        "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",
    "budgie":
        "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",
    "cinnamon":
        "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",
    "kde":
        "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAARvElEQVR42u1daZBcV3U+59z7Xu8zrZE02qWRLMmStVq7JVkabMCYBBscMJVAYkIgCYFgQhKqIE5VAKeAmBQ2RVhCKAoSCCTGFapiQ7CxtSFka7EsyVrGsjbPjGZG0kzv673n5MfrlkeaHlmWprtHUt+q/tUz7737fWf97nkzAI3VWDfywmvhIZcsWCNX8nsvvbwDGwTUCOxrlRS8EUAfzWTgjQj8aCICb1TQRwsZ2AC+vkRQA/z6PjM2gK+vN1AD/PruBRvA19cbqAF+ffdIDfDru1dqgF/fPVMD/PrunRrg15cEaoBfXxKoAX59SaAG+PUlgRrg15cEakBW34XXivULKmMn3XLQRsanJDimyKGxwOGxjgRbghyIhmDctPHOS/+7L7jpGxsElUGxuvJ1yKKwKk5ZvNfMWRfXx3eF1dlj0yh9rnUoOsQgfEVGermShR714CMKiCC4gVTiXQ/PpGhrRFgAEUEAAJgBTB4wFABBdelNIzGCEAea+9Pv+LtWmDB9ae7W+wEyA/2q/9Q+3Xt4QPcc8um+o5Mp1jXtSsEvY3Y5JOhryl3ZGslnWIoFFkQsEYQg1iL7NQBc0lAEkFFYp9/6t69C6/SVNtZfQK0dDI5psc2TWnj2aigIAKdjRZU8e1yf3NkZeu7rG6q5JxrtoaeCFRMQKSDlfZAIANH7XDqEoVidXX7/ZrvozpWciBnUrgtAKKYgkolbTsYMp2IGSGtunT1Ld+2/KgO9HOzoeqp6RCwMH/etNpNu2Z/b+LHbOZUyoEgNIhU9QrUGAaBQGAO/emSzr+O5tdWuiq6rKgiFpXLcBxRfOJa6+6EWQEXAlgBoqMdYY6gpqvXeX+zw731io5Ay1X5mqqv1IwogcVW9ApBBmNJ3fvoITJg5RXJpC6SG7pstYyCssbvjROiZry4AJEaRqqvF9fOAcnUjTIJkAXDECS/H/dySd282S+5ezYmYAaXV0B9kAaUFCtlc6MnPF7CQiYiIXE0VNLobMSQGERR/ZMC2zjmMwgpA0CPiqpLAIMsvxf0Jcw9m7vjLtZxOWSBSwyUPCoRU8OlHdumzx+YKKoMgqhZQUM3DT6m5ETeUSL7nK92JB/51bnbthzeJ0jkUVoLKXKk3IJtyZcqIgOIGk6l3PhRGchxgi4DDxf1m7ez48RbfoafXCw3fxFUjDFHtww6TOMFE8j1fOcUzbl0g2bzkN360PfEH3zpppiza523e84Yr9ojSfdJveXA/TJwzXXJpUznuG0uhZk2v7no5tOVbt5W75FpCQjWzfkQBQOFA87nke750kmcuX8jJAQOkFCdihifMvzn5/q8vytz+Z5tF+zIorFBYgQiKcrMgcpmyCQrYoi+/8He3mGX3rC3FfV0h7jM6PoLk2YHQL74YBTYOAuDl32dkvKBmnXA5JudWfuBlmbdqA5/pL4DjugAAoLSWXIqBEAvrP7TRzFxzNPDsYylxQ/n8xgcivi0/SLrHtq8SohReOukCgKBtnXso/dYHV0MmPUzcZwEABu3q4FMPH1WJvpX1sP6aEoDglXS+w79qzS+5NweOzwWwcr4eL4UITsSstM6ZnXrfowCIQBEXQPD5S1qmeLIimawIkk2986EAar9PcmkGqqAPWbbUHNXuM9/c5J58oV1IGWRbF1mGapZ8S+Wm6js6z931X89TKERgeWiMV1pJPs1i8izZZA4sgCjHXgbDAPkMZtd9ZBtMndMm2VTluG+NpUhUqwPP7gy+8O/tgsog187yL8a4pqwjCAESB3f/eEV8/p3dGJ08SYp59vSci01DETU3+bHzyCv63PFW0W4ORCo3bUSK01koLPydGTY6aQYk0lwx7jMzBsIK+o53hX715ZsAUTzPlLq9H1DbKkgEBUCwkA0FtnzrFDo+BBEZ0pE6fgKQvP+ZxzY3/fAjM1T/idmi/RkcjgAkBDbA42a2eSGtUgfLAkqBFHOF8FNfiFEu2VLukuspn9T85l6tT9Z3dOsadfi53RRpVsDGAqAHvj9ElD7T2/TTBzv8u36yEcQ6gCj4hkAhSDE/vKzBbCkQouCmf/mt7jm8QEgV65F0R0UnjAAIiBLc/M0WiJ8ZAO0QsLHo+gkTZ/rCP/1UWvccXCSkiwAlyeIyxQeoJMiVujOxFszUpf7zMkgV5I8rJqCm0nPJmlWscyadPXkanQACIYuYYujnn+tTsc5ZQrqIbJzLjs8igNpFII0gFbaCSkk2Zc3Su1bnbr1/Mwrrq5Y+RiAR18UDBMmACBZnrt5p25bdwulYkUJNTmDrv/3G6T288HXwL5tQRl8A9CtbX8DMQD9qzRU9gZA4mbLZjX9+u5kw/wCKrRsJtScAUTx5QRlAEgCA7NL7NAAA+QIKuw6fCLz4+Nry4cmbujYzk1+D0/liNrT1O4coFCDgCiUuEAJbBNIq/Y7PRsANpMrh8LokQJCMJ655FZAnL1iNbBw7ZuoJM23ZIskkLfoC5N/z36+BNe6bi/mD7mUBODBG3MNPr4Mjz++ncFR7yX1oeSu5lJXJc2akNn7iJRAmgfp5QVX7ABQ+f30OtvRxy/RuM2Fu3LTOcczE+dMBUYF2gAd6487RbQu8BH0VlQl6nhZ55quR+Ae+mwbl+oGNDFFBlVacjBuz/L51+VN7fuM78ut116UUkZ//9m1m6mKx428aZ5umTIVwy1J0FIAASKEAkM8YCke1Ora9g3KJlVczh1MKRQAiSAOdbcFN39iSfddDGzgZM4CkK4RExbkMZ97210t0z6GTKt4946rvP9pCUPrtn1lfXPV7t9vJi+aLPxyRfJq9yYO4kWKOAb0n0D2H0wAoAjgyx5PKyfsOPLlBHXx2F4WGCUVICKYgGIyG03d9NilIVgCk1qVpddnOJWOcTBrJpyzYongjJVoDKV0aJwFgAIqddr1yc8T2joAooV8/OlmSZ+OgfZX7A9KK03HDs1cszN72oa3lJvH6IQDJG/VApIqnUaVBBson3EFRfAQUDyYBZEqdmRx89rH95A/QsDMrSilOJkx+3R+3F6ct21Pr0rS6BAgzWGOA2Q7boXqZs0qShzK+w8+s1/t++TyFmzXYCqHIG+gisEYy7/jsFA4093ulaXWnNWpThrr+IDVFNAaaNSgHgZmBjQG2tnQoIkgA7AsXyrCNvPqKHNr09Vky0NOPrg9BmCt4Kkk+xzJ26oT0nZ8+CiUPuuYJaPr53+/zbf7+Jn1i5z7MJRMYiBBFohqDzQpQIwgDEAA3TylUJfl5QApmBsaHnv3aEXQDNKykrbTiZMzYRW9flVty7xYUq2sxmFXVMtQ5tWu5c2qXh0Ww5YxpvWl3cfLipJ20IGomzJ0jyvEBA5hJ80MAgghC1QpF7itbbivs/fl2s+zetZyI2YrzQUSKMymbaf/EGt21v0OfPTb3Wu+ES9IDCmb6xzsndi4Pbv9ee+Rnn14a+M33dlOwSXM2xcXJC2/mQHM/CFM1ZAEEIUGywS3fnidnO3vR56dhQhGCNYDa1em3/Q2L9mdqRkA1/iJIWXoAETyvBSmnAIjiHt8+i9OJArAVirY2FWdvOADgHd5fDrcgzMDWAhuDYg0w22Hno4UJhRVlYy3hZ/75JGofggAP+l68a1kL2qcANeG8W+dl2j++pxqgD8a6dkeSIoggCiwrAbKU6J2qO/fs5pvbl0s+y9ll723zHfxlHthqLx9U0IOEPZUTFaHjAigHkACAQVOwlNGHWjUDAHCktcuMmd7jHt+xSu/+2Taz6r3rOd6fB1IaHJ8i168AASRxLqlPvnDEfXVbVncdmHRN54BLajYCENj9OKZmrTFczImaPHd6dtn9mwI7f9ReUY5GFPGHo+QGEVLnMhg/fU6les/RQHeSYp2sEl1+3dNxc9nzBodBZOOk13zolJ3Xfqv+7vv7Q1u/vTjetqJbTW6bzDkASJzu16/s63Bf3W71ay/eRKkzK2oJxflVs0OZcpxXujDwwH8koGnCeDEFg1pD5KefPKi7Dyy+mATRbq4487YXKX0uTInecZQZGAdvcGZQvkZ+zsbtmXu+uBa1A2rfkzsiv3h4TXHGit3FRXfn9KHntO7eP4ey8ZbBXiOAjCBUDW1ocAiqCwHlqeXM2j/ZXNjwkY2ciltARHRchFy8v+knDw6o/pOzPQC9UcVhOm1+vV4vVVHn840yyMYpTl26N3XfP80TVC6YAlMkqgNPfG77xS9flLpfQRBVzem4iwmg4b6oZmWEYrVpvflQfs0H13MmzUBIgERSyAsEWsYm7380Wpyy+KXykWS5kvLOF8h6cd2b/0Sx2vt4YUdQGRBBZOMUZt++I33fV+aCcvzARQRSJPksZ9/yqfkcGd/teYkqlg79FQrrWoJffSlimNAjpEz6zr8iUI4CNhdMx0k+wxIcMy75vq8tyK7+4CbRbq5cSSEAeaopsCByucwtnbKxd+hjtfgisczGj29Ov/tLa4ScoJgCAyoERBJTQAk2j0m8/xuSvPuhHSii6nk4P6QZmdg69R+qaP2Mwiq3/Pe3mBX3rJBUYujgLBKCMQwiyHPXzyzMvO0UiuxXyb4gFrNhBKFKHwBB2zShq7DonhfTd32myd58+yLJJAwII+CgCTkkBC4KBJqboO2WqXiue5vu62gTJFuNRvDi1Xum8/PDJuFq5gIBtAii7Ni2o/EPfnc6ACgvwV2kkpYaJHQCxIVUkZyggz4fyEDvgD798lHdczhN8S6XcglXgEQCzQU7ZlrRTprfbCbNn4uRsSHOZUCKeUOBJi35DHsy/0XTd2wtahcgG483//ABoGxyTHmsvVbhp6ZlKCKiANrU2z5TJF/A4UySgfSFD2SNQX9YAyLgmWOv0bhZ00Ap4FTcgj8yxs6/Y6VdcAcAA5QVHVQlM7IAkkuBpOJMoWYSVJq6D3TwxFvmAgJILn2ht5FSUswbik5syWz4i+3h//vyWq/yqe3SwzFVDS9AAHRe291XmHnr/FKzBaWJOAukFDVFNZx5rSu49TsnnKNblxXbVj5fWHqfU5iyeDFqF2wqZrxuF7HcTHgXKZ1lBZs05hJ5ffjZfb49P3Oczr1LC7M3/Db7lk+0ScuUSeVq67w3IAgoADQFW36+Wlo/XEqIr0pJWjpzzaz98KZC+0fbORkrAgNSKKqlmLW+PU9sC+z4wWLMJ8dc4Bhj217NrvpAb3HhXbdJLsOA6sLcxczoD5Fv539u9u/9n1kU75p2PumLoASiZzIbPtZRXPKudWKKwPmMQQShpqjj7HxiW+jpR9aXk3i1BnWHI2DYKYDqJGMBQbLua3tmsYVNMm/tTaj9pE688FLoyS+c87381Cq0hUA5IQqSBVKWMv3jMJs4V1x8zyQp5mVIPEcAsIZDT33Bp5I9U4VUEQABxbsGFrNh99Vt06mnY4eZfAtSdEIUA36ldz2xLVwD8Csl3zf0gOo1ZiiCyCissqv/aBMWM+jf8/jGUpVkhjRCJS3Hhsf1xP/w+y3g+P0gg0pXYUY3RNTXcaL5R386BUqvNV0AJnoH/iis2B/pz7R/8hDYgpwHH6SqryZdqr+qgxYkiCIKECXw/A/bBwM9eI5osJIJAKBSZydS4vRxmTjvJskbAYTXCXAU6Z4jXcCmcjlZEgIFyVIu2RL+5T+uG/zdqH0/oKqdsVzwJuQlyz9BsiBM+uyxXtQKKmn5qnt/uS6SS8nj59/O9zxLqg3+G2FIV3uBqz8vYAVvWH14oOq+juKQnySlOJsRp+fgxPLhyxsRD8Jlka2u4NdeiriKsAUAoHo7olK0rzdVwoxOADHW1akGOme8HlKunUUjxWR1NXPPqlX/ySmS6IuDcgmEBUQYHQ3O6YOngI3rhbPRQcDlYvamHrbxVxNHFvxrKARdv4uqxWzD+qvkAQ0SRhYbqtWNGuCPcA5okDAyWFC9btwAf4SqoBuZhJHYO42WB7kRwR/RPuBGImEk90qj9cFuBPDftBTxZtb1JltUy7joWnvg6wn8qnrA9eANtTAiul42cq0+c+NfmtfZWOpqmaOFjHp66KgIDfUiYjSExlEXm6tNxmjLR9dEcrxSUhpiYWM11mhf/w8j7MDx7fvK+gAAAABJRU5ErkJggg==",
    "gnome":
        "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",
}

SYSTEM_ICONS = {
    "gnome": "gnome",
    "kde": "kde",
    "cinnamon": "cinnamon",
    "budgie": "budgie",
}


def icon_texture(name: str) -> Any:
    """Texture GDK d'une icône embarquée (None si les données sont refusées)."""
    payload = ICONS_B64.get(name)
    if not payload:
        return None
    try:
        return Gdk.Texture.new_from_bytes(GLib.Bytes.new(base64.b64decode(payload)))
    except (GLib.Error, ValueError, TypeError):
        return None


def _icon_image(name: str, size: int) -> Optional[Gtk.Image]:
    """Image d'une icône embarquée, dimensionnée à `size` pixels."""
    texture = icon_texture(name)
    if texture is None:
        return None
    image = Gtk.Image.new_from_paintable(texture)
    image.set_pixel_size(size)
    return image


class SystemInfoWindow(Adw.Window):
    """Fenêtre « Système » : identité de la console, de la session et de l'application."""

    def __init__(self, parent: "Ps5ManagerWindow", accent: str) -> None:
        super().__init__(transient_for=parent, modal=True, title=T("system_info"))
        self._parent = parent
        self._copy_lines: list[str] = []
        self.set_default_size(560, 680)

        os_name, kernel = get_os_summary()
        desktop_icon = SYSTEM_ICONS.get(DESKTOP_ID)

        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title=T("system_info"), subtitle=APP_NAME)
        )
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic")
        copy_btn.set_tooltip_text(T("sys_copy"))
        copy_btn.add_css_class("flat")
        copy_btn.connect("clicked", self._on_copy)
        header.pack_start(copy_btn)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        content.set_margin_top(18)
        content.set_margin_bottom(24)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(self._hero(os_name, kernel, desktop_icon))

        grp_system = pref_group(title=T("system_info"))
        self._add_row(grp_system, T("sys_os"), os_name, "computer-symbolic")
        self._add_row(
            grp_system, T("sys_kernel"), kernel, "application-x-executable-symbolic"
        )
        self._add_row(
            grp_system, T("sys_arch"), os.uname().machine,
            "application-x-firmware-symbolic",
        )
        self._add_row(
            grp_system, T("sys_dnf"), "DNF5" if IS_DNF5 else "DNF 4",
            "package-x-generic-symbolic",
        )
        content.append(grp_system)

        grp_session = pref_group(title=T("sys_group_session"))
        desktop_row = self._add_row(grp_session, T("sys_desktop"), DESKTOP_LABEL)
        desktop_image = _icon_image(desktop_icon, 22) if desktop_icon else None
        if desktop_image is not None:
            desktop_row.add_prefix(desktop_image)
        else:
            desktop_row.add_prefix(
                Gtk.Image.new_from_icon_name("video-display-symbolic")
            )
        self._add_row(
            grp_session, T("sys_dm"), DISPLAY_MANAGER_LABEL,
            "preferences-system-symbolic",
        )
        self._add_row(grp_session, T("sys_session"), DESKTOP_SESSION, "system-run-symbolic")
        self._add_row(
            grp_session, T("sys_user"), f"{REAL_USER} (uid {REAL_UID})",
            "system-users-symbolic",
        )
        self._add_row(
            grp_session, T("sys_accent"), accent, "applications-graphics-symbolic"
        )
        content.append(grp_session)

        grp_soft = pref_group(title=T("sys_group_software"))
        gamescope_row = self._add_row(
            grp_soft,
            T("sys_gamescope"),
            T("sys_installed") if shutil.which("gamescope") else T("not_installed"),
        )
        gamescope_image = _icon_image("gamescope", 22)
        if gamescope_image is not None:
            gamescope_row.add_prefix(gamescope_image)
        else:
            gamescope_row.add_prefix(
                Gtk.Image.new_from_icon_name("applications-games-symbolic")
            )
        self._add_row(
            grp_soft,
            T("sys_steam"),
            T("sys_installed") if shutil.which("steam") else T("not_installed"),
            "applications-games-symbolic",
        )
        content.append(grp_soft)

        grp_app = pref_group(title=T("sys_group_app"))
        self._add_row(grp_app, T("sys_version"), APP_VERSION, "info-symbolic")
        self._add_row(
            grp_app, T("sys_file"), os.path.abspath(sys.argv[0]),
            "text-x-generic-symbolic",
        )
        log_row = self._add_row(
            grp_app, T("sys_log"), str(parent.logger.path),
            "utilities-terminal-symbolic",
        )
        open_btn = Gtk.Button(icon_name="document-open-symbolic")
        open_btn.set_tooltip_text(T("sys_open"))
        open_btn.set_valign(Gtk.Align.CENTER)
        open_btn.add_css_class("flat")
        open_btn.connect("clicked", self._on_open_log)
        log_row.add_suffix(open_btn)
        content.append(grp_app)

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(
            Adw.Clamp(maximum_size=560, tightening_threshold=420, child=content)
        )

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scroll)
        self.set_content(toolbar)

    # ---- Construction ----
    def _hero(
        self, os_name: str, kernel: str, desktop_icon: Optional[str]
    ) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)

        logo = _icon_image("fedora", 72)
        if logo is None:
            logo = Gtk.Image.new_from_icon_name("computer-symbolic")
            logo.set_pixel_size(48)
        logo.set_valign(Gtk.Align.CENTER)
        box.append(logo)

        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        titles.set_valign(Gtk.Align.CENTER)
        titles.set_hexpand(True)
        name = Gtk.Label(label=APP_NAME, xalign=0.0)
        name.add_css_class("title-2")
        subtitle = Gtk.Label(label=f"{os_name} · Linux {kernel}", xalign=0.0)
        subtitle.add_css_class("dim-label")
        subtitle.set_wrap(True)
        titles.append(name)
        titles.append(subtitle)
        box.append(titles)

        if desktop_icon:
            badge = _icon_image(desktop_icon, 56)
            if badge is not None:
                badge.set_valign(Gtk.Align.CENTER)
                badge.set_tooltip_text(DESKTOP_LABEL)
                box.append(badge)
        return box

    def _add_row(
        self,
        group: Adw.PreferencesGroup,
        label: str,
        value: str,
        icon: Optional[str] = None,
    ) -> Adw.ActionRow:
        row = plain_row(Adw.ActionRow, title=label, subtitle=value)
        row.set_subtitle_selectable(True)
        if icon:
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        group.add(row)
        self._copy_lines.append(f"{label} : {value}")
        return row

    # ---- Actions ----
    def _on_copy(self, *_args: Any) -> None:
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set("\n".join(self._copy_lines))
        self._parent.toast(T("sys_copy_done"))

    def _on_open_log(self, *_args: Any) -> None:
        self._parent.open_live_log(follow=False)


class Ps5ManagerWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, theme_sync: SystemThemeSync) -> None:
        super().__init__(
            application=app,
            title=APP_NAME,
            default_width=1160,
            default_height=760,
        )
        self.theme_sync = theme_sync
        self.logger = SessionLogger()
        self.busy = False
        self.auto_log_opened = False
        self.log_window: Optional[TextLogWindow] = None
        self.setup_window: Optional["SetupWindow"] = None
        self.active_section = "logs"
        self.sidebar_rows: dict[str, Adw.ActionRow] = {}

        self.busy_spinner = Gtk.Spinner()
        self.overlay = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(260)
        self.split.set_max_sidebar_width(330)

        # Breakpoint responsive pour petites fenêtres
        bp = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 720sp")
        )
        bp.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(bp)

        self.split.set_sidebar(self._build_sidebar())
        self.split.set_content(self._build_content())
        self.overlay.set_child(self.split)
        self.set_content(self.overlay)

        self._select_section("logs")

        # Vérification de mise à jour en arrière-plan (l'ouverture reste instantanée)
        self.start_auto_update()

    # ---- Barre latérale ----
    def _build_sidebar(self) -> Adw.NavigationPage:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_title_widget(Gtk.Label(label=APP_NAME, css_classes=["title"]))

        search_btn = Gtk.ToggleButton(icon_name="system-search-symbolic")
        search_btn.set_tooltip_text(T("search_placeholder"))
        self.search_btn = search_btn
        header.pack_start(search_btn)

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_model = Gio.Menu()
        menu_model.append(T("setup_menu"), "win.run-setup")
        menu_model.append(T("system_info"), "win.show-sysinfo")
        menu_model.append(T("about"), "win.show-about")
        menu_btn.set_menu_model(menu_model)
        self.menu_model = menu_model
        header.pack_end(menu_btn)

        self._register_window_actions()
        box.append(header)

        # Barre de recherche
        self.search_entry = Gtk.SearchEntry(placeholder_text=T("search_placeholder"))
        search_bar = Gtk.SearchBar(child=self.search_entry)
        search_bar.connect_entry(self.search_entry)
        search_btn.bind_property(
            "active", search_bar, "search-mode-enabled",
            2  # BIDIRECTIONAL
        )
        self.search_entry.connect("search-changed", self._on_search_changed)
        box.append(search_bar)

        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.set_filter_func(self._filter_sidebar_row)
        self.sidebar_list.connect("row-activated", self._on_sidebar_activated)

        prev_group = 1
        for sec_id, icon, label_key, grp in SECTIONS:
            if grp != prev_group:
                sep = Gtk.Separator(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    valign=Gtk.Align.CENTER,
                    vexpand=False,
                )
                sep.set_size_request(-1, 1)
                sep_row = Gtk.ListBoxRow(
                    selectable=False, activatable=False, focusable=False
                )
                sep_row.add_css_class("ps5-sidebar-sep")
                sep_row.set_child(sep)
                sep_row.is_separator = True  # type: ignore[attr-defined]
                self.sidebar_list.append(sep_row)
                prev_group = grp

            row = plain_row(Adw.ActionRow,
                title=T(label_key),
                activatable=True,
            )
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.sec_id = sec_id  # type: ignore[attr-defined]
            row.label_key = label_key  # type: ignore[attr-defined]
            self.sidebar_rows[sec_id] = row
            self.sidebar_list.append(row)

        scroll = Gtk.ScrolledWindow(
            child=self.sidebar_list, hexpand=True, vexpand=True
        )
        box.append(scroll)
        return Adw.NavigationPage(child=box, title=APP_NAME)

    def _register_window_actions(self) -> None:
        act_sys = Gio.SimpleAction.new("show-sysinfo", None)
        act_sys.connect("activate", lambda *_: self._show_sysinfo())
        self.add_action(act_sys)

        act_about = Gio.SimpleAction.new("show-about", None)
        act_about.connect("activate", lambda *_: self._show_about())
        self.add_action(act_about)

        act_setup = Gio.SimpleAction.new("run-setup", None)
        act_setup.connect("activate", lambda *_: self.start_recommended_setup())
        self.add_action(act_setup)

    def _filter_sidebar_row(self, row: Gtk.ListBoxRow) -> bool:
        q = self.search_entry.get_text().strip().lower()
        if not q:
            return True
        if getattr(row, "is_separator", False):
            return False
        sec_id = getattr(row, "sec_id", "")
        label_key = getattr(row, "label_key", "")
        title = (T(label_key) if label_key else getattr(row, "get_title", lambda: "")()).lower()
        return q in title or q in sec_id

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self.sidebar_list.invalidate_filter()

    def _on_sidebar_activated(self, _lb: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        sec_id = getattr(row, "sec_id", None)
        if sec_id:
            self._select_section(sec_id)
            self.split.set_show_content(True)

    # ---- Contenu principal ----
    def _build_content(self) -> Adw.NavigationPage:
        self.nav = Adw.NavigationView()
        placeholder = Adw.NavigationPage(child=Gtk.Box(), title=APP_NAME)
        self.nav.add(placeholder)
        return Adw.NavigationPage(child=self.nav, title=APP_NAME)

    def _select_section(self, sec_id: str) -> None:
        self.active_section = sec_id
        row = self.sidebar_rows.get(sec_id)
        if row:
            self.sidebar_list.select_row(row)
        page = self._make_section_page(sec_id)
        self.nav.replace([page])

    def rebuild_ui_for_language(self) -> None:
        for sec_id, row in self.sidebar_rows.items():
            row.set_title(T(row.label_key))  # type: ignore[attr-defined]
        self.search_entry.set_placeholder_text(T("search_placeholder"))
        search_btn = getattr(self, "search_btn", None)
        if search_btn is not None:
            search_btn.set_tooltip_text(T("search_placeholder"))
        # Le menu burger est un Gio.Menu construit une seule fois : sans cette
        # reconstruction il gardait les libellés de l'ancienne langue jusqu'au
        # redémarrage de l'application.
        menu_model = getattr(self, "menu_model", None)
        if menu_model is not None:
            menu_model.remove_all()
            menu_model.append(T("setup_menu"), "win.run-setup")
            menu_model.append(T("system_info"), "win.show-sysinfo")
            menu_model.append(T("about"), "win.show-about")
        self._select_section(self.active_section)

    def _make_section_page(self, sec_id: str) -> Adw.NavigationPage:
        sec_meta = next((s for s in SECTIONS if s[0] == sec_id), SECTIONS[0])
        title = T(sec_meta[2])

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=title))

        if self.busy_spinner.get_parent() is not None:
            self.busy_spinner.unparent()
        header.pack_end(self.busy_spinner)
        log_btn = Gtk.Button(icon_name="utilities-terminal-symbolic")
        log_btn.set_tooltip_text(T("logs_live"))
        log_btn.connect("clicked", lambda *_: self.open_live_log(follow=True))
        header.pack_end(log_btn)

        toolbar.add_top_bar(header)

        pref_page = Adw.PreferencesPage()
        builder = PAGE_BUILDERS.get(sec_id)
        if builder:
            builder(self, pref_page)

        toolbar.set_content(pref_page)
        return Adw.NavigationPage(child=toolbar, title=title)

    # ---- Helpers d'interface Libadwaita ----
    def row(
        self,
        title: str,
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        callback: Optional[Callable] = None,
        suffix_icon: Optional[str] = "go-next-symbolic",
    ) -> Adw.ActionRow:
        r = plain_row(Adw.ActionRow,
            title=title,
            activatable=callback is not None,
        )
        if subtitle:
            r.set_subtitle(subtitle)
        if icon:
            r.add_prefix(Gtk.Image.new_from_icon_name(icon))
        if suffix_icon:
            r.add_suffix(Gtk.Image.new_from_icon_name(suffix_icon))
        if callback:
            r.connect("activated", callback)
        return r

    def toast(self, message: str) -> None:
        self.overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def show_info(self, heading: str, body: str) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("ok", T("close"))
        dlg.set_default_response("ok")
        dlg.present(self)

    def show_confirm(
        self,
        heading: str,
        body: str,
        on_confirm: Callable[[], None],
        destructive: bool = True,
    ) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        dlg.add_response("cancel", T("cancel"))
        dlg.add_response("ok", T("confirm"))
        if destructive:
            dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def _on_resp(_d, resp):
            if resp == "ok":
                on_confirm()

        dlg.connect("response", _on_resp)
        dlg.present(self)

    def show_prompt(
        self,
        heading: str,
        body: str,
        placeholder: str,
        on_submit: Callable[[str], None],
        password: bool = False,
    ) -> None:
        dlg = Adw.AlertDialog(heading=heading, body=body)
        entry = (
            Gtk.PasswordEntry(show_peek_icon=True)
            if password
            else Gtk.Entry(placeholder_text=placeholder)
        )
        entry.set_margin_top(8)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", T("cancel"))
        dlg.add_response("ok", T("ok"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("ok")
        dlg.set_close_response("cancel")

        def _on_resp(_d, resp):
            if resp == "ok":
                on_submit(entry.get_text())

        dlg.connect("response", _on_resp)
        dlg.present(self)

    def show_text_modal(self, title: str, content: str) -> None:
        win = TextLogWindow(self, title)
        win.load_text(content or T("logs_none"))
        win.present()

    def open_live_log(self, follow: bool = True) -> None:
        if self.log_window is None:
            self.log_window = TextLogWindow(self, T("sec_logs"))
        self.log_window.title_widget.set_title(T("logs_live"))
        self.log_window.present()
        if follow:
            self.log_window.follow(self.logger.path)

    # ---- Setup recommandé ----
    def maybe_show_welcome(self) -> None:
        """Choix de la langue, puis boîte de bienvenue (premier lancement)."""
        if welcome_seen():
            return
        mark_welcome_seen()
        # Différé d'une boucle : la fenêtre principale doit être réalisée avant la boîte.
        GLib.idle_add(self._present_welcome_language)

    def set_ui_language(self, code: str) -> None:
        global UI_LANG
        UI_LANG = code
        write_ui_lang(code)
        self.rebuild_ui_for_language()

    def _present_welcome_language(self) -> bool:
        """Premier choix de la langue, avant le message de setup.

        Le texte est volontairement bilingue : la langue de l'interface n'est pas
        encore connue au tout premier lancement.
        """
        dlg = Adw.AlertDialog(
            heading="Choose your language · Choisissez votre langue",
            body=(
                "PS5 Fedora Manager is available in French, English, Spanish, "
                "Italian, German and Brazilian Portuguese.\n"
                "PS5 Fedora Manager est disponible en français, anglais, espagnol, "
                "italien, allemand et portugais du Brésil."
            ),
        )
        for _code in reversed(LANG_ORDER):
            dlg.add_response(_code, LANG_LABELS[_code])
        default = UI_LANG if UI_LANG in LANG_LABELS else "fr"
        dlg.set_response_appearance(default, Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response(default)
        dlg.set_close_response(default)

        def _on_resp(_d, resp: str) -> None:
            if resp in LANG_LABELS:
                self.set_ui_language(resp)
            GLib.idle_add(self._present_welcome)

        dlg.connect("response", _on_resp)
        dlg.present(self)
        return False

    def _present_welcome(self) -> bool:
        dlg = Adw.AlertDialog(
            heading=T("setup_welcome_title"), body=T("setup_welcome_body")
        )
        dlg.add_response("manual", T("setup_welcome_manual"))
        dlg.add_response("setup", T("setup_welcome_recommended"))
        dlg.set_response_appearance("setup", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("setup")
        dlg.set_close_response("manual")

        def _on_resp(_d, resp: str) -> None:
            if resp == "setup":
                self.start_recommended_setup(confirm=False)

        dlg.connect("response", _on_resp)
        dlg.present(self)
        return False

    def start_recommended_setup(self, confirm: bool = True) -> None:
        if self.busy:
            self.toast(T("busy"))
            return
        if self.setup_window is not None:
            self.setup_window.present()
            return

        def _go() -> None:
            self.busy = True
            self.busy_spinner.start()
            self.setup_window = SetupWindow(self, _build_setup_plan(self))
            self.setup_window.present()
            self.setup_window.start()

        if confirm:
            self.show_confirm(
                T("setup_title"), T("setup_confirm_body"), _go, destructive=False
            )
        else:
            _go()

    def prompt_reboot(self, done: int, failed: int) -> None:
        dlg = Adw.AlertDialog(
            heading=T("setup_reboot_title"),
            body=T("setup_reboot_body") % (done, failed),
        )
        dlg.add_response("later", T("setup_later"))
        dlg.add_response("reboot", T("setup_reboot_now"))
        dlg.set_response_appearance("reboot", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("later")
        dlg.set_close_response("later")

        def _on_resp(_d, resp: str) -> None:
            if resp == "reboot":
                self.run_task(
                    T("setup_reboot_title"),
                    lambda e: (
                        self.run_cmd_pty(["systemctl", "reboot"], e) == 0,
                        T("done"),
                    ),
                )

        dlg.connect("response", _on_resp)
        dlg.present(self)


    # ---- Mise à jour automatique au lancement ----
    def start_auto_update(self) -> None:
        """Cherche une version plus récente et l'installe, sans bloquer l'ouverture."""
        if os.environ.get("PS5_MANAGER_NO_UPDATE_CHECK"):
            return
        threading.Thread(target=self._auto_update_worker, daemon=True).start()

    def _auto_update_worker(self) -> None:
        latest = fetch_latest_version()
        if not latest or version_tuple(latest) <= version_tuple(APP_VERSION):
            return
        if os.environ.get("PS5_MANAGER_SKIP_UPDATE") == latest:
            # Déjà tenté au lancement précédent : ne jamais boucler sur un échec.
            GLib.idle_add(self._auto_update_result, latest, False)
            return
        installed = install_update(latest)
        GLib.idle_add(self._auto_update_result, latest, installed)

    def _auto_update_result(self, latest: str, installed: bool) -> bool:
        if not installed:
            self.toast(
                _L(
                    "Mise à jour %s disponible : installe-la depuis « Mise à jour du manager »."
                    % latest,
                    "Update %s available: install it from “Manager update”." % latest,
                )
            )
            return False
        self.toast(
            _L(
                "Mise à jour %s installée — redémarrage…" % latest,
                "Update %s installed — restarting…" % latest,
            )
        )
        os.environ["PS5_MANAGER_SKIP_UPDATE"] = latest
        GLib.timeout_add(2500, self._restart_after_update)
        return False

    def _restart_after_update(self) -> bool:
        """Relance l'application sur la nouvelle version, sauf action en cours."""
        if getattr(self, "busy", False):
            self.toast(
                _L(
                    "Mise à jour installée — active au prochain démarrage.",
                    "Update installed — active on next start.",
                )
            )
            return False
        app = self.get_application()
        if app is not None:
            app.restart_on_exit = True  # type: ignore[attr-defined]
        if self.log_window is not None:
            self.log_window.destroy()
            self.log_window = None
        self.destroy()
        if app is not None:
            app.quit()
        return False

    # ---- Exécuteur asynchrone via PTY ----
    def run_task(
        self,
        title: str,
        fn: Callable[[Callable[[str], None]], tuple[bool, str]],
        on_done: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        if self.busy:
            self.toast(T("busy"))
            return
        self.busy = True
        self.busy_spinner.start()
        self.logger.write_line(f"──── {title}")

        if log_window_enabled() and not self.auto_log_opened:
            self.auto_log_opened = True
            self.open_live_log(follow=True)

        def _emit(line: str) -> None:
            self.logger.write_line(line)

        def _worker() -> None:
            ok = False
            msg = ""
            try:
                ok, msg = fn(_emit)
            except Exception as exc:
                ok = False
                msg = str(exc)
            self.logger.write_line(f"──── fin : {title} ({'OK' if ok else 'ERR'})")
            GLib.idle_add(self._finish_task, title, ok, msg, on_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_task(
        self,
        title: str,
        ok: bool,
        msg: str,
        on_done: Optional[Callable[[bool, str], None]],
    ) -> bool:
        self.busy = False
        self.busy_spinner.stop()
        if msg:
            if ok:
                self.toast(f"{title} — {msg}")
            else:
                self.show_info(title, msg)
        else:
            self.toast(f"{title} — {T('done') if ok else T('failed') % 1}")
        if on_done:
            on_done(ok, msg)
        return False

    def run_cmd_pty(
        self,
        cmd: list[str] | str,
        emit: Callable[[str], None],
        as_user: bool = False,
        shell: bool = False,
    ) -> int:
        if isinstance(cmd, str) and not shell:
            full_cmd: list[str] | str = ["bash", "-c", cmd]
        else:
            full_cmd = cmd

        proc_kwargs: dict[str, Any] = user_subprocess_kwargs() if as_user else {"env": os.environ}
        prefix = f"[{REAL_USER}] " if as_user and REAL_USER != "root" else ""
        self.logger.write_line(f"commande : {prefix}{full_cmd}")
        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            full_cmd,
            shell=shell,
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            **proc_kwargs,
        )
        os.close(slave_fd)

        buf = b""
        while True:
            rlist, _, _ = select.select([master_fd], [], [], 0.2)
            if rlist:
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    raw_line, buf = buf.split(b"\n", 1)
                    emit(strip_ansi(raw_line.decode("utf-8", errors="replace")))
            elif proc.poll() is not None:
                break
        if buf:
            emit(strip_ansi(buf.decode("utf-8", errors="replace")))
        os.close(master_fd)
        return proc.wait()

    # ---- Actions menu global ----
    def _show_sysinfo(self) -> None:
        SystemInfoWindow(self, self.theme_sync.current_accent).present()

    def _show_about(self) -> None:
        debug_info = (
            f"{T('debug_version')} : {APP_VERSION}\n"
            f"GTK {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}\n"
            f"Libadwaita {Adw.MAJOR_VERSION}.{Adw.MINOR_VERSION}.{Adw.MICRO_VERSION}\n"
            f"Python {sys.version.split()[0]}\n"
            f"{T('sys_file')} : {os.path.abspath(sys.argv[0])}"
        )
        # Vrai logo de l'application, repli sur une icône symbolique s'il est absent
        icon_name = "ps5-manager"
        display = Gdk.Display.get_default()
        if display is not None and not Gtk.IconTheme.get_for_display(display).has_icon(icon_name):
            icon_name = "applications-system-symbolic"

        if not hasattr(Adw, "AboutDialog"):
            self.show_info(APP_NAME, f"{APP_NAME} {APP_VERSION} — GTK4 / Libadwaita (nexgen999)")
            return

        about = Adw.AboutDialog(
            application_name=APP_NAME,
            application_icon=icon_name,
            version=APP_VERSION,
            developer_name="nexgen999",
            developers=["nexgen999"],
            copyright="© 2026 nexgen999",
            website="https://github.com/nexgen999/ps5-fedora-manager",
            issue_url="https://github.com/nexgen999/ps5-fedora-manager/issues",
            comments=(
                _L("Gestionnaire système, matériel et logiciels pour Fedora sur PS5.", "System, hardware and software manager for Fedora on PS5.")
            ),
            debug_info=debug_info,
            release_notes_version=APP_VERSION,
            release_notes=_safe_release_notes(release_notes_html()),
        )
        about.present(self)


# ------------------------------------------------------------------------------
# Builders des 19 pages
# ------------------------------------------------------------------------------
def build_page_logs(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = pref_group(title=T("logs_group_main"))
    g1.add(
        win.row(
            T("logs_live"),
            T("logs_live_sub"),
            "media-playback-start-symbolic",
            lambda *_: win.open_live_log(follow=True),
        )
    )
    g1.add(
        win.row(
            T("logs_session"),
            os.path.basename(win.logger.path),
            "text-x-generic-symbolic",
            lambda *_: win.open_live_log(follow=True),
        )
    )
    g1.add(
        win.row(
            T("logs_old"),
            T("logs_old_sub"),
            "folder-documents-symbolic",
            lambda *_: _push_old_logs(win),
        )
    )
    page.add(g1)

    g2 = pref_group(title=T("logs_group_opts"))
    sw = plain_row(Adw.SwitchRow,
        title=T("logs_auto"),
        subtitle=T("logs_auto_sub"),
    )
    sw.add_prefix(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
    sw.set_active(log_window_enabled())
    sw.connect("notify::active", lambda r, _p: set_log_window_enabled(r.get_active()))
    g2.add(sw)

    def _do_clear():
        win.logger.clear_all()
        win.toast(T("logs_cleared"))

    g2.add(
        win.row(
            T("logs_clear"),
            T("logs_clear_sub"),
            "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("logs_clear"), T("logs_clear_confirm"), _do_clear
            ),
        )
    )
    page.add(g2)


def _push_old_logs(win: Ps5ManagerWindow) -> None:
    sub = Adw.PreferencesPage()
    grp = pref_group(title=T("logs_old"))
    files = win.logger.list_logs()
    if not files:
        grp.add(plain_row(Adw.ActionRow, title=T("logs_none")))
    for path in files:
        name = os.path.basename(path)
        size_kb = max(1, os.path.getsize(path) // 1024) if os.path.exists(path) else 0
        grp.add(
            win.row(
                name,
                f"{size_kb} Ko",
                "text-x-generic-symbolic",
                lambda _r, p=path, n=name: _open_file_log(win, p, n),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("logs_old")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("logs_old")))


def _open_file_log(win: Ps5ManagerWindow, path: str, name: str) -> None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            win.show_text_modal(name, fh.read())
    except OSError as exc:
        win.show_info(name, str(exc))


def _fill_software_status(
    win: "Ps5ManagerWindow", pending: list[tuple[Adw.ActionRow, SoftwareItem]]
) -> None:
    """Complète les statuts RPM / Flatpak hors du fil GTK.

    `rpm -q` et surtout `flatpak info` prennent du temps : les exécuter pendant
    la construction de la page gelait l'interface. Les lignes sont affichées
    tout de suite avec leur description, puis leur sous-titre est complété.
    """
    if not pending:
        return

    def _worker() -> None:
        results = [
            (row, item, detect_software_status(item)[1]) for row, item in pending
        ]
        GLib.idle_add(_apply, results)

    def _apply(results: list[tuple[Adw.ActionRow, SoftwareItem, str]]) -> bool:
        for row, item, label in results:
            desc = item.description_fr if UI_LANG == "fr" else item.description_en
            try:
                row.set_subtitle(f"{desc} · {label}")
            except Exception:  # ligne déjà détruite (page quittée)
                pass
        return False

    threading.Thread(target=_worker, daemon=True).start()


def build_page_library(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    seen_categories: set[str] = set()
    pending: list[tuple[Adw.ActionRow, SoftwareItem]] = []
    for cat_id, title_key, sub_key in SOFTWARE_CATEGORIES:
        items = [
            it for it in SOFTWARE_CATALOG
            if it.category == cat_id and _software_supported(it)
        ]
        if not items:
            continue
        seen_categories.add(cat_id)
        grp = pref_group(title=T(title_key), description=T(sub_key))
        for item in items:
            desc = item.description_fr if UI_LANG == "fr" else item.description_en
            row = win.row(
                item.name,
                desc,
                item.icon,
                lambda _r, it=item: _push_software_actions(win, it),
            )
            pending.append((row, item))
            grp.add(row)
        page.add(grp)

    extra = [
        it for it in SOFTWARE_CATALOG
        if it.category not in seen_categories and _software_supported(it)
    ]
    if extra:
        grp = pref_group(title=T("lib_title"), description=T("lib_sub"))
        for item in extra:
            desc = item.description_fr if UI_LANG == "fr" else item.description_en
            row = win.row(
                item.name,
                desc,
                item.icon,
                lambda _r, it=item: _push_software_actions(win, it),
            )
            pending.append((row, item))
            grp.add(row)
        page.add(grp)

    _fill_software_status(win, pending)

    g_ai = pref_group(title=T("sec_aidev"), description=T("aidev_open_sub"))
    g_ai.add(
        win.row(
            T("sec_aidev"),
            T("aidev_open_sub"),
            "applications-development-symbolic",
            lambda *_: win._select_section("aidev"),
        )
    )
    page.add(g_ai)

    for app_id, app_name, desc_key, app_url in APPIMAGE_APPS:
        g_app = pref_group(title=app_name, description=T(desc_key))

        def _flatpak(action: str, app_id: str = app_id, app_name: str = app_name) -> None:
            if action == "install":
                cmd = (
                    "command -v flatpak >/dev/null || dnf install -y flatpak; "
                    "flatpak remote-add --if-not-exists flathub "
                    "https://flathub.org/repo/flathub.flatpakrepo; "
                    f"flatpak install -y --system flathub {app_id}"
                )
            elif action == "update":
                cmd = f"flatpak update -y {app_id}"
            else:
                cmd = f"flatpak uninstall -y --system {app_id}"
            label = f"{app_name} — {T('appimage_' + action)}"
            win.run_task(label, lambda e, c=cmd: (win.run_cmd_pty(c, e) == 0, T("done")))

        g_app.add(
            win.row(
                T("appimage_install"), app_id, "system-software-install-symbolic",
                lambda *_, f=_flatpak: f("install"),
            )
        )
        g_app.add(
            win.row(
                T("appimage_update"), None, "software-update-available-symbolic",
                lambda *_, f=_flatpak: f("update"),
            )
        )
        g_app.add(
            win.row(
                T("appimage_uninstall"), None, "user-trash-symbolic",
                lambda *_, n=app_name: win.show_confirm(
                    f"{n} — {T('appimage_uninstall')}",
                    T("appimage_uninstall_confirm") % n,
                    lambda f=_flatpak: f("uninstall"),
                ),
            )
        )
        g_app.add(
            win.row(
                T("appimage_flathub"), app_url, "web-browser-symbolic",
                lambda *_, u=app_url: open_uri(u),
            )
        )
        page.add(g_app)


def _push_software_actions(win: Ps5ManagerWindow, item: SoftwareItem) -> None:
    code, status_lbl = detect_software_status(item)
    sub = Adw.PreferencesPage()
    grp = pref_group(
        title=item.name,
        description=f"{status_lbl}",
    )

    def _run_sw(action: str) -> None:
        if item.kind == "dual" and action == "install" and code == "none":
            dlg = Adw.AlertDialog(
                heading=item.name, body=T("choose_format") % item.name
            )
            dlg.add_response("cancel", T("cancel"))
            dlg.add_response("rpm", T("format_rpm"))
            dlg.add_response("flatpak", T("format_flatpak"))
            dlg.set_response_appearance("rpm", Adw.ResponseAppearance.SUGGESTED)

            def _resp(_d, resp):
                if resp in ("rpm", "flatpak"):
                    _exec_software_action(win, item, action, forced_fmt=resp)

            dlg.connect("response", _resp)
            dlg.present(win)
        else:
            _exec_software_action(win, item, action)

    actions = [
        ("install", T("install"), "system-software-install-symbolic"),
        ("update", T("update"), "software-update-available-symbolic"),
        ("check", T("check"), "dialog-question-symbolic"),
        ("remove", T("remove"), "user-trash-symbolic"),
    ]
    for act, lbl, ic in actions:
        grp.add(win.row(lbl, None, ic, lambda _r, a=act: _run_sw(a)))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=item.name))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=item.name))


def _ensure_rpmfusion(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    if os.path.isfile("/etc/yum.repos.d/rpmfusion-nonfree.repo"):
        return True
    fed = subprocess.run(["rpm", "-E", "%fedora"], capture_output=True, text=True).stdout.strip() or "45"
    rc = win.run_cmd_pty(
        [
            "dnf", "install", "-y",
            f"https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-{fed}.noarch.rpm",
            f"https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fed}.noarch.rpm",
        ],
        emit,
    )
    return rc == 0


def _ensure_copr_repo(win: Ps5ManagerWindow, copr_slug: str, emit: Callable[[str], None]) -> bool:
    slug_pattern = copr_slug.replace("/", "*")
    if glob.glob(f"/etc/yum.repos.d/*{slug_pattern}*.repo"):
        return True
    if subprocess.run(["dnf", "copr", "--help"], capture_output=True).returncode != 0:
        win.run_cmd_pty(["dnf", "install", "-y", "dnf5-plugins" if IS_DNF5 else "dnf-plugins-core"], emit)
    rc = win.run_cmd_pty(["dnf", "copr", "enable", "-y", copr_slug], emit)
    return rc == 0


def _ensure_flathub() -> bool:
    if not shutil.which("flatpak"):
        return False
    res = subprocess.run(
        ["flatpak", "remote-add", "--system", "--if-not-exists", "flathub", FLATHUB_REPO],
        capture_output=True,
    )
    return res.returncode == 0


def _exec_software_action(
    win: Ps5ManagerWindow,
    item: SoftwareItem,
    action: str,
    forced_fmt: Optional[str] = None,
) -> None:
    def _task(emit: Callable[[str], None]) -> tuple[bool, str]:
        fmt, _ = detect_software_status(item)
        kind = item.kind
        if kind == "dual":
            target_fmt = forced_fmt or (fmt if fmt != "none" else "rpm")
            if action == "install" and fmt != "none":
                return True, f"{item.name} ({fmt})"
            if action != "install" and fmt == "none":
                return False, f"{item.name} : {T('not_installed')}"
            if target_fmt == "rpm":
                if action == "install":
                    if item.name == "Opera":
                        win.run_cmd_pty(["rpm", "--import", OPERA_KEY], emit)
                        with open(OPERA_REPO_FILE, "w", encoding="utf-8") as fh:
                            fh.write(
                                "[opera]\nname=Opera packages\ntype=rpm-md\n"
                                "baseurl=https://rpm.opera.com/rpm\ngpgcheck=1\n"
                                f"gpgkey={OPERA_KEY}\nenabled=1\n"
                            )
                    else:
                        if IS_DNF5:
                            win.run_cmd_pty(["dnf", "config-manager", "addrepo", f"--from-repofile={BRAVE_REPO}"], emit)
                        else:
                            win.run_cmd_pty(["dnf", "config-manager", "--add-repo", BRAVE_REPO], emit)
                        win.run_cmd_pty(["rpm", "--import", BRAVE_KEY], emit)
                    rc = win.run_cmd_pty(["dnf", "install", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "update":
                    rc = win.run_cmd_pty(["dnf", "upgrade", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "remove":
                    rc = win.run_cmd_pty(["dnf", "remove", "-y", item.rpm_name], emit)
                    return rc == 0, T("done") if rc == 0 else T("failed") % rc
                if action == "check":
                    res = subprocess.run(["dnf", "check-update", "-q", item.rpm_name], capture_output=True)
                    if res.returncode == 0:
                        return True, f"{item.name} : à jour (RPM)"
                    if res.returncode == 100:
                        return True, f"{item.name} : mise à jour disponible (RPM)"
                    return False, "Vérification impossible"
            else:
                kind = "flatpak"

        if kind == "rpm":
            pkgs = [item.rpm_name, *item.extra_rpms]
            if action in ("install", "update"):
                if item.rpm_name == "steam":
                    _ensure_rpmfusion(win, emit)
                if item.copr_repo and not _ensure_copr_repo(win, item.copr_repo, emit):
                    return False, f"Impossible d'activer le dépôt COPR {item.copr_repo}"
                if action == "install":
                    rc = win.run_cmd_pty(["dnf", "install", "-y", *pkgs], emit)
                    if rc == 0 and item.post_install_user_cmd:
                        win.run_cmd_pty(list(item.post_install_user_cmd), emit, as_user=True)
                else:
                    if fmt == "none":
                        return False, f"{item.name} : {T('not_installed')}"
                    rc = win.run_cmd_pty(["dnf", "upgrade", "-y", "--refresh", *pkgs], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                if fmt == "none":
                    return True, T("not_installed")
                rc = win.run_cmd_pty(["dnf", "remove", "-y", *pkgs], emit)
                if rc == 0 and item.copr_repo:
                    if win.run_cmd_pty(["dnf", "copr", "remove", "-y", item.copr_repo], emit) != 0:
                        win.run_cmd_pty(["dnf", "copr", "disable", "-y", item.copr_repo], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                if fmt == "none":
                    return True, T("not_installed")
                res = subprocess.run(["dnf", "check-update", "-q", *pkgs], capture_output=True)
                if res.returncode == 0:
                    return True, f"{item.name} : à jour"
                if res.returncode == 100:
                    return True, f"{item.name} : mise à jour disponible"
                return False, "Vérification impossible"

        if kind == "flatpak":
            if action == "install":
                if not _ensure_flathub():
                    return False, "Flathub indisponible"
                rc = win.run_cmd_pty(["flatpak", "install", "--system", "--noninteractive", "flathub", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "update":
                rc = win.run_cmd_pty(["flatpak", "update", "--system", "--noninteractive", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(["flatpak", "uninstall", "--system", "--noninteractive", item.fp_id], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                if fmt == "none":
                    return True, T("not_installed")
                res = subprocess.run(["flatpak", "remote-ls", "--system", "--updates", "flathub"], capture_output=True, text=True)
                has_upd = any(line.split()[0] == item.fp_id for line in res.stdout.splitlines() if line.strip())
                return True, f"{item.name} : {'mise à jour disponible' if has_upd else 'à jour'}"

        if kind == "decky":
            if action in ("install", "update"):
                rc = win.run_cmd_pty(f"curl -fsSL '{DECKY_INSTALL}' | bash", emit, as_user=True)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(f"curl -fsSL '{DECKY_UNINSTALL}' | bash", emit, as_user=True)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                return True, T("installed") if fmt == "installed" else T("not_installed")

        if kind == "ghrpm":
            repo = item.gh_repo or "balena-io/etcher"
            pattern = item.gh_asset_pattern or r"x86_64\.rpm$"
            if action in ("install", "update"):
                url = gh_latest_asset(repo, pattern)
                if not url:
                    return False, "RPM introuvable sur GitHub"
                rc = win.run_cmd_pty(["dnf", "install", "-y", "--setopt=localpkg_gpgcheck=0", url], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "remove":
                rc = win.run_cmd_pty(["dnf", "remove", "-y", item.rpm_name], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc
            if action == "check":
                inst = subprocess.run(["rpm", "-q", "--qf", "%{VERSION}", item.rpm_name], capture_output=True, text=True)
                if inst.returncode != 0:
                    return True, T("not_installed")
                url = gh_latest_asset(repo, pattern) or ""
                m = re.search(r"(\d+\.\d+(?:\.\d+)?)", url.rsplit("/", 1)[-1]) if url else None
                latest = m.group(1) if m else ""
                if latest and latest != inst.stdout.strip():
                    return True, f"{inst.stdout.strip()} -> {latest}"
                return True, f"{inst.stdout.strip()} (à jour)"
        return False, "Action inconnue"

    win.run_task(f"{item.name} — {T(action)}", _task, lambda *_: win._select_section("library"))


# ------------------------------------------------------------------------------
# Mise à jour automatique au lancement
# La version publiée est lue dans version.txt (quelques octets), le script est
# téléchargé seulement si une version plus récente existe, puis validé (taille,
# APP_VERSION, compilation) avant d'être installé dans /usr/local/bin.
# ------------------------------------------------------------------------------
RAW_BRANCH = "main"
MIN_SCRIPT_BYTES = 20000


def raw_base_url() -> str:
    """URL « raw » du dépôt, déduite de REPO_URL (surchargée par PS5_MANAGER_REPO)."""
    match = re.search(r"github\.com[/:]([^/]+)/([^/\s]+?)(?:\.git)?$", REPO_URL.strip())
    if not match:
        return ""
    return f"https://raw.githubusercontent.com/{match.group(1)}/{match.group(2)}/{RAW_BRANCH}"


def version_tuple(value: str) -> tuple[int, int, int]:
    """« 0.9.0 » → (0, 9, 0) : comparaison numérique, pas alphabétique."""
    numbers = [int(part) for part in re.findall(r"\d+", value or "")[:3]]
    while len(numbers) < 3:
        numbers.append(0)
    return (numbers[0], numbers[1], numbers[2])


def fetch_latest_version(timeout: float = 8.0) -> str:
    """Version publiée dans le dépôt, chaîne vide si hors ligne ou dépôt inconnu."""
    base = raw_base_url()
    if not base:
        return ""
    request = urllib.request.Request(
        f"{base}/version.txt",
        headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(64).decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError):
        return ""
    found = re.search(r"\d+\.\d+(?:\.\d+)?", raw)
    return found.group(0) if found else ""


def install_update(expected: str, timeout: float = 60.0) -> bool:
    """Télécharge le script du dépôt et l'installe dans /usr/local/bin.

    Le profil « fichier unique » est mis à jour en place ; une installation
    pilotée par git (/opt/ps5-manager) reste gérée par la page « Mise à jour du
    manager », qui fait un `reset --hard`.
    """
    base = raw_base_url()
    if not base:
        return False
    request = urllib.request.Request(
        f"{base}/ps5_manager.py",
        headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except (urllib.error.URLError, OSError, ValueError):
        return False
    if len(data) < MIN_SCRIPT_BYTES:
        return False
    found = re.search(rb'APP_VERSION = "([^"]+)"', data)
    if not found:
        return False
    downloaded = found.group(1).decode("utf-8", "replace")
    if version_tuple(downloaded) < version_tuple(expected):
        return False
    try:
        compile(data, "ps5-manager.py", "exec")  # script valide ou rien
    except SyntaxError:
        return False
    tmp_path = os.path.join(tempfile.gettempdir(), "ps5-manager-update.py")
    try:
        with open(tmp_path, "wb") as handle:
            handle.write(data)
        os.chmod(tmp_path, 0o755)
        rc = subprocess.run(
            [
                "install", "-o", "root", "-g", "root", "-m", "0755",
                tmp_path, "/usr/local/bin/ps5-manager",
            ],
            capture_output=True,
        ).returncode
        if rc != 0:
            return False
        apply_install_permissions()
        return True
    except OSError:
        return False
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def build_page_update(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("mgr_title"))

    def _do_update():
        def _task(emit):
            rc_deps = win.run_cmd_pty(["dnf", "install", "-y", *INTERFACE_DEPS], emit)
            if rc_deps != 0:
                return False, T("failed") % rc_deps
            # xhost est optionnel mais recommandé sous GNOME Wayland/Xwayland
            win.run_cmd_pty(["dnf", "install", "-y", "xhost"], emit)

            if os.path.isdir(os.path.join(INSTALL_DIR, ".git")):
                rc = win.run_cmd_pty(["git", "-C", INSTALL_DIR, "fetch", "--all", "--prune"], emit)
                if rc == 0:
                    rc = win.run_cmd_pty(["git", "-C", INSTALL_DIR, "reset", "--hard", "origin/main"], emit)
                if rc == 0:
                    # Fichiers laissés par les anciennes versions (hors suivi git)
                    win.run_cmd_pty(["git", "-C", INSTALL_DIR, "clean", "-fdx"], emit)
            else:
                # Ancienne installation non-git : on vide le dossier et on repart proprement
                if os.path.isdir(INSTALL_DIR):
                    for entry in os.listdir(INSTALL_DIR):
                        target = os.path.join(INSTALL_DIR, entry)
                        try:
                            if os.path.isdir(target) and not os.path.islink(target):
                                shutil.rmtree(target, ignore_errors=True)
                            else:
                                os.remove(target)
                        except OSError:
                            pass
                os.makedirs(INSTALL_DIR, mode=0o755, exist_ok=True)
                rc = win.run_cmd_pty(["git", "clone", REPO_URL, INSTALL_DIR], emit)
            if rc != 0:
                return False, T("failed") % rc

            # Détecte le point d'entrée GTK4 dans le dépôt cloné
            script_src = None
            for cand in ("ps5_manager.py", "ps5-manager.py"):
                cand_path = os.path.join(INSTALL_DIR, cand)
                if os.path.isfile(cand_path):
                    script_src = cand
                    break

            install_pairs = []
            if script_src:
                install_pairs.append((script_src, "/usr/local/bin/ps5-manager", "0755"))
            install_pairs.extend([
                ("ps5-manager.desktop", "/usr/share/applications/ps5-manager.desktop", "0644"),
                ("icon.png", "/usr/share/pixmaps/ps5-manager.png", "0644"),
            ])

            for src, dst, mode in install_pairs:
                p = os.path.join(INSTALL_DIR, src)
                if os.path.isfile(p):
                    rc_inst = win.run_cmd_pty(["install", "-o", "root", "-g", "root", "-m", mode, p, dst], emit)
                    if rc_inst != 0:
                        return False, T("failed") % rc_inst

            remove_legacy_install(emit)
            apply_install_permissions()
            win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)
            emit(_L("Droits (root:root, 0755/0644, Polkit GUI, SELinux) appliqués.", "Permissions (root:root, 0755/0644, Polkit GUI, SELinux) applied."))
            emit(f"{APP_NAME} {APP_VERSION} installé.")
            emit(_L("Redémarrage automatique de PS5 Fedora Manager…", "Restarting PS5 Fedora Manager…"))
            return True, T("done")

        def _on_update_done(ok: bool, _msg: str) -> None:
            if not ok:
                return
            win.toast(
                _L("Mise à jour terminée — redémarrage automatique…", "Update finished — restarting…")
            )

            def _do_restart() -> bool:
                app = win.get_application()
                if app is not None:
                    app.restart_on_exit = True  # type: ignore[attr-defined]
                if win.log_window is not None:
                    win.log_window.destroy()
                    win.log_window = None
                win.destroy()
                if app is not None:
                    app.quit()
                return False

            GLib.timeout_add(900, _do_restart)

        win.run_task(T("mgr_update"), _task, _on_update_done)

    def _do_uninstall():
        for target in (
            INSTALL_DIR,
            "/usr/local/bin/ps5-manager",
            "/usr/share/applications/ps5-manager.desktop",
            "/usr/share/pixmaps/ps5-manager.png",
            POLKIT_POLICY_PATH,
        ):
            shutil.rmtree(target, ignore_errors=True) if os.path.isdir(target) else (
                os.remove(target) if os.path.exists(target) else None
            )
        remove_legacy_install()
        win.toast(T("done"))
        GLib.timeout_add_seconds(1, lambda: win.close() or False)

    grp.add(win.row(T("mgr_update"), T("mgr_update_sub"), "software-update-available-symbolic", lambda *_: _do_update()))
    grp.add(
        win.row(
            T("mgr_uninstall"),
            T("mgr_uninstall_sub"),
            "user-trash-symbolic",
            lambda *_: win.show_confirm(T("mgr_uninstall"), T("mgr_uninstall_confirm"), _do_uninstall),
        )
    )
    page.add(grp)


def build_page_lang(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_lang"))

    def _view_packs():
        packs = subprocess.run(["rpm", "-qa", "langpacks-*", "glibc-langpack-*"], capture_output=True, text=True).stdout
        loc = subprocess.run(["localectl", "status"], capture_output=True, text=True).stdout
        win.show_text_modal(T("lang_view"), f"===== Langpacks =====\n{packs}\n===== localectl =====\n{loc}")

    def _install_lang(code: str):
        code = code.strip().split(".")[0]
        if not code:
            return
        def _task(emit):
            rc = win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{code}", f"glibc-langpack-{code}"], emit)
            if rc != 0:
                short = code.split("_")[0]
                rc = win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{short}", f"glibc-langpack-{short}"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(T("lang_install"), _task)

    grp.add(win.row(T("lang_view"), T("lang_view_sub"), "preferences-desktop-locale-symbolic", lambda *_: _view_packs()))
    grp.add(
        win.row(
            T("lang_install"),
            T("lang_install_sub"),
            "system-software-install-symbolic",
            lambda *_: win.show_prompt(T("lang_install"), T("lang_install_prompt"), "fr_FR.UTF-8", _install_lang),
        )
    )
    grp.add(win.row(T("lang_full"), T("lang_full_sub"), "preferences-system-symbolic", lambda *_: _push_full_lang_config(win)))
    page.add(grp)


def _push_full_lang_config(win: Ps5ManagerWindow) -> None:
    locales = subprocess.run(["localectl", "list-locales"], capture_output=True, text=True).stdout.splitlines() or ["fr_FR.UTF-8", "en_US.UTF-8"]
    keymaps = subprocess.run(["localectl", "list-x11-keymap-layouts"], capture_output=True, text=True).stdout.splitlines() or ["fr", "us", "de", "es"]

    sub = Adw.PreferencesPage()
    grp = pref_group(title=T("lang_full"))

    loc_row = plain_row(Adw.ComboRow, title=T("lang_pick_locale"), model=Gtk.StringList.new(sorted(set(locales))[:80]))
    kb_row = plain_row(Adw.ComboRow, title=T("lang_pick_kb"), model=Gtk.StringList.new(sorted(set(keymaps))[:80]))
    grp.add(loc_row)
    grp.add(kb_row)

    def _apply(*_):
        loc = loc_row.get_selected_item().get_string()
        kb = kb_row.get_selected_item().get_string()
        def _task(emit):
            short = loc.split(".")[0]
            win.run_cmd_pty(["dnf", "install", "-y", f"langpacks-{short}", f"glibc-langpack-{short}"], emit)
            win.run_cmd_pty(["localectl", "set-locale", f"LANG={loc}"], emit)
            win.run_cmd_pty(
                ["gdbus", "call", "--system", "--dest", "org.freedesktop.Accounts",
                 "--object-path", f"/org/freedesktop/Accounts/User{REAL_UID}",
                 "--method", "org.freedesktop.Accounts.User.SetLanguage", loc],
                emit,
            )
            if DESKTOP_ID in ("gnome", "budgie"):
                win.run_cmd_pty(
                    ["gsettings", "set", "org.gnome.system.locale", "region", loc],
                    emit,
                    as_user=True,
                )
            win.run_cmd_pty(["localectl", "set-keymap", kb], emit)
            win.run_cmd_pty(["localectl", "set-x11-keymap", kb], emit)
            return True, f"{loc} / {kb}"
        def _logout() -> None:
            cmd = logout_command()
            try:
                if cmd[0] == "loginctl":
                    subprocess.Popen(cmd)
                else:
                    subprocess.Popen(cmd, **user_subprocess_kwargs())
            except OSError as exc:
                win.show_info(T("lang_full"), str(exc))

        def _after(ok, _m):
            if ok:
                win.show_confirm(
                    T("lang_full"),
                    T("lang_logout_confirm") % (loc, kb, DESKTOP_LABEL),
                    _logout,
                    destructive=False,
                )
        win.run_task(T("lang_full"), _task, _after)

    grp.add(win.row(T("ok"), None, "object-select-symbolic", _apply))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("lang_full")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("lang_full")))


def build_page_repos(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = pref_group(title=T("sec_repos"))

    def _list_all():
        dnf_out = subprocess.run(["dnf", "repolist", "--all"], capture_output=True, text=True).stdout
        fp_sys = subprocess.run(["flatpak", "remotes", "--system"], capture_output=True, text=True).stdout if shutil.which("flatpak") else "Flatpak absent"
        fp_usr = subprocess.run(["flatpak", "remotes", "--user"], capture_output=True, text=True, **user_subprocess_kwargs()).stdout if shutil.which("flatpak") else ""
        win.show_text_modal(T("repo_list"), f"===== DNF =====\n{dnf_out}\n\n===== Flatpak (system) =====\n{fp_sys}\n\n===== Flatpak (user) =====\n{fp_usr}")

    def _install_rpmfusion_task(emit):
        ok = _ensure_rpmfusion(win, emit)
        return ok, T("done") if ok else T("failed") % 1

    def _install_flathub_task(_emit):
        ok = _ensure_flathub()
        return ok, T("done") if ok else T("failed") % 1

    g1.add(win.row(T("repo_list"), T("repo_list_sub"), "view-list-symbolic", lambda *_: _list_all()))
    g1.add(win.row(T("repo_rpmfusion"), T("repo_rpmfusion_sub"), "system-software-install-symbolic", lambda *_: win.run_task("RPM Fusion", _install_rpmfusion_task)))
    g1.add(win.row(T("repo_flathub"), T("repo_flathub_sub"), "system-software-install-symbolic", lambda *_: win.run_task("Flathub", _install_flathub_task)))
    def _enable_openh264_task(emit):
        cmd = (
            ["dnf", "config-manager", "setopt", "fedora-cisco-openh264.enabled=1"]
            if IS_DNF5
            else ["dnf", "config-manager", "--set-enabled", "fedora-cisco-openh264"]
        )
        rc = win.run_cmd_pty(cmd, emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc

    def _install_codecs_task(emit):
        if not _ensure_rpmfusion(win, emit):
            return False, T("failed") % 1
        rc = win.run_cmd_pty(
            [
                "dnf", "install", "-y",
                "gstreamer1-plugins-ugly",
                "gstreamer1-plugins-bad-free-extras",
            ],
            emit,
        )
        return rc == 0, T("done") if rc == 0 else T("failed") % rc

    g1.add(win.row(T("repo_refresh"), T("repo_refresh_sub"), "view-refresh-symbolic", lambda *_: _refresh_repos_task(win)))
    g1.add(win.row(T("repo_openh264"), T("repo_openh264_sub"), "software-update-available-symbolic", lambda *_: win.run_task(T("repo_openh264"), _enable_openh264_task)))
    g1.add(win.row(T("repo_codecs"), T("repo_codecs_sub"), "video-display-symbolic", lambda *_: win.run_task(T("repo_codecs"), _install_codecs_task)))
    g1.add(
        win.row(
            T("repo_add"),
            None,
            "list-add-symbolic",
            lambda *_: win.show_prompt(
                T("repo_add"), T("repo_add_prompt"), "https://.../example.repo",
                lambda url: win.run_task(T("repo_add"), lambda e: (
                    win.run_cmd_pty(["dnf", "config-manager", "addrepo", f"--from-repofile={url}"] if IS_DNF5 else ["dnf", "config-manager", "--add-repo", url], e) == 0,
                    T("done"),
                )) if url.strip() else None,
            ),
        )
    )
    page.add(g1)

    group = desktop_group()
    g_de = pref_group(
        title=T("repo_de_title") % DESKTOP_LABEL,
        description=T("repo_de_sub") % group,
    )
    g_de.add(
        win.row(
            T("repo_de_group"),
            f"@{group}",
            "system-software-install-symbolic",
            lambda *_: _install_desktop_group(win),
        )
    )
    page.add(g_de)

    g2 = pref_group()
    g2.add(
        win.row(
            T("repo_disable"), T("repo_disable_sub"), "action-unavailable-symbolic",
            lambda *_: win.show_prompt(
                T("repo_disable"), T("repo_id_prompt"), "rpmfusion-nonfree",
                lambda rid: win.run_task(T("repo_disable"), lambda e: (
                    win.run_cmd_pty(["dnf", "config-manager", "setopt", f"{rid}.enabled=0"] if IS_DNF5 else ["dnf", "config-manager", "--set-disabled", rid], e) == 0,
                    T("done"),
                )) if rid.strip() else None,
            ),
        )
    )
    g2.add(
        win.row(
            T("repo_rm_dnf"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("repo_rm_dnf"), T("repo_id_prompt"), "brave-browser",
                lambda rid: _remove_dnf_repo_file(win, rid.strip()),
            ),
        )
    )
    g2.add(
        win.row(
            T("repo_rm_flatpak"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("repo_rm_flatpak"), T("repo_fp_prompt"), "flathub",
                lambda rname: win.run_task(T("repo_rm_flatpak"), lambda e: (
                    win.run_cmd_pty(["flatpak", "remote-delete", "--system", rname], e) == 0
                    or win.run_cmd_pty(["flatpak", "remote-delete", "--user", rname], e, as_user=True) == 0,
                    T("done"),
                )) if rname.strip() else None,
            ),
        )
    )
    page.add(g2)


def _refresh_repos_task(win: Ps5ManagerWindow) -> None:
    def _task(emit):
        rc = win.run_cmd_pty(["bash", "-c", "dnf clean all && dnf makecache --refresh"], emit)
        if rc == 0 and shutil.which("flatpak"):
            win.run_cmd_pty(["flatpak", "update", "--appstream", "-y"], emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc
    win.run_task(T("repo_refresh"), _task)


def _remove_dnf_repo_file(win: Ps5ManagerWindow, rid: str) -> None:
    if not rid:
        return
    matches = []
    for path in glob.glob("/etc/yum.repos.d/*.repo"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                if re.search(rf"^\s*\[{re.escape(rid)}\]", fh.read(), re.MULTILINE):
                    matches.append(path)
        except OSError:
            pass
    if not matches:
        win.show_info(T("repo_rm_dnf"), T("repo_none") % rid)
        return
    def _do_rm_files():
        for p in matches:
            os.remove(p)
        win.toast(T("done"))

    win.show_confirm(
        T("repo_rm_dnf"),
        "\n".join(matches),
        _do_rm_files,
    )


def build_page_users(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_users"))

    def _list_users():
        lines = []
        try:
            with open("/etc/passwd", encoding="utf-8") as fh:
                for ln in fh:
                    parts = ln.strip().split(":")
                    if len(parts) >= 7:
                        uid = int(parts[2])
                        if 1000 <= uid < 65534:
                            lines.append(f"{parts[0]:<18} uid={uid:<6} home={parts[5]:<22} shell={parts[6]}")
        except OSError:
            pass
        win.show_text_modal(T("usr_list"), "\n".join(lines) or T("logs_none"))

    grp.add(win.row(T("usr_list"), T("usr_list_sub"), "system-users-symbolic", lambda *_: _list_users()))
    grp.add(
        win.row(
            T("usr_edit_me") % REAL_USER,
            T("usr_edit_me_sub"),
            "avatar-default-symbolic",
            lambda *_: win.show_prompt(
                T("usr_edit_me") % REAL_USER,
                T("usr_new_pass_prompt"),
                "",
                lambda pw: _set_user_password(win, REAL_USER, pw),
                password=True,
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_add"), None, "list-add-symbolic",
            lambda *_: win.show_prompt(
                T("usr_add"), T("usr_name_prompt"), "nouvel_utilisateur",
                lambda uname: win.show_prompt(
                    uname, T("usr_pass_prompt"), "",
                    lambda pw: _create_user(win, uname.strip(), pw),
                    password=True,
                ) if uname.strip() else None,
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_del"), None, "user-trash-symbolic",
            lambda *_: win.show_prompt(
                T("usr_del"), T("usr_name_prompt"), "",
                lambda uname: _delete_user(win, uname.strip()),
            ),
        )
    )
    grp.add(
        win.row(
            T("usr_root"), None, "dialog-password-symbolic",
            lambda *_: _root_status_dialog(win),
        )
    )
    page.add(grp)


def _set_user_password(win: Ps5ManagerWindow, user: str, pw: str) -> None:
    if not pw:
        return
    res = subprocess.run(["chpasswd"], input=f"{user}:{pw}\n", text=True, capture_output=True)
    if res.returncode == 0:
        win.toast(T("done"))
    else:
        win.show_info(user, res.stderr or T("failed") % res.returncode)


def _create_user(win: Ps5ManagerWindow, uname: str, pw: str) -> None:
    if not uname:
        return
    res = subprocess.run(["useradd", "-m", "-s", "/bin/bash", uname], capture_output=True, text=True)
    if res.returncode == 0:
        if pw:
            subprocess.run(["chpasswd"], input=f"{uname}:{pw}\n", text=True)
        win.toast(f"{uname} — {T('done')}")
    else:
        win.show_info(T("usr_add"), res.stderr or T("failed") % res.returncode)


def _delete_user(win: Ps5ManagerWindow, uname: str) -> None:
    if not uname or uname in ("root", REAL_USER):
        win.show_info(T("usr_del"), T("usr_refuse") % uname)
        return
    win.show_confirm(
        T("usr_del"),
        T("usr_del_confirm") % uname,
        lambda: win.run_task(T("usr_del"), lambda e: (win.run_cmd_pty(["userdel", "-r", uname], e) == 0, T("done"))),
    )


def _root_status_dialog(win: Ps5ManagerWindow) -> None:
    st = subprocess.run(["passwd", "-S", "root"], capture_output=True, text=True).stdout.strip()
    win.show_confirm(
        T("usr_root"),
        f"{st}\n\n{T('usr_new_pass_prompt')}",
        lambda: win.show_prompt(
            "Root", T("usr_pass_prompt"), "", lambda pw: _set_user_password(win, "root", pw), password=True
        ),
        destructive=False,
    )


def build_page_fedora(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_fedora"))
    grp.add(
        win.row(
            T("fed_apps"), T("fed_apps_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("fed_apps"), lambda e: (
                win.run_cmd_pty(["dnf", "upgrade", "-y"], e) == 0
                and (
                    not shutil.which("flatpak")
                    or (
                        win.run_cmd_pty(["flatpak", "update", "--system", "--noninteractive"], e) == 0
                        and win.run_cmd_pty(["flatpak", "update", "--user", "--noninteractive"], e, as_user=True) == 0
                    )
                ),
                T("done"),
            )),
        )
    )
    grp.add(
        win.row(
            T("fed_sys"), T("fed_sys_sub"), "software-update-available-symbolic",
            lambda *_: win.run_task(T("fed_sys"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "--refresh", "-y"], e) == 0, T("done"))),
        )
    )
    grp.add(
        win.row(
            T("fed_lang"), T("fed_lang_sub"), "preferences-desktop-locale-symbolic",
            lambda *_: win.run_task(T("fed_lang"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "-y", "langpacks-*", "glibc-langpack-*"], e) == 0, T("done"))),
        )
    )
    grp.add(win.row(T("fed_meta"), T("repo_refresh_sub"), "view-refresh-symbolic", lambda *_: _refresh_repos_task(win)))
    page.add(grp)


def build_page_maint(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    g1 = pref_group(title=T("sec_maint"))

    def _clean_all():
        def _task(emit):
            win.run_cmd_pty(["bash", "-c", "dnf clean all && dnf makecache >/dev/null 2>&1 || true; journalctl --vacuum-time=7d || true; rm -rf /tmp/* /var/tmp/* 2>/dev/null || true"], emit)
            thumbs = os.path.join(REAL_HOME, ".cache", "thumbnails")
            if os.path.isdir(thumbs):
                shutil.rmtree(thumbs, ignore_errors=True)
            if shutil.which("flatpak"):
                win.run_cmd_pty(["flatpak", "uninstall", "--system", "--unused", "--noninteractive"], emit)
            return True, T("done")
        win.run_task(T("mnt_all"), _task)

    g1.add(win.row(T("mnt_all"), T("mnt_all_sub"), "edit-clear-all-symbolic", lambda *_: win.show_confirm(T("mnt_all"), T("mnt_all_sub"), _clean_all)))
    g1.add(win.row(T("mnt_cache"), "dnf clean all", "edit-clear-all-symbolic", lambda *_: win.run_task(T("mnt_cache"), lambda e: (win.run_cmd_pty(["dnf", "clean", "all"], e) == 0, T("done")))))
    g1.add(win.row(T("mnt_autoremove"), "dnf autoremove -y", "user-trash-symbolic", lambda *_: win.show_confirm(T("mnt_autoremove"), "dnf autoremove -y", lambda: win.run_task(T("mnt_autoremove"), lambda e: (win.run_cmd_pty(["dnf", "autoremove", "-y"], e) == 0, T("done"))))))
    g1.add(win.row(T("mnt_journal"), "journalctl --vacuum-time=7d", "text-x-generic-symbolic", lambda *_: win.run_task(T("mnt_journal"), lambda e: (win.run_cmd_pty(["journalctl", "--vacuum-time=7d"], e) == 0, T("done")))))
    g1.add(win.row(T("mnt_tmp"), "/tmp & /var/tmp", "folder-symbolic", lambda *_: win.show_confirm(T("mnt_tmp"), "rm -rf /tmp/* /var/tmp/*", lambda: win.run_task(T("mnt_tmp"), lambda e: (win.run_cmd_pty(["bash", "-c", "rm -rf /tmp/* /var/tmp/* 2>/dev/null || true"], e) == 0, T("done"))))))
    def _clean_thumbs():
        shutil.rmtree(os.path.join(REAL_HOME, ".cache", "thumbnails"), ignore_errors=True)
        win.toast(T("done"))

    g1.add(win.row(T("mnt_thumbs"), "~/.cache/thumbnails", "image-x-generic-symbolic", lambda *_: _clean_thumbs()))
    def _desktop_db_task(emit):
        win.run_cmd_pty(["update-desktop-database", "-q", "/usr/share/applications"], emit)
        win.run_cmd_pty(
            ["update-desktop-database", "-q", os.path.join(REAL_HOME, ".local", "share", "applications")],
            emit,
            as_user=True,
        )
        return True, T("done")

    g1.add(win.row(T("mnt_desktop_db"), T("mnt_desktop_db_sub"), "view-refresh-symbolic", lambda *_: win.run_task(T("mnt_desktop_db"), _desktop_db_task)))
    g1.add(win.row(T("mnt_fonts"), "fc-cache -f", "font-x-generic-symbolic", lambda *_: win.run_task(T("mnt_fonts"), lambda e: (win.run_cmd_pty(["fc-cache", "-f"], e) == 0, T("done")))))
    g1.add(win.row(T("mnt_kernels"), None, "drive-harddisk-symbolic", lambda *_: _clean_old_kernels(win)))
    g1.add(win.row(T("mnt_disk"), "df -hT", "drive-harddisk-symbolic", lambda *_: win.show_text_modal(T("mnt_disk"), subprocess.run(["df", "-hT"], capture_output=True, text=True).stdout)))
    page.add(g1)

    if DESKTOP_ID == "kde":
        g_kde = pref_group(title=T("mnt_kde_title"), description=T("mnt_kde_sub"))

        def _kde_menu_task(emit):
            tool = _desktop_tool("kbuildsycoca6", "kbuildsycoca5")
            if not tool:
                emit(T("not_installed"))
                return False
            rc = win.run_cmd_pty([tool, "--noincremental"], emit, as_user=True)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc

        g_kde.add(
            win.row(
                T("mnt_kde_menu"),
                T("mnt_kde_menu_sub"),
                "view-refresh-symbolic",
                lambda *_: win.run_task(T("mnt_kde_menu"), _kde_menu_task),
            )
        )
        page.add(g_kde)


def _installed_kernel_packages() -> list[tuple[str, str]]:
    """Retourne [(nevra, version), ...] triés du plus récent au plus ancien."""
    res = subprocess.run(
        ["rpm", "-qa", "linux-ps5*", "kernel-core*", "--qf", "%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\t%{VERSION}\n"],
        capture_output=True, text=True,
    )
    items: list[tuple[str, str]] = []
    for line in res.stdout.splitlines():
        if "\t" in line:
            nevra, ver = line.split("\t", 1)
            items.append((nevra.strip(), ver.strip()))

    def _ver_key(ver_str: str) -> tuple:
        return tuple(int(p) if p.isdigit() else p for p in re.split(r"([0-9]+)", ver_str))

    items.sort(key=lambda it: _ver_key(it[1]), reverse=True)
    return items


def _is_protected_kernel(ver: str, cur_k: str, esp_k: str) -> bool:
    if ver == cur_k or cur_k.startswith(ver + "-") or cur_k.startswith(ver + "."):
        return True
    if esp_k and (ver == esp_k or esp_k.startswith(ver + "-") or esp_k.startswith(ver + ".")):
        return True
    return False


def _remove_kernel_package(win: Ps5ManagerWindow, nevra: str, ver: str, emit: Callable[[str], None]) -> bool:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    if _is_protected_kernel(ver, cur_k, esp_k):
        emit(f"REFUS : {nevra} est actif ({cur_k}) ou sur /boot/efi ({esp_k}).")
        return False

    rc = win.run_cmd_pty(["dnf", "remove", "-y", nevra], emit)
    if rc != 0:
        return False

    # Nettoie l'initramfs généré par dracut pour l'ancien noyau supprimé
    for initrd in glob.glob(f"/boot/initrd.img-{ver}*"):
        initrd_k = os.path.basename(initrd)[len("initrd.img-"):]
        if not _is_protected_kernel(initrd_k, cur_k, esp_k):
            try:
                os.remove(initrd)
                emit(f"Supprimé : {initrd}")
            except OSError:
                pass

    # Vérifie que /boot/efi possède toujours un noyau bootable après suppression
    target_k = esp_k if (esp_k and os.path.isfile(f"/boot/vmlinuz-{esp_k}")) else cur_k
    if not (os.path.isfile("/boot/efi/bzImage") and os.path.isfile("/boot/efi/initrd.img")):
        if os.path.isfile("/etc/kernel/postinst.d/zz-update-boot"):
            win.run_cmd_pty(["/etc/kernel/postinst.d/zz-update-boot", target_k, f"/boot/vmlinuz-{target_k}"], emit)
        elif os.path.isfile(f"/boot/vmlinuz-{target_k}") and os.path.isfile(f"/boot/initrd.img-{target_k}"):
            shutil.copy2(f"/boot/vmlinuz-{target_k}", "/boot/efi/bzImage")
            shutil.copy2(f"/boot/initrd.img-{target_k}", "/boot/efi/initrd.img")
            os.sync()
    return True


def _clean_old_kernels(win: Ps5ManagerWindow) -> None:
    pkgs = _installed_kernel_packages()
    if not pkgs:
        win.show_info(T("mnt_kernels"), T("krn_none"))
        return

    cur_k = os.uname().release
    esp_k = _esp_kernel_version()

    # Garde toujours : le noyau démarré, le noyau /boot/efi, et le plus récent
    removable: list[tuple[str, str]] = []
    kept_latest = False
    for nevra, ver in pkgs:
        if _is_protected_kernel(ver, cur_k, esp_k):
            continue
        if not kept_latest:
            kept_latest = True
            continue
        removable.append((nevra, ver))

    if not removable:
        lines = [f"• {n} ({T('krn_protected') if _is_protected_kernel(v, cur_k, esp_k) else T('krn_installed')})" for n, v in pkgs]
        win.show_info(T("mnt_kernels"), T("krn_no_old") + "\n\n" + "\n".join(lines))
        return

    summary = "\n".join(f"• {n}" for n, _v in removable)

    def _do_clean():
        def _task(emit):
            for nevra, ver in removable:
                if not _remove_kernel_package(win, nevra, ver, emit):
                    return False, f"{nevra} : {T('failed') % 1}"
            return True, T("done")
        win.run_task(T("mnt_kernels"), _task)

    win.show_confirm(
        T("mnt_kernels"),
        f"Paquets à supprimer (noyau actif {cur_k} conservé) :\n\n{summary}",
        _do_clean,
    )


def build_page_power(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_power"), description=T("pwr_env_sub") % DESKTOP_LABEL)

    sys_sleep_enabled = (
        subprocess.run(["systemctl", "is-enabled", "sleep.target"], capture_output=True, text=True).stdout.strip()
        != "masked"
    )

    info = plain_row(
        Adw.ActionRow,
        title=T("pwr_env"),
        subtitle=f"{DESKTOP_LABEL} · {T('pwr_note_' + DESKTOP_ID)}",
    )
    info.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
    grp.add(info)

    sw_sys = plain_row(Adw.SwitchRow, title=T("pwr_sys"), subtitle=T("pwr_sys_sub"))
    sw_sys.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-power-symbolic"))
    sw_sys.set_active(sys_sleep_enabled)

    def _on_sys_toggle(row, _p):
        act = "unmask" if row.get_active() else "mask"
        rc = subprocess.run(["systemctl", act, "sleep.target", "suspend.target", "hibernate.target", "hybrid-sleep.target", "suspend-then-hibernate.target"]).returncode
        win.toast(T("done") if rc == 0 else T("failed") % rc)

    sw_sys.connect("notify::active", _on_sys_toggle)
    grp.add(sw_sys)

    sw_scr = plain_row(Adw.SwitchRow, title=T("pwr_scr"), subtitle=T("pwr_scr_sub"))
    sw_scr.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
    sw_scr.set_active(screen_sleep_state())

    def _on_scr_toggle(row, _p):
        rc = run_user_commands(screen_sleep_commands(row.get_active()))
        win.toast(T("done") if rc == 0 else T("failed") % rc)

    sw_scr.connect("notify::active", _on_scr_toggle)
    grp.add(sw_scr)

    def _set_full(enable: bool):
        act = "unmask" if enable else "mask"
        rc = run_user_commands(full_sleep_commands(enable))
        sys_rc = subprocess.run(["systemctl", act, "sleep.target", "suspend.target", "hibernate.target", "hybrid-sleep.target", "suspend-then-hibernate.target"]).returncode
        if rc == 0:
            rc = sys_rc
        win._select_section("power")
        win.toast(T("done") if rc == 0 else T("failed") % rc)

    grp.add(win.row(T("pwr_enable_full"), T("pwr_full_sub"), "object-select-symbolic", lambda *_: _set_full(True)))
    grp.add(win.row(T("pwr_disable_full"), T("pwr_full_sub"), "action-unavailable-symbolic", lambda *_: _set_full(False)))
    page.add(grp)


def build_page_fan(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_fan"))

    def _svc_active(name: str) -> bool:
        return subprocess.run(["systemctl", "is-active", name], capture_output=True).returncode == 0

    sw_fan = plain_row(Adw.SwitchRow, title=T("fan_svc"), subtitle=T("fan_svc_sub"))
    sw_fan.add_prefix(Gtk.Image.new_from_icon_name("weather-windy-symbolic"))
    sw_fan.set_active(_svc_active("ps5fan.service"))
    sw_fan.connect(
        "notify::active",
        lambda r, _p: win.toast(
            T("done") if subprocess.run(["systemctl", "enable" if r.get_active() else "disable", "--now", "ps5fan.service"]).returncode == 0
            else T("failed") % 1
        ),
    )
    grp.add(sw_fan)

    sw_boost = plain_row(Adw.SwitchRow, title=T("fan_boost"), subtitle=T("fan_boost_sub"))
    sw_boost.add_prefix(Gtk.Image.new_from_icon_name("power-profile-performance-symbolic"))
    sw_boost.set_active(_svc_active("ps5boost.service"))
    sw_boost.connect(
        "notify::active",
        lambda r, _p: win.toast(
            T("done") if subprocess.run(["systemctl", "enable" if r.get_active() else "disable", "--now", "ps5boost.service"]).returncode == 0
            else T("failed") % 1
        ),
    )
    grp.add(sw_boost)

    def _show_fan_status():
        s1 = subprocess.run(["systemctl", "status", "ps5fan.service"], capture_output=True, text=True).stdout
        s2 = subprocess.run(["systemctl", "status", "ps5boost.service"], capture_output=True, text=True).stdout
        ctrl = ""
        if os.access("/usr/local/sbin/ps5_control", os.X_OK):
            ctrl = subprocess.run(["/usr/local/sbin/ps5_control", "--status"], capture_output=True, text=True).stdout
        win.show_text_modal(T("fan_status"), f"=== ps5fan.service ===\n{s1}\n\n=== ps5boost.service ===\n{s2}\n\n{ctrl}")

    grp.add(win.row(T("fan_status"), None, "utilities-system-monitor-symbolic", lambda *_: _show_fan_status()))
    grp.add(win.row(T("fan_restart"), None, "view-refresh-symbolic", lambda *_: win.toast(T("done") if subprocess.run(["systemctl", "restart", "ps5fan.service"]).returncode == 0 else T("failed") % 1)))
    grp.add(
        win.row(
            T("fan_tools"), T("fan_tools_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("fan_tools"), lambda e: (
                win.run_cmd_pty(["bash", "-c", f"tmp=$(mktemp -d) && git clone --depth=1 '{TOOLS_REPO}' \"$tmp/tools\" && cd \"$tmp/tools\" && ./install.sh && rm -rf \"$tmp\""], e) == 0,
                T("done"),
            )),
        )
    )
    page.add(grp)


def build_page_hw(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_hw"))

    def _hw_nodes():
        hwmon = subprocess.run(["ls", "-l", "/sys/class/hwmon/"], capture_output=True, text=True).stdout
        nodes = [
            "/sys/bus/platform/devices/ps5-fan/target_temp",
            "/sys/class/misc/ps5_buzzer/beep",
            "/sys/class/devfreq/ps5-gpufreq",
            "/sys/class/leds/ps5:rgb:multi_intensity",
        ]
        lines = ["===== /sys/class/hwmon/ =====", hwmon, "===== PS5 nodes ====="]
        for p in nodes:
            lines.append(f"  {'OK    ' if os.path.exists(p) else 'ABSENT'}  {p}")
        win.show_text_modal(T("hw_check"), "\n".join(lines))

    def _hwcon_check():
        local_f = os.path.join(HWCON_PREFIX, "src", "pyproject.toml")
        if not os.path.isfile(local_f):
            win.show_info(T("sec_hw"), T("not_installed"))
            return
        local_ver = ""
        with open(local_f, encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip().startswith("version"):
                    local_ver = ln.split('"')[1]
                    break
        try:
            with urllib.request.urlopen(HWCON_PYPROJECT, timeout=8) as r:
                remote_txt = r.read().decode("utf-8", errors="replace")
            remote_ver = next((ln.split('"')[1] for ln in remote_txt.splitlines() if ln.strip().startswith("version")), "")
        except (urllib.error.URLError, OSError):
            remote_ver = ""
        win.show_info(T("sec_hw"), f"Installée : {local_ver or '?'}\nGitHub : {remote_ver or '?'}")

    grp.add(win.row(T("hw_check"), T("hw_check_sub"), "applications-system-symbolic", lambda *_: _hw_nodes()))
    grp.add(
        win.row(
            T("hw_install"), T("hw_install_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("hw_install"), lambda e: (
                # Dépendance obligatoire : sans PyQt6 système, l'installation est abandonnée
                win.run_cmd_pty(["dnf", "install", "-y", "python3-PyQt6"], e) == 0
                and win.run_cmd_pty(
                    f"curl -fsSL '{HWCON_INSTALL}' | bash -s -- --passwordless", e, as_user=True
                ) == 0,
                T("done"),
            )),
        )
    )
    grp.add(win.row(T("hw_check_upd"), None, "software-update-available-symbolic", lambda *_: _hwcon_check()))
    grp.add(
        win.row(
            T("hw_uninstall"), None, "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("hw_uninstall"), T("hw_uninstall"),
                lambda: win.run_task(T("hw_uninstall"), lambda e: (
                    win.run_cmd_pty(f"curl -fsSL '{HWCON_INSTALL}' | bash -s -- --uninstall", e, as_user=True) == 0,
                    T("done"),
                )),
            ),
        )
    )
    page.add(grp)

    # Plugin Decky (mode Jeu) : dépôt NotHavocc/ps5-hwcon-plugin
    grp_plugin = pref_group(title=T("hw_plugin_group"), description=T("hw_plugin_group_sub"))
    grp_plugin.add(
        win.row(
            T("hw_plugin_install"), T("hw_plugin_install_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("hw_plugin_install"), lambda e: (
                win.run_cmd_pty(f"curl -fsSL '{HWCON_PLUGIN_INSTALL}' | bash", e, as_user=True) == 0,
                T("done"),
            )),
        )
    )
    grp_plugin.add(
        win.row(
            T("hw_plugin_uninstall"), None, "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("hw_plugin_uninstall"), T("hw_plugin_uninstall_confirm"),
                lambda: win.run_task(T("hw_plugin_uninstall"), lambda e: (
                    win.run_cmd_pty(
                        f"curl -fsSL '{HWCON_PLUGIN_INSTALL}' | bash -s -- --uninstall",
                        e, as_user=True,
                    ) == 0,
                    T("done"),
                )),
            ),
        )
    )
    page.add(grp_plugin)


def build_page_deps(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("deps_group"), description=T("deps_group_sub"))
    grp.add(
        win.row(
            T("deps_fuse"), T("deps_fuse_sub"), "application-x-addon-symbolic",
            lambda *_: win.run_task(T("deps_fuse"), lambda e: (
                win.run_cmd_pty(["dnf", "install", "-y", "fuse", "fuse-libs"], e) == 0,
                T("done"),
            )),
        )
    )
    grp.add(
        win.row(
            T("deps_steam32"), T("deps_steam32_sub"), "video-display-symbolic",
            lambda *_: win.run_task(T("deps_steam32"), lambda e: (
                win.run_cmd_pty(
                    ["dnf", "install", "-y", "mesa-vulkan-drivers.i686",
                     "mesa-dri-drivers.i686", "libva.i686"], e,
                ) == 0,
                T("done"),
            )),
        )
    )
    page.add(grp)

    def _versions(title: str, cmds: tuple[str, ...]) -> None:
        blocks = []
        for cmd in cmds:
            out = subprocess.run(
                ["bash", "-c", cmd], capture_output=True, text=True,
                **user_subprocess_kwargs(),
            )
            txt = (out.stdout or out.stderr).strip() or T("not_installed")
            blocks.append(f"$ {cmd}\n{txt}")
        win.show_text_modal(title, "\n\n".join(blocks))

    grp_py = pref_group(title=T("deps_python_group"), description=T("deps_python_group_sub"))
    grp_py.add(
        win.row(
            T("deps_python"), T("deps_python_sub"), "applications-development-symbolic",
            lambda *_: win.run_task(T("deps_python"), lambda e: (
                win.run_cmd_pty(["dnf", "install", "-y", "python3", "python3-pip"], e) == 0,
                T("done"),
            )),
        )
    )

    def _venv_task(emit: Callable[[str], None]) -> tuple[bool, str]:
        code = win.run_cmd_pty(
            "python3 -m venv my_project && . my_project/bin/activate "
            "&& python3 --version && pip3 --version",
            emit,
            as_user=True,
        )
        if code == 0:
            emit("")
            emit(T("deps_python_venv_ready") % ("~/my_project", "~/my_project"))
        return code == 0, (T("done") if code == 0 else T("failed") % code)

    grp_py.add(
        win.row(
            T("deps_python_venv"), T("deps_python_venv_sub"), "folder-new-symbolic",
            lambda *_: win.run_task(T("deps_python_venv"), _venv_task),
        )
    )
    grp_py.add(
        win.row(
            T("deps_python_versions"), T("deps_python_versions_sub"), "dialog-information-symbolic",
            lambda *_: _versions(
                T("deps_python_versions"), ("python3 --version", "pip3 --version"),
            ),
        )
    )
    grp_py.add(
        win.row(
            T("deps_tkinter"), T("deps_tkinter_sub"), "application-x-addon-symbolic",
            lambda *_: win.run_task(T("deps_tkinter"), lambda e: (
                win.run_cmd_pty(["dnf", "install", "-y", "python3-tkinter"], e) == 0,
                T("done"),
            )),
        )
    )
    page.add(grp_py)

    grp_node = pref_group(title=T("deps_node_group"), description=T("deps_node_group_sub"))
    grp_node.add(
        win.row(
            T("deps_node_install"), T("deps_node_install_sub"), "system-software-install-symbolic",
            lambda *_: win.run_task(T("deps_node_install"), lambda e: (
                win.run_cmd_pty(["dnf", "install", "-y", "nodejs", "npm"], e) == 0,
                T("done"),
            )),
        )
    )
    grp_node.add(
        win.row(
            T("deps_node_update"), T("deps_node_update_sub"), "software-update-available-symbolic",
            lambda *_: win.run_task(T("deps_node_update"), lambda e: (
                win.run_cmd_pty(["dnf", "upgrade", "-y", "--refresh", "nodejs", "npm"], e) == 0,
                T("done"),
            )),
        )
    )
    grp_node.add(
        win.row(
            T("deps_node_major"), T("deps_node_major_sub"), "software-update-available-symbolic",
            lambda *_: win.run_task(T("deps_node_major"), lambda e: (
                win.run_cmd_pty(
                    "curl -fsSL https://rpm.nodesource.com/setup_26.x | bash - "
                    "&& dnf install -y nodejs",
                    e,
                ) == 0,
                T("done"),
            )),
        )
    )
    grp_node.add(
        win.row(
            T("deps_node_versions"), T("deps_node_versions_sub"), "dialog-information-symbolic",
            lambda *_: _versions(
                T("deps_node_versions"), ("node --version", "npm --version"),
            ),
        )
    )
    grp_node.add(
        win.row(
            T("deps_node_uninstall"), None, "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("deps_node_uninstall"), T("deps_node_uninstall_confirm"),
                lambda: win.run_task(T("deps_node_uninstall"), lambda e: (
                    win.run_cmd_pty(["dnf", "remove", "-y", "nodejs", "npm"], e) == 0,
                    T("done"),
                )),
            ),
        )
    )
    page.add(grp_node)


def build_page_features(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    """Add Fedora Feature : paquets et services Fedora activés en une action."""

    def _install(
        title_key: str, packages: list[str], hint_key: Optional[str] = None
    ) -> Callable[[], None]:
        def _on_done(ok: bool, _message: str) -> None:
            if ok and hint_key:
                win.toast(T(hint_key))

        def _activate(*_args: Any) -> None:
            win.run_task(
                T(title_key),
                lambda e: (
                    win.run_cmd_pty(["dnf", "install", "-y", *packages], e) == 0,
                    T("done"),
                ),
                _on_done,
            )

        return _activate

    def _service(title_key: str, args: list[str]) -> Callable[[], None]:
        def _activate(*_args: Any) -> None:
            win.run_task(
                T(title_key),
                lambda e: (
                    win.run_cmd_pty(["systemctl", *args], e) == 0,
                    T("done"),
                ),
            )

        return _activate

    grp_mobile = pref_group(
        title=T("features_group_mobile"), description=T("features_group_mobile_sub")
    )
    grp_mobile.add(
        win.row(
            T("features_mobile_install"),
            f"{T('features_mobile_install_sub')} · {T('features_de_sub') % DESKTOP_LABEL}",
            "network-wireless-symbolic",
            _install(
                "features_mobile_install",
                mobile_feature_packages(),
                hint_key="features_mobile_done" if DESKTOP_ID == "gnome" else None,
            ),
        )
    )
    page.add(grp_mobile)

    grp_print = pref_group(
        title=T("features_group_print"), description=T("features_group_print_sub")
    )
    grp_print.add(
        win.row(
            T("features_print_install"),
            f"{T('features_print_install_sub')} · {T('features_de_sub') % DESKTOP_LABEL}",
            "system-software-install-symbolic",
            _install(
                "features_print_install",
                printer_feature_packages(),
            ),
        )
    )
    grp_print.add(
        win.row(
            T("features_print_enable"),
            T("features_print_enable_sub"),
            "system-run-symbolic",
            _service("features_print_enable", ["enable", "--now", "cups"]),
        )
    )
    grp_print.add(
        win.row(
            T("features_print_disable"),
            T("features_print_disable_sub"),
            "process-stop-symbolic",
            lambda *_: win.show_confirm(
                T("features_print_disable"),
                T("features_print_disable_confirm"),
                _service("features_print_disable", ["disable", "--now", "cups"]),
            ),
        )
    )
    grp_print.add(
        win.row(
            T("features_print_sockets"),
            T("features_print_sockets_sub"),
            "network-offline-symbolic",
            lambda *_: win.show_confirm(
                T("features_print_sockets"),
                T("features_print_sockets_confirm"),
                _service(
                    "features_print_sockets",
                    ["disable", "--now", "cups.socket", "cups.path"],
                ),
            ),
        )
    )

    def _show_status(*_args: Any) -> None:
        out = subprocess.run(
            ["systemctl", "status", "cups", "--no-pager", "--full"],
            capture_output=True,
            text=True,
        )
        txt = ((out.stdout or "") + (out.stderr or "")).strip()
        win.show_text_modal(
            T("features_print_status"), txt or T("not_installed")
        )

    grp_print.add(
        win.row(
            T("features_print_status"),
            T("features_print_status_sub"),
            "dialog-information-symbolic",
            _show_status,
        )
    )
    page.add(grp_print)


def build_page_gaming(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    def _run_script(kind: str, title: str) -> None:
        script = _gaming_script(kind)

        def task(emit: Callable[[str], None]) -> tuple[bool, str]:
            fd, path = tempfile.mkstemp(
                prefix="ps5-manager-gamescope-", suffix=".sh", dir="/tmp"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(script)
            os.chmod(path, 0o700)
            try:
                code = win.run_cmd_pty(["bash", path], emit)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
            return code == 0, (T("done") if code == 0 else T("failed") % code)

        win.run_task(title, task)

    grp = pref_group(
        title=T("gaming_group"),
        description=f"{T('gaming_group_sub')} · {DESKTOP_LABEL} / {DISPLAY_MANAGER_LABEL}",
    )
    grp.add(
        win.row(
            T("gaming_install"), T("gaming_install_sub"), "system-software-install-symbolic",
            lambda *_: _run_script("install", T("gaming_install")),
        )
    )
    grp.add(
        win.row(
            T("gaming_uninstall"), None, "user-trash-symbolic",
            lambda *_: win.show_confirm(
                T("gaming_uninstall"), T("gaming_uninstall_confirm"),
                lambda: _run_script("uninstall", T("gaming_uninstall")),
            ),
        )
    )

    def _show_session_log(*_args: Any) -> None:
        paths = ["/var/log/ps5-manager/gaming-session.log"]
        if REAL_HOME:
            paths.append(
                os.path.join(REAL_HOME, ".cache/ps5-manager/gaming-session.log")
            )
        chunks = []
        for log_path in paths:
            try:
                with open(log_path, encoding="utf-8", errors="replace") as fh:
                    chunks.append(f"{log_path}\n\n{fh.read()[-20000:]}")
            except OSError:
                continue
        win.show_text_modal(
            T("gaming_log"), "\n\n".join(chunks) or T("gaming_log_empty")
        )

    grp.add(
        win.row(
            T("gaming_log"), T("gaming_log_sub"), "text-x-generic-symbolic",
            _show_session_log,
        )
    )
    page.add(grp)


def build_page_fix(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("fix_group"), description=T("fix_group_sub"))
    grp.add(
        win.row(
            T("fix_steam"), T("fix_steam_sub"), "view-refresh-symbolic",
            lambda *_: win.show_confirm(
                T("fix_steam"), T("fix_steam_confirm"),
                lambda: win.run_task(T("fix_steam"), lambda e: (
                    win.run_cmd_pty(
                        "pkill -9 steam 2>/dev/null; nohup steam >/dev/null 2>&1 &",
                        e, as_user=True,
                    ) == 0,
                    T("done"),
                )),
            ),
        )
    )
    page.add(grp)


def build_page_mesa(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(title=T("sec_mesa"))

    def _vulkan_summary(radv_only: bool):
        if not shutil.which("vulkaninfo"):
            win.show_info(T("sec_mesa"), T("mesa_no_vulkaninfo"))
            return
        out = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True).stdout
        if radv_only:
            lines = [ln for ln in out.splitlines() if re.search(r"radv|deviceName|driverName", ln, re.I)]
            out = "\n".join(lines) or "Aucun périphérique RADV détecté."
        win.show_text_modal(T("mesa_radv") if radv_only else T("mesa_summary"), out)

    grp.add(win.row(T("mesa_tools"), T("mesa_tools_sub"), "system-software-install-symbolic", lambda *_: win.run_task(T("mesa_tools"), lambda e: (win.run_cmd_pty(["dnf", "install", "-y", "vulkan-tools", "mesa-demos"], e) == 0, T("done")))))
    grp.add(win.row(T("mesa_upd"), T("mesa_upd_sub"), "software-update-available-symbolic", lambda *_: win.run_task(T("mesa_upd"), lambda e: (win.run_cmd_pty(["dnf", "upgrade", "-y", "mesa*", "vulkan*"], e) == 0, T("done")))))
    grp.add(win.row(T("mesa_radv"), None, "video-display-symbolic", lambda *_: _vulkan_summary(True)))
    grp.add(win.row(T("mesa_summary"), None, "utilities-terminal-symbolic", lambda *_: _vulkan_summary(False)))
    page.add(grp)


def _esp_kernel_version() -> str:
    bz = "/boot/efi/bzImage"
    if not os.path.isfile(bz):
        return ""
    try:
        with open(bz, "rb") as fh:
            data = fh.read()
        m = re.search(rb"Linux version ([^\s]+)", data)
        if m:
            return m.group(1).decode("utf-8", errors="ignore")
    except OSError:
        pass
    return ""


def _install_kernel_release(win: Ps5ManagerWindow, tag: str, ver: str) -> None:
    """Télécharge et installe le RPM linux-ps5 de la release GitHub demandée."""
    if os.uname().machine != "x86_64":
        win.show_info(T("sec_kernel"), "x86_64 uniquement.")
        return
    state, asset_url = gh_tag_rpm(KERNEL_REPO, tag)
    if state == "norpm":
        win.show_info(f"Kernel {ver}", T("krn_no_rpm"))
        return
    if state == "ok" and asset_url:
        rpm_url = asset_url
        rpm_name = os.path.basename(asset_url)
    else:
        rpm_name = f"linux-ps5-{ver}-1.x86_64.rpm"
        rpm_url = f"{KERNEL_BASE}/releases/download/{tag}/{rpm_name}"

    def _do():
        def _task(emit):
            tmp_dir = "/tmp/ps5-kernel"
            os.makedirs(tmp_dir, exist_ok=True)
            local_rpm = os.path.join(tmp_dir, rpm_name)
            try:
                rc = win.run_cmd_pty(["curl", "-fL", "--retry", "3", "-o", local_rpm, rpm_url], emit)
                if rc != 0 or not os.path.isfile(local_rpm):
                    return False, T("failed") % (rc or 1)

                # Extrait le KVER exact depuis la liste des fichiers du RPM avant installation
                qlp = subprocess.run(["rpm", "-qlp", local_rpm], capture_output=True, text=True).stdout
                kver = ""
                for path in qlp.splitlines():
                    m = re.match(r"^/(?:usr/)?lib/modules/([^/]+)$", path.strip())
                    if m:
                        kver = m.group(1)
                        break

                # --replacepkgs : réinstalle une même version issue d'un autre commit
                rc = win.run_cmd_pty(
                    ["rpm", "-ivh", "--nosignature", "--replacefiles", "--replacepkgs", local_rpm],
                    emit,
                )
                if rc != 0:
                    return False, T("failed") % rc

                if not kver and os.path.isdir("/lib/modules"):
                    mod_dirs = sorted(
                        [d for d in os.listdir("/lib/modules") if os.path.isdir(os.path.join("/lib/modules", d)) and ver in d],
                        key=lambda d: os.path.getmtime(os.path.join("/lib/modules", d)),
                        reverse=True,
                    )
                    kver = mod_dirs[0] if mod_dirs else ver
                kver = kver or ver

                win.run_cmd_pty(["depmod", "-a", kver], emit)

                if not os.path.isfile(f"/boot/initrd.img-{kver}") and shutil.which("dracut"):
                    win.run_cmd_pty(["dracut", "--force", "--no-hostonly", f"/boot/initrd.img-{kver}", kver], emit)

                if os.access("/etc/kernel/postinst.d/zz-update-boot", os.X_OK):
                    win.run_cmd_pty(["/etc/kernel/postinst.d/zz-update-boot", kver, f"/boot/vmlinuz-{kver}"], emit)
                elif os.path.isdir("/boot/efi") and os.path.isfile(f"/boot/vmlinuz-{kver}"):
                    for dst in ("/boot/efi/bzImage", "/boot/efi/initrd.img"):
                        if os.path.isfile(dst):
                            shutil.copy2(dst, dst + ".old")
                    shutil.copy2(f"/boot/vmlinuz-{kver}", "/boot/efi/bzImage")
                    if os.path.isfile(f"/boot/initrd.img-{kver}"):
                        shutil.copy2(f"/boot/initrd.img-{kver}", "/boot/efi/initrd.img")
                    os.sync()

                return True, f"Kernel {kver} {T('done')}"
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        win.run_task(f"Kernel {ver}", _task, lambda *_: win._select_section("kernel"))

    win.show_confirm(
        f"Kernel {ver}",
        f"{tag}\n{rpm_name}\n\n{T('krn_install_sub')}",
        _do,
        destructive=False,
    )


def build_page_kernel(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version() or "—"
    grp = pref_group(
        title=T("sec_kernel"),
        description=f"{T('krn_running')}: {cur_k} · {T('krn_esp')}: {esp_k}",
    )

    def _check_latest():
        tag = gh_latest_tag(KERNEL_REPO)
        if not tag or not tag.startswith("kernel-"):
            win.show_info(T("sec_kernel"), T("gh_unreachable"))
            return
        ver = tag[len("kernel-"):].rsplit("-", 1)[0]
        win.show_info(T("krn_latest"), f"Tag : {tag}\nVersion : {ver}\nActuel : {cur_k}")

    def _install_latest():
        tag = gh_latest_tag(KERNEL_REPO)
        if not tag or not tag.startswith("kernel-"):
            win.show_info(T("sec_kernel"), T("gh_release_missing"))
            return
        ver = tag[len("kernel-"):].rsplit("-", 1)[0]
        _install_kernel_release(win, tag, ver)

    grp.add(win.row(T("krn_latest"), T("krn_latest_sub"), "software-update-available-symbolic", lambda *_: _check_latest()))
    grp.add(win.row(T("krn_install"), T("krn_install_sub"), "system-software-install-symbolic", lambda *_: _install_latest()))
    grp.add(win.row(T("krn_pick"), T("krn_pick_sub"), "folder-download-symbolic", lambda *_: _push_kernel_releases(win)))
    grp.add(win.row(T("krn_boot"), T("krn_boot_sub"), "media-playback-start-symbolic", lambda *_: _push_boot_kernels(win)))
    grp.add(win.row(T("krn_remove"), T("krn_remove_sub"), "user-trash-symbolic", lambda *_: _push_remove_kernels(win)))
    page.add(grp)


def _push_kernel_releases(win: Ps5ManagerWindow) -> None:
    cur_k = os.uname().release
    installed = [ver for _nevra, ver in _installed_kernel_packages()]
    sub = Adw.PreferencesPage()
    grp = pref_group(title=T("krn_pick"), description=T("krn_pick_sub"))

    tags = gh_release_tags(KERNEL_REPO, prefix="kernel-", limit=60)
    if not tags:
        grp.add(plain_row(Adw.ActionRow, title=T("krn_pick_empty")))
    for tag in tags:
        ver = tag[len("kernel-"):].rsplit("-", 1)[0]
        sha = tag.rsplit("-", 1)[-1]
        flags = []
        if cur_k.startswith(ver):
            flags.append(T("krn_running"))
        if any(v.startswith(ver) for v in installed):
            flags.append(T("krn_installed"))
        if not flags:
            flags.append(T("krn_available"))
        grp.add(
            win.row(
                f"Kernel {ver}",
                f"{sha} · " + " · ".join(flags),
                "drive-harddisk-symbolic",
                lambda _r, t=tag, v=ver: _install_kernel_release(win, t, v),
            )
        )

    grp.add(
        win.row(
            T("krn_releases_page"), f"{KERNEL_REPO}/releases", "web-browser-symbolic",
            lambda *_: open_uri(f"{KERNEL_BASE}/releases"),
        )
    )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("krn_pick")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("krn_pick")))


def _push_remove_kernels(win: Ps5ManagerWindow) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    pkgs = _installed_kernel_packages()

    sub = Adw.PreferencesPage()
    grp = pref_group(
        title=T("krn_remove"),
        description=f"{T('krn_running')}: {cur_k} · {T('krn_esp')}: {esp_k or '—'}",
    )
    if not pkgs:
        grp.add(plain_row(Adw.ActionRow, title=T("krn_none")))

    for nevra, ver in pkgs:
        protected = _is_protected_kernel(ver, cur_k, esp_k)
        status = T("krn_protected") if protected else T("krn_installed")
        if protected:
            r = win.row(nevra, status, "security-high-symbolic", None, suffix_icon=None)
        else:
            def _ask_remove(n=nevra, v=ver):
                def _task(emit):
                    ok = _remove_kernel_package(win, n, v, emit)
                    return ok, T("done") if ok else (T("failed") % 1)

                def _refresh(*_):
                    win.nav.pop()
                    _push_remove_kernels(win)

                win.show_confirm(
                    T("krn_remove"),
                    f"dnf remove -y {n}",
                    lambda: win.run_task(n, _task, _refresh),
                )
            r = win.row(nevra, status, "user-trash-symbolic", lambda _r, cb=_ask_remove: cb())
        grp.add(r)

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("krn_remove")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("krn_remove")))


def _push_boot_kernels(win: Ps5ManagerWindow) -> None:
    cur_k = os.uname().release
    esp_k = _esp_kernel_version()
    found = sorted(
        [os.path.basename(p)[len("vmlinuz-"):] for p in glob.glob("/boot/vmlinuz-*") if not os.path.basename(p).startswith("vmlinuz-0-rescue")],
        reverse=True,
    )
    sub = Adw.PreferencesPage()
    grp = pref_group(title=T("krn_boot"), description=f"{T('krn_running')}: {cur_k}")
    if not found:
        grp.add(plain_row(Adw.ActionRow, title=T("krn_boot_none")))
    for kver in found:
        flags = []
        if kver == cur_k:
            flags.append(T("krn_running"))
        if esp_k and kver == esp_k:
            flags.append(T("krn_esp"))
        if not flags:
            flags.append(T("krn_installed"))

        def _copy_kernel(ver: str):
            def _do():
                if not (os.path.isfile(f"/boot/vmlinuz-{ver}") and os.path.isfile(f"/boot/initrd.img-{ver}")):
                    win.show_info(T("sec_kernel"), T("krn_files_missing") % (ver, ver))
                    return
                for dst in ("/boot/efi/bzImage", "/boot/efi/initrd.img"):
                    if os.path.isfile(dst):
                        shutil.copy2(dst, dst + ".bak")
                shutil.copy2(f"/boot/vmlinuz-{ver}", "/boot/efi/bzImage")
                shutil.copy2(f"/boot/initrd.img-{ver}", "/boot/efi/initrd.img")
                os.sync()
                win.toast(f"{ver} -> /boot/efi")
                win.nav.pop()
                _push_boot_kernels(win)
            win.show_confirm(T("krn_boot"), f"/boot/vmlinuz-{ver} -> /boot/efi/bzImage\n/boot/initrd.img-{ver} -> /boot/efi/initrd.img", _do, destructive=False)

        grp.add(win.row(kver, " · ".join(flags), "drive-harddisk-symbolic", lambda _r, v=kver: _copy_kernel(v)))
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("krn_boot")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("krn_boot")))


def build_page_ui_lang(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    global UI_LANG
    grp = pref_group(title=T("ui_lang_title"), description=T("ui_lang_sub"))

    def _switch(code: str) -> None:
        global UI_LANG
        UI_LANG = code
        write_ui_lang(code)
        win.rebuild_ui_for_language()
        win.toast(LANG_LABELS.get(code, code))

    for code in LANG_ORDER:
        r = plain_row(Adw.ActionRow, title=LANG_LABELS[code], activatable=True)
        r.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic"))
        if code == UI_LANG:
            r.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        r.connect("activated", lambda _r, c=code: _switch(c))
        grp.add(r)
    page.add(grp)

    if DESKTOP_ID == "gnome":
        g_accent = pref_group(
            title=T("accent_label"),
            description=f"{T('follow_gnome')} ({win.theme_sync.current_accent})",
        )
        info_row = plain_row(Adw.ActionRow,
            title=T("follow_gnome"),
            subtitle=f"org.gnome.desktop.interface accent-color → {win.theme_sync.current_accent}",
        )
        info_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-color-symbolic"))
        g_accent.add(info_row)
        page.add(g_accent)


# ------------------------------------------------------------------------------
# Section IA & Développeur (Ollama + Open WebUI + VSCodium + Modèles)
# ------------------------------------------------------------------------------
AI_MODELS_CATALOG: list[tuple[str, str, str]] = [
    ("qwen2.5-coder:3b", "Code léger · recommandé CPU / PS5 (~2 Go)", "Lightweight coding · recommended for CPU / PS5 (~2 GB)"),
    ("qwen2.5-coder:7b", "Code avancé · GPU / 16 Go RAM (~4.7 Go)", "Advanced coding · GPU / 16 GB RAM (~4.7 GB)"),
    ("gemma4:e2b", "Gemma 4 ultra-léger · rapide sur CPU", "Gemma 4 ultra-light · fast on CPU"),
    ("gemma4:e4b", "Gemma 4 compact E4B · polyvalent", "Gemma 4 compact E4B · versatile"),
    ("qwen3.5:4b", "Qwen 3.5 compact 4B · usage général", "Qwen 3.5 compact 4B · general purpose"),
    ("nemotron-3.5-bolt:e4b", "Nemotron 3.5 Bolt E4B · réponses rapides", "Nemotron 3.5 Bolt E4B · fast responses"),
    ("deepseek-r1:8b", "DeepSeek R1 8B · raisonnement avancé", "DeepSeek R1 8B · advanced reasoning"),
    ("eriktonon/deepseek-v4.1-flash-1017:9b", "DeepSeek V4.1 Flash 9B · communautaire", "DeepSeek V4.1 Flash 9B · community"),
    ("mimo-v2.6:9b", "MiMo V2.6 9B · raisonnement & code", "MiMo V2.6 9B · reasoning & coding"),
    ("gemma4:12b", "Gemma 4 12B · modèle lourd (~8+ Go RAM)", "Gemma 4 12B · heavy model (~8+ GB RAM)"),
]

VSCODIUM_GPG = "https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/-/raw/master/pub.gpg"
VSCODIUM_REPO_FILE = "/etc/yum.repos.d/vscodium.repo"
VSCODIUM_REPO_CONTENT = (
    "[gitlab.com_paulcarroty_vscodium_repo]\n"
    "name=download.vscodium.com\n"
    "baseurl=https://download.vscodium.com/rpms/\n"
    "enabled=1\n"
    "gpgcheck=1\n"
    "repo_gpgcheck=1\n"
    f"gpgkey={VSCODIUM_GPG}\n"
    "metadata_expire=1h\n"
)
OPENWEBUI_IMAGE = "ghcr.io/open-webui/open-webui:main"
OPENWEBUI_ICON_URL = "https://cdn.jsdelivr.net/gh/selfhst/icons/png/open-webui.png"
OPENWEBUI_ICON_PATH = "/usr/share/pixmaps/open-webui.png"
OPENWEBUI_DESKTOP_PATH = "/usr/share/applications/open-webui.desktop"
OPENWEBUI_LAUNCHER_PATH = "/usr/local/bin/open-webui-launch"


def _ollama_bin() -> Optional[str]:
    found = shutil.which("ollama")
    if found and os.access(found, os.X_OK):
        return found
    candidates = [
        "/usr/local/bin/ollama",
        "/usr/bin/ollama",
        "/bin/ollama",
        "/opt/ollama/bin/ollama",
    ]
    if REAL_HOME and REAL_HOME != "/root":
        candidates.extend([
            os.path.join(REAL_HOME, ".local", "bin", "ollama"),
            os.path.join(REAL_HOME, "bin", "ollama"),
        ])
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _ollama_installed() -> bool:
    return _ollama_bin() is not None


def _ollama_service_exists() -> bool:
    for unit_path in (
        "/etc/systemd/system/ollama.service",
        "/usr/lib/systemd/system/ollama.service",
        "/lib/systemd/system/ollama.service",
    ):
        if os.path.isfile(unit_path):
            return True
    res = subprocess.run(
        ["systemctl", "list-unit-files", "ollama.service"],
        capture_output=True, text=True,
    )
    return "ollama.service" in (res.stdout or "")


def _ollama_version() -> str:
    bin_path = _ollama_bin()
    if not bin_path:
        return ""
    res = subprocess.run([bin_path, "--version"], capture_output=True, text=True)
    out = res.stdout.strip() or res.stderr.strip()
    if "version is" in out:
        return out.splitlines()[-1].strip()
    return out.splitlines()[0].strip() if out else ""


def _ollama_api_reachable(timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ollama_service_active() -> bool:
    if subprocess.run(["systemctl", "is-active", "--quiet", "ollama"], capture_output=True).returncode == 0:
        return True
    return _ollama_api_reachable()


def _ollama_service_enabled() -> bool:
    return subprocess.run(["systemctl", "is-enabled", "--quiet", "ollama"], capture_output=True).returncode == 0


def _format_bytes_human(num_bytes: int) -> str:
    if num_bytes <= 0:
        return ""
    gb = num_bytes / (1000 ** 3)
    if gb >= 1.0:
        return f"{gb:.1f} GB"
    mb = num_bytes / (1000 ** 2)
    return f"{mb:.0f} MB"


def _ollama_model_dirs() -> list[str]:
    dirs: list[str] = []
    env_dir = os.environ.get("OLLAMA_MODELS", "").strip()
    if env_dir:
        dirs.append(env_dir)
    for unit_glob in (
        "/etc/systemd/system/ollama.service",
        "/etc/systemd/system/ollama.service.d/*.conf",
    ):
        for p in glob.glob(unit_glob):
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        m = re.search(r"OLLAMA_MODELS=[\"']?([^\"'\s]+)", line)
                        if m:
                            dirs.append(m.group(1))
            except OSError:
                pass
    dirs.extend([
        "/usr/share/ollama/.ollama/models",
        "/var/lib/ollama/.ollama/models",
        "/var/lib/ollama/models",
        os.path.join(REAL_HOME, ".ollama", "models"),
        "/root/.ollama/models",
    ])
    unique: list[str] = []
    for d in dirs:
        if d and d not in unique and os.path.isdir(d):
            unique.append(d)
    return unique


def _scan_ollama_manifests_on_disk() -> dict[str, str]:
    """Scanne les manifests locaux d'Ollama même lorsque ollama.service est arrêté."""
    models: dict[str, str] = {}
    for base_dir in _ollama_model_dirs():
        manifests_root = os.path.join(base_dir, "manifests")
        if not os.path.isdir(manifests_root):
            continue
        for root_dir, _dirs, files in os.walk(manifests_root):
            for fname in files:
                fpath = os.path.join(root_dir, fname)
                rel = os.path.relpath(fpath, manifests_root)
                parts = rel.split(os.sep)
                if len(parts) < 4:
                    continue
                registry, namespace, model = parts[0], parts[1], "/".join(parts[2:-1])
                tag = parts[-1]
                if registry == "registry.ollama.ai" and namespace == "library":
                    model_name = f"{model}:{tag}"
                elif registry == "registry.ollama.ai":
                    model_name = f"{namespace}/{model}:{tag}"
                else:
                    model_name = f"{registry}/{namespace}/{model}:{tag}"
                size_bytes = 0
                try:
                    with open(fpath, encoding="utf-8") as fh:
                        data = json.load(fh)
                    cfg = data.get("config") or {}
                    if isinstance(cfg, dict):
                        size_bytes += int(cfg.get("size") or 0)
                    for layer in data.get("layers") or []:
                        if isinstance(layer, dict):
                            size_bytes += int(layer.get("size") or 0)
                except (OSError, ValueError, TypeError):
                    pass
                models.setdefault(model_name, _format_bytes_human(size_bytes))
    return models


def _ollama_installed_models() -> dict[str, str]:
    """Retourne {nom_modele: taille} via `ollama list` et repli disque si le daemon est arrêté."""
    models: dict[str, str] = {}
    bin_path = _ollama_bin()
    if bin_path:
        env = dict(os.environ)
        env.setdefault("OLLAMA_HOST", "127.0.0.1:11434")
        try:
            res = subprocess.run([bin_path, "list"], capture_output=True, text=True, env=env, timeout=3)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4:
                        models[parts[0]] = f"{parts[2]} {parts[3]}"
                    elif parts:
                        models[parts[0]] = ""
        except (OSError, subprocess.SubprocessError):
            pass
    for name, sz in _scan_ollama_manifests_on_disk().items():
        if name not in models:
            models[name] = sz
    return models


def _ollama_running_models() -> set[str]:
    bin_path = _ollama_bin()
    if not bin_path:
        return set()
    try:
        res = subprocess.run([bin_path, "ps"], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return set()
    if res.returncode != 0:
        return set()
    running: set[str] = set()
    for line in res.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            running.add(parts[0])
    return running


def _podman_bin() -> Optional[str]:
    found = shutil.which("podman")
    if found and os.access(found, os.X_OK):
        return found
    for cand in ("/usr/bin/podman", "/usr/local/bin/podman"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _podman_run(args: list[str], owner: str = "user", timeout: int = 12) -> subprocess.CompletedProcess[str]:
    podman = _podman_bin() or "podman"
    kw = user_subprocess_kwargs() if owner == "user" else {}
    return subprocess.run([podman, *args], capture_output=True, text=True, timeout=timeout, **kw)


def _parse_podman_ps_for_openwebui(stdout: str) -> Optional[str]:
    for line in stdout.splitlines():
        parts = line.strip().split("\t", 1)
        if len(parts) < 2:
            continue
        name = parts[0].strip().lstrip("/")
        state = parts[1].strip().lower()
        if name == "open-webui":
            if state.startswith("up"):
                return "running"
            return state
    return None


def _podman_webui_context() -> tuple[str, str]:
    """Retourne (état, propriétaire 'user'|'root')."""
    podman = _podman_bin()
    if not podman:
        return "no_podman", "user"
    contexts = ["user", "root"] if REAL_USER != "root" else ["root"]
    for ctx in contexts:
        try:
            res_ps = _podman_run(["ps", "-a", "--format", "{{.Names}}\t{{.State}}"], owner=ctx, timeout=12)
            if res_ps.returncode == 0:
                st = _parse_podman_ps_for_openwebui(res_ps.stdout)
                if st:
                    return st, ctx
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            res_ins = _podman_run(["inspect", "-f", "{{.State.Status}}", "open-webui"], owner=ctx, timeout=12)
            if res_ins.returncode == 0 and res_ins.stdout.strip():
                return res_ins.stdout.strip().lower(), ctx
        except (OSError, subprocess.SubprocessError):
            pass
    return "missing", "user"


def _podman_webui_state() -> str:
    """Retourne 'running', 'exited'/'stopped', 'missing', ou 'no_podman'."""
    return _podman_webui_context()[0]


def _vscodium_installed() -> bool:
    return subprocess.run(["rpm", "-q", "codium"], capture_output=True).returncode == 0


FREEBUFF_PACKAGE = "freebuff"
# Terminaux essayés pour « Lancer Freebuff » (l'agent est une TUI : il lui faut
# un vrai terminal, pas le journal de l'application).
FREEBUFF_TERMINALS: tuple[tuple[str, list[str]], ...] = (
    ("ptyxis", ["--"]),
    ("kgx", ["--"]),
    ("gnome-terminal", ["--"]),
    ("konsole", ["-e"]),
    ("xfce4-terminal", ["-x"]),
    ("mate-terminal", ["-x"]),
    ("tilix", ["-e"]),
    ("xterm", ["-e"]),
)


def _npm_bin() -> Optional[str]:
    found = shutil.which("npm")
    if found and os.access(found, os.X_OK):
        return found
    for cand in ("/usr/local/bin/npm", "/usr/bin/npm", "/bin/npm"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _freebuff_bin() -> Optional[str]:
    found = shutil.which("freebuff")
    if found and os.access(found, os.X_OK):
        return found
    candidates = ["/usr/local/bin/freebuff", "/usr/bin/freebuff"]
    if REAL_HOME:
        candidates.append(os.path.join(REAL_HOME, ".npm-global", "bin", "freebuff"))
        candidates.append(os.path.join(REAL_HOME, ".local", "bin", "freebuff"))
    for cand in candidates:
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _freebuff_version() -> str:
    """Version du paquet npm global freebuff (chaîne vide s'il est absent)."""
    roots: list[str] = []
    prefix = os.environ.get("npm_config_prefix", "").strip()
    if prefix:
        roots.append(os.path.join(prefix, "lib", "node_modules"))
    roots.extend(["/usr/local/lib/node_modules", "/usr/lib/node_modules"])
    if REAL_HOME:
        roots.append(os.path.join(REAL_HOME, ".npm-global", "lib", "node_modules"))
        roots.append(os.path.join(REAL_HOME, ".local", "lib", "node_modules"))
    for root in roots:
        pkg = os.path.join(root, FREEBUFF_PACKAGE, "package.json")
        if not os.path.isfile(pkg):
            continue
        try:
            with open(pkg, encoding="utf-8") as fh:
                return str(json.load(fh).get("version") or "")
        except (OSError, ValueError):
            continue
    return ""


def _freebuff_installed() -> bool:
    return bool(_freebuff_version()) or _freebuff_bin() is not None


def _ensure_npm_ready(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    if _npm_bin():
        return True
    emit(_L("Node.js et npm sont requis pour Freebuff : installation…",
            "Node.js and npm are required for Freebuff: installing…"))
    if win.run_cmd_pty(["dnf", "install", "-y", "nodejs", "npm"], emit) != 0:
        return False
    return _npm_bin() is not None


def _launch_freebuff() -> bool:
    """Ouvre freebuff dans le premier terminal disponible de la session."""
    return _launch_in_terminal("freebuff")


def _ensure_vscodium_repo(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    rc = win.run_cmd_pty(["rpmkeys", "--import", VSCODIUM_GPG], emit)
    if rc != 0:
        return False
    try:
        with open(VSCODIUM_REPO_FILE, "w", encoding="utf-8") as fh:
            fh.write(VSCODIUM_REPO_CONTENT)
        os.chmod(VSCODIUM_REPO_FILE, 0o644)
        os.chown(VSCODIUM_REPO_FILE, 0, 0)
        return True
    except OSError as exc:
        emit(f"Erreur écriture {VSCODIUM_REPO_FILE} : {exc}")
        return False


def _ensure_ollama_ready(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    if not _ollama_installed():
        emit(_L("Ollama non détecté — installation avec pciutils…", "Ollama not detected — installing with pciutils…"))
        if win.run_cmd_pty(["dnf", "install", "-y", "pciutils"], emit) != 0:
            return False
        if win.run_cmd_pty("curl -fsSL https://ollama.com/install.sh | sh", emit) != 0:
            return False
    if not _ollama_service_active() and _ollama_service_exists():
        win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
    return _ollama_installed()


def _create_openwebui_container(win: Ps5ManagerWindow, emit: Callable[[str], None], owner: str = "user") -> int:
    podman = _podman_bin() or "podman"
    return win.run_cmd_pty(
        [
            podman, "run", "-d", "--network=host",
            "-v", "open-webui:/app/backend/data",
            "-e", "OLLAMA_BASE_URL=http://127.0.0.1:11434",
            "--name", "open-webui",
            "--restart", "always",
            OPENWEBUI_IMAGE,
        ],
        emit,
        as_user=(owner == "user"),
    )


def _run_quick_service_action(
    win: Ps5ManagerWindow,
    title: str,
    fn: Callable[[], tuple[bool, str]],
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    if win.busy:
        win.toast(T("busy"))
        return
    win.busy = True
    win.busy_spinner.start()
    win.logger.write_line(f"──── {title}")

    def _worker() -> None:
        ok = False
        msg = ""
        try:
            ok, msg = fn()
        except Exception as exc:
            ok = False
            msg = str(exc)
        win.logger.write_line(f"──── fin : {title} ({'OK' if ok else 'ERR'}) {msg}")

        def _finish() -> bool:
            win.busy = False
            win.busy_spinner.stop()
            if ok:
                win.toast(f"{title} — {T('done')}")
            else:
                win.show_info(title, msg or T("failed") % 1)
            if on_done:
                on_done()
            return False

        GLib.idle_add(_finish)

    threading.Thread(target=_worker, daemon=True).start()


_AIDEV_STATE: dict[str, Any] = {}
_AIDEV_STATE_AT = 0.0
_AIDEV_LOADING = False
AIDEV_STATE_TTL = 30.0


def _aidev_state(win: "Ps5ManagerWindow") -> dict[str, Any]:
    """État Podman / Ollama sans bloquer le rendu de la page IA.

    Le premier rendu utilise des valeurs provisoires et lance la collecte dans
    un thread ; la section est reconstruite une fois les données prêtes (cache
    30 s) pour éviter tout gel à l'ouverture.
    """
    global _AIDEV_LOADING, _AIDEV_STATE_AT
    fresh = _AIDEV_STATE and (time.monotonic() - _AIDEV_STATE_AT) < AIDEV_STATE_TTL
    if fresh:
        return _AIDEV_STATE
    if not _AIDEV_LOADING:
        _AIDEV_LOADING = True

        def _after() -> bool:
            # Ne reconstruit que si la page IA est affichée à la racine :
            # sinon on arracherait l'utilisateur d'une sous-page ouverte.
            try:
                depth = win.nav.get_navigation_stack().get_n_items()
            except Exception:  # noqa: BLE001
                depth = 1
            if win.active_section == "aidev" and depth <= 1:
                win._select_section("aidev")
            return False

        def _worker() -> None:
            global _AIDEV_LOADING, _AIDEV_STATE_AT
            try:
                data = {
                    "webui": _podman_webui_context(),
                    "models": _ollama_installed_models(),
                }
            except Exception:  # noqa: BLE001 - jamais bloquant
                data = {"webui": ("", ""), "models": {}}
            _AIDEV_STATE.update(data)
            _AIDEV_STATE_AT = time.monotonic()
            _AIDEV_LOADING = False
            GLib.idle_add(_after)

        threading.Thread(target=_worker, daemon=True).start()
    return _AIDEV_STATE or {"webui": ("loading", ""), "models": {}}


def build_page_aidev(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    ollama_ok = _ollama_installed()
    ollama_svc = _ollama_service_exists()
    ollama_act = _ollama_service_active() if (ollama_ok or ollama_svc) else False
    ollama_boot = _ollama_service_enabled() if ollama_svc else False
    ai_state = _aidev_state(win)
    webui_st, webui_owner = ai_state["webui"]
    codium_ok = _vscodium_installed()
    freebuff_ok = _freebuff_installed()
    freebuff_ver = _freebuff_version() if freebuff_ok else ""
    installed_models = ai_state["models"]

    # 1) Outils & Applications IA / Dev
    g_tools = pref_group(title=T("aidev_stack"), description=T("aidev_stack_sub"))

    if ollama_ok:
        ver_str = _ollama_version() or "Ollama"
        ollama_sub = f"{ver_str} · {'actif' if ollama_act else 'arrêté'}"
    elif ollama_svc:
        ollama_sub = f"Service détecté · {'actif' if ollama_act else 'arrêté'}"
    else:
        ollama_sub = "pciutils + script officiel ollama.com"
    g_tools.add(
        win.row(
            "Ollama (moteur IA local)",
            ollama_sub,
            "utilities-terminal-symbolic",
            lambda *_: _push_ollama_actions(win),
        )
    )

    owner_tag = "Podman root" if webui_owner == "root" else "Podman"
    webui_labels = {
        "loading": "…",
        "running": f"Actif ({owner_tag}) · http://127.0.0.1:8080",
        "exited": f"Installé (arrêté) · {owner_tag}",
        "stopped": f"Installé (arrêté) · {owner_tag}",
        "created": f"Installé (arrêté) · {owner_tag}",
        "paused": f"En pause · {owner_tag}",
        "missing": "Non installé · Podman ghcr.io/open-webui",
        "no_podman": "Podman absent (sera installé automatiquement)",
    }
    g_tools.add(
        win.row(
            "Open WebUI (interface web IA)",
            webui_labels.get(webui_st, webui_st),
            "web-browser-symbolic",
            lambda *_: _push_webui_actions(win),
        )
    )

    g_tools.add(
        win.row(
            _L("VSCodium (éditeur de code libre)", "VSCodium (free code editor)"),
            T("installed_rpm") if codium_ok else f"{T('not_installed')} · dépôt officiel RPM",
            "applications-development-symbolic",
            lambda *_: _push_vscodium_actions(win),
        )
    )

    if freebuff_ver:
        freebuff_sub = f"{freebuff_ver} · npm (global)"
    elif freebuff_ok:
        freebuff_sub = _L("Installé (binaire détecté)", "Installed (binary found)")
    else:
        freebuff_sub = _L("Non installé · npm install -g freebuff",
                          "Not installed · npm install -g freebuff")
    g_tools.add(
        win.row(
            _L("Freebuff (agent de code IA)", "Freebuff (AI coding agent)"),
            freebuff_sub,
            "utilities-terminal-symbolic",
            lambda *_: _push_freebuff_actions(win),
        )
    )
    page.add(g_tools)

    # 2) Contrôle des services IA
    g_srv = pref_group(title=T("aidev_services"), description=T("aidev_services_sub"))

    sw_ollama = plain_row(Adw.SwitchRow,
        title="Service Ollama (ollama.service)",
        subtitle=(
            _L("Démarrer / arrêter le serveur IA (port 11434)", "Start / stop local AI server (port 11434)")
        ),
    )
    sw_ollama.add_prefix(Gtk.Image.new_from_icon_name("system-run-symbolic"))
    sw_ollama.set_active(ollama_act)
    sw_ollama.set_sensitive(ollama_ok or ollama_svc)

    def _toggle_ollama(r, _p):
        act = "start" if r.get_active() else "stop"

        def _do():
            if not _ollama_service_exists():
                return False, "L'unité systemd ollama.service est introuvable. Réinstallez ou mettez à jour Ollama."
            res = subprocess.run(["systemctl", act, "ollama"], capture_output=True, text=True)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or f"code {res.returncode}").strip()
                return False, f"systemctl {act} ollama :\n{err}"
            if act == "start":
                import time
                for _ in range(10):
                    if _ollama_api_reachable(timeout=0.5):
                        break
                    time.sleep(0.4)
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Ollama ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_ollama.connect("notify::active", _toggle_ollama)
    g_srv.add(sw_ollama)

    sw_boot = plain_row(Adw.SwitchRow,
        title=(
            _L("Démarrage automatique Ollama au boot", "Start Ollama automatically at boot")
        ),
        subtitle="systemctl enable / disable ollama",
    )
    sw_boot.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-time-symbolic"))
    sw_boot.set_active(ollama_boot)
    sw_boot.set_sensitive(ollama_svc)

    def _toggle_ollama_boot(r, _p):
        act = "enable" if r.get_active() else "disable"

        def _do():
            res = subprocess.run(["systemctl", act, "ollama"], capture_output=True, text=True)
            if res.returncode != 0:
                return False, (res.stderr or res.stdout or f"code {res.returncode}").strip()
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Ollama boot ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_boot.connect("notify::active", _toggle_ollama_boot)
    g_srv.add(sw_boot)

    sw_webui = plain_row(Adw.SwitchRow,
        title="Conteneur Open WebUI (Podman)",
        subtitle="podman start / stop open-webui",
    )
    sw_webui.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))
    sw_webui.set_active(webui_st == "running")
    sw_webui.set_sensitive(webui_st not in ("missing", "no_podman"))

    def _toggle_webui(r, _p):
        act = "start" if r.get_active() else "stop"

        def _do():
            res = _podman_run([act, "open-webui"], owner=webui_owner, timeout=30)
            if res.returncode != 0:
                err = (res.stderr or res.stdout or f"code {res.returncode}").strip()
                return False, f"podman {act} open-webui ({webui_owner}) :\n{err}"
            return True, T("done")

        _run_quick_service_action(
            win,
            f"Open WebUI ({act})",
            _do,
            lambda: win._select_section("aidev"),
        )

    sw_webui.connect("notify::active", _toggle_webui)
    g_srv.add(sw_webui)

    def _start_all():
        def _task(emit):
            did_any = False
            rc1 = 0
            rc2 = 0
            if _ollama_service_exists() or _ollama_installed():
                did_any = True
                rc1 = win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
            else:
                emit(_L("Ollama non détecté sur ce système.", "Ollama not detected on this system."))

            st_now, owner_now = _podman_webui_context()
            podman = _podman_bin()
            if st_now not in ("missing", "no_podman") and podman:
                did_any = True
                rc2 = win.run_cmd_pty([podman, "start", "open-webui"], emit, as_user=(owner_now == "user"))
            elif podman:
                # Affiche le diagnostic podman ps -a dans le journal pour transparence
                try:
                    diag = _podman_run(["ps", "-a"], owner="user", timeout=10)
                    emit(f"podman ps -a ({REAL_USER}) rc={diag.returncode}: {(diag.stdout or diag.stderr).strip()}")
                except Exception as exc:
                    emit(f"Erreur podman ps -a : {exc}")
                emit(_L("Conteneur Podman open-webui non détecté.", "open-webui Podman container not detected."))
            else:
                emit(_L("Podman non installé.", "Podman not installed."))

            if not did_any:
                return False, "Aucun service Ollama ou Open WebUI détecté."
            ok = rc1 == 0 and rc2 == 0
            return ok, T("done") if ok else T("failed") % (rc1 or rc2)
        win.run_task("Démarrer Ollama + Open WebUI", _task, lambda *_: win._select_section("aidev"))

    def _stop_all():
        def _task(emit):
            did_any = False
            st_now, owner_now = _podman_webui_context()
            if st_now == "running":
                did_any = True
                podman = _podman_bin() or "podman"
                win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=(owner_now == "user"))
            if _ollama_service_exists() or _ollama_service_active():
                did_any = True
                win.run_cmd_pty(["systemctl", "stop", "ollama"], emit)
            if not did_any:
                return False, "Aucun service actif détecté."
            return True, T("done")
        win.run_task("Arrêter Ollama + Open WebUI", _task, lambda *_: win._select_section("aidev"))

    g_srv.add(
        win.row(
            _L("Tout démarrer (Ollama + Open WebUI)", "Start all (Ollama + Open WebUI)"),
            "systemctl start ollama && podman start open-webui",
            "media-playback-start-symbolic",
            lambda *_: _start_all(),
        )
    )
    g_srv.add(
        win.row(
            _L("Tout arrêter (libérer la RAM)", "Stop all (free RAM)"),
            "podman stop open-webui && systemctl stop ollama",
            "media-playback-stop-symbolic",
            lambda *_: _stop_all(),
        )
    )

    def _open_webui_browser():
        if os.access(OPENWEBUI_LAUNCHER_PATH, os.X_OK) and webui_owner == "user":
            subprocess.Popen([OPENWEBUI_LAUNCHER_PATH], **user_subprocess_kwargs())
            return
        st_now, _ = _podman_webui_context()
        if st_now == "running":
            subprocess.Popen(["xdg-open", "http://127.0.0.1:8080"], **user_subprocess_kwargs())
        else:
            win.show_info("Open WebUI", _L("Démarrez d'abord le conteneur Open WebUI.", "Start the Open WebUI container first."))

    def _show_podman_ps():
        if not _podman_bin():
            win.show_info("Podman", T("ai_podman_absent"))
            return
        chunks: list[str] = []
        try:
            r_usr = _podman_run(["ps", "-a"], owner="user", timeout=12)
            txt_usr = "\n".join(p for p in (r_usr.stdout.strip(), r_usr.stderr.strip()) if p) or "(vide)"
            chunks.append(f"=== podman ps -a ({REAL_USER}) [rc={r_usr.returncode}] ===\n{txt_usr}")
        except Exception as exc:
            chunks.append(f"=== podman ps -a ({REAL_USER}) ===\nErreur : {exc}")
        if REAL_USER != "root":
            try:
                r_rt = _podman_run(["ps", "-a"], owner="root", timeout=12)
                txt_rt = "\n".join(p for p in (r_rt.stdout.strip(), r_rt.stderr.strip()) if p)
                if txt_rt:
                    chunks.append(f"\n=== podman ps -a (root) ===\n{txt_rt}")
            except Exception:
                pass
        win.show_text_modal("podman ps -a", "\n".join(chunks))

    def _show_webui_logs():
        if not _podman_bin():
            win.show_info("Open WebUI", T("ai_podman_absent"))
            return
        st_now, owner_now = _podman_webui_context()
        if st_now in ("missing", "no_podman"):
            try:
                r_diag = _podman_run(["ps", "-a"], owner="user", timeout=10)
                diag = (r_diag.stderr or r_diag.stdout or "").strip()
            except Exception as exc:
                diag = str(exc)
            detail = f"\n\nDiagnostic :\n{diag}" if diag else ""
            win.show_info("Open WebUI", f"Conteneur open-webui introuvable.{detail}")
            return
        podman = _podman_bin() or "podman"
        kw = user_subprocess_kwargs() if owner_now == "user" else {}
        try:
            res = subprocess.run(
                [podman, "logs", "--tail", "30", "open-webui"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=12, **kw,
            )
            out = strip_ansi(res.stdout or "").strip() or "(aucun log)"
            win.show_text_modal("podman logs --tail 30 open-webui", out)
        except Exception as exc:
            win.show_info("podman logs --tail 30 open-webui", f"Erreur : {exc}")

    g_srv.add(
        win.row(
            _L("Ouvrir Open WebUI dans le navigateur", "Open Open WebUI in browser"),
            "http://127.0.0.1:8080",
            "web-browser-symbolic",
            lambda *_: _open_webui_browser(),
        )
    )
    g_srv.add(
        win.row(
            _L("État des conteneurs Podman (podman ps -a)", "Podman containers status (podman ps -a)"),
            _L("Vérifie l'état exact de open-webui", "Check open-webui's exact state"),
            "view-list-symbolic",
            lambda *_: _show_podman_ps(),
        )
    )
    g_srv.add(
        win.row(
            _L("Logs Open WebUI (podman logs --tail 30)", "Open WebUI logs (podman logs --tail 30)"),
            _L("Affiche les 30 dernières lignes du conteneur open-webui", "Show the last 30 lines of the open-webui container"),
            "utilities-terminal-symbolic",
            lambda *_: _show_webui_logs(),
        )
    )
    page.add(g_srv)

    # 3) Modèles IA locaux
    g_mod = pref_group(title=T("aidev_models"), description=T("aidev_models_sub"))
    if installed_models:
        preview = ", ".join(list(installed_models.keys())[:4])
        if len(installed_models) > 4:
            preview += f" (+{len(installed_models) - 4})"
        models_sub = f"{len(installed_models)} installé(s) : {preview}"
    else:
        models_sub = "0 installé · qwen2.5-coder, deepseek, gemma4, mimo, nemotron…"
    g_mod.add(
        win.row(
            _L("Gérer les modèles IA (catalogue & installés)", "Manage AI models (catalog & installed)"),
            models_sub,
            "folder-download-symbolic",
            lambda *_: _push_ai_models(win),
        )
    )

    def _show_ollama_list():
        bin_path = _ollama_bin()
        if not bin_path and not installed_models:
            win.show_info("Ollama", T("ai_ollama_absent"))
            return
        out = ""
        if bin_path:
            res = subprocess.run([bin_path, "list"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                out = res.stdout.strip()
        if not out:
            disk_models = _ollama_installed_models()
            if disk_models:
                lines = ["(Service Ollama arrêté — modèles détectés sur le disque)", "", f"{'NOM':42} {'TAILLE':12}"]
                for m_name, m_size in sorted(disk_models.items()):
                    lines.append(f"{m_name:42} {m_size or '-'}")
                out = "\n".join(lines)
            else:
                out = "(aucun modèle)"
        win.show_text_modal("ollama list", out)

    def _show_ollama_ps():
        bin_path = _ollama_bin()
        if not bin_path:
            win.show_info("Ollama", T("ai_ollama_absent"))
            return
        res = subprocess.run([bin_path, "ps"], capture_output=True, text=True)
        out = (res.stdout or res.stderr or "").strip() or "(aucun modèle actif)"
        win.show_text_modal("ollama ps", out)

    g_mod.add(
        win.row(
            _L("Voir les modèles installés (ollama list)", "List installed models (ollama list)"),
            None,
            "view-list-symbolic",
            lambda *_: _show_ollama_list(),
        )
    )
    g_mod.add(
        win.row(
            _L("Modèles actifs en RAM (ollama ps)", "Active models in RAM (ollama ps)"),
            _L("Affiche les modèles actuellement chargés en mémoire", "Show the models currently loaded in memory"),
            "utilities-system-monitor-symbolic",
            lambda *_: _show_ollama_ps(),
        )
    )
    page.add(g_mod)

    # 4) Propositions utiles pour PS5 Linux
    g_ext = pref_group(title=T("aidev_extras"), description=T("aidev_extras_sub"))

    def _hw_ai_diag():
        cmd = (
            "echo '=== Mémoire RAM / Swap (PS5 unifiée 16 Go) ==='; free -h; "
            "echo ''; echo '=== Processeur ==='; lscpu | grep -E 'Model name|CPU\\(s\\)|Thread'; "
            "echo ''; echo '=== GPU / PCI (pciutils) ==='; lspci | grep -iE 'vga|display|amd' || true; "
            "echo ''; echo '=== Espace disque modèles ==='; df -h / /var /usr/share/ollama 2>/dev/null || df -h /"
        )
        out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True).stdout
        win.show_text_modal(_L("Diagnostic matériel IA (PS5)", "AI hardware diagnostics (PS5)"), out)

    g_ext.add(
        win.row(
            _L("Diagnostic RAM / GPU / Disque pour l'IA", "AI RAM / GPU / Disk diagnostic"),
            _L("Vérifie la mémoire libre avant d'exécuter un modèle 7B / 9B / 12B", "Check free memory before running a 7B / 9B / 12B model"),
            "applications-system-symbolic",
            lambda *_: _hw_ai_diag(),
        )
    )
    g_ext.add(
        win.row(
            _L("Nettoyer les anciennes images Podman", "Prune unused Podman images"),
            _L("podman image prune -f (libère l'espace après mise à jour Open WebUI)", "podman image prune -f (frees space after updating Open WebUI)"),
            "edit-clear-all-symbolic",
            lambda *_: win.run_task(
                "Podman prune",
                lambda e: (win.run_cmd_pty([_podman_bin() or "podman", "image", "prune", "-f"], e, as_user=(webui_owner == "user")) == 0, T("done")),
            ),
        )
    )
    if REAL_USER != "root":
        g_ext.add(
            win.row(
                T("podman_linger") % REAL_USER,
                T("podman_linger_sub") % REAL_USER,
                "user-available-symbolic",
                lambda *_: win.run_task(
                    "loginctl enable-linger",
                    lambda e: (win.run_cmd_pty(["loginctl", "enable-linger", REAL_USER], e) == 0, T("done")),
                ),
            )
        )
    page.add(g_ext)


def _install_openwebui_desktop_entry(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> bool:
    """Télécharge l'icône Open WebUI localement dans Fedora et crée le lanceur GNOME."""
    rc_icon = win.run_cmd_pty(
        ["curl", "-fL", "--retry", "3", "-o", OPENWEBUI_ICON_PATH, OPENWEBUI_ICON_URL],
        emit,
    )
    if rc_icon == 0 and os.path.isfile(OPENWEBUI_ICON_PATH):
        try:
            os.chmod(OPENWEBUI_ICON_PATH, 0o644)
            os.chown(OPENWEBUI_ICON_PATH, 0, 0)
        except OSError:
            pass
    else:
        emit(_L("Avertissement : impossible de télécharger open-webui.png (icône générique utilisée).", "Warning: could not download open-webui.png (generic icon used)."))

    launcher_script = """#!/bin/sh
if command -v podman >/dev/null 2>&1 && podman container exists open-webui 2>/dev/null; then
    state=$(podman inspect -f '{{.State.Running}}' open-webui 2>/dev/null || echo false)
    if [ "$state" != "true" ]; then
        podman start open-webui >/dev/null 2>&1 || true
        i=0
        while [ "$i" -lt 15 ]; do
            curl -fsS http://127.0.0.1:8080 >/dev/null 2>&1 && break
            sleep 1
            i=$((i + 1))
        done
    fi
fi
exec xdg-open "http://127.0.0.1:8080"
"""
    desktop_entry = f"""[Desktop Entry]
Name=Open WebUI
Comment=Interface web locale pour Ollama (IA)
Exec={OPENWEBUI_LAUNCHER_PATH}
Icon={OPENWEBUI_ICON_PATH if os.path.isfile(OPENWEBUI_ICON_PATH) else 'web-browser'}
Terminal=false
Type=Application
Categories=Development;Utility;Network;
Keywords=AI;IA;Ollama;OpenWebUI;LLM;Chat;
StartupNotify=true
"""
    try:
        with open(OPENWEBUI_LAUNCHER_PATH, "w", encoding="utf-8") as fh:
            fh.write(launcher_script)
        os.chmod(OPENWEBUI_LAUNCHER_PATH, 0o755)
        os.chown(OPENWEBUI_LAUNCHER_PATH, 0, 0)

        with open(OPENWEBUI_DESKTOP_PATH, "w", encoding="utf-8") as fh:
            fh.write(desktop_entry)
        os.chmod(OPENWEBUI_DESKTOP_PATH, 0o644)
        os.chown(OPENWEBUI_DESKTOP_PATH, 0, 0)
    except OSError as exc:
        emit(f"Erreur création lanceur Open WebUI : {exc}")
        return False

    if shutil.which("restorecon"):
        win.run_cmd_pty(
            ["restorecon", "-RF", OPENWEBUI_ICON_PATH, OPENWEBUI_LAUNCHER_PATH, OPENWEBUI_DESKTOP_PATH],
            emit,
        )
    win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)
    emit(f"Raccourci installé : {OPENWEBUI_DESKTOP_PATH} (icône : {OPENWEBUI_ICON_PATH})")
    return True


def _remove_openwebui_desktop_entry(win: Ps5ManagerWindow, emit: Callable[[str], None]) -> None:
    for path in (OPENWEBUI_DESKTOP_PATH, OPENWEBUI_ICON_PATH, OPENWEBUI_LAUNCHER_PATH):
        if os.path.exists(path):
            try:
                os.remove(path)
                emit(f"Supprimé : {path}")
            except OSError:
                pass
    win.run_cmd_pty(["update-desktop-database", "/usr/share/applications/"], emit)


def _push_ollama_actions(win: Ps5ManagerWindow) -> None:
    installed = _ollama_installed()
    sub = Adw.PreferencesPage()
    grp = pref_group(
        title="Ollama",
        description=_ollama_version() if installed else "Non installé · pciutils + install.sh",
    )

    def _install_or_update(label: str):
        def _task(emit):
            if win.run_cmd_pty(["dnf", "install", "-y", "pciutils"], emit) != 0:
                return False, T("failed") % 1
            rc = win.run_cmd_pty("curl -fsSL https://ollama.com/install.sh | sh", emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(label, _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _uninstall(purge_models: bool):
        def _task(emit):
            win.run_cmd_pty(["systemctl", "stop", "ollama"], emit)
            win.run_cmd_pty(["systemctl", "disable", "ollama"], emit)
            cmds = [
                "rm -f /etc/systemd/system/ollama.service",
                "systemctl daemon-reload",
                "rm -f /usr/local/bin/ollama /usr/bin/ollama",
                "rm -rf /usr/lib/ollama",
            ]
            if purge_models:
                cmds.append("rm -rf /usr/share/ollama")
            win.run_cmd_pty(["bash", "-c", " && ".join(cmds)], emit)
            return True, T("done")
        win.run_task(_L("Désinstaller Ollama", "Uninstall Ollama"), _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(
        win.row(
            T("install"),
            "dnf install -y pciutils && curl -fsSL https://ollama.com/install.sh | sh",
            "system-software-install-symbolic",
            lambda *_: _install_or_update("Installer Ollama"),
        )
    )
    grp.add(
        win.row(
            T("update"),
            _L("Met à jour Ollama vers la dernière version officielle", "Update Ollama to the latest official version"),
            "software-update-available-symbolic",
            lambda *_: _install_or_update("Mettre à jour Ollama"),
        )
    )
    grp.add(
        win.row(
            T("remove"),
            _L("Supprime le service et les binaires, conserve /usr/share/ollama", "Removes the service and binaries, keeps /usr/share/ollama"),
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm(_L("Désinstaller Ollama", "Uninstall Ollama"), _L("Supprimer Ollama tout en conservant les modèles dans /usr/share/ollama ?", "Remove Ollama while keeping the models in /usr/share/ollama?"), lambda: _uninstall(False))
                if _ollama_installed()
                else win.show_info("Ollama", T("not_installed"))
            ),
        )
    )
    if installed:
        grp.add(
            win.row(
                _L("Désinstaller complètement (+ supprimer tous les modèles)", "Uninstall completely (+ delete all models)"),
                "Supprime aussi /usr/share/ollama",
                "edit-delete-symbolic",
                lambda *_: win.show_confirm("Purger Ollama", _L("Supprimer définitivement Ollama ET tous les modèles téléchargés (/usr/share/ollama) ?", "Permanently remove Ollama AND all downloaded models (/usr/share/ollama)?"), lambda: _uninstall(True)),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="Ollama"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="Ollama"))


def _push_webui_actions(win: Ps5ManagerWindow) -> None:
    st, owner = _podman_webui_context()
    has_desktop = os.path.isfile(OPENWEBUI_DESKTOP_PATH) and os.path.isfile(OPENWEBUI_ICON_PATH)
    sub = Adw.PreferencesPage()
    grp = pref_group(
        title="Open WebUI (Podman)",
        description=T("ai_webui_state")
        % (st, owner, T("ai_icon_installed") if has_desktop else T("ai_icon_absent")),
    )

    def _install():
        def _task(emit):
            if not _podman_bin():
                if win.run_cmd_pty(["dnf", "install", "-y", "podman"], emit) != 0:
                    return False, T("failed") % 1
            cur_st, cur_owner = _podman_webui_context()
            if cur_st in ("missing", "no_podman"):
                rc = _create_openwebui_container(win, emit, owner="user")
                if rc != 0:
                    return False, T("failed") % rc
            _install_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task("Installer Open WebUI", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _update():
        def _task(emit):
            if not _podman_bin():
                if win.run_cmd_pty(["dnf", "install", "-y", "podman"], emit) != 0:
                    return False, T("failed") % 1
            podman = _podman_bin() or "podman"
            _, cur_owner = _podman_webui_context()
            as_user = cur_owner == "user"
            if win.run_cmd_pty([podman, "pull", OPENWEBUI_IMAGE], emit, as_user=as_user) != 0:
                return False, T("failed") % 1
            win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=as_user)
            win.run_cmd_pty([podman, "rm", "open-webui"], emit, as_user=as_user)
            rc = _create_openwebui_container(win, emit, owner=cur_owner)
            if rc != 0:
                return False, T("failed") % rc
            _install_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task("Mettre à jour Open WebUI", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _install_icon_only():
        def _task(emit):
            ok = _install_openwebui_desktop_entry(win, emit)
            return ok, T("done") if ok else T("failed") % 1
        win.run_task("Icône Open WebUI", _task, lambda *_: (win.nav.pop(), _push_webui_actions(win)))

    def _uninstall(purge_data: bool):
        def _task(emit):
            podman = _podman_bin() or "podman"
            _, cur_owner = _podman_webui_context()
            as_user = cur_owner == "user"
            win.run_cmd_pty([podman, "stop", "open-webui"], emit, as_user=as_user)
            win.run_cmd_pty([podman, "rm", "open-webui"], emit, as_user=as_user)
            if purge_data:
                win.run_cmd_pty([podman, "volume", "rm", "open-webui"], emit, as_user=as_user)
                win.run_cmd_pty([podman, "rmi", OPENWEBUI_IMAGE], emit, as_user=as_user)
            _remove_openwebui_desktop_entry(win, emit)
            return True, T("done")
        win.run_task(_L("Désinstaller Open WebUI", "Uninstall Open WebUI"), _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(
        win.row(
            T("install"),
            _L("Podman + conteneur open-webui + icône locale dans le menu GNOME", "Podman + open-webui container + local applications-menu icon"),
            "system-software-install-symbolic",
            lambda *_: _install(),
        )
    )
    grp.add(
        win.row(
            T("update"),
            _L("podman pull + recréation (données conservées) + icône GNOME", "podman pull + recreate (data kept) + menu icon"),
            "software-update-available-symbolic",
            lambda *_: _update(),
        )
    )
    grp.add(
        win.row(
            _L("Ouvrir dans le navigateur (http://127.0.0.1:8080)", "Open in the browser (http://127.0.0.1:8080)"),
            _L("Démarre open-webui si arrêté puis ouvre la page web", "Starts open-webui if stopped, then opens the web page"),
            "web-browser-symbolic",
            lambda *_: subprocess.Popen([OPENWEBUI_LAUNCHER_PATH], **user_subprocess_kwargs())
            if os.access(OPENWEBUI_LAUNCHER_PATH, os.X_OK)
            else subprocess.Popen(["xdg-open", "http://127.0.0.1:8080"], **user_subprocess_kwargs()),
        )
    )
    grp.add(
        win.row(
            _L("Installer / mettre à jour l'icône GNOME (menu Applications)", "Install / update the menu icon (Applications)"),
            _L("Télécharge open-webui.png dans /usr/share/pixmaps/ et crée open-webui.desktop", "Downloads open-webui.png into /usr/share/pixmaps/ and creates open-webui.desktop"),
            "image-x-generic-symbolic",
            lambda *_: _install_icon_only(),
        )
    )
    grp.add(
        win.row(
            T("remove"),
            _L("Supprime conteneur + lanceur/icône GNOME (conserve les conversations)", "Removes the container + menu launcher/icon (keeps conversations)"),
            "user-trash-symbolic",
            lambda *_: win.show_confirm(
                _L("Désinstaller Open WebUI", "Uninstall Open WebUI"),
                _L("Supprimer le conteneur open-webui et son icône du menu GNOME en conservant vos données ?", "Remove the open-webui container and its menu icon while keeping your data?"),
                lambda: _uninstall(False),
            ),
        )
    )
    if st not in ("missing", "no_podman"):
        grp.add(
            win.row(
                _L("Désinstaller complètement (conteneur + volume + image + icône)", "Uninstall completely (container + volume + image + icon)"),
                _L("Supprime aussi le volume open-webui et l'image", "Also removes the open-webui volume and image"),
                "edit-delete-symbolic",
                lambda *_: win.show_confirm(
                    "Purger Open WebUI",
                    _L("Supprimer le conteneur, l'icône, l'image ET toutes les conversations (volume open-webui) ?", "Remove the container, the icon, the image AND all conversations (open-webui volume)?"),
                    lambda: _uninstall(True),
                ),
            )
        )
    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="Open WebUI"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="Open WebUI"))


def _push_vscodium_actions(win: Ps5ManagerWindow) -> None:
    installed = _vscodium_installed()
    sub = Adw.PreferencesPage()
    grp = pref_group(
        title="VSCodium",
        description=T("installed_rpm") if installed else T("not_installed"),
    )

    def _install():
        def _task(emit):
            if not _ensure_vscodium_repo(win, emit):
                return False, "Erreur configuration dépôt VSCodium"
            rc = win.run_cmd_pty(["dnf", "install", "-y", "codium"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task("Installer VSCodium", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _update():
        def _task(emit):
            if not _ensure_vscodium_repo(win, emit):
                return False, "Erreur configuration dépôt VSCodium"
            rc = win.run_cmd_pty(["dnf", "upgrade", "-y", "--refresh", "codium"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task("Mettre à jour VSCodium", _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _remove():
        def _task(emit):
            rc = win.run_cmd_pty(["dnf", "remove", "-y", "codium"], emit)
            if rc == 0 and os.path.isfile(VSCODIUM_REPO_FILE):
                try:
                    os.remove(VSCODIUM_REPO_FILE)
                except OSError:
                    pass
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(_L("Désinstaller VSCodium", "Uninstall VSCodium"), _task, lambda *_: (win.nav.pop(), win._select_section("aidev")))

    grp.add(win.row(T("install"), _L("Clé GPG + vscodium.repo + dnf install codium", "GPG key + vscodium.repo + dnf install codium"), "system-software-install-symbolic", lambda *_: _install()))
    grp.add(win.row(T("update"), "dnf upgrade -y --refresh codium", "software-update-available-symbolic", lambda *_: _update()))
    if installed:
        grp.add(win.row("Lancer VSCodium", _L("Ouvre codium sous votre session utilisateur", "Opens codium in your user session"), "applications-development-symbolic", lambda *_: subprocess.Popen(["codium"], **user_subprocess_kwargs())))
    grp.add(
        win.row(
            T("remove"),
            _L("dnf remove -y codium + retrait dépôt", "dnf remove -y codium + repository removal"),
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm(_L("Désinstaller VSCodium", "Uninstall VSCodium"), _L("Supprimer VSCodium (codium) et son dépôt ?", "Remove VSCodium (codium) and its repository?"), _remove)
                if _vscodium_installed()
                else win.show_info("VSCodium", T("not_installed"))
            ),
        )
    )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="VSCodium"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="VSCodium"))


def _push_freebuff_actions(win: Ps5ManagerWindow) -> None:
    version = _freebuff_version()
    installed = _freebuff_installed()
    if version:
        desc = f"{version} · npm (global)"
    elif installed:
        desc = _L("Installé (binaire détecté)", "Installed (binary found)")
    else:
        desc = T("not_installed")
    sub = Adw.PreferencesPage()
    grp = pref_group(title="Freebuff", description=desc)

    def _install():
        def _task(emit):
            if not _ensure_npm_ready(win, emit):
                return False, _L("Node.js et npm sont requis pour Freebuff.",
                                 "Node.js and npm are required for Freebuff.")
            npm = _npm_bin() or "npm"
            rc = win.run_cmd_pty([npm, "install", "-g", FREEBUFF_PACKAGE], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(_L("Installer Freebuff", "Install Freebuff"), _task,
                     lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _update():
        def _task(emit):
            if not _ensure_npm_ready(win, emit):
                return False, _L("Node.js et npm sont requis pour Freebuff.",
                                 "Node.js and npm are required for Freebuff.")
            npm = _npm_bin() or "npm"
            rc = win.run_cmd_pty([npm, "install", "-g", f"{FREEBUFF_PACKAGE}@latest"], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(_L("Mettre à jour Freebuff", "Update Freebuff"), _task,
                     lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _remove():
        def _task(emit):
            npm = _npm_bin()
            if not npm:
                return False, _L("npm est introuvable : Freebuff n'a pas été installé par npm.",
                                 "npm not found: Freebuff was not installed with npm.")
            rc = win.run_cmd_pty([npm, "uninstall", "-g", FREEBUFF_PACKAGE], emit)
            return rc == 0, T("done") if rc == 0 else T("failed") % rc
        win.run_task(_L("Désinstaller Freebuff", "Uninstall Freebuff"), _task,
                     lambda *_: (win.nav.pop(), win._select_section("aidev")))

    def _launch():
        if not _launch_freebuff():
            win.show_info("Freebuff", _L(
                "Terminal introuvable : lance « freebuff » depuis un terminal.",
                "No terminal found: run “freebuff” from a terminal.",
            ))

    grp.add(
        win.row(
            T("install"),
            _L("npm install -g freebuff (Node.js + npm installés si absents)",
               "npm install -g freebuff (Node.js + npm installed if missing)"),
            "system-software-install-symbolic",
            lambda *_: _install(),
        )
    )
    grp.add(
        win.row(
            T("update"),
            "npm install -g freebuff@latest",
            "software-update-available-symbolic",
            lambda *_: _update() if _freebuff_installed() else win.show_info("Freebuff", T("not_installed")),
        )
    )
    if installed:
        grp.add(
            win.row(
                _L("Lancer Freebuff dans un terminal", "Launch Freebuff in a terminal"),
                _L("Ouvre freebuff dans un terminal sous votre session utilisateur",
                   "Opens freebuff in a terminal in your user session"),
                "utilities-terminal-symbolic",
                lambda *_: _launch(),
            )
        )
    grp.add(
        win.row(
            T("remove"),
            "npm uninstall -g freebuff",
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm(
                    _L("Désinstaller Freebuff", "Uninstall Freebuff"),
                    _L("Supprimer Freebuff (npm uninstall -g freebuff) ?",
                       "Remove Freebuff (npm uninstall -g freebuff)?"),
                    _remove,
                )
                if _freebuff_installed()
                else win.show_info("Freebuff", T("not_installed"))
            ),
        )
    )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title="Freebuff"))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title="Freebuff"))


def _push_ai_models(win: Ps5ManagerWindow) -> None:
    # Réutilise la liste déjà collectée par la page IA quand elle existe,
    # pour ne pas relancer `ollama list` à chaque navigation.
    installed = _AIDEV_STATE.get("models") or _ollama_installed_models()
    running = _ollama_running_models()
    sub = Adw.PreferencesPage()

    # 1) Modèles déjà installés sur le système (incluant modèles personnalisés)
    g_inst = pref_group(
        title=_L("Modèles installés sur le système", "Installed models on system"),
        description=T("ai_models_count") % (len(installed), len(running)),
    )
    if not _ollama_installed():
        g_inst.add(plain_row(Adw.ActionRow, title=_L("Ollama n'est pas installé (sera installé au premier pull).", "Ollama is not installed (installed on the first pull).")))
    elif not installed:
        g_inst.add(plain_row(Adw.ActionRow, title=_L("Aucun modèle installé pour le moment.", "No model installed yet.")))
    else:
        for name, size in installed.items():
            state = "Actif en RAM" if name in running else "Installé"
            sub_lbl = f"{state} · {size}" if size else state
            g_inst.add(
                win.row(
                    name,
                    sub_lbl,
                    "media-playback-start-symbolic" if name in running else "drive-harddisk-symbolic",
                    lambda _r, m=name: _push_model_actions(win, m),
                )
            )
    if running:
        def _stop_all_models():
            def _task(emit):
                ollama = _ollama_bin() or "ollama"
                for m in list(_ollama_running_models()):
                    win.run_cmd_pty([ollama, "stop", m], emit)
                return True, T("done")
            win.run_task("Décharger tous les modèles", _task, lambda *_: (win.nav.pop(), _push_ai_models(win)))

        g_inst.add(
            win.row(
                _L("Décharger tous les modèles de la RAM", "Unload all models from RAM"),
                _L("ollama stop sur tous les modèles actifs", "ollama stop on all active models"),
                "media-playback-stop-symbolic",
                lambda *_: _stop_all_models(),
            )
        )
    sub.add(g_inst)

    # 2) Catalogue rapide des modèles demandés
    g_cat = pref_group(
        title=_L("Catalogue des modèles recommandés", "Recommended models catalog"),
        description=_L("Cliquez sur un modèle pour le télécharger, mettre à jour, stopper ou supprimer", "Click a model to download, update, stop or remove it"),
    )
    for model_id, desc_fr, desc_en in AI_MODELS_CATALOG:
        desc = desc_fr if UI_LANG == "fr" else desc_en
        if model_id in running:
            badge = "Actif en RAM"
        elif model_id in installed:
            badge = f"Installé ({installed[model_id]})" if installed[model_id] else "Installé"
        else:
            badge = "Non installé"
        g_cat.add(
            win.row(
                model_id,
                f"{desc} · {badge}",
                "folder-download-symbolic",
                lambda _r, m=model_id: _push_model_actions(win, m),
            )
        )

    def _pull_custom():
        win.show_prompt(
            "Télécharger un modèle Ollama",
            "Nom exact du modèle (ex : llama3.2:3b, mistral:7b) :",
            "qwen2.5-coder:3b",
            lambda name: _exec_model_pull(win, name.strip(), refresh_models=True) if name.strip() else None,
        )

    g_cat.add(
        win.row(
            _L("Télécharger un autre modèle (nom personnalisé)", "Pull a custom model"),
            "ollama pull <nom_du_modele>",
            "list-add-symbolic",
            lambda *_: _pull_custom(),
        )
    )
    sub.add(g_cat)

    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=T("aidev_models")))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=T("aidev_models")))


def _exec_model_pull(win: Ps5ManagerWindow, model_name: str, refresh_models: bool = False) -> None:
    def _task(emit):
        if not _ensure_ollama_ready(win, emit):
            return False, "Échec préparation Ollama"
        ollama = _ollama_bin() or "ollama"
        rc = win.run_cmd_pty([ollama, "pull", model_name], emit)
        return rc == 0, T("done") if rc == 0 else T("failed") % rc

    def _after(*_):
        if refresh_models:
            win.nav.pop()
            _push_ai_models(win)

    win.run_task(f"ollama pull {model_name}", _task, _after)


def _push_model_actions(win: Ps5ManagerWindow, model_name: str) -> None:
    installed = _ollama_installed_models()
    running = _ollama_running_models()
    is_inst = model_name in installed
    is_run = model_name in running
    status = "Actif en RAM" if is_run else (f"Installé ({installed[model_name]})" if is_inst else "Non installé")

    sub = Adw.PreferencesPage()
    grp = pref_group(title=model_name, description=status)

    grp.add(
        win.row(
            "Mettre à jour (ollama pull)" if is_inst else "Télécharger (ollama pull)",
            f"ollama pull {model_name}",
            "system-software-install-symbolic",
            lambda *_: _exec_model_pull(win, model_name, refresh_models=False),
        )
    )

    if is_inst:
        grp.add(
            win.row(
                _L("Décharger de la RAM (ollama stop)", "Unload from RAM (ollama stop)"),
                f"ollama stop {model_name}",
                "media-playback-stop-symbolic",
                lambda *_: win.run_task(
                    f"ollama stop {model_name}",
                    lambda e: (win.run_cmd_pty([_ollama_bin() or "ollama", "stop", model_name], e) == 0, T("done")),
                ),
            )
        )

        def _show_model_details():
            ollama = _ollama_bin() or "ollama"
            res = subprocess.run([ollama, "show", model_name], capture_output=True, text=True)
            win.show_text_modal(model_name, res.stdout or res.stderr or "(indisponible — démarrez ollama.service)")

        grp.add(
            win.row(
                _L("Afficher les détails du modèle (ollama show)", "Show model details (ollama show)"),
                _L("Architecture, quantification, paramètres et licence", "Architecture, quantization, parameters and licence"),
                "dialog-information-symbolic",
                lambda *_: _show_model_details(),
            )
        )

        def _do_remove():
            def _task(emit):
                ollama = _ollama_bin() or "ollama"
                if not _ollama_service_active() and _ollama_service_exists():
                    win.run_cmd_pty(["systemctl", "start", "ollama"], emit)
                # Toujours stopper le modèle avant de le supprimer s'il est en RAM
                if model_name in _ollama_running_models():
                    win.run_cmd_pty([ollama, "stop", model_name], emit)
                rc = win.run_cmd_pty([ollama, "rm", model_name], emit)
                return rc == 0, T("done") if rc == 0 else T("failed") % rc

            def _after(*_):
                win.nav.pop()
                win.nav.pop()
                _push_ai_models(win)

            win.run_task(f"ollama rm {model_name}", _task, _after)

        grp.add(
            win.row(
                _L("Supprimer le modèle (stop auto + ollama rm)", "Remove the model (auto stop + ollama rm)"),
                f"Stoppe si actif puis exécute ollama rm {model_name}",
                "user-trash-symbolic",
                lambda *_: win.show_confirm(
                    f"Supprimer {model_name}",
                    f"Le modèle sera stoppé s'il est actif puis supprimé (ollama rm {model_name}).",
                    _do_remove,
                ),
            )
        )

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=model_name))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=model_name))


# ------------------------------------------------------------------------------
# Page « Développement » : environnement complet, par catégorie
# (composants système → outils CLI → applications graphiques)
# ------------------------------------------------------------------------------
DEV_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("components", "Composants (socle système)", "Components (system base)"),
    ("tools", "Outils en ligne de commande", "Command-line tools"),
    ("apps", "Applications graphiques", "Graphical applications"),
)

GH_DESKTOP_FLATPAK = "io.github.shiftey.Desktop"
FORGEJO_BIN = "/usr/local/bin/forgejo"
FORGEJO_UNIT = "/etc/systemd/system/forgejo.service"
FORGEJO_DATA = "/var/lib/forgejo"
FORGEJO_URL = "http://localhost:3000"


def _forgejo_download() -> str:
    """Bloc shell partagé : télécharge la dernière version de Forgejo."""
    return r"""API="https://codeberg.org/api/v1/repos/forgejo/forgejo/releases/latest"
TAG=$(curl -fsSL "$API" 2>/dev/null | grep -o '"tag_name":"v[^"]*"' | head -n 1 | cut -d'"' -f4)
if [ -z "${TAG:-}" ]; then
  TAG=$(curl -fsSL "https://code.forgejo.org/api/v1/repos/forgejo/forgejo/releases/latest" 2>/dev/null \
    | grep -o '"tag_name":"v[^"]*"' | head -n 1 | cut -d'"' -f4)
fi
[ -n "${TAG:-}" ] || { echo "Forgejo : impossible de joindre Codeberg"; exit 1; }
VER="${TAG#v}"
case "$(uname -m)" in
  x86_64) ARCH=amd64 ;;
  aarch64) ARCH=arm64 ;;
  *) echo "Forgejo : architecture non gérée ($(uname -m))"; exit 1 ;;
esac
URL="https://codeberg.org/forgejo/forgejo/releases/download/v${VER}/forgejo-${VER}-linux-${ARCH}"
echo "Forgejo ${VER} (${ARCH}) : $URL"
curl -fsSL -o /tmp/forgejo.download "$URL" || \
  curl -fsSL -o /tmp/forgejo.download \
    "https://code.forgejo.org/forgejo/forgejo/releases/download/v${VER}/forgejo-${VER}-linux-${ARCH}"
chmod 755 /tmp/forgejo.download
"""


FORGEJO_CONF = r"""APP_NAME = Forgejo (local)
RUN_USER = forgejo
WORK_PATH = /var/lib/forgejo
RUN_MODE = prod

[server]
PROTOCOL = http
HTTP_ADDR = 127.0.0.1
HTTP_PORT = 3000
ROOT_URL = http://localhost:3000/
DISABLE_SSH = true
OFFLINE_MODE = true

[database]
DB_TYPE = sqlite3
PATH = /var/lib/forgejo/data/forgejo.db

[repository]
ROOT = /var/lib/forgejo/gitea-repositories

[service]
DISABLE_REGISTRATION = false
REQUIRE_SIGNIN_VIEW = false
"""

FORGEJO_UNIT_FILE = r"""[Unit]
Description=Forgejo (serveur Git local, PS5 Fedora Manager)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=forgejo
Group=forgejo
WorkingDirectory=/var/lib/forgejo
Environment=USER=forgejo HOME=/var/lib/forgejo GITEA_WORK_DIR=/var/lib/forgejo
ExecStart=/usr/local/bin/forgejo web --config /etc/forgejo/app.ini
Restart=on-failure
RestartSec=3
LimitNOFILE=524288

[Install]
WantedBy=multi-user.target
"""

FORGEJO_INSTALL = (
    "set -e\n"
    "command -v curl >/dev/null 2>&1 || dnf install -y curl\n"
    + _forgejo_download()
    + r"""install -o root -g root -m 0755 /tmp/forgejo.download /usr/local/bin/forgejo
rm -f /tmp/forgejo.download
getent group forgejo >/dev/null 2>&1 || groupadd --system forgejo
id forgejo >/dev/null 2>&1 || useradd --system --gid forgejo --home-dir /var/lib/forgejo --shell /usr/sbin/nologin forgejo
mkdir -p /var/lib/forgejo/data /etc/forgejo
cat > /etc/forgejo/app.ini <<'INI'
__FORGEJO_CONF__INI
cat > /etc/systemd/system/forgejo.service <<'UNIT'
__FORGEJO_UNIT__UNIT
chown -R forgejo:forgejo /var/lib/forgejo
systemctl daemon-reload
systemctl enable --now forgejo
sleep 2
systemctl is-active --quiet forgejo || { echo "Forgejo n'a pas démarré : journalctl -u forgejo -n 30"; exit 1; }
echo "Forgejo actif sur __FORGEJO_URL__"
"""
).replace("__FORGEJO_CONF__", FORGEJO_CONF).replace("__FORGEJO_UNIT__", FORGEJO_UNIT_FILE).replace(
    "__FORGEJO_URL__", FORGEJO_URL
)

FORGEJO_UPDATE = (
    "set -e\n"
    + _forgejo_download()
    + r"""systemctl stop forgejo 2>/dev/null || true
install -o root -g root -m 0755 /tmp/forgejo.download /usr/local/bin/forgejo
rm -f /tmp/forgejo.download
systemctl start forgejo
systemctl is-active --quiet forgejo || { echo "Forgejo n'a pas redémarré : journalctl -u forgejo -n 30"; exit 1; }
echo "Forgejo mis à jour"
"""
)

FORGEJO_REMOVE = r"""systemctl disable --now forgejo 2>/dev/null || true
rm -f /etc/systemd/system/forgejo.service
systemctl daemon-reload
rm -f /usr/local/bin/forgejo
echo "Forgejo désinstallé : les données restent dans /var/lib/forgejo"
"""

DOCKER_INSTALL = r"""set -e
command -v curl >/dev/null 2>&1 || dnf install -y curl
if dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo 2>/dev/null; then
  echo "dépôt docker-ce ajouté"
else
  dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
fi
dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker __USER__ 2>/dev/null || true
docker --version
"""

DOCKER_UPDATE = (
    "dnf upgrade -y --refresh docker-ce docker-ce-cli containerd.io "
    "docker-buildx-plugin docker-compose-plugin"
)

DOCKER_REMOVE = r"""systemctl disable --now docker 2>/dev/null || true
dnf remove -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true
rm -f /etc/yum.repos.d/docker-ce.repo
echo "Docker Engine retiré : les données restent dans /var/lib/docker"
"""

GH_DESKTOP_INSTALL = r"""command -v flatpak >/dev/null 2>&1 || dnf install -y flatpak
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install -y flathub __GH_DESKTOP__
"""


def _dev_rpm_ok(name: str) -> bool:
    return subprocess.run(["rpm", "-q", name], capture_output=True).returncode == 0


def _docker_installed() -> bool:
    return _dev_rpm_ok("docker-ce")


def _forgejo_installed() -> bool:
    return os.path.isfile(FORGEJO_BIN)


def _flatpak_app_installed(app_id: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    try:
        res = subprocess.run(["flatpak", "info", app_id], capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


def _dev_spawn(cmd: list[str]) -> bool:
    try:
        subprocess.Popen(cmd, **user_subprocess_kwargs())
        return True
    except OSError:
        return False


def _launch_in_terminal(command: str) -> bool:
    """Lance une commande interactive dans le premier terminal disponible."""
    for name, extra in FREEBUFF_TERMINALS:
        path = shutil.which(name)
        if not path:
            continue
        try:
            subprocess.Popen(
                [path, *extra, "bash", "-lc", f'cd "$HOME" && {command}'],
                **user_subprocess_kwargs(),
            )
            return True
        except OSError:
            continue
    return False


def _dev_entry(
    key: str,
    group: str,
    title_fr: str,
    title_en: str,
    sub: str,
    icon: str,
    packages: tuple[str, ...] = (),
    install: tuple[str, ...] = (),
    update: tuple[str, ...] = (),
    remove: tuple[str, ...] = (),
    check: Optional[Callable[[], bool]] = None,
    panel: Optional[Callable] = None,
    launch: Optional[Callable[[], bool]] = None,
    launch_fr: str = "",
    launch_en: str = "",
    note_fr: str = "",
    note_en: str = "",
    install_desc: str = "",
    update_desc: str = "",
    remove_desc: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "group": group,
        "title_fr": title_fr,
        "title_en": title_en,
        "sub": sub,
        "icon": icon,
        "packages": packages,
        "install": install,
        "update": update,
        "remove": remove,
        "check": check,
        "panel": panel,
        "launch": launch,
        "launch_fr": launch_fr,
        "launch_en": launch_en,
        "note_fr": note_fr,
        "note_en": note_en,
        "install_desc": install_desc,
        "update_desc": update_desc,
        "remove_desc": remove_desc,
    }


DEV_CATALOG: tuple[dict[str, Any], ...] = (
    # ---- Composants ---------------------------------------------------------
    _dev_entry(
        "build", "components",
        "Socle de compilation", "Build essentials",
        "gcc, g++, make, cmake, meson, ninja, autotools, rpmdevtools",
        "applications-engineering-symbolic",
        packages=(
            "git", "gcc", "gcc-c++", "make", "cmake", "meson", "ninja-build",
            "pkgconf-pkg-config", "autoconf", "automake", "libtool", "patch",
            "rpmdevtools", "rpmlint",
        ),
    ),
    _dev_entry(
        "python-gtk", "components",
        "Python + GTK4 / Libadwaita", "Python + GTK4 / Libadwaita",
        "python3-devel, gtk4-devel, libadwaita-devel, blueprint-compiler",
        "text-x-python-symbolic",
        packages=(
            "python3-devel", "python3-pip", "python3-virtualenv", "python3-pytest",
            "gobject-introspection-devel", "gtk4-devel", "libadwaita-devel",
            "libsecret-devel", "blueprint-compiler", "desktop-file-utils",
            "appstream", "gtk4-devel-tools", "devhelp",
        ),
    ),
    _dev_entry(
        "containers", "components",
        "Conteneurs (Podman, Distrobox, Toolbox)", "Containers (Podman, Distrobox, Toolbox)",
        "podman, podman-docker, buildah, skopeo, distrobox, toolbox",
        "application-x-executable-symbolic",
        packages=(
            "podman", "podman-docker", "buildah", "skopeo", "distrobox", "toolbox",
        ),
    ),
    _dev_entry(
        "docker", "components",
        "Docker Engine + Compose", "Docker Engine + Compose",
        "dépôt docker-ce, docker-ce, containerd, compose-plugin, buildx",
        "application-x-executable-symbolic",
        check=_docker_installed,
        install=(DOCKER_INSTALL,),
        update=(DOCKER_UPDATE,),
        remove=(DOCKER_REMOVE,),
        install_desc="dépôt docker-ce + docker-ce + compose/buildx",
        update_desc=DOCKER_UPDATE,
        remove_desc="systemctl disable docker + dnf remove docker-ce",
        note_fr="Déconnecte-toi puis reconnecte-toi pour activer les groupes docker, libvirt et kvm.",
        note_en="Log out and back in to enable the docker, libvirt and kvm groups.",
    ),
    _dev_entry(
        "virt", "components",
        "Virtualisation KVM / QEMU", "KVM / QEMU virtualization",
        "qemu-kvm, libvirt, virt-manager, GNOME Boxes, OVMF, swtpm",
        "computer-symbolic",
        packages=(
            "qemu-kvm", "libvirt", "virt-install", "virt-manager", "virt-viewer",
            "gnome-boxes", "edk2-ovmf", "swtpm", "swtpm-tools",
        ),
        install=(
            "systemctl enable --now libvirtd 2>/dev/null || "
            "systemctl enable --now virtqemud.socket virtnetworkd.socket",
            "usermod -aG libvirt,kvm __USER__ 2>/dev/null || true",
        ),
        note_fr="Déconnecte-toi puis reconnecte-toi pour activer les groupes docker, libvirt et kvm.",
        note_en="Log out and back in to enable the docker, libvirt and kvm groups.",
    ),
    _dev_entry(
        "node", "components",
        "Node.js / npm", "Node.js / npm",
        "nodejs, npm (+ corepack pour pnpm/yarn)",
        "text-x-script-symbolic",
        packages=("nodejs", "npm"),
        install=("command -v corepack >/dev/null 2>&1 && corepack enable || true",),
    ),
    _dev_entry(
        "rust", "components",
        "Rust / Cargo", "Rust / Cargo",
        "rust, cargo, rustfmt, clippy",
        "text-x-script-symbolic",
        packages=("rust", "cargo", "rustfmt", "clippy"),
    ),
    # ---- Outils -------------------------------------------------------------
    _dev_entry(
        "cli-search", "tools",
        "Recherche & navigation", "Search & navigation",
        "ripgrep, fd-find, bat, eza, fzf, zoxide",
        "system-search-symbolic",
        packages=("ripgrep", "fd-find", "bat", "eza", "fzf", "zoxide"),
    ),
    _dev_entry(
        "git-tools", "tools",
        "Git & plateformes (GitHub, GitLab)", "Git & platforms (GitHub, GitLab)",
        "gh, glab, lazygit, git-delta, git-lfs",
        "folder-git-symbolic",
        packages=("gh", "glab", "lazygit", "git-delta", "git-lfs"),
        install=(
            "git config --system core.pager delta 2>/dev/null || true",
            "git config --system interactive.diffFilter 'delta --color-only' 2>/dev/null || true",
        ),
    ),
    _dev_entry(
        "terminal", "tools",
        "Terminal (tmux, zellij)", "Terminal (tmux, zellij)",
        "tmux + zellij (COPR varlad/zellij)",
        "utilities-terminal-symbolic",
        packages=("tmux",),
        install=("dnf copr enable -y varlad/zellij && dnf install -y zellij",),
        remove=("dnf remove -y zellij 2>/dev/null || true", "dnf copr remove -y varlad/zellij 2>/dev/null || true"),
    ),
    _dev_entry(
        "diag", "tools",
        "Diagnostic système", "System diagnostics",
        "btop, ncdu, duf, fastfetch, hyperfine, lsof, strace, ltrace, sysstat, perf",
        "utilities-system-monitor-symbolic",
        packages=(
            "btop", "ncdu", "duf", "fastfetch", "hyperfine", "lsof", "strace",
            "ltrace", "sysstat", "perf",
        ),
    ),
    _dev_entry(
        "debug", "tools",
        "Debug & profilage", "Debug & profiling",
        "gdb, lldb, valgrind, heaptrack, sysprof",
        "applications-utilities-symbolic",
        packages=("gdb", "lldb", "valgrind", "heaptrack", "sysprof"),
    ),
    _dev_entry(
        "python-quality", "tools",
        "Qualité Python (uv, ruff, mypy)", "Python quality (uv, ruff, mypy)",
        "ruff, mypy, pre-commit, pytest (+ uv si absent des dépôts)",
        "text-x-python-symbolic",
        packages=("ruff", "mypy", "pre-commit", "python3-pytest"),
        install=(
            "dnf install -y uv || curl -LsSf https://astral.sh/uv/install.sh | sh",
        ),
    ),
    _dev_entry(
        "data", "tools",
        "JSON & HTTP (jq, yq, httpie)", "JSON & HTTP (jq, yq, httpie)",
        "jq, yq, httpie",
        "text-x-generic-symbolic",
        packages=("jq", "yq", "httpie"),
    ),
    _dev_entry(
        "automation", "tools",
        "Automatisation (just, direnv, shellcheck)", "Automation (just, direnv, shellcheck)",
        "just, direnv, shellcheck, shfmt",
        "view-refresh-symbolic",
        packages=("just", "direnv", "shellcheck"),
        install=("dnf install -y shfmt || dnf install -y golang-github-mvdan-sh 2>/dev/null || true",),
    ),
    # ---- Applications -------------------------------------------------------
    _dev_entry(
        "vscodium", "apps",
        "VSCodium", "VSCodium",
        "éditeur de code libre (dépôt officiel VSCodium)",
        "applications-development-symbolic",
        check=_vscodium_installed,
        panel=_push_vscodium_actions,
    ),
    _dev_entry(
        "github-desktop", "apps",
        "GitHub Desktop", "GitHub Desktop",
        "Flatpak io.github.shiftey.Desktop (fork Linux communautaire)",
        "folder-git-symbolic",
        check=lambda: _flatpak_app_installed(GH_DESKTOP_FLATPAK),
        install=(GH_DESKTOP_INSTALL.replace("__GH_DESKTOP__", GH_DESKTOP_FLATPAK),),
        update=(f"flatpak update -y {GH_DESKTOP_FLATPAK}",),
        remove=(f"flatpak uninstall -y {GH_DESKTOP_FLATPAK}",),
        launch=lambda: _dev_spawn(["flatpak", "run", GH_DESKTOP_FLATPAK]),
        launch_fr="Ouvre GitHub Desktop (Flatpak) sous votre session",
        launch_en="Opens GitHub Desktop (Flatpak) in your session",
        install_desc="flatpak install flathub io.github.shiftey.Desktop",
        update_desc=f"flatpak update {GH_DESKTOP_FLATPAK}",
        remove_desc=f"flatpak uninstall {GH_DESKTOP_FLATPAK}",
    ),
    _dev_entry(
        "forgejo", "apps",
        "Forgejo (serveur Git local)", "Forgejo (local Git server)",
        "service systemd + binaire officiel + SQLite, http://localhost:3000",
        "network-server-symbolic",
        check=_forgejo_installed,
        install=(FORGEJO_INSTALL,),
        update=(FORGEJO_UPDATE,),
        remove=(FORGEJO_REMOVE,),
        launch=lambda: (open_uri(FORGEJO_URL), True)[1],
        launch_fr="Ouvre Forgejo dans le navigateur (http://localhost:3000)",
        launch_en="Opens Forgejo in the browser (http://localhost:3000)",
        install_desc="forgejo-*-linux-amd64 + unité systemd forgejo.service",
        update_desc="téléchargement de la dernière version + systemctl restart forgejo",
        remove_desc="systemctl disable forgejo + suppression du binaire",
        note_fr="Désinstallation : les données restent dans /var/lib/forgejo.",
        note_en="Uninstall: the data stays in /var/lib/forgejo.",
    ),
    _dev_entry(
        "editors", "apps",
        "Éditeurs terminal (Neovim, Helix)", "Terminal editors (Neovim, Helix)",
        "neovim, helix",
        "utilities-terminal-symbolic",
        packages=("neovim", "helix"),
        launch=lambda: _launch_in_terminal("nvim"),
        launch_fr="Ouvre Neovim dans un terminal",
        launch_en="Opens Neovim in a terminal",
    ),
    _dev_entry(
        "sqlite", "apps",
        "Bases de données (SQLite)", "Databases (SQLite)",
        "sqlite, sqlitebrowser",
        "drive-harddisk-symbolic",
        packages=("sqlite", "sqlitebrowser"),
        launch=lambda: _dev_spawn(["sqlitebrowser"]),
        launch_fr="Ouvre SQLite Browser",
        launch_en="Opens SQLite Browser",
    ),
)

WEB_GROUPS: tuple[tuple[str, str, str], ...] = (
    ("servers", "Serveurs & langages", "Servers & languages"),
    ("panels", "Panneaux & bases de données", "Panels & databases"),
    ("network", "Réseau & accès", "Network & access"),
)

PHP_PACKAGES = (
    "php", "php-cli", "php-fpm", "php-mysqlnd", "php-pdo", "php-gd",
    "php-mbstring", "php-xml", "php-opcache", "php-zip", "php-intl",
)

APACHE_INSTALL = r"""set -e
dnf install -y httpd httpd-tools mod_ssl
systemctl enable --now httpd
firewall-cmd --permanent --add-service=http --add-service=https >/dev/null 2>&1 || true
firewall-cmd --reload >/dev/null 2>&1 || true
httpd -t
echo "Apache actif : http://localhost"
"""

APACHE_UPDATE = "dnf upgrade -y --refresh httpd httpd-tools mod_ssl && systemctl reload httpd 2>/dev/null || true"

APACHE_REMOVE = r"""systemctl disable --now httpd 2>/dev/null || true
dnf remove -y httpd httpd-tools mod_ssl || true
echo "Apache retiré (configuration conservée en .rpmsave dans /etc/httpd)"
"""

NGINX_INSTALL = r"""set -e
dnf install -y nginx
systemctl enable --now nginx
firewall-cmd --permanent --add-service=http --add-service=https >/dev/null 2>&1 || true
firewall-cmd --reload >/dev/null 2>&1 || true
nginx -t
echo "Nginx actif : http://localhost"
"""

NGINX_UPDATE = "dnf upgrade -y --refresh nginx && systemctl reload nginx 2>/dev/null || true"

NGINX_REMOVE = r"""systemctl disable --now nginx 2>/dev/null || true
dnf remove -y nginx || true
echo "Nginx retiré"
"""

PHP_INSTALL = r"""set -e
dnf install -y __PHP_PACKAGES__
systemctl enable --now php-fpm
php -v | head -n 1
"""

PHP_REMOVE = r"""systemctl disable --now php-fpm 2>/dev/null || true
dnf remove -y __PHP_PACKAGES__ || true
"""

PHP_WEB_HANDLER = r"""set -e
SOCK=/run/php-fpm/www.sock
CHANGED=0
mkdir -p /run/php-fpm
[ -S "$SOCK" ] || systemctl enable --now php-fpm >/dev/null 2>&1 || true
if [ -f /etc/httpd/conf/httpd.conf ]; then
  cp -f /etc/httpd/conf.d/php-fpm.conf /etc/httpd/conf.d/php-fpm.conf.bak-ps5 2>/dev/null || true
  cat > /etc/httpd/conf.d/php-fpm.conf <<'CONF'
# PHP via PHP-FPM (PS5 Fedora Manager)
<FilesMatch \.php$>
  SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
</FilesMatch>
DirectoryIndex index.php index.html
CONF
  if httpd -t >/dev/null 2>&1; then
    systemctl reload httpd 2>/dev/null || true
    CHANGED=1
    echo "Apache : handler PHP-FPM ajouté"
  else
    echo "Apache : configuration invalide, httpd NON rechargé (voir httpd -t)"
  fi
fi
if [ -f /etc/nginx/nginx.conf ]; then
  mkdir -p /etc/nginx/default.d
  cp -f /etc/nginx/default.d/php-fpm.conf /etc/nginx/default.d/php-fpm.conf.bak-ps5 2>/dev/null || true
  cat > /etc/nginx/default.d/php-fpm.conf <<'CONF'
# PHP via PHP-FPM (PS5 Fedora Manager)
index index.php index.html;
location ~ \.php$ {
    root /usr/share/nginx/html;
    fastcgi_pass unix:/run/php-fpm/www.sock;
    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
}
CONF
  if nginx -t >/dev/null 2>&1; then
    systemctl reload nginx 2>/dev/null || true
    CHANGED=1
    echo "Nginx : handler PHP-FPM ajouté"
  else
    echo "Nginx : configuration invalide, nginx NON rechargé (voir nginx -t)"
  fi
fi
[ "$CHANGED" -eq 1 ] || { echo "Ni Apache ni Nginx installé : installe d'abord un serveur"; exit 1; }
"""

PHP_WEB_REMOVE = r"""rm -f /etc/httpd/conf.d/php-fpm.conf /etc/nginx/default.d/php-fpm.conf
httpd -t >/dev/null 2>&1 && systemctl reload httpd 2>/dev/null || true
nginx -t >/dev/null 2>&1 && systemctl reload nginx 2>/dev/null || true
echo "Handler FastCGI retiré"
"""

MARIADB_INSTALL = r"""set -e
dnf install -y mariadb-server
systemctl enable --now mariadb
systemctl is-active --quiet mariadb
echo "MariaDB actif : root local via socket (mariadb-secure-installation pour le durcir)"
"""

MYSQL_INSTALL = r"""set -e
dnf install -y community-mysql-server
systemctl enable --now mysqld
systemctl is-active --quiet mysqld
echo "MySQL actif : root local via socket (mysql_secure_installation pour le durcir)"
"""

COCKPIT_INSTALL = r"""set -e
dnf install -y cockpit cockpit-packagekit cockpit-storaged cockpit-networkmanager \
  cockpit-files cockpit-podman cockpit-machines
systemctl enable --now cockpit.socket
firewall-cmd --permanent --add-service=cockpit >/dev/null 2>&1 || true
firewall-cmd --reload >/dev/null 2>&1 || true
echo "Cockpit actif : https://localhost:9090"
"""

COCKPIT_REMOVE = r"""systemctl disable --now cockpit.socket 2>/dev/null || true
dnf remove -y cockpit cockpit-packagekit cockpit-storaged cockpit-networkmanager \
  cockpit-files cockpit-podman cockpit-machines || true
"""

PHPMYADMIN_INSTALL = r"""set -e
dnf install -y httpd phpMyAdmin
systemctl enable --now httpd
systemctl restart httpd
echo "phpMyAdmin : http://localhost/phpMyAdmin"
"""

ADMINER_INSTALL = r"""set -e
dnf install -y httpd
systemctl enable --now httpd
curl -fsSL -o /var/www/html/adminer.php https://www.adminer.org/latest.php
chmod 644 /var/www/html/adminer.php
echo "Adminer : http://localhost/adminer.php"
"""

ADMINER_REMOVE = r"""rm -f /var/www/html/adminer.php
echo "Adminer retiré"
"""

WEBMIN_INSTALL = r"""set -e
rpm --import https://download.webmin.com/jcameron-key.asc
cat > /etc/yum.repos.d/webmin.repo <<'REPO'
[Webmin]
name=Webmin Distribution Neutral
baseurl=https://download.webmin.com/download/yum
enabled=1
gpgkey=https://download.webmin.com/jcameron-key.asc
gpgcheck=1
REPO
dnf install -y webmin
systemctl enable --now webmin
echo "Webmin actif : https://localhost:10000"
"""

WEBMIN_REMOVE = r"""systemctl disable --now webmin 2>/dev/null || true
dnf remove -y webmin || true
rm -f /etc/yum.repos.d/webmin.repo
"""

FIREWALL_HTTP = (
    "firewall-cmd --permanent --add-service=http --add-service=https "
    "&& firewall-cmd --reload && firewall-cmd --list-services"
)

FIREWALL_HTTP_REMOVE = (
    "firewall-cmd --permanent --remove-service=http --remove-service=https "
    "2>/dev/null || true; firewall-cmd --reload || true"
)


def _firewall_http_ok() -> bool:
    if not shutil.which("firewall-cmd"):
        return False
    try:
        res = subprocess.run(
            ["firewall-cmd", "--query-service=http"], capture_output=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return res.returncode == 0


def _adminer_installed() -> bool:
    return os.path.isfile("/var/www/html/adminer.php")


WEB_CATALOG: tuple[dict[str, Any], ...] = (
    _dev_entry(
        "apache", "servers",
        "Apache (httpd)", "Apache (httpd)",
        "httpd, httpd-tools, mod_ssl + service + pare-feu 80/443",
        "network-server-symbolic",
        check=lambda: _dev_rpm_ok("httpd"),
        install=(APACHE_INSTALL,),
        update=(APACHE_UPDATE,),
        remove=(APACHE_REMOVE,),
        launch=lambda: (open_uri("http://localhost"), True)[1],
        launch_fr="Ouvre http://localhost dans le navigateur",
        launch_en="Opens http://localhost in the browser",
        install_desc="dnf install httpd httpd-tools mod_ssl + systemctl enable --now httpd",
        update_desc=APACHE_UPDATE,
        remove_desc="systemctl disable httpd + dnf remove httpd",
        note_fr="Apache : page par défaut sur http://localhost après activation du service.",
        note_en="Apache: default page on http://localhost once the service is running.",
    ),
    _dev_entry(
        "nginx", "servers",
        "Nginx", "Nginx",
        "nginx (LEMP) + service + pare-feu 80/443",
        "network-server-symbolic",
        check=lambda: _dev_rpm_ok("nginx"),
        install=(NGINX_INSTALL,),
        update=(NGINX_UPDATE,),
        remove=(NGINX_REMOVE,),
        launch=lambda: (open_uri("http://localhost"), True)[1],
        launch_fr="Ouvre http://localhost dans le navigateur",
        launch_en="Opens http://localhost in the browser",
        install_desc="dnf install nginx + systemctl enable --now nginx",
        update_desc=NGINX_UPDATE,
        remove_desc="systemctl disable nginx + dnf remove nginx",
        note_fr="Nginx : page par défaut sur http://localhost après activation du service.",
        note_en="Nginx: default page on http://localhost once the service is running.",
    ),
    _dev_entry(
        "php", "servers",
        "PHP 8 + extensions", "PHP 8 + extensions",
        "php, php-fpm, mysqlnd, pdo, gd, mbstring, xml, opcache, zip, intl",
        "text-x-script-symbolic",
        packages=PHP_PACKAGES,
        install=(PHP_INSTALL.replace("__PHP_PACKAGES__", " ".join(PHP_PACKAGES)),),
        remove=(PHP_REMOVE.replace("__PHP_PACKAGES__", " ".join(PHP_PACKAGES)),),
        note_fr="PHP-FPM : socket /run/php-fpm/www.sock ; l'entrée « PHP ↔ Apache / Nginx » ajoute le handler FastCGI.",
        note_en="PHP-FPM: socket /run/php-fpm/www.sock; the “PHP ↔ Apache / Nginx” entry adds the FastCGI handler.",
    ),
    _dev_entry(
        "php-handler", "servers",
        "PHP ↔ Apache / Nginx (FastCGI)", "PHP ↔ Apache / Nginx (FastCGI)",
        "handler FastCGI vers /run/php-fpm/www.sock + test de configuration",
        "text-x-script-symbolic",
        check=lambda: _dev_rpm_ok("php-fpm"),
        install=(PHP_WEB_HANDLER,),
        update=(PHP_WEB_HANDLER,),
        remove=(PHP_WEB_REMOVE,),
        install_desc="conf.d/php-fpm.conf (Apache) + default.d/php-fpm.conf (Nginx)",
        update_desc="réécrit les deux fichiers puis teste httpd -t / nginx -t",
        remove_desc="supprime les deux fichiers puis recharge les serveurs",
    ),
    _dev_entry(
        "mariadb", "servers",
        "MariaDB", "MariaDB",
        "mariadb-server + service (root local via socket)",
        "drive-harddisk-symbolic",
        check=lambda: _dev_rpm_ok("mariadb-server"),
        install=(MARIADB_INSTALL,),
        remove=("systemctl disable --now mariadb 2>/dev/null || true", "dnf remove -y mariadb-server || true"),
        install_desc="dnf install mariadb-server + systemctl enable --now mariadb",
        remove_desc="systemctl disable mariadb + dnf remove mariadb-server",
        note_fr="MariaDB : lance « mariadb-secure-installation » pour durcir le serveur ; root se connecte en local via socket.",
        note_en="MariaDB: run “mariadb-secure-installation” to harden the server; root connects locally over the socket.",
    ),
    _dev_entry(
        "mysql", "servers",
        "MySQL (community)", "MySQL (community)",
        "community-mysql-server + service (root local via socket)",
        "drive-harddisk-symbolic",
        check=lambda: _dev_rpm_ok("community-mysql-server"),
        install=(MYSQL_INSTALL,),
        remove=("systemctl disable --now mysqld 2>/dev/null || true", "dnf remove -y community-mysql-server || true"),
        install_desc="dnf install community-mysql-server + systemctl enable --now mysqld",
        remove_desc="systemctl disable mysqld + dnf remove community-mysql-server",
        note_fr="MySQL community : lance « mysql_secure_installation » après l'installation.",
        note_en="MySQL community: run “mysql_secure_installation” after installing.",
    ),
    _dev_entry(
        "certbot", "servers",
        "Certbot (HTTPS Let's Encrypt)", "Certbot (HTTPS Let's Encrypt)",
        "certbot + plugins apache/nginx (certificats gratuits)",
        "security-high-symbolic",
        packages=("certbot", "python3-certbot-apache", "python3-certbot-nginx"),
        note_fr="Certbot : « certbot --apache » ou « certbot --nginx » une fois le domaine pointé.",
        note_en="Certbot: “certbot --apache” or “certbot --nginx” once the domain points here.",
    ),
    _dev_entry(
        "cockpit", "panels",
        "Panneau web Cockpit", "Cockpit web panel",
        "cockpit + modules (paquets, stockage, réseau, Podman, VM), port 9090",
        "preferences-system-symbolic",
        check=lambda: _dev_rpm_ok("cockpit"),
        install=(COCKPIT_INSTALL,),
        update=("dnf upgrade -y --refresh cockpit cockpit-podman cockpit-machines",),
        remove=(COCKPIT_REMOVE,),
        launch=lambda: (open_uri("https://localhost:9090"), True)[1],
        launch_fr="Ouvre Cockpit (https://localhost:9090)",
        launch_en="Opens Cockpit (https://localhost:9090)",
        install_desc="cockpit + modules + systemctl enable --now cockpit.socket",
        update_desc="dnf upgrade cockpit cockpit-podman cockpit-machines",
        remove_desc="systemctl disable cockpit.socket + dnf remove cockpit*",
        note_fr="Cockpit : https://localhost:9090 (comptes système, port 9090 ouvert dans le pare-feu).",
        note_en="Cockpit: https://localhost:9090 (system accounts, port 9090 opened in the firewall).",
    ),
    _dev_entry(
        "phpmyadmin", "panels",
        "phpMyAdmin", "phpMyAdmin",
        "interface web MySQL/MariaDB (/phpMyAdmin), accès localhost",
        "web-browser-symbolic",
        check=lambda: _dev_rpm_ok("phpMyAdmin"),
        install=(PHPMYADMIN_INSTALL,),
        remove=("dnf remove -y phpMyAdmin || true",),
        launch=lambda: (open_uri("http://localhost/phpMyAdmin"), True)[1],
        launch_fr="Ouvre http://localhost/phpMyAdmin",
        launch_en="Opens http://localhost/phpMyAdmin",
        install_desc="dnf install phpMyAdmin + httpd + systemctl restart httpd",
        remove_desc="dnf remove phpMyAdmin",
        note_fr="phpMyAdmin est limité à localhost par défaut (/etc/httpd/conf.d/phpMyAdmin.conf).",
        note_en="phpMyAdmin is restricted to localhost by default (/etc/httpd/conf.d/phpMyAdmin.conf).",
    ),
    _dev_entry(
        "adminer", "panels",
        "Adminer", "Adminer",
        "un seul fichier PHP : /var/www/html/adminer.php",
        "web-browser-symbolic",
        check=_adminer_installed,
        install=(ADMINER_INSTALL,),
        update=(ADMINER_INSTALL,),
        remove=(ADMINER_REMOVE,),
        launch=lambda: (open_uri("http://localhost/adminer.php"), True)[1],
        launch_fr="Ouvre http://localhost/adminer.php",
        launch_en="Opens http://localhost/adminer.php",
        install_desc="curl https://www.adminer.org/latest.php → /var/www/html",
        update_desc="re-télécharge la dernière version",
        remove_desc="supprime /var/www/html/adminer.php",
        note_fr="Adminer : un seul fichier PHP dans /var/www/html/adminer.php.",
        note_en="Adminer: a single PHP file in /var/www/html/adminer.php.",
    ),
    _dev_entry(
        "webmin", "panels",
        "Webmin", "Webmin",
        "panneau d'administration complet (dépôt officiel), port 10000",
        "preferences-system-symbolic",
        check=lambda: _dev_rpm_ok("webmin"),
        install=(WEBMIN_INSTALL,),
        update=("dnf upgrade -y --refresh webmin && systemctl restart webmin",),
        remove=(WEBMIN_REMOVE,),
        launch=lambda: (open_uri("https://localhost:10000"), True)[1],
        launch_fr="Ouvre Webmin (https://localhost:10000)",
        launch_en="Opens Webmin (https://localhost:10000)",
        install_desc="dépôt webmin + dnf install webmin + systemctl enable --now webmin",
        update_desc="dnf upgrade webmin + systemctl restart webmin",
        remove_desc="systemctl disable webmin + dnf remove webmin + dépôt retiré",
        note_fr="Webmin écoute sur https://localhost:10000 ; crée un compte depuis l'interface.",
        note_en="Webmin listens on https://localhost:10000; create an account from its interface.",
    ),
    _dev_entry(
        "firewall-web", "network",
        "Pare-feu web (80 / 443 / 9090)", "Web firewall (80 / 443 / 9090)",
        "firewalld : ouvre http, https et console Cockpit",
        "security-medium-symbolic",
        check=_firewall_http_ok,
        install=(FIREWALL_HTTP,),
        update=(FIREWALL_HTTP,),
        remove=(FIREWALL_HTTP_REMOVE,),
        install_desc="firewall-cmd --add-service=http --add-service=https",
        update_desc="réapplique les services http/https",
        remove_desc="retire http et https de la zone par défaut",
        note_fr="Nécessaire pour accéder au serveur depuis une autre machine du réseau.",
        note_en="Required to reach the server from another machine on the network.",
    ),
    _dev_entry(
        "openssh", "network",
        "Serveur OpenSSH (accès distant)", "OpenSSH server (remote access)",
        "openssh-server + service (port 22)",
        "utilities-terminal-symbolic",
        packages=("openssh-server",),
        install=("systemctl enable --now sshd",),
        remove=("systemctl disable --now sshd 2>/dev/null || true",),
        note_fr="OpenSSH : sshd écoute sur le port 22 ; ouvre-le dans le pare-feu si nécessaire.",
        note_en="OpenSSH: sshd listens on port 22; open it in the firewall when needed.",
    ),
)


_DEV_PKG_CACHE: dict[str, bool] = {}
_DEV_PKG_CACHE_AT = 0.0
_DEV_CACHE_TTL = 30.0


def _dev_invalidate() -> None:
    global _DEV_PKG_CACHE_AT
    _DEV_PKG_CACHE_AT = 0.0


def _dev_installed_packages() -> set[str]:
    """Paquets RPM installés parmi ceux du catalogue (une seule requête rpm)."""
    global _DEV_PKG_CACHE_AT
    fresh = _DEV_PKG_CACHE and (time.monotonic() - _DEV_PKG_CACHE_AT) < _DEV_CACHE_TTL
    if fresh:
        return {name for name, ok in _DEV_PKG_CACHE.items() if ok}
    wanted = sorted(
        {pkg for entry in (*DEV_CATALOG, *WEB_CATALOG) for pkg in entry["packages"]}
    )
    installed: set[str] = set()
    if wanted:
        try:
            res = subprocess.run(
                ["rpm", "-q", "--queryformat", "%{NAME}\n", *wanted],
                capture_output=True, text=True, timeout=20,
            )
            installed = {line.strip() for line in (res.stdout or "").splitlines() if line.strip()}
        except (OSError, subprocess.SubprocessError):
            installed = set()
    _DEV_PKG_CACHE.clear()
    _DEV_PKG_CACHE.update({pkg: pkg in installed for pkg in wanted})
    _DEV_PKG_CACHE_AT = time.monotonic()
    return installed


def _dev_state(entry: dict[str, Any]) -> tuple[int, int]:
    check = entry["check"]
    if check is not None:
        try:
            return (1 if check() else 0), 1
        except Exception:  # noqa: BLE001 - une détection ne doit jamais bloquer la page
            return 0, 1
    packages = entry["packages"]
    if not packages:
        return 0, 0
    installed = _dev_installed_packages()
    return sum(1 for pkg in packages if pkg in installed), len(packages)


def _dev_desc(entry: dict[str, Any], action: str) -> str:
    override = entry.get(f"{action}_desc") or ""
    if override:
        return override
    packages = entry["packages"]
    if packages:
        return ", ".join(packages)
    generic = {
        "install": ("script d'installation intégré", "built-in install script"),
        "update": ("script de mise à jour intégré", "built-in update script"),
        "remove": ("script de désinstallation intégré", "built-in removal script"),
    }[action]
    return _L(*generic)


def _dev_execute(
    win: Ps5ManagerWindow, entry: dict[str, Any], action: str, emit: Callable[[str], None]
) -> tuple[bool, str]:
    """Exécute install / update / remove d'une entrée du catalogue."""
    codes: list[int] = []
    packages = list(entry["packages"])
    if packages:
        if action == "install":
            cmd = ["dnf", "install", "-y", *packages]
        elif action == "update":
            cmd = ["dnf", "upgrade", "-y", "--refresh", *packages]
        else:
            cmd = ["dnf", "remove", "-y", *packages]
        codes.append(win.run_cmd_pty(cmd, emit))
    for step in entry[action]:
        codes.append(win.run_cmd_pty(step.replace("__USER__", REAL_USER), emit))
    if not codes:
        return False, _L("Rien à faire pour cette entrée.", "Nothing to do for this entry.")
    failed = [code for code in codes if code != 0]
    if failed:
        return False, T("failed") % failed[0]
    return True, T("done")


def _push_dev_entry(
    win: Ps5ManagerWindow, entry: dict[str, Any], section: str = "dev"
) -> None:
    done, total = _dev_state(entry)
    title = _L(entry["title_fr"], entry["title_en"])
    if total > 1:
        status = f"{done}/{total} · {entry['sub']}"
    elif done:
        status = f"{T('installed_rpm')} · {entry['sub']}"
    else:
        status = f"{T('not_installed')} · {entry['sub']}"
    sub = Adw.PreferencesPage()
    grp = pref_group(title=title, description=status)

    def _run(action: str) -> None:
        label = {
            "install": (_L("Installer", "Install") + f" {title}"),
            "update": (_L("Mettre à jour", "Update") + f" {title}"),
            "remove": (_L("Désinstaller", "Uninstall") + f" {title}"),
        }[action]

        def _task(emit):
            return _dev_execute(win, entry, action, emit)

        def _after(*_):
            _dev_invalidate()
            win.nav.pop()
            win._select_section(section)

        win.run_task(label, _task, _after)

    grp.add(
        win.row(
            T("install"),
            _dev_desc(entry, "install"),
            "system-software-install-symbolic",
            lambda *_: _run("install"),
        )
    )
    grp.add(
        win.row(
            T("update"),
            _dev_desc(entry, "update"),
            "software-update-available-symbolic",
            lambda *_: (
                _run("update") if _dev_state(entry)[0] else win.show_info(title, T("not_installed"))
            ),
        )
    )
    launch = entry["launch"]
    if launch is not None and done:
        launch_desc = _L(entry["launch_fr"], entry["launch_en"]) if entry["launch_fr"] else ""

        def _do_launch():
            if not launch():
                win.show_info(title, _L(
                    "Lancement impossible : commande ou terminal introuvable.",
                    "Cannot launch: command or terminal not found.",
                ))

        grp.add(
            win.row(
                _L("Lancer", "Launch") + f" {title}",
                launch_desc,
                "media-playback-start-symbolic",
                lambda *_: _do_launch(),
            )
        )
    grp.add(
        win.row(
            T("remove"),
            _dev_desc(entry, "remove"),
            "user-trash-symbolic",
            lambda *_: (
                win.show_confirm(
                    _L("Désinstaller", "Uninstall") + f" {title}",
                    _L("Supprimer", "Remove") + f" {title} ?",
                    lambda: _run("remove"),
                )
                if _dev_state(entry)[0]
                else win.show_info(title, T("not_installed"))
            ),
        )
    )
    if entry["note_fr"]:
        grp.add(plain_row(Adw.ActionRow, title=_L(entry["note_fr"], entry["note_en"])))

    sub.add(grp)
    tb = Adw.ToolbarView()
    hb = Adw.HeaderBar()
    hb.set_title_widget(Adw.WindowTitle(title=title))
    tb.add_top_bar(hb)
    tb.set_content(sub)
    win.nav.push(Adw.NavigationPage(child=tb, title=title))


def _build_catalog_page(
    win: Ps5ManagerWindow,
    page: Adw.PreferencesPage,
    groups: tuple[tuple[str, str, str], ...],
    catalog: tuple[dict[str, Any], ...],
    section: str,
    notes: tuple[tuple[str, str], ...] = (),
) -> None:
    """Rend un catalogue (page Développement ou Serveur web)."""
    for gid, gfr, gen in groups:
        grp = pref_group(title=_L(gfr, gen), description="")
        for entry in catalog:
            if entry["group"] != gid:
                continue
            done, total = _dev_state(entry)
            subtitle = f"{done}/{total} · {entry['sub']}" if total else entry["sub"]
            panel = entry["panel"]
            if panel is not None:
                callback = (lambda *_, p=panel: p(win))
            else:
                callback = (lambda *_, e=entry: _push_dev_entry(win, e, section))
            grp.add(
                win.row(
                    _L(entry["title_fr"], entry["title_en"]),
                    subtitle,
                    entry["icon"],
                    callback,
                )
            )
        page.add(grp)
    intro = pref_group(
        title=_L("À propos de cette page", "About this page"),
        description=_L(
            "Installation, mise à jour et désinstallation par catégorie — tout est optionnel.",
            "Install, update and uninstall by category — everything is optional.",
        ),
    )
    for note_fr, note_en in notes:
        intro.add(plain_row(Adw.ActionRow, title=_L(note_fr, note_en)))
    page.add(intro)


def build_page_dev(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    _build_catalog_page(
        win, page, DEV_GROUPS, DEV_CATALOG, "dev",
        notes=(
            (
                "Les groupes docker, libvirt et kvm ne s'appliquent qu'après une reconnexion.",
                "The docker, libvirt and kvm groups only apply after signing in again.",
            ),
        ),
    )


def build_page_web(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    _build_catalog_page(
        win, page, WEB_GROUPS, WEB_CATALOG, "websrv",
        notes=(
            (
                "Apache et Nginx ne peuvent pas écouter le port 80 en même temps : garde un seul serveur actif.",
                "Apache and Nginx cannot listen on port 80 at the same time: keep a single server running.",
            ),
            (
                "Les groupes docker, libvirt et kvm ne s'appliquent qu'après une reconnexion.",
                "The docker, libvirt and kvm groups only apply after signing in again.",
            ),
        ),
    )


# ------------------------------------------------------------------------------
# Installation facile : profils pré-configurés (assistant + progression)
# Le setup 1 clic d'origine (_build_setup_plan / start_recommended_setup) n'est
# pas modifié : ces profils réutilisent son moteur d'étapes et sa fenêtre.
# ------------------------------------------------------------------------------
EASY_FIELDS: dict[str, dict[str, Any]] = {
    "server_name": {
        "fr": "Nom du serveur (ServerName)",
        "en": "Server name (ServerName)",
        "default": "localhost",
        "sanitize": "host",
    },
    "docroot": {
        "fr": "Dossier web (DocumentRoot)",
        "en": "Web root (DocumentRoot)",
        "default": "/var/www/html",
        "sanitize": "path",
    },
    "db_root_password": {
        "fr": "Mot de passe root MariaDB/MySQL (facultatif)",
        "en": "MariaDB/MySQL root password (optional)",
        "default": "",
        "secret": True,
    },
    "db_name": {
        "fr": "Base de données à créer (facultatif)",
        "en": "Database to create (optional)",
        "default": "app",
    },
    "db_user": {
        "fr": "Utilisateur de la base (facultatif)",
        "en": "Database user (optional)",
        "default": "appuser",
    },
    "db_password": {
        "fr": "Mot de passe de la base (facultatif)",
        "en": "Database password (optional)",
        "default": "",
        "secret": True,
    },
}

WEB_FIELDS = ("server_name", "docroot", "db_root_password", "db_name", "db_user", "db_password")

EASY_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "key": "lamp",
        "title_fr": "Serveur web LAMP",
        "title_en": "LAMP web server",
        "sub_fr": "Apache + PHP + MariaDB + phpMyAdmin, prêt à héberger un site",
        "sub_en": "Apache + PHP + MariaDB + phpMyAdmin, ready to host a site",
        "icon": "network-server-symbolic",
        "entries": (
            "apache", "php", "php-handler", "mariadb", "phpmyadmin", "adminer",
            "cockpit", "certbot", "firewall-web", "openssh",
        ),
        "defaults": ("apache", "php", "php-handler", "mariadb", "phpmyadmin", "firewall-web"),
        "fields": WEB_FIELDS,
        "config": "apache",
    },
    {
        "key": "lemp",
        "title_fr": "Serveur web LEMP",
        "title_en": "LEMP web server",
        "sub_fr": "Nginx + PHP-FPM + MariaDB, la variante légère",
        "sub_en": "Nginx + PHP-FPM + MariaDB, the lightweight variant",
        "icon": "network-server-symbolic",
        "entries": (
            "nginx", "php", "php-handler", "mariadb", "phpmyadmin", "adminer",
            "cockpit", "certbot", "firewall-web", "openssh",
        ),
        "defaults": ("nginx", "php", "php-handler", "mariadb", "phpmyadmin", "firewall-web"),
        "fields": WEB_FIELDS,
        "config": "nginx",
    },
    {
        "key": "code",
        "title_fr": "Code & outils",
        "title_en": "Code & tools",
        "sub_fr": "Compilation, Python + GTK4, outils CLI, qualité et debug",
        "sub_en": "Build tools, Python + GTK4, CLI tools, quality and debug",
        "icon": "applications-engineering-symbolic",
        "entries": (
            "build", "python-gtk", "cli-search", "git-tools", "terminal", "diag",
            "python-quality", "debug", "node", "rust", "docker", "virt",
            "github-desktop", "editors", "sqlite",
        ),
        "defaults": (
            "build", "python-gtk", "cli-search", "git-tools", "terminal", "diag",
            "python-quality",
        ),
        "fields": (),
        "config": "",
    },
    {
        "key": "services",
        "title_fr": "Conteneurs & services",
        "title_en": "Containers & services",
        "sub_fr": "Podman, Docker, Forgejo local, Cockpit, pare-feu et SSH",
        "sub_en": "Podman, Docker, local Forgejo, Cockpit, firewall and SSH",
        "icon": "application-x-executable-symbolic",
        "entries": ("containers", "docker", "forgejo", "cockpit", "firewall-web", "openssh"),
        "defaults": ("containers", "forgejo", "firewall-web"),
        "fields": (),
        "config": "",
    },
)


def _catalog_entry(key: str) -> Optional[dict[str, Any]]:
    for entry in (*DEV_CATALOG, *WEB_CATALOG):
        if entry["key"] == key:
            return entry
    return None


def _easy_host(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9.-]", "", value or "")
    return cleaned or "localhost"


def _easy_path(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9/._-]", "", value or "")
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned or "/var/www/html"


def _easy_ident(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "", value or "")


def _sql_literal(value: str) -> str:
    """Échappe une valeur pour un littéral SQL entre apostrophes."""
    cleaned = (value or "").replace("\r", " ").replace("\n", " ").strip()
    return cleaned.replace("\\", "\\\\").replace("'", "''")


def _easy_web_config(kind: str, server: str, docroot: str) -> str:
    """Hôte virtuel Apache ou Nginx + page de test PHP."""
    if kind == "apache":
        vhost = "\n".join([
            "cat > /etc/httpd/conf.d/ps5-easy.conf <<'CONF'",
            "<VirtualHost *:80>",
            f"    ServerName {server}",
            f'    DocumentRoot "{docroot}"',
            f'    <Directory "{docroot}">',
            "        AllowOverride All",
            "        Require all granted",
            "    </Directory>",
            "    ErrorLog /var/log/httpd/ps5-easy-error.log",
            "    CustomLog /var/log/httpd/ps5-easy-access.log combined",
            "</VirtualHost>",
            "CONF",
            "if httpd -t >/dev/null 2>&1; then",
            "  systemctl reload httpd 2>/dev/null || systemctl restart httpd 2>/dev/null || true",
            f'  echo "Apache : hôte virtuel prêt (http://{server})"',
            "else",
            '  echo "Apache : configuration refusée par httpd -t (voir /etc/httpd/conf.d/ps5-easy.conf)"',
            "fi",
        ])
    else:
        vhost = "\n".join([
            "mkdir -p /etc/nginx/conf.d",
            "cat > /etc/nginx/conf.d/ps5-easy.conf <<'CONF'",
            "server {",
            "    listen 80;",
            f"    server_name {server};",
            f'    root "{docroot}";',
            "    index index.php index.html;",
            "    location / { try_files $uri $uri/ =404; }",
            "}",
            "CONF",
            "if nginx -t >/dev/null 2>&1; then",
            "  systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true",
            f'  echo "Nginx : hôte virtuel prêt (http://{server})"',
            "else",
            '  echo "Nginx : configuration refusée par nginx -t (voir /etc/nginx/conf.d/ps5-easy.conf)"',
            "fi",
        ])
    return vhost


def _easy_db_sql(root_pw: str, db_name: str, db_user: str, db_pass: str) -> tuple[str, str]:
    """Retourne (SQL MariaDB, SQL MySQL) pour le mot de passe root et la base."""
    mariadb: list[str] = []
    mysql: list[str] = []
    if root_pw:
        mariadb.append(
            "ALTER USER 'root'@'localhost' IDENTIFIED VIA unix_socket "
            f"OR mysql_native_password USING PASSWORD('{root_pw}');"
        )
        mysql.append(
            f"ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '{root_pw}';"
        )
    if db_name:
        for statements in (mariadb, mysql):
            statements.append(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        if db_user:
            grant = f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost';"
            if db_pass:
                mariadb.insert(
                    -1,
                    f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' "
                    f"IDENTIFIED BY '{db_pass}';",
                )
                mysql.insert(
                    -1,
                    f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' "
                    f"IDENTIFIED BY '{db_pass}';",
                )
            else:
                mariadb.insert(-1, f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost';")
                mysql.insert(-1, f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost';")
            mariadb.append(grant)
            mysql.append(grant)
    if mariadb:
        mariadb.append("FLUSH PRIVILEGES;")
    if mysql:
        mysql.append("FLUSH PRIVILEGES;")
    return "\n".join(mariadb), "\n".join(mysql)


def _easy_config_script(
    profile: dict[str, Any], selected: tuple[str, ...], values: dict[str, str]
) -> str:
    """Script de configuration du profil (hôte virtuel + base de données)."""
    kind = profile.get("config") or ""
    if not kind:
        return ""
    server = _easy_host(values.get("server_name", "localhost"))
    docroot = _easy_path(values.get("docroot", "/var/www/html"))
    lines = [
        f'mkdir -p "{docroot}"',
        _easy_web_config(kind, server, docroot),
        f'cat > "{docroot}/index.php" <<\'PHP\'',
        '<?php echo "PS5 Fedora Manager : PHP fonctionne.\\n";',
        "PHP",
    ]
    lines.append(
        'if command -v semanage >/dev/null 2>&1 && command -v restorecon >/dev/null 2>&1; then\n'
        f'  semanage fcontext -a -t httpd_sys_content_t "{docroot}(/.*)?" 2>/dev/null || true\n'
        f'  restorecon -R "{docroot}" 2>/dev/null || true\n'
        "fi"
    )
    lines.append("setsebool -P httpd_can_network_connect_db on 2>/dev/null || true")

    mariadb_sql, mysql_sql = _easy_db_sql(
        _sql_literal(values.get("db_root_password", "")),
        _easy_ident(values.get("db_name", "")),
        _easy_ident(values.get("db_user", "")),
        _sql_literal(values.get("db_password", "")),
    )
    want_db = (
        ("mariadb" in selected or "mysql" in selected)
        and bool(mariadb_sql or mysql_sql)
    )
    if want_db and mariadb_sql:
        lines.extend([
            'if systemctl is-active --quiet mariadb 2>/dev/null; then',
            "  cat > /tmp/ps5-easy-db.sql <<'SQL'",
            mariadb_sql,
            "SQL",
            "  if mariadb -u root < /tmp/ps5-easy-db.sql; then",
            '    echo "MariaDB : configuration appliquée"',
            "  else",
            '    echo "MariaDB : configuration refusée (mot de passe root déjà défini ?)"',
            "  fi",
            "  rm -f /tmp/ps5-easy-db.sql",
            "fi",
        ])
    if want_db and mysql_sql:
        lines.extend([
            'if systemctl is-active --quiet mysqld 2>/dev/null; then',
            "  cat > /tmp/ps5-easy-db.sql <<'SQL'",
            mysql_sql,
            "SQL",
            "  if mysql -u root < /tmp/ps5-easy-db.sql; then",
            '    echo "MySQL : configuration appliquée"',
            "  else",
            '    echo "MySQL : configuration refusée (mot de passe root déjà défini ?)"',
            "  fi",
            "  rm -f /tmp/ps5-easy-db.sql",
            "fi",
        ])
    return "\n".join(lines) + "\n"


def _build_easy_plan(
    win: Ps5ManagerWindow,
    profile: dict[str, Any],
    selected: tuple[str, ...],
    values: dict[str, str],
) -> list[SetupStep]:
    """Transforme un profil en étapes exécutées par la fenêtre de progression."""
    steps: list[SetupStep] = []
    for key in profile["entries"]:
        if key not in selected:
            continue
        entry = _catalog_entry(key)
        if entry is None or entry["panel"] is not None:
            continue
        label = _L(entry["title_fr"], entry["title_en"])

        def _runner(emit, e=entry):
            ok, _msg = _dev_execute(win, e, "install", emit)
            return ok

        steps.append(SetupStep(label, [(label, _runner)]))
    config = _easy_config_script(profile, selected, values)
    if config:
        label = _L("Configuration du serveur", "Server configuration")
        steps.append(
            SetupStep(
                label,
                [(label, lambda emit, script=config: win.run_cmd_pty(script, emit) == 0)],
            )
        )
    return steps


class EasySetupWindow(SetupWindow):
    """Même fenêtre de progression que le setup 1 clic, sans redémarrage proposé."""

    def __init__(
        self, win: "Ps5ManagerWindow", plan: list[SetupStep], title: str, section: str
    ) -> None:
        self._easy_title = title
        self._easy_section = section
        super().__init__(win, plan)
        self.title_widget.set_title(title)
        self.connect("destroy", self._forget_window)

    def _forget_window(self, *_args) -> None:
        setattr(self.win, "easy_setup_window", None)

    def _finish(self) -> bool:
        self._running = False
        if self._flush_id is not None:
            GLib.source_remove(self._flush_id)
            self._flush_id = None
        self._flush()
        self.title_widget.set_subtitle(T("setup_finished"))
        self.progress.set_fraction(1.0)
        self.progress.set_text(T("setup_summary") % (self._done_count, self._fail_count))
        self.close_btn.set_sensitive(True)
        self.win.busy = False
        self.win.busy_spinner.stop()
        _dev_invalidate()
        self.close()
        try:
            self.win._select_section(self._easy_section)
        except Exception:  # noqa: BLE001 - la page se reconstruira au prochain affichage
            pass
        if self._fail_count:
            self.win.show_info(
                self._easy_title, T("setup_summary") % (self._done_count, self._fail_count)
            )
        else:
            self.win.toast(f"{self._easy_title} — {T('done')}")
        return False

    def _on_close_request(self, *_args) -> bool:
        return bool(self._running)


class EasySetupConfigWindow(Adw.Window):
    """Assistant : choix des composants, réglages, puis lancement."""

    def __init__(self, win: "Ps5ManagerWindow", profile: dict[str, Any]) -> None:
        title = _L(profile["title_fr"], profile["title_en"])
        super().__init__(
            transient_for=win, title=title, default_width=820, default_height=820
        )
        self.win = win
        self.profile = profile
        self.switches: dict[str, Adw.SwitchRow] = {}
        self.fields: dict[str, Any] = {}

        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title=title, subtitle=_L(profile["sub_fr"], profile["sub_en"]))
        )

        page = Adw.PreferencesPage()
        grp_comp = pref_group(
            title=_L("Composants à installer", "Components to install"),
            description=_L(
                "Décoche ce dont tu n'as pas besoin — rien n'est obligatoire.",
                "Uncheck what you don't need — nothing is mandatory.",
            ),
        )
        for key in profile["entries"]:
            entry = _catalog_entry(key)
            if entry is None:
                continue
            row = plain_row(
                Adw.SwitchRow,
                title=_L(entry["title_fr"], entry["title_en"]),
                subtitle=entry["sub"],
            )
            done, total = _dev_state(entry)
            if total and done == total:
                row.set_subtitle(f"{entry['sub']} · {T('installed_rpm')}")
            row.set_active(key in profile["defaults"])
            self.switches[key] = row
            grp_comp.add(row)
        page.add(grp_comp)

        if profile["fields"]:
            grp_cfg = pref_group(
                title=_L("Configuration", "Configuration"),
                description=_L(
                    "Utilisé pour l'hôte virtuel et la base de données.",
                    "Used for the virtual host and the database.",
                ),
            )
            for fkey in profile["fields"]:
                spec = EASY_FIELDS[fkey]
                label = _L(spec["fr"], spec["en"])
                password_row = getattr(Adw, "PasswordEntryRow", None)
                if spec.get("secret") and password_row is not None:
                    row = plain_row(password_row, title=label)
                else:
                    row = plain_row(Adw.EntryRow, title=label)
                row.set_text(spec.get("default", ""))
                self.fields[fkey] = row
                grp_cfg.add(row)
            page.add(grp_cfg)

        cancel_btn = Gtk.Button(label=T("cancel"))
        cancel_btn.connect("clicked", lambda *_: self.close())
        start_btn = Gtk.Button(label=_L("Installer la sélection", "Install selection"))
        start_btn.add_css_class("suggested-action")
        start_btn.connect("clicked", lambda *_: self._start())

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        bottom.set_halign(Gtk.Align.END)
        bottom.set_margin_top(10)
        bottom.set_margin_bottom(10)
        bottom.set_margin_start(12)
        bottom.set_margin_end(12)
        bottom.append(cancel_btn)
        bottom.append(start_btn)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(page)
        toolbar.add_bottom_bar(bottom)
        self.set_content(toolbar)

    def _start(self) -> None:
        selected = tuple(key for key, row in self.switches.items() if row.get_active())
        if not selected:
            self.win.show_info(
                _L(self.profile["title_fr"], self.profile["title_en"]),
                _L("Aucun composant sélectionné.", "No component selected."),
            )
            return
        values = {key: row.get_text() for key, row in self.fields.items()}
        self.close()
        _start_easy_setup(self.win, self.profile, selected, values)


def _start_easy_setup(
    win: "Ps5ManagerWindow",
    profile: dict[str, Any],
    selected: tuple[str, ...],
    values: dict[str, str],
) -> None:
    if win.busy:
        win.toast(T("busy"))
        return
    existing = getattr(win, "easy_setup_window", None)
    if existing is not None:
        existing.present()
        return
    plan = _build_easy_plan(win, profile, selected, values)
    if not plan:
        win.show_info(
            _L(profile["title_fr"], profile["title_en"]),
            _L("Aucun composant sélectionné.", "No component selected."),
        )
        return
    win.busy = True
    win.busy_spinner.start()
    window = EasySetupWindow(
        win, plan, _L(profile["title_fr"], profile["title_en"]), "easy"
    )
    setattr(win, "easy_setup_window", window)
    window.present()
    window.start()


def build_page_easy(win: Ps5ManagerWindow, page: Adw.PreferencesPage) -> None:
    grp = pref_group(
        title=T("sec_easy"),
        description=_L(
            "Choisis un profil, ajuste les composants et la configuration, puis lance l'installation.",
            "Pick a profile, adjust components and configuration, then start the install.",
        ),
    )
    for profile in EASY_PROFILES:
        title = _L(profile["title_fr"], profile["title_en"])
        grp.add(
            win.row(
                title,
                _L(profile["sub_fr"], profile["sub_en"]),
                profile["icon"],
                lambda *_, p=profile: EasySetupConfigWindow(win, p).present(),
            )
        )
    page.add(grp)

    info = pref_group(title=_L("Bon à savoir", "Good to know"), description="")
    info.add(
        plain_row(
            Adw.ActionRow,
            title=_L(
                "Le setup 1 clic d'origine (menu ⋮) reste inchangé.",
                "The original 1-click setup (⋮ menu) is unchanged.",
            ),
        )
    )
    info.add(
        plain_row(
            Adw.ActionRow,
            title=_L(
                "Les profils peuvent être relancés : ce qui est déjà installé est simplement mis à jour.",
                "Profiles can be run again: what is already installed is only updated.",
            ),
        )
    )
    page.add(info)


PAGE_BUILDERS = {
    "logs": build_page_logs,
    "library": build_page_library,
    "aidev": build_page_aidev,
    "dev": build_page_dev,
    "websrv": build_page_web,
    "easy": build_page_easy,
    "deps": build_page_deps,
    "gaming": build_page_gaming,
    "features": build_page_features,
    "update": build_page_update,
    "lang": build_page_lang,
    "repos": build_page_repos,
    "users": build_page_users,
    "fedora": build_page_fedora,
    "maint": build_page_maint,
    "power": build_page_power,
    "fan": build_page_fan,
    "hw": build_page_hw,
    "mesa": build_page_mesa,
    "kernel": build_page_kernel,
    "fix": build_page_fix,
    "ui_lang": build_page_ui_lang,
}


# ------------------------------------------------------------------------------
# Application
# ------------------------------------------------------------------------------
class Ps5ManagerApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self.theme_sync: Optional[SystemThemeSync] = None
        self.restart_on_exit: bool = False

    def do_activate(self) -> None:
        if self.theme_sync is None:
            self.theme_sync = SystemThemeSync()
            self.theme_sync.start()
        win = self.props.active_window
        if not win:
            win = Ps5ManagerWindow(self, self.theme_sync)
        win.present()
        win.maybe_show_welcome()


def main() -> int:
    warnings.simplefilter("ignore", DeprecationWarning)
    # Quitte /root (défini par pkexec) pour éviter tout EACCES lors des sous-processus utilisateur
    try:
        if os.getcwd() == "/root":
            os.chdir(INSTALL_DIR if os.path.isdir(INSTALL_DIR) else "/tmp")
    except OSError:
        pass
    for attr in ("NavigationSplitView", "NavigationView", "PreferencesPage", "ToolbarView"):
        if not hasattr(Adw, attr):
            sys.stderr.write(
                f"Adw.{attr} est absent : libadwaita 1.4+ requis (Fedora 39–45).\n"
            )
            return 1
    app = Ps5ManagerApp()
    rc = app.run(sys.argv)
    if app.restart_on_exit:
        target = (
            "/usr/local/bin/ps5-manager"
            if os.path.isfile("/usr/local/bin/ps5-manager")
            else os.path.abspath(sys.argv[0])
        )
        time.sleep(0.2)
        os.execv(sys.executable, [sys.executable, target, *sys.argv[1:]])
    return rc


if __name__ == "__main__":
    sys.exit(main())
