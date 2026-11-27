#!/usr/bin/env bash
#@ id: lang-it
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: Italian language pack
#@ title_fr: Paquet de langue Italien
#@ desc: Italian translations for the system and applications.
#@ desc_fr: Traductions Italien pour le système et les applications.
#@ packages: langpacks-it
#@ root: yes
set -euo pipefail

PKGS=(langpacks-it)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-it…"
dnf install -y --skip-unavailable "${PKGS[@]}"
