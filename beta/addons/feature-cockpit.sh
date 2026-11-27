#!/usr/bin/env bash
#@ id: feature-cockpit
#@ version: 1.0.0
#@ section: features
#@ icon: network-server-symbolic
#@ title: Cockpit
#@ title_fr: Cockpit
#@ desc: Web console for services, logs and storage.
#@ desc_fr: Console web pour les services, journaux et stockage.
#@ packages: cockpit cockpit-storaged cockpit-networkmanager
#@ root: yes
set -euo pipefail

PKGS=(cockpit cockpit-storaged cockpit-networkmanager)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de feature-cockpit…"
dnf install -y --skip-unavailable "${PKGS[@]}"
