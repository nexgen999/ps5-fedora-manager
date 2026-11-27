#!/usr/bin/env bash
#@ id: deps-build
#@ version: 1.0.0
#@ section: deps
#@ icon: application-x-addon-symbolic
#@ title: Build tools
#@ title_fr: Outils de compilation
#@ desc: gcc, make, kernel headers and dkms for out-of-tree modules.
#@ desc_fr: gcc, make, en-têtes du noyau et dkms pour les modules externes.
#@ packages: gcc gcc-c++ make kernel-devel dkms openssl-devel
#@ root: yes
set -euo pipefail

PKGS=(gcc gcc-c++ make kernel-devel dkms openssl-devel)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-build…"
dnf install -y --skip-unavailable "${PKGS[@]}"
