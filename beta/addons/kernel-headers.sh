#!/usr/bin/env bash
#@ id: kernel-headers
#@ version: 1.0.0
#@ section: kernel
#@ icon: drive-harddisk-symbolic
#@ title: Kernel headers
#@ title_fr: En-têtes du noyau
#@ desc: Headers matching the running kernel, for module builds.
#@ desc_fr: En-têtes correspondant au noyau courant, pour compiler des modules.
#@ packages: kernel-headers kernel-devel
#@ root: yes
set -euo pipefail

PKGS=(kernel-headers kernel-devel)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de kernel-headers…"
dnf install -y --skip-unavailable "${PKGS[@]}"
