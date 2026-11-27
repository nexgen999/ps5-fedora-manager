#!/usr/bin/env bash
#@ id: fan-tools
#@ version: 1.0.0
#@ section: fan
#@ icon: weather-windy-symbolic
#@ title: PS5 fan control
#@ title_fr: Contrôle du ventilateur PS5
#@ desc: Fan curve and temperature service for the PS5.
#@ desc_fr: Courbe de ventilation et service de température pour la PS5.
#@ check_paths: /usr/local/sbin/ps5_control /usr/lib/systemd/system/ps5fan.service
#@ root: yes
set -euo pipefail

PKGS=()

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de fan-tools…"
dnf install -y --skip-unavailable "${PKGS[@]}"
