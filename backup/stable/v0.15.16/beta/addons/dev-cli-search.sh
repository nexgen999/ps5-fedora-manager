#!/usr/bin/env bash
#@ id: dev-cli-search
#@ version: 1.0.0
#@ section: dev
#@ icon: edit-find-symbolic
#@ title: Search & navigation
#@ title_fr: Recherche et navigation
#@ desc: ripgrep, fd, bat, eza, fzf and zoxide.
#@ desc_fr: ripgrep, fd, bat, eza, fzf et zoxide.
#@ packages: ripgrep fd-find bat eza fzf zoxide
#@ root: yes
set -euo pipefail

PKGS=(ripgrep fd-find bat eza fzf zoxide)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-cli-search…"
dnf install -y --skip-unavailable "${PKGS[@]}"
