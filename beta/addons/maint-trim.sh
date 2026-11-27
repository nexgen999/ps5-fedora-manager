#!/usr/bin/env bash
#@ id: maint-trim
#@ version: 1.0.0
#@ section: maint
#@ icon: drive-harddisk-symbolic
#@ title: SSD trim
#@ title_fr: TRIM du SSD
#@ desc: Weekly TRIM timer for the internal drive.
#@ desc_fr: Minuterie TRIM hebdomadaire pour le disque interne.
#@ packages: util-linux
#@ root: yes
set -euo pipefail

PKGS=(util-linux)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de maint-trim…"
dnf install -y --skip-unavailable "${PKGS[@]}"
