#!/usr/bin/env bash
#@ id: web-db
#@ version: 1.0.0
#@ section: websrv
#@ icon: network-server-symbolic
#@ title: MariaDB
#@ title_fr: MariaDB
#@ desc: Database server for web applications.
#@ desc_fr: Serveur de base de données pour les applications web.
#@ packages: mariadb-server
#@ root: yes
set -euo pipefail

PKGS=(mariadb-server)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de web-db…"
dnf install -y --skip-unavailable "${PKGS[@]}"
