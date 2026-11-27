#!/usr/bin/env bash
#@ id: lang-pt
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: Portuguese language pack
#@ title_fr: Paquet de langue Portugais
#@ desc: Portuguese translations for the system and applications.
#@ desc_fr: Traductions Portugais pour le système et les applications.
#@ packages: langpacks-pt
#@ root: yes
set -euo pipefail

PKGS=(langpacks-pt)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-pt…"
dnf install -y --skip-unavailable "${PKGS[@]}"
