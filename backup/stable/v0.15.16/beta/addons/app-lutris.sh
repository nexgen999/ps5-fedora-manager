#!/usr/bin/env bash
#@ id: app-lutris
#@ version: 1.0.0
#@ section: library
#@ icon: applications-games-symbolic
#@ title: Lutris
#@ title_fr: Lutris
#@ desc: Game manager for Windows and emulated titles.
#@ desc_fr: Gestionnaire de jeux Windows et émulés.
#@ packages: lutris
#@ needs: repo-rpmfusion
#@ root: yes
set -euo pipefail

PKGS=(lutris)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de app-lutris…"
dnf install -y --skip-unavailable "${PKGS[@]}"
