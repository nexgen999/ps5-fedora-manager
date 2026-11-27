#!/usr/bin/env bash
#@ id: ai-python
#@ version: 1.0.0
#@ section: aidev
#@ icon: text-x-python-symbolic
#@ title: Python for AI
#@ title_fr: Python pour l'IA
#@ desc: Python, pip, venv and Jupyter for experiments.
#@ desc_fr: Python, pip, venv et Jupyter pour les expérimentations.
#@ packages: python3 python3-pip python3-virtualenv python3-notebook
#@ root: yes
set -euo pipefail

PKGS=(python3 python3-pip python3-virtualenv python3-notebook)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de ai-python…"
dnf install -y --skip-unavailable "${PKGS[@]}"
