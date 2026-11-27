#!/usr/bin/env bash
#@ id: lang-fr
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: French language pack
#@ title_fr: Paquet de langue Français
#@ desc: French translations for the system and applications.
#@ desc_fr: Traductions Français pour le système et les applications.
#@ packages: langpacks-fr
#@ root: yes
set -euo pipefail

PKGS=(langpacks-fr)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-fr…"
dnf install -y --skip-unavailable "${PKGS[@]}"
