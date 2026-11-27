#!/usr/bin/env bash
#@ id: dev-terminal
#@ version: 1.0.0
#@ section: dev
#@ icon: utilities-terminal-symbolic
#@ title: Terminal (tmux, zellij)
#@ title_fr: Terminal (tmux, zellij)
#@ desc: Terminal multiplexers for long sessions.
#@ desc_fr: Multiplexeurs de terminal pour les longues sessions.
#@ packages: tmux zellij
#@ root: yes
set -euo pipefail

PKGS=(tmux zellij)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-terminal…"
dnf install -y --skip-unavailable "${PKGS[@]}"
