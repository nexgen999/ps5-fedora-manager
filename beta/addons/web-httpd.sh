#!/usr/bin/env bash
#@ id: web-httpd
#@ version: 1.0.0
#@ section: websrv
#@ icon: network-server-symbolic
#@ title: Apache httpd + PHP
#@ title_fr: Apache httpd + PHP
#@ desc: Apache web server with the PHP module.
#@ desc_fr: Serveur web Apache avec le module PHP.
#@ packages: httpd php php-mysqlnd
#@ root: yes
set -euo pipefail

PKGS=(httpd php php-mysqlnd)

if [ "${1:-}" = "--check" ]; then
    rpm -q "${PKGS[@]}" >/dev/null 2>&1 && exit 0
    exit 1
fi

echo "→ Installation de web-httpd…"
dnf install -y --skip-unavailable "${PKGS[@]}"
