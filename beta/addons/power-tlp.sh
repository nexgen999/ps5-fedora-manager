#!/usr/bin/env bash
#@ id: power-tlp
#@ version: 1.0.0
#@ section: power
#@ icon: battery-good-symbolic
#@ title: TLP
#@ title_fr: TLP
#@ desc: Advanced power management for laptops and handhelds.
#@ desc_fr: Gestion avancée de l'énergie pour portables et consoles portables.
#@ packages: tlp tlp-rdw
#@ root: yes
set -euo pipefail

PKGS=(tlp tlp-rdw)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de power-tlp…"
dnf install -y --skip-unavailable "${PKGS[@]}"
