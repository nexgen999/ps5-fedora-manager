#!/usr/bin/env bash
#@ id: feature-mobile
#@ version: 1.0.0
#@ section: features
#@ icon: phone-symbolic
#@ title: Phone integration
#@ title_fr: Intégration du téléphone
#@ desc: GSConnect extension for notifications and file transfer.
#@ desc_fr: Extension GSConnect pour les notifications et le transfert de fichiers.
#@ packages: gnome-shell-extension-gsconnect nautilus-gsconnect
#@ root: yes
set -euo pipefail

PKGS=(gnome-shell-extension-gsconnect nautilus-gsconnect)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de feature-mobile…"
dnf install -y --skip-unavailable "${PKGS[@]}"
