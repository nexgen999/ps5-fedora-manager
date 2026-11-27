#!/usr/bin/env bash
#@ id: feature-toolbox
#@ version: 1.0.0
#@ section: features
#@ icon: utilities-terminal-symbolic
#@ title: Toolbox
#@ title_fr: Toolbox
#@ desc: Containerised development environments.
#@ desc_fr: Environnements de développement conteneurisés.
#@ packages: toolbox
#@ root: yes
set -euo pipefail

PKGS=(toolbox)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de feature-toolbox…"
dnf install -y --skip-unavailable "${PKGS[@]}"
