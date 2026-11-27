#!/usr/bin/env bash
#@ id: deps-fuse
#@ version: 1.0.0
#@ section: deps
#@ icon: application-x-addon-symbolic
#@ title: FUSE stack
#@ title_fr: Pile FUSE
#@ desc: fusermount and libfuse for AppImages and Flatpak runtimes.
#@ desc_fr: fusermount et libfuse pour les AppImage et les runtimes Flatpak.
#@ packages: fuse fuse-libs
#@ root: yes
set -euo pipefail

PKGS=(fuse fuse-libs)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-fuse…"
dnf install -y --skip-unavailable "${PKGS[@]}"
