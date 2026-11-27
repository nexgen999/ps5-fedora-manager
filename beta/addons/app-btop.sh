#!/usr/bin/env bash
#@ id: app-btop
#@ version: 1.0.0
#@ section: library
#@ icon: utilities-system-monitor-symbolic
#@ title: btop
#@ title_fr: btop
#@ desc: Resource monitor for the terminal.
#@ desc_fr: Moniteur de ressources en terminal.
#@ packages: btop
#@ root: yes
set -euo pipefail

PKGS=(btop)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de app-btop…"
dnf install -y --skip-unavailable "${PKGS[@]}"
