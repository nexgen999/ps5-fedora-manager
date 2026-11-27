#!/usr/bin/env bash
#@ id: lang-ja
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: Japanese language pack
#@ title_fr: Paquet de langue Japonais
#@ desc: Japanese translations for the system and applications.
#@ desc_fr: Traductions Japonais pour le système et les applications.
#@ packages: langpacks-ja
#@ root: yes
set -euo pipefail

PKGS=(langpacks-ja)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-ja…"
dnf install -y --skip-unavailable "${PKGS[@]}"
