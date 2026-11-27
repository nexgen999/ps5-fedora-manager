#!/usr/bin/env bash
#@ id: audio-presets-jackhack
#@ version: 1.0.0
#@ section: audio
#@ icon: media-playlist-shuffle-symbolic
#@ title: Community presets (JackHack96)
#@ title_fr: Presets communautaires (JackHack96)
#@ desc: Ten ready-made presets installed in the desktop account.
#@ desc_fr: Dix presets prêts à l'emploi, installés dans le compte de bureau.
#@ check_paths: ~/.config/easyeffects/output
#@ needs: audio-easyeffects
#@ root: no
set -euo pipefail

DESKTOP_USER="${SUDO_USER:-$(id -un)}"
PRESETS_DIR="$HOME/.config/easyeffects/output"
INSTALLER="https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh"

if [ "${1:-}" = "--check" ]; then
    [ "$(id -u)" -eq 0 ] && PRESETS_DIR="/home/$DESKTOP_USER/.config/easyeffects/output"
    ls "$PRESETS_DIR"/*.json >/dev/null 2>&1
    exit $?
fi

echo "→ Installation des presets JackHack96 (option 1 : tout)…"
if [ "$(id -u)" -eq 0 ] && [ "$DESKTOP_USER" != root ]; then
    runuser -u "$DESKTOP_USER" -- bash -c \
        "printf '1\n' | bash <(curl -fsSL '$INSTALLER')"
else
    printf '1\n' | bash <(curl -fsSL "$INSTALLER")
fi
