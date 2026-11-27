#!/usr/bin/env bash
#@ id: hw-decky-loader
#@ version: 1.0.0
#@ section: hardware
#@ icon: applications-games-symbolic
#@ title: Decky Loader
#@ title_fr: Decky Loader
#@ desc: Plugin loader used by the PS5 Hardware Control plugin.
#@ desc_fr: Chargeur de plugins utilisé par le plugin PS5 Hardware Control.
#@ check_paths: ~/homebrew
#@ root: no
set -euo pipefail

DESKTOP_USER="${SUDO_USER:-$(id -un)}"
INSTALLER="https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/install_release.sh"

if [ "${1:-}" = "--check" ]; then
    [ -d "/home/$DESKTOP_USER/homebrew" ] || [ -d "$HOME/homebrew" ]
    exit $?
fi

echo "→ Installation de Decky Loader…"
if [ "$(id -u)" -eq 0 ] && [ "$DESKTOP_USER" != root ]; then
    runuser -u "$DESKTOP_USER" -- bash -c "curl -fsSL '$INSTALLER' | bash"
else
    curl -fsSL "$INSTALLER" | bash
fi
