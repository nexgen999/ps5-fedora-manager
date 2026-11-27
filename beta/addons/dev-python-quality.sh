#!/usr/bin/env bash
#@ id: dev-python-quality
#@ version: 1.0.0
#@ section: dev
#@ icon: text-x-python-symbolic
#@ title: Python quality
#@ title_fr: Qualité Python
#@ desc: uv, ruff, mypy and pre-commit.
#@ desc_fr: uv, ruff, mypy et pre-commit.
#@ packages: uv ruff mypy pre-commit
#@ root: yes
set -euo pipefail

PKGS=(uv ruff mypy pre-commit)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-python-quality…"
dnf install -y --skip-unavailable "${PKGS[@]}"
