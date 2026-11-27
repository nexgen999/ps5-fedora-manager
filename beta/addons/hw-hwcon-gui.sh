#!/usr/bin/env bash
#@ id: hw-hwcon-gui
#@ version: 1.0.0
#@ section: hardware
#@ icon: applications-system-symbolic
#@ title: Hardware Control GUI
#@ title_fr: Hardware Control (interface)
#@ desc: PyQt6 interface for the PS5 fan and LED controller.
#@ desc_fr: Interface PyQt6 pour le contrôleur de ventilateur et de LED.
#@ check_paths: /opt/ps5-hwcon-gui/src/pyproject.toml
#@ root: yes
set -euo pipefail

INSTALLER="https://raw.githubusercontent.com/NotHavocc/ps5-hwcon-gui/main/install.sh"

if [ "${1:-}" = "--check" ]; then
    [ -f /opt/ps5-hwcon-gui/src/pyproject.toml ]
    exit $?
fi

echo "→ Installation de l'interface Hardware Control…"
dnf install -y --skip-unavailable python3-PyQt6
bash <(curl -fsSL "$INSTALLER") --passwordless
