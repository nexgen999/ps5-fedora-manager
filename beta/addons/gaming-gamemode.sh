#!/usr/bin/env bash
#@ id: gaming-gamemode
#@ version: 1.0.0
#@ section: gaming
#@ icon: applications-games-symbolic
#@ title: GameMode
#@ title_fr: GameMode
#@ desc: Temporary performance tuning while a game runs.
#@ desc_fr: Réglages de performance temporaires pendant un jeu.
#@ packages: gamemode
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(gamemode)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de gaming-gamemode…"
dnf install -y --skip-unavailable "${PKGS[@]}"
