#!/usr/bin/env bash
#@ id: dev-git-tools
#@ version: 1.1.0
#@ section: dev
#@ icon: git-symbolic
#@ title: Git & platforms
#@ title_fr: Git et plateformes
#@ desc: Git, git-lfs, GitHub/GitLab CLIs, lazygit and git-delta.
#@ desc_fr: Git, git-lfs, CLI GitHub/GitLab, lazygit et git-delta.
#@ packages: git git-lfs gh glab lazygit git-delta
#@ root: yes
set -euo pipefail

PKGS=(git git-lfs gh glab lazygit git-delta)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-git-tools…"
dnf install -y --skip-unavailable "${PKGS[@]}"
