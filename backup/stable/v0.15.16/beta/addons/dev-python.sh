#!/usr/bin/env bash
#@ id: dev-python
#@ version: 1.0.0
#@ section: dev
#@ icon: text-x-python-symbolic
#@ title: Python development
#@ title_fr: Développement Python
#@ desc: Headers, debugger and linting tools for Python.
#@ desc_fr: En-têtes, débogueur et outils de vérification pour Python.
#@ packages: python3-devel python3-debugpy python3-flake8 python3-black
#@ root: yes
set -euo pipefail

PKGS=(python3-devel python3-debugpy python3-flake8 python3-black)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-python…"
dnf install -y --skip-unavailable "${PKGS[@]}"
