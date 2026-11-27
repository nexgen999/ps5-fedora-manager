#!/usr/bin/env bash
#@ id: deps-tkinter
#@ version: 1.0.0
#@ section: deps
#@ icon: text-x-python-symbolic
#@ title: Python Tkinter
#@ title_fr: Python Tkinter
#@ desc: Tk bindings for Python GUI scripts.
#@ desc_fr: Bindings Tk pour les scripts Python à interface graphique.
#@ packages: python3-tkinter
#@ root: yes
set -euo pipefail

PKGS=(python3-tkinter)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de deps-tkinter…"
dnf install -y --skip-unavailable "${PKGS[@]}"
