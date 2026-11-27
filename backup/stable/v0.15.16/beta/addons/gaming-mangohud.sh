#!/usr/bin/env bash
#@ id: gaming-mangohud
#@ version: 1.0.0
#@ section: gaming
#@ icon: applications-games-symbolic
#@ title: MangoHud
#@ title_fr: MangoHud
#@ desc: FPS, temperatures and frame-time overlay.
#@ desc_fr: Surcouche FPS, températures et temps de frame.
#@ packages: mangohud
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(mangohud)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de gaming-mangohud…"
dnf install -y --skip-unavailable "${PKGS[@]}"
