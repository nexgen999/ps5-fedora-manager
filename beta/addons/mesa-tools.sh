#!/usr/bin/env bash
#@ id: mesa-tools
#@ version: 1.0.0
#@ section: mesa
#@ icon: video-display-symbolic
#@ title: Mesa diagnostic tools
#@ title_fr: Outils de diagnostic Mesa
#@ desc: glxinfo, eglinfo and the Mesa demos.
#@ desc_fr: glxinfo, eglinfo et les démos Mesa.
#@ packages: mesa-demos
#@ root: yes
set -euo pipefail

PKGS=(mesa-demos)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de mesa-tools…"
dnf install -y --skip-unavailable "${PKGS[@]}"
