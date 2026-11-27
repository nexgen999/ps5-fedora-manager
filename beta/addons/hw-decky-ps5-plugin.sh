#!/usr/bin/env bash
#@ id: hw-decky-ps5-plugin
#@ version: 1.0.0
#@ section: hardware
#@ icon: applications-system-symbolic
#@ title: PS5 Hardware Control plugin
#@ title_fr: Plugin PS5 Hardware Control
#@ desc: Decky plugin to control the PS5 fan and LEDs.
#@ desc_fr: Plugin Decky pour piloter le ventilateur et les LED de la PS5.
#@ check_paths: ~/homebrew/plugins/ps5-hardware-control /home/*/homebrew/plugins/ps5-hardware-control
#@ needs: hw-decky-loader
#@ root: no
set -euo pipefail

DESKTOP_USER="${SUDO_USER:-$(id -un)}"
INSTALLER="https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-plugin/main/install.sh"

if [ "${1:-}" = "--check" ]; then
    for base in "/home/$DESKTOP_USER/homebrew/plugins" "$HOME/homebrew/plugins" /home/*/homebrew/plugins; do
        [ -d "$base" ] || continue
        ls "$base" 2>/dev/null | grep -qiE 'ps5-hardware-control|ps5-hwcon|hwcon' && exit 0
    done
    exit 1
fi

echo "→ Installation du plugin PS5 Hardware Control…"
if [ "$(id -u)" -eq 0 ] && [ "$DESKTOP_USER" != root ]; then
    runuser -u "$DESKTOP_USER" -- bash -c "curl -fsSL '$INSTALLER' | bash"
else
    curl -fsSL "$INSTALLER" | bash
fi
