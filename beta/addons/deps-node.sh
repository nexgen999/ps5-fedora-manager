#!/usr/bin/env bash
#@ id: deps-node
#@ version: 1.0.0
#@ section: deps
#@ icon: text-x-script-symbolic
#@ title: Node.js and npm
#@ title_fr: Node.js et npm
#@ desc: JavaScript runtime and package manager.
#@ desc_fr: Environnement JavaScript et gestionnaire de paquets.
#@ packages: nodejs npm
#@ root: yes
set -euo pipefail

PKGS=(nodejs npm)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-node…"
dnf install -y --skip-unavailable "${PKGS[@]}"
