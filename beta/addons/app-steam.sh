#!/usr/bin/env bash
#@ id: app-steam
#@ version: 1.0.0
#@ section: library
#@ icon: applications-games-symbolic
#@ title: Steam
#@ title_fr: Steam
#@ desc: Steam client from RPM Fusion.
#@ desc_fr: Client Steam depuis RPM Fusion.
#@ packages: steam
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(steam)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de app-steam…"
dnf install -y --skip-unavailable "${PKGS[@]}"
