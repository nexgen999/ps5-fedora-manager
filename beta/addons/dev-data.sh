#!/usr/bin/env bash
#@ id: dev-data
#@ version: 1.0.0
#@ section: dev
#@ icon: applications-utilities-symbolic
#@ title: JSON & HTTP
#@ title_fr: JSON et HTTP
#@ desc: jq, yq, httpie, SQLite and its browser.
#@ desc_fr: jq, yq, httpie, SQLite et son navigateur.
#@ packages: jq yq httpie sqlite sqlitebrowser
#@ root: yes
set -euo pipefail

PKGS=(jq yq httpie sqlite sqlitebrowser)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de dev-data…"
dnf install -y --skip-unavailable "${PKGS[@]}"
