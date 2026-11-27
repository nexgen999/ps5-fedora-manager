#!/usr/bin/env bash
#@ id: deps-32bit
#@ version: 1.0.0
#@ section: deps
#@ icon: video-display-symbolic
#@ title: 32-bit graphics stack
#@ title_fr: Bibliothèques graphiques 32 bits
#@ desc: Needed by Steam and 32-bit games on Fedora.
#@ desc_fr: Nécessaires à Steam et aux jeux 32 bits sous Fedora.
#@ packages: mesa-vulkan-drivers.i686 mesa-dri-drivers.i686 libva.i686
#@ root: yes
set -euo pipefail

PKGS=(mesa-vulkan-drivers.i686 mesa-dri-drivers.i686 libva.i686)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-32bit…"
dnf install -y --skip-unavailable "${PKGS[@]}"
