#!/usr/bin/env bash
#@ id: dev-editors
#@ version: 1.0.0
#@ section: dev
#@ icon: accessories-text-editor-symbolic
#@ title: Terminal editors
#@ title_fr: Éditeurs en terminal
#@ desc: Neovim and Helix.
#@ desc_fr: Neovim et Helix.
#@ packages: neovim helix
#@ root: yes
set -euo pipefail

PKGS=(neovim helix)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-editors…"
dnf install -y --skip-unavailable "${PKGS[@]}"
