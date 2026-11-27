#!/usr/bin/env bash
#@ id: gaming-gamescope
#@ version: 1.0.0
#@ section: gaming
#@ icon: applications-games-symbolic
#@ title: Gamescope + MangoHud
#@ title_fr: Gamescope + MangoHud
#@ desc: Micro-compositor for full-screen games and a performance overlay.
#@ desc_fr: Micro-compositeur pour jeux en plein écran et surcouche de performance.
#@ packages: gamescope mangohud
#@ root: yes
set -euo pipefail

PKGS=(gamescope mangohud)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de Gamescope et MangoHud…"
dnf install -y --skip-unavailable "${PKGS[@]}"
