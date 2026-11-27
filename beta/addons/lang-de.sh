#!/usr/bin/env bash
#@ id: lang-de
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: German language pack
#@ title_fr: Paquet de langue Allemand
#@ desc: German translations for the system and applications.
#@ desc_fr: Traductions Allemand pour le système et les applications.
#@ packages: langpacks-de
#@ root: yes
set -euo pipefail

PKGS=(langpacks-de)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-de…"
dnf install -y --skip-unavailable "${PKGS[@]}"
