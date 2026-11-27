#!/usr/bin/env bash
#@ id: power-profiles
#@ version: 1.0.0
#@ section: power
#@ icon: preferences-system-power-symbolic
#@ title: Power profiles
#@ title_fr: Profils d'alimentation
#@ desc: Balanced, performance and power-saver profiles.
#@ desc_fr: Profils équilibré, performance et économie d'énergie.
#@ packages: power-profiles-daemon
#@ root: yes
set -euo pipefail

PKGS=(power-profiles-daemon)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de power-profiles…"
dnf install -y --skip-unavailable "${PKGS[@]}"
