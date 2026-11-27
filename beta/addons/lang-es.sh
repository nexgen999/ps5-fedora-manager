#!/usr/bin/env bash
#@ id: lang-es
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: Spanish language pack
#@ title_fr: Paquet de langue Espagnol
#@ desc: Spanish translations for the system and applications.
#@ desc_fr: Traductions Espagnol pour le système et les applications.
#@ packages: langpacks-es
#@ root: yes
set -euo pipefail

PKGS=(langpacks-es)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-es…"
dnf install -y --skip-unavailable "${PKGS[@]}"
