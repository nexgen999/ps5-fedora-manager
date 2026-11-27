#!/usr/bin/env bash
#@ id: dev-automation
#@ version: 1.0.0
#@ section: dev
#@ icon: system-run-symbolic
#@ title: Automation
#@ title_fr: Automatisation
#@ desc: just, direnv and shellcheck.
#@ desc_fr: just, direnv et shellcheck.
#@ packages: just direnv shellcheck
#@ root: yes
set -euo pipefail

PKGS=(just direnv shellcheck)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-automation…"
dnf install -y --skip-unavailable "${PKGS[@]}"
