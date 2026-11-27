#!/usr/bin/env bash
#@ id: dev-git-tools
#@ version: 1.0.0
#@ section: dev
#@ icon: git-symbolic
#@ title: Git & GitHub CLI
#@ title_fr: Git et GitHub CLI
#@ desc: git, git-lfs and the gh command line client.
#@ desc_fr: git, git-lfs et le client en ligne de commande gh.
#@ packages: git git-lfs gh
#@ root: yes
set -euo pipefail

PKGS=(git git-lfs gh)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-git-tools…"
dnf install -y --skip-unavailable "${PKGS[@]}"
