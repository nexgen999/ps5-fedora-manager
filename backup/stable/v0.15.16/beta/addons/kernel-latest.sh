#!/usr/bin/env bash
#@ id: kernel-latest
#@ version: 1.0.0
#@ section: kernel
#@ icon: drive-harddisk-symbolic
#@ title: Latest kernel
#@ title_fr: Noyau le plus récent
#@ desc: Installs and reports the newest kernel available.
#@ desc_fr: Installe et indique le noyau le plus récent disponible.
#@ packages: kernel
#@ root: yes
set -euo pipefail

PKGS=(kernel)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de kernel-latest…"
dnf install -y --skip-unavailable "${PKGS[@]}"
