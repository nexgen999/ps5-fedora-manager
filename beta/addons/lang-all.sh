#!/usr/bin/env bash
#@ id: lang-all
#@ version: 1.0.0
#@ section: lang
#@ icon: preferences-desktop-locale-symbolic
#@ title: Install every language pack
#@ title_fr: Installer tous les paquets de langue
#@ desc: fr, en, es, it, de, pt, ja, zh and ru.
#@ desc_fr: fr, en, es, it, de, pt, ja, zh et ru.
#@ packages: langpacks-fr langpacks-es langpacks-it langpacks-de langpacks-pt langpacks-ja langpacks-zh_CN langpacks-ru
#@ root: yes
set -euo pipefail

PKGS=(langpacks-fr langpacks-es langpacks-it langpacks-de langpacks-pt langpacks-ja langpacks-zh_CN langpacks-ru)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de lang-all…"
dnf install -y --skip-unavailable "${PKGS[@]}"
