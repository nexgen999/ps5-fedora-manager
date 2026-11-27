#!/usr/bin/env bash
#@ id: app-fastfetch
#@ version: 1.0.0
#@ section: library
#@ icon: utilities-terminal-symbolic
#@ title: fastfetch
#@ title_fr: fastfetch
#@ desc: System information in one screen.
#@ desc_fr: Informations système en un écran.
#@ packages: fastfetch
#@ root: yes
set -euo pipefail

PKGS=(fastfetch)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de app-fastfetch…"
dnf install -y --skip-unavailable "${PKGS[@]}"
